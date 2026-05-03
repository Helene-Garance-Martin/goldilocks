# src/diagram_builder.py
# ------------------------------------------------------------
# GOLDILOCKS — Diagram Builder
# Builds Mermaid diagram syntax from pipeline data
# ------------------------------------------------------------

import sys
import os
import re
sys.path.insert(0, os.path.dirname(__file__))

from snap_resolver import (
    SNAP_SHAPES, CLASSDEFS,
    resolve_snap_type, get_icon
)

# ------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------

STYLED_TYPES = {
    "httpclient", "script", "pipeexec",
    "sftp_get", "sftp_put", "mapper",
    "filter", "trigger"
}

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

safe_id        = lambda snap_id: "n" + snap_id.replace("-", "_")[:8]
safe_file_name = lambda name: re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_")


# ------------------------------------------------------------
# LABEL FORMATTER
# ------------------------------------------------------------

def format_label(label: str, snap_type: str) -> str:
    tag   = get_icon(snap_type)
    words = label.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > 28:
            if current:
                lines.append(current.strip())
            current = word
        else:
            current += " " + word
    if current:
        lines.append(current.strip())
    formatted = "<br/>".join(lines)
    return f"{tag}<br/>{formatted}"


# ------------------------------------------------------------
# BUILD DIAGRAM
# ------------------------------------------------------------

def build_pipeline_diagram(pipelines: list, direction: str = "LR") -> str:
    """
    Build a complete Mermaid diagram from pipeline data.
    Each pipeline becomes a subgraph.
    Parent/child relationships shown between subgraphs.
    """
    lines = []
    lines.append("%%{init: {'theme': 'base', 'flowchart': {'nodeSpacing': 50, 'rankSpacing': 80, 'padding': 16}, 'themeVariables': {'clusterBkg': '#FAFAFA', 'clusterBorder': '#CCCCCC'}}}%%")
    lines.append(f"flowchart {direction}")
    lines.append("")

    all_snap_types    = {}
    pipeline_node_ids = {}

    for pipeline in pipelines:
        pipeline_name = pipeline.get("name", "Unknown")
        snap_map      = pipeline.get("snap_map", {})
        link_map      = pipeline.get("link_map", {})

        p_safe_id = "p_" + safe_file_name(pipeline_name)[:16]
        pipeline_node_ids[pipeline_name] = p_safe_id

        lines.append(f"    subgraph {p_safe_id}[\"{pipeline_name}\"]")
        lines.append(f"        direction {direction}")
        lines.append("")

        # ── Snap nodes ────────────────────────────────────
        for snap_id, snap in snap_map.items():
            try:
                label = snap["property_map"]["info"]["label"]["value"]
            except (KeyError, TypeError):
                label = snap_id

            class_id  = snap.get("class_id", "unknown")
            snap_type = resolve_snap_type(class_id)
            node_id   = safe_id(snap_id)
            formatted = format_label(label, snap_type)

            shape_open, shape_close = SNAP_SHAPES.get(snap_type, SNAP_SHAPES["default"])
            lines.append(f"        {node_id}{shape_open}{formatted}{shape_close}")
            all_snap_types[node_id] = snap_type

        lines.append("")

        # ── Snap connections ── list comprehension ────────
        lines += [
            f"        {safe_id(link['src_id'])} --> {safe_id(link['dst_id'])}"
            for link in link_map.values()
        ]

        lines.append("    end")
        lines.append("")

    # ── Parent/child CALLS relationships ──────────────────
    for pipeline in pipelines:
        pipeline_name = pipeline.get("name", "")
        snap_map      = pipeline.get("snap_map", {})
        p_safe_id     = pipeline_node_ids.get(pipeline_name, "")

        for snap_id, snap in snap_map.items():
            snap_type = resolve_snap_type(snap.get("class_id", ""))
            if snap_type == "pipeexec":
                try:
                    child_name = snap["property_map"]["settings"]["pipeline"]["value"]
                    for other in pipelines:
                        other_name = other.get("name", "")
                        if child_name in other_name or other_name in child_name:
                            child_safe_id = pipeline_node_ids.get(other_name, "")
                            if child_safe_id and child_safe_id != p_safe_id:
                                lines.append(f"    {p_safe_id} -.->|CALLS| {child_safe_id}")
                except (KeyError, TypeError):
                    pass

    lines.append("")
    lines.append(CLASSDEFS)
    lines.append("")

    # ── Assign classDefs ── list comprehension ─────────────
    lines += [
        f"    class {node_id} {'default' if snap_type not in STYLED_TYPES else snap_type}"
        for node_id, snap_type in all_snap_types.items()
    ]

    return "\n".join(lines)