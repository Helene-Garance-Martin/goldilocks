# src/dag_mermaid_renderer.py
# ------------------------------------------------------------
# GOLDILOCKS — DAG Mermaid Renderer
# Renders a DAGModel into Mermaid syntax.
#
# Emits a single YAML front matter block combining title + Mermaid
# config — the modern (v10+) pattern that replaces the older
# `%%{init: ...}%%` directive. All sizing, spacing and label policy
# lives here, so the source travels cleanly between Confluence
# (ContentCraft macro), GitHub, GitLab, Notion, Obsidian and
# mermaid.live without per-host tweaks.
# ------------------------------------------------------------

from dag_models import DAGModel
from snap_resolver import get_icon
from mermaid_styles import NODE_SHAPES, CLASSDEFS


# Single front matter: title + config in one YAML block.
# {title} is filled in by str.format at render time.
MERMAID_FRONTMATTER = """---
title: "{title}"
config:
  flowchart:
    useMaxWidth: false
    htmlLabels: false
    nodeSpacing: 30
    rankSpacing: 45
    curve: basis
    padding: 8
  themeVariables:
    fontSize: '14px'
---"""


def safe_mermaid_id(node_id: str) -> str:
    """
    Convert a DAG node id into a Mermaid-safe node id.
    """
    return "n_" + node_id.replace(":", "_").replace("-", "_")


def format_mermaid_label(label: str, snap_type: str) -> str:
    """
    Add icon and readable label for Mermaid nodes.
    """
    icon = get_icon(snap_type)
    return f"{icon}<br/>{label}"


def _yaml_safe_title(title: str) -> str:
    """
    Escape characters that would break a YAML double-quoted scalar.
    Keeps pipeline names with colons, quotes or backslashes safe in
    the front matter.
    """
    return title.replace("\\", "\\\\").replace('"', '\\"')


def render_dag_mermaid(dag: DAGModel, direction: str = "LR") -> str:
    """
    Render a DAGModel as Mermaid flowchart syntax.
    """

    lines = []

    # Front matter: title + config in a single YAML block.
    safe_title = _yaml_safe_title(dag.pipeline_name)
    lines.append(MERMAID_FRONTMATTER.format(title=safe_title))
    lines.append(f"flowchart {direction}")
    lines.append("")

    # Nodes
    lines.append("    %% Nodes")
    for node in dag.nodes:
        node_id = safe_mermaid_id(node.id)
        label = format_mermaid_label(node.label, node.type)

        shape = NODE_SHAPES.get(
            node.type,
            NODE_SHAPES["default"]
        )

        node_str = shape.replace("{label}", label)

        lines.append(f"    {node_id}{node_str}:::{node.type}")

    lines.append("")

    # Edges
    lines.append("    %% Edges")
    for edge in dag.edges:
        source = safe_mermaid_id(edge.source)
        target = safe_mermaid_id(edge.target)
        lines.append(f"    {source} --> {target}")

    lines.append("")

    # External references / child pipeline calls
    pipeexec_nodes = [
        node for node in dag.nodes
        if node.type == "pipeexec"
    ]

    for index, ref in enumerate(dag.external_references, 1):
        ref_id = f"external_ref_{index}"
        clean_ref = ref.replace("\\", "/").split("/")[-1]
        lines.append(f'    {ref_id}["📦 {clean_ref}"]:::pipeexec')

        for node in pipeexec_nodes:
            source = safe_mermaid_id(node.id)
            lines.append(f"    {source} -.->|CALLS| {ref_id}")
    
    lines.append("")

    # Styles
    lines.append("    %% Styles")
    lines.append(CLASSDEFS)

    return "\n".join(lines)