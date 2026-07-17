# src/dag_mermaid_renderer.py
# ------------------------------------------------------------
# GOLDILOCKS — DAG Mermaid Renderer
# Mermaid syntax, labels, configuration and visual styling only.
# ------------------------------------------------------------

from goldilocks_cli.core.dag_models import DAGModel, DAGNode, PipelineCall
from goldilocks_cli.core.mermaid_styles import CLASSDEFS, NODE_SHAPES
from goldilocks_cli.core.snap_resolver import get_icon


def safe_mermaid_id(node_id: str) -> str:
    """Convert a DAG node id into a Mermaid-safe node id."""
    safe = "".join(character if character.isalnum() else "_" for character in node_id)
    return "n_" + safe


def _escape_label(label: str) -> str:
    return (
        str(label)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_mermaid_label(label: str, snap_type: str) -> str:
    """Add the existing type icon and a readable label."""
    if snap_type == "collapsed_chain":
        return _escape_label(label)
    icon = "📦" if snap_type == "pipeline" else get_icon(snap_type)
    return f"{icon}<br/>{_escape_label(label)}"


def _yaml_safe_title(title: str) -> str:
    return title.replace("\\", "\\\\").replace('"', '\\"')


def build_mermaid_frontmatter(title: str) -> str:
    """Build central diagram-local Mermaid configuration.

    Mermaid treats rendering limits such as ``maxTextSize`` and ``maxEdges``
    as secure configuration. They must be supplied to ``mmdc`` through its
    configuration file, not embedded in diagram front matter.
    """
    return "\n".join(
        [
            "---",
            f'title: "{_yaml_safe_title(title)}"',
            "config:",
            "  flowchart:",
            "    useMaxWidth: false",
            "    htmlLabels: false",
            "    nodeSpacing: 30",
            "    rankSpacing: 45",
            "    curve: basis",
            "    padding: 8",
            "  themeVariables:",
            "    fontSize: '14px'",
            "---",
        ]
    )


def _node_line(node: DAGNode, indent: str = "    ") -> str:
    node_id = safe_mermaid_id(node.id)
    label = format_mermaid_label(node.label, node.type)
    shape = NODE_SHAPES.get(node.type, NODE_SHAPES["default"])
    node_str = shape.replace("{label}", label)
    return f"{indent}{node_id}{node_str}:::{node.type}"


def _edge_line(source: str, target: str, relationship: str, indent: str = "    ") -> str:
    source_id = safe_mermaid_id(source)
    target_id = safe_mermaid_id(target)
    if relationship == "CONNECTS_TO":
        return f"{indent}{source_id} --> {target_id}"
    if relationship == "CALLS":
        return f"{indent}{source_id} -.->|CALLS| {target_id}"
    if "ERROR" in relationship.upper():
        return f"{indent}{source_id} -.->|ERROR| {target_id}"
    return f"{indent}{source_id} -.->|{relationship}| {target_id}"


def _collapse_provenance_lines(dag: DAGModel, indent: str = "    ") -> list[str]:
    lines: list[str] = []
    for node in dag.nodes:
        if node.synthetic_kind != "linear_chain":
            continue
        description = (
            f"{node.first_snap_name} -> ... -> {node.last_snap_name}, "
            f"{node.snap_count} snaps"
        )
        lines.append(f"{indent}%% {safe_mermaid_id(node.id)}: {description}")
    return lines


def render_dag_mermaid(
    dag: DAGModel,
    direction: str = "LR",
    *,
    include_external_references: bool = True,
) -> str:
    """Render one already-prepared DAGModel as Mermaid flowchart syntax."""
    lines = [
        build_mermaid_frontmatter(dag.pipeline_name),
        f"flowchart {direction}",
        "",
        "    %% Nodes",
    ]
    lines.extend(_collapse_provenance_lines(dag))
    lines.extend(_node_line(node) for node in dag.nodes)
    lines.extend(["", "    %% Execution edges"])
    lines.extend(
        _edge_line(edge.source, edge.target, edge.relationship)
        for edge in dag.edges
    )

    if include_external_references:
        lines.extend(["", "    %% Child pipeline calls"])
        external_index = 1
        for node in dag.nodes:
            if node.type != "pipeexec" or not node.child_pipeline:
                continue
            clean_ref = node.child_pipeline.replace("\\", "/").split("/")[-1]
            ref_id = f"external:{external_index}:{clean_ref}"
            external_index += 1
            external_node = DAGNode(
                id=ref_id,
                label=clean_ref,
                type="pipeline",
            )
            lines.append(_node_line(external_node))
            lines.append(_edge_line(node.id, ref_id, "CALLS"))

    lines.extend(["", "    %% Styles", CLASSDEFS])
    return "\n".join(lines)


def render_project_mermaid(
    dags: list[DAGModel],
    calls: list[PipelineCall],
    direction: str = "LR",
) -> str:
    """Render an all-snaps project view from already-prepared pipeline DAGs."""
    lines = [
        build_mermaid_frontmatter("Goldilocks Combined"),
        "flowchart TD",
        "",
    ]

    for dag in dags:
        subgraph_id = safe_mermaid_id(f"pipeline:{dag.pipeline_id or dag.pipeline_name}")
        title = _escape_label(dag.pipeline_name)
        lines.append(f'    subgraph {subgraph_id}["{title}"]')
        lines.append(f"        direction {direction}")
        lines.extend(_collapse_provenance_lines(dag, indent="        "))
        lines.extend(_node_line(node, indent="        ") for node in dag.nodes)
        for edge in dag.edges:
            lines.append(
                _edge_line(
                    edge.source,
                    edge.target,
                    edge.relationship,
                    indent="        ",
                )
            )
        lines.append("    end")
        lines.append("")

    lines.append("    %% Pipeline calls")
    for call in calls:
        source = call.source_snap_id
        if source is None:
            source = f"pipeline:{call.source_pipeline_id}"
        target = f"pipeline:{call.target_pipeline_id}"
        lines.append(_edge_line(source, target, "CALLS"))

    lines.extend(["", "    %% Styles", CLASSDEFS])
    return "\n".join(lines)
