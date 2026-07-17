from goldilocks_cli.core.dag_mermaid_renderer import (
    render_dag_mermaid,
    render_project_mermaid,
)
from goldilocks_cli.core.dag_models import DAGModel, DAGNode, PipelineCall
from goldilocks_cli.core.dag_transform import collapse_linear_chains


def _collapsed_dag() -> DAGModel:
    nodes = [
        DAGNode(id="start", label="Start", type="trigger", next_ids=["n1"]),
        *[
            DAGNode(
                id=f"n{index}",
                label=f"Mapper {index}",
                type="mapper",
                next_ids=[f"n{index + 1}" if index < 4 else "end"],
            )
            for index in range(1, 5)
        ],
        DAGNode(id="end", label="End", type="script"),
    ]
    from goldilocks_cli.core.dag_models import DAGEdge

    sequence = ["start", "n1", "n2", "n3", "n4", "end"]
    edges = [
        DAGEdge(source=source, target=target)
        for source, target in zip(sequence, sequence[1:])
    ]
    return collapse_linear_chains(
        DAGModel(pipeline_name="Collapsed", nodes=nodes, edges=edges)
    )


def test_mermaid_frontmatter_does_not_emit_secure_rendering_limits():
    diagram = render_dag_mermaid(DAGModel(pipeline_name="Limits"))

    assert "config:" in diagram
    assert "flowchart:" in diagram
    assert "maxTextSize:" not in diagram
    assert "maxEdges:" not in diagram


def test_collapsed_node_has_class_label_and_provenance():
    diagram = render_dag_mermaid(_collapsed_dag())

    assert ":::collapsed_chain" in diagram
    assert "⋯ 4 snaps ⋯" in diagram
    assert "classDef collapsed_chain" in diagram
    assert "Mapper 1 -> ... -> Mapper 4, 4 snaps" in diagram


def test_hundred_snap_linear_pipeline_renders_as_readable_collapsed_view():
    from goldilocks_cli.core.dag_models import DAGEdge

    nodes = [DAGNode(id="start", label="Start", type="trigger")]
    nodes.extend(
        DAGNode(id=f"m{index}", label=f"Mapper {index}", type="mapper")
        for index in range(98)
    )
    nodes.append(DAGNode(id="end", label="End", type="script"))
    sequence = [node.id for node in nodes]
    edges = [
        DAGEdge(source=source, target=target)
        for source, target in zip(sequence, sequence[1:])
    ]
    dag = DAGModel(pipeline_name="100 snaps", nodes=nodes, edges=edges)

    collapsed = collapse_linear_chains(dag)
    diagram = render_dag_mermaid(collapsed)

    assert len(collapsed.nodes) == 3
    assert "⋯ 98 snaps ⋯" in diagram
    assert "n_start --> n_collapsed" in diagram
    assert "--> n_end" in diagram


def test_project_renderer_uses_calls_without_snap_inference():
    parent = DAGModel(
        pipeline_name="Parent",
        pipeline_id="parent",
        nodes=[DAGNode(id="parent:snap", label="Snap", type="mapper")],
    )
    child = DAGModel(
        pipeline_name="Child",
        pipeline_id="child",
        nodes=[DAGNode(id="child:snap", label="Snap", type="mapper")],
    )
    calls = [
        PipelineCall(
            source_pipeline_id="parent",
            source_pipeline_name="Parent",
            target_pipeline_id="child",
            target_pipeline_name="Child",
        )
    ]

    diagram = render_project_mermaid([parent, child], calls)

    assert "|CALLS|" in diagram
    assert "n_pipeline_parent" in diagram
    assert "n_pipeline_child" in diagram


def test_pipeline_index_mermaid_contains_pipeline_nodes_and_calls_only():
    from goldilocks_cli.core.dag_builder import build_pipeline_index_dag

    parent = DAGModel(
        pipeline_name="Parent",
        pipeline_id="parent",
        nodes=[DAGNode(id="parent:snap", label="Hidden Snap", type="mapper")],
    )
    child = DAGModel(
        pipeline_name="Child",
        pipeline_id="child",
        nodes=[DAGNode(id="child:snap", label="Another Hidden Snap", type="script")],
    )
    calls = [
        PipelineCall(
            source_pipeline_id="parent",
            source_pipeline_name="Parent",
            target_pipeline_id="child",
            target_pipeline_name="Child",
        )
    ]
    index = build_pipeline_index_dag([parent, child], calls)

    diagram = render_dag_mermaid(index, include_external_references=False)

    assert "Parent" in diagram
    assert "Child" in diagram
    assert "|CALLS|" in diagram
    assert "Hidden Snap" not in diagram
    assert "Another Hidden Snap" not in diagram
