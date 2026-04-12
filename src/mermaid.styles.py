# ============================================================
# 🐻 GOLDILOCKS — Mermaid Canonical Style Library
# ============================================================
# A consistent visual language for all Goldilocks pipeline
# diagrams. Import this as a reference when generating
# .mmd files via diagram_generator.py / visualiser.py
#
# Conventions:
#   - Node colours represent Snap TYPE
#   - Node borders represent Error handling behaviour
#   - Direction chosen per diagram (LR or TD)
# ============================================================


# ------------------------------------------------------------
# DIRECTION
# ------------------------------------------------------------
# Use LR (left to right) for long sequential pipelines
# Use TD (top to bottom) for hierarchical / parent-child flows
#
# LR example:  SFTP → Script → HTTP → PipeExec
# TD example:  Parent pipeline
#                  └── Child pipeline
#                          └── Sub-child pipeline

DIRECTION_LR = "LR"   # left to right — sequential pipelines
DIRECTION_TD = "TD"   # top to bottom — hierarchical pipelines


# ------------------------------------------------------------
# NODE SHAPES — by Snap type
# ------------------------------------------------------------
# Mermaid shape syntax:
#   [label]   = rectangle       → standard processing snap
#   (label)   = rounded rect    → start / trigger snap
#   {label}   = diamond         → decision / router snap
#   ([label]) = stadium         → database snap
#   [[label]] = subroutine      → pipeline execute (child call)
#   ((label)) = circle          → endpoint / terminator
#   >label]   = asymmetric      → file / SFTP snap

NODE_SHAPES = {
    "httpclient":   "[{label}]",        # rectangle    — HTTP Request
    "script":       "[{label}]",        # rectangle    — Script snap
    "pipeexec":     "[[{label}]]",      # subroutine   — Pipeline Execute (child call)
    "mapper":       "[{label}]",        # rectangle    — Mapper
    "sftp_get":     ">{label}]",        # asymmetric   — SFTP Get (file in)
    "sftp_put":     ">{label}]",        # asymmetric   — SFTP Put (file out)
    "db_select":    "([{label}])",      # stadium      — Database Select
    "db_insert":    "([{label}])",      # stadium      — Database Insert
    "filter":       "{{label}}",        # diamond      — Filter / Router
    "trigger":      "({label})",        # rounded      — Trigger / Scheduler
    "default":      "[{label}]",        # rectangle    — fallback
}


# ------------------------------------------------------------
# NODE COLOURS — by Snap type
# ------------------------------------------------------------
# Gold palette for Goldilocks — warm, distinctive, readable
#
# Mermaid style syntax:
#   style NODE_ID fill:#hex,stroke:#hex,color:#hex

COLOURS_BY_TYPE = {
    "httpclient":   {"fill": "#D4A017", "stroke": "#8B6914", "color": "#1A1A1A"},   # gold        — HTTP
    "script":       {"fill": "#4A90D9", "stroke": "#2C5F8A", "color": "#FFFFFF"},   # blue        — Script
    "pipeexec":     {"fill": "#7B68EE", "stroke": "#483D8B", "color": "#FFFFFF"},   # purple      — Pipeline Execute
    "mapper":       {"fill": "#5CB85C", "stroke": "#3D7A3D", "color": "#FFFFFF"},   # green       — Mapper
    "sftp_get":     {"fill": "#F0A500", "stroke": "#A06800", "color": "#1A1A1A"},   # amber       — SFTP Get
    "sftp_put":     {"fill": "#E07B00", "stroke": "#904D00", "color": "#FFFFFF"},   # dark amber  — SFTP Put
    "db_select":    {"fill": "#20B2AA", "stroke": "#147870", "color": "#FFFFFF"},   # teal        — Database
    "db_insert":    {"fill": "#17A589", "stroke": "#0E6B5A", "color": "#FFFFFF"},   # dark teal   — Database Insert
    "filter":       {"fill": "#E74C3C", "stroke": "#922B21", "color": "#FFFFFF"},   # red         — Filter/Router
    "trigger":      {"fill": "#95A5A6", "stroke": "#626D6E", "color": "#FFFFFF"},   # grey        — Trigger
    "default":      {"fill": "#F5F5F5", "stroke": "#AAAAAA", "color": "#1A1A1A"},   # light grey  — unknown
}


# ------------------------------------------------------------
# NODE BORDERS — by Error handling behaviour
# ------------------------------------------------------------
# stroke-width encodes error behaviour:
#   1px  = passthrough (errors flow on)
#   3px  = fail        (pipeline stops on error)
#   2px  = continue    (errors ignored)

BORDERS_BY_ERROR = {
    "fail":         {"stroke-width": "3px", "stroke-dasharray": "0"},       # solid thick   — hard stop
    "passthrough":  {"stroke-width": "1px", "stroke-dasharray": "0"},       # solid thin    — errors pass on
    "continue":     {"stroke-width": "2px", "stroke-dasharray": "5,3"},     # dashed        — errors ignored
    "default":      {"stroke-width": "1px", "stroke-dasharray": "0"},       # solid thin    — fallback
}


# ------------------------------------------------------------
# EDGE STYLES
# ------------------------------------------------------------

EDGE_STYLES = {
    "default":      "-->",      # solid arrow       — normal data flow
    "error":        "-.->",     # dashed arrow      — error path
    "conditional":  "==>",      # thick arrow       — conditional flow
    "label":        "-->|{label}|",  # labelled arrow — named connection
}


# ------------------------------------------------------------
# LEGEND TEMPLATE
# ------------------------------------------------------------
# Include this at the bottom of every diagram for readability

LEGEND = """
    subgraph Legend
        direction LR
        L1[HTTP Request]:::http
        L2[Script]:::script
        L3[[Pipeline Execute]]:::pipeexec
        L4>SFTP]:::sftp
        L5([Database]):::db
    end
"""


# ------------------------------------------------------------
# CLASSDEFS — paste these into every .mmd file
# ------------------------------------------------------------
# classDef defines reusable style classes in Mermaid

CLASSDEFS = """
    classDef http      fill:#D4A017,stroke:#8B6914,color:#1A1A1A
    classDef script    fill:#4A90D9,stroke:#2C5F8A,color:#FFFFFF
    classDef pipeexec  fill:#7B68EE,stroke:#483D8B,color:#FFFFFF
    classDef mapper    fill:#5CB85C,stroke:#3D7A3D,color:#FFFFFF
    classDef sftp      fill:#F0A500,stroke:#A06800,color:#1A1A1A
    classDef db        fill:#20B2AA,stroke:#147870,color:#FFFFFF
    classDef filter    fill:#E74C3C,stroke:#922B21,color:#FFFFFF
    classDef trigger   fill:#95A5A6,stroke:#626D6E,color:#FFFFFF
    classDef default   fill:#F5F5F5,stroke:#AAAAAA,color:#1A1A1A
"""


# ------------------------------------------------------------
# SNAP TYPE RESOLVER
# ------------------------------------------------------------
# Maps SnapLogic class_id → canonical type name

def resolve_snap_type(class_id: str) -> str:
    """
    Given a SnapLogic class_id, return the canonical Goldilocks type.
    Used to look up colours, shapes and classDefs.
    """
    # Lambda — one-liner check for each type
    is_type = lambda keyword: keyword in class_id.lower()

    if is_type("httpclient"):   return "httpclient"
    if is_type("script"):       return "script"
    if is_type("pipeexec"):     return "pipeexec"
    if is_type("mapper"):       return "mapper"
    if is_type("sftp-get"):     return "sftp_get"
    if is_type("sftp-put"):     return "sftp_put"
    if is_type("db-select"):    return "db_select"
    if is_type("db-insert"):    return "db_insert"
    if is_type("filter"):       return "filter"
    if is_type("trigger"):      return "trigger"
    return "default"


# ------------------------------------------------------------
# DIAGRAM BUILDER
# ------------------------------------------------------------

def build_diagram(
    pipeline_name: str,
    snaps: dict,
    links: dict,
    direction: str = DIRECTION_LR
) -> str:
    """
    Build a complete Mermaid diagram string from pipeline data.

    Args:
        pipeline_name: Human-readable pipeline name
        snaps: dict of {snap_id: {"label": str, "class_id": str, "error": str}}
        links: dict of {link_id: {"src_id": str, "dst_id": str}}
        direction: DIRECTION_LR or DIRECTION_TD

    Returns:
        Complete .mmd file content as a string
    """
    lines = []

    # Header
    lines.append(f"---")
    lines.append(f"title: {pipeline_name}")
    lines.append(f"---")
    lines.append(f"flowchart {direction}")
    lines.append("")

    # Nodes
    lines.append("    %% ── Snaps (nodes) ──────────────────────────────────")
    for snap_id, snap in snaps.items():
        label     = snap.get("label", snap_id)
        class_id  = snap.get("class_id", "")
        snap_type = resolve_snap_type(class_id)

        # Safe node ID (Mermaid doesn't like hyphens)
        node_id = snap_id.replace("-", "_")[:8]

        # Shape based on type
        shape = NODE_SHAPES.get(snap_type, NODE_SHAPES["default"])
        node_label = shape.replace("{label}", label)

        lines.append(f"    {node_id}{node_label}:::{snap_type}")

    lines.append("")

    # Edges
    lines.append("    %% ── Connections (edges) ────────────────────────────")
    for link_id, link in links.items():
        src = link["src_id"].replace("-", "_")[:8]
        dst = link["dst_id"].replace("-", "_")[:8]
        lines.append(f"    {src} --> {dst}")

    lines.append("")

    # ClassDefs
    lines.append("    %% ── Style classes ──────────────────────────────────")
    lines.append(CLASSDEFS)

    return "\n".join(lines)


# ------------------------------------------------------------
# EXAMPLE USAGE
# ------------------------------------------------------------

if __name__ == "__main__":
    # Example — build a diagram from mock data
    example_snaps = {
        "snap-001": {"label": "SFTP Get File",         "class_id": "com-snaplogic-snaps-sftp-get",              "error": "fail"},
        "snap-002": {"label": "Build JWT Token",        "class_id": "com-snaplogic-scripting-language-script",   "error": "fail"},
        "snap-003": {"label": "SharePoint Post Request","class_id": "com-snaplogic-snaps-apisuite-httpclient",   "error": "fail"},
        "snap-004": {"label": "Sends File",             "class_id": "com-snaplogic-snaps-flow-pipeexec",         "error": "fail"},
    }
    example_links = {
        "link-001": {"src_id": "snap-001", "dst_id": "snap-002"},
        "link-002": {"src_id": "snap-002", "dst_id": "snap-003"},
        "link-003": {"src_id": "snap-003", "dst_id": "snap-004"},
    }

    diagram = build_diagram(
        pipeline_name="SharePoint Token Pipeline",
        snaps=example_snaps,
        links=example_links,
        direction=DIRECTION_LR
    )

    print(diagram)

    # Save to file
    with open("diagrams/example_diagram.mmd", "w") as f:
        f.write(diagram)

    print("\n✅ Diagram saved to diagrams/example_diagram.mmd")