# src/dag_mermaid_renderer.py
# ------------------------------------------------------------
# GOLDILOCKS — DAG Mermaid Renderer
# Renders a DAGModel into Mermaid syntax.
# ------------------------------------------------------------

from dag_models import DAGModel
from snap_resolver import get_icon
from mermaid_styles import NODE_SHAPES, CLASSDEFS


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


def render_dag_mermaid(dag: DAGModel, direction: str = "LR") -> str:
    """
    Render a DAGModel as Mermaid flowchart syntax.
    """

    lines = []

    lines.append(f"flowchart {direction}")
    lines.append("")

    lines.append("    %% Title")
    lines.append(
        f'    pipeline_title["<b>{dag.pipeline_name}</b>"]:::diagram_title'
    )
    lines.append('    title_spacer[" "]:::title_spacer')
    lines.append("    pipeline_title --> title_spacer")
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

    # Styles
    lines.append("    %% Styles")
    lines.append(
        "    classDef diagram_title fill:none,stroke:none,font-size:30px,font-weight:bold;"
    )
    lines.append(
        "    classDef title_spacer fill:none,stroke:none,color:transparent;"
    )
    lines.append(CLASSDEFS)

    return "\n".join(lines)

    return "\n".join(lines)