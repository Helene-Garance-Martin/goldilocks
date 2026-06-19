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
   
     """
    return title.replace("\\", "\\\\").replace('"', '\\"')


def _clean_child_pipeline_ref(ref: str) -> str:
    """
    Convert a child pipeline path into a readable display name.
    """
    return ref.replace("\\", "/").split("/")[-1]


def render_dag_mermaid(dag: DAGModel, direction: str = "LR") -> str:
    """
    Render a DAGModel as Mermaid flowchart syntax.
    """

    lines = []


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
            NODE_SHAPES["default"],
        )

        node_str = shape.replace("{label}", label)

        lines.append(f"    {node_id}{node_str}:::{node.type}")

    lines.append("")

    # Execution edges
    lines.append("    %% Execution edges")
    for edge in dag.edges:
        source = safe_mermaid_id(edge.source)
        target = safe_mermaid_id(edge.target)
        lines.append(f"    {source} --> {target}")

    lines.append("")

    # Child pipeline calls
    lines.append("    %% Child pipeline calls")
    external_index = 1

    for node in dag.nodes:
        if node.type != "pipeexec":
            continue

        if not node.child_pipeline:
            continue

        clean_ref = _clean_child_pipeline_ref(node.child_pipeline)
        ref_id = f"external_ref_{external_index}"
        external_index += 1

        lines.append(f'    {ref_id}["📦 {clean_ref}"]:::pipeexec')

        source = safe_mermaid_id(node.id)
        lines.append(f"    {source} -.->|CALLS| {ref_id}")

    lines.append("")

    # Styles
    lines.append("    %% Styles")
    lines.append(CLASSDEFS)

    return "\n".join(lines)