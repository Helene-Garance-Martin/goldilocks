# src/diagram_builder.py
# ------------------------------------------------------------
# GOLDILOCKS — Diagram Builder
# Builds Mermaid diagram syntax from pipeline data
# ------------------------------------------------------------

import sys
import os
import re

sys.path.insert(0, os.path.dirname(__file__))

from snap_resolver import resolve_snap_type, get_icon
from mermaid_styles import NODE_SHAPES as SNAP_SHAPES, CLASSDEFS


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

safe_id = lambda snap_id: "n" + snap_id.replace("-", "_")[:8]

safe_file_name = lambda name: re.sub(
    r"[^a-zA-Z0-9_]+",
    "_",
    name
).strip("_")


# ------------------------------------------------------------
# LABEL FORMATTER
# ------------------------------------------------------------

def format_label(label: str, snap_type: str) -> str:
    """
    Format Mermaid labels with icons + line wrapping.
    """

    tag = get_icon(snap_type)

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
# PIPELINE DISPLAY ORDER
# ------------------------------------------------------------

def sort_pipelines_for_display(pipelines: list) -> list:
    """
    Put parent/orchestrator pipelines first,
    then child/detail pipelines.

    Parent pipelines are detected via Pipeline Execute snaps.
    """

    def has_child_call(pipeline: dict) -> bool:

        snap_map = pipeline.get("snap_map", {})

        return any(
            resolve_snap_type(
                snap.get("class_id", "")
            ) == "pipeexec"

            for snap in snap_map.values()
        )

    return sorted(
        pipelines,
        key=lambda p: (
            not has_child_call(p),     # parents first
            p.get("name", "").lower()
        )
    )


# ------------------------------------------------------------
# BUILD DIAGRAM
# ------------------------------------------------------------

def build_pipeline_diagram(
    pipelines: list,
    direction: str = "LR"
) -> str:
    """
    Build a complete Mermaid diagram from pipeline data.

    Each pipeline becomes a subgraph.
    Parent/child relationships shown between subgraphs.
    """

    lines = []

    lines.append(
        "%%{init: {'theme': 'base', "
        "'flowchart': {'nodeSpacing': 50, "
        "'rankSpacing': 80, 'padding': 16}, "
        "'themeVariables': {"
        "'clusterBkg': '#FAFAFA', "
        "'clusterBorder': '#CCCCCC'}}}%%"
    )

    lines.append(f"flowchart {direction}")
    lines.append("")

    all_snap_types = {}
    pipeline_node_ids = {}

    # --------------------------------------------------------
    # Sort pipelines so orchestrators appear first
    # --------------------------------------------------------

    pipelines = sort_pipelines_for_display(pipelines)

    # --------------------------------------------------------
    # Render each pipeline subgraph
    # --------------------------------------------------------

    for pipeline in pipelines:

        pipeline_name = pipeline.get("name", "Unknown")

        snap_map = pipeline.get("snap_map", {})
        link_map = pipeline.get("link_map", {})

        p_safe_id = "p_" + safe_file_name(
            pipeline_name
        )[:16]

        pipeline_node_ids[pipeline_name] = p_safe_id

        lines.append(
            f'    subgraph {p_safe_id}["{pipeline_name}"]'
        )

        lines.append(f"        direction {direction}")
        lines.append("")

        # ----------------------------------------------------
        # Snap nodes
        # ----------------------------------------------------

        for snap_id, snap in snap_map.items():

            try:
                label = snap["property_map"]["info"]["label"]["value"]

            except (KeyError, TypeError):
                label = snap_id

            class_id = snap.get("class_id", "unknown")

            snap_type = resolve_snap_type(class_id)

            node_id = safe_id(snap_id)

            formatted = format_label(
                label,
                snap_type
            )

            shape = SNAP_SHAPES.get(
                snap_type,
                SNAP_SHAPES["default"]
            )

            node_str = shape.replace(
                "{label}",
                formatted
            )

            lines.append(
                f"        {node_id}{node_str}"
            )

            all_snap_types[node_id] = snap_type

        lines.append("")

        # ----------------------------------------------------
        # Snap connections
        # ----------------------------------------------------

        for link in link_map.values():

            src = safe_id(link["src_id"])
            dst = safe_id(link["dst_id"])

            lines.append(
                f"        {src} --> {dst}"
            )

        lines.append("    end")
        lines.append("")

    # --------------------------------------------------------
    # Parent / child CALLS relationships
    # --------------------------------------------------------

    for pipeline in pipelines:

        pipeline_name = pipeline.get("name", "")

        snap_map = pipeline.get("snap_map", {})

        p_safe_id = pipeline_node_ids.get(
            pipeline_name,
            ""
        )

        for snap in snap_map.values():

            snap_type = resolve_snap_type(
                snap.get("class_id", "")
            )

            if snap_type == "pipeexec":

                try:

                    child_name = (
                        snap["property_map"]
                        ["settings"]
                        ["pipeline"]
                        ["value"]
                    )

                    for other in pipelines:

                        other_name = other.get("name", "")

                        if (
                            child_name in other_name
                            or other_name in child_name
                        ):

                            child_safe_id = (
                                pipeline_node_ids.get(
                                    other_name,
                                    ""
                                )
                            )

                            if (
                                child_safe_id
                                and child_safe_id != p_safe_id
                            ):

                                lines.append(
                                    f"    {p_safe_id} "
                                    f"-.->|CALLS| "
                                    f"{child_safe_id}"
                                )

                except (KeyError, TypeError):
                    pass

    lines.append("")

    # --------------------------------------------------------
    # ClassDefs
    # --------------------------------------------------------

    lines.append(
        "    %% ── Style classes ─────────────────────────────"
    )

    lines.append(CLASSDEFS)

    lines.append("")

    # --------------------------------------------------------
    # Class assignments
    # --------------------------------------------------------

    for node_id, snap_type in all_snap_types.items():

        lines.append(
            f"    class {node_id} {snap_type}"
        )

    return "\n".join(lines)