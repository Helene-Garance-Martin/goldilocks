from pathlib import Path

from goldilocks_cli.commands.visualise import _render_project_dags
from goldilocks_cli.core.dag_builder import (
    build_pipeline_index_dag,
    build_project_dags,
    resolve_pipeline_calls,
)
from goldilocks_cli.core.dag_models import DAGEdge, DAGModel, DAGNode, PipelineCall
from goldilocks_cli.core.visualisation_scale import PROJECT_PIPELINE_THRESHOLD


def _raw_pipeline(index: int, child: str | None = None) -> dict:
    snap = {
        "class_id": "com-snaplogic-snaps-transform-mapper",
        "property_map": {"info": {"label": {"value": f"Mapper {index}"}}},
    }
    if child:
        snap = {
            "class_id": "com-snaplogic-snaps-flow-pipeexec",
            "property_map": {
                "info": {"label": {"value": f"Call {child}"}},
                "settings": {"pipeline": {"value": f"../shared/{child}"}},
            },
        }
    return {
        "instance_id": f"p{index}",
        "name": f"Pipeline {index}",
        "snap_map": {f"s{index}": snap},
        "link_map": {},
    }


def _simple_dags(count: int) -> list[DAGModel]:
    return [
        DAGModel(
            pipeline_name=f"Pipeline {index}",
            pipeline_id=f"p{index}",
            nodes=[DAGNode(id=f"p{index}:s", label="Snap", type="mapper")],
            edges=[],
        )
        for index in range(count)
    ]


def test_project_below_threshold_keeps_combined_behaviour(tmp_path):
    paths = _render_project_dags(
        _simple_dags(2),
        [],
        out=tmp_path,
        direction="LR",
        fmt="mmd",
        explicit_collapse=None,
        combined=False,
    )

    assert (tmp_path / "goldilocks_combined.mmd") in paths
    assert not (tmp_path / "goldilocks_pipeline_index.mmd").exists()


def test_twenty_pipeline_project_generates_individuals_and_index(tmp_path, capsys):
    count = PROJECT_PIPELINE_THRESHOLD + 5
    paths = _render_project_dags(
        _simple_dags(count),
        [],
        out=tmp_path,
        direction="LR",
        fmt="mmd",
        explicit_collapse=None,
        combined=False,
    )

    pipeline_files = list(tmp_path.glob("Pipeline_*.mmd"))
    assert len(pipeline_files) == count
    assert (tmp_path / "goldilocks_pipeline_index.mmd") in paths
    assert not (tmp_path / "goldilocks_combined.mmd").exists()
    output = capsys.readouterr().out
    assert "Project total" in output
    assert f"{count} nodes · 0 edges" in output


def test_pipeline_index_has_one_node_per_pipeline_and_calls_only():
    raw = [_raw_pipeline(index) for index in range(4)]
    raw[0] = _raw_pipeline(0, child="Pipeline 1")
    dags = build_project_dags(raw)
    calls = resolve_pipeline_calls(dags)

    index = build_pipeline_index_dag(dags, calls)

    assert len(index.nodes) == 4
    assert all(node.type == "pipeline" for node in index.nodes)
    assert index.edges == [DAGEdge(source="p0", target="p1", relationship="CALLS")]


def test_pipeline_without_calls_still_appears_in_index():
    dags = build_project_dags([_raw_pipeline(index) for index in range(3)])
    index = build_pipeline_index_dag(dags, [])

    assert {node.label for node in index.nodes} == {
        "Pipeline 0",
        "Pipeline 1",
        "Pipeline 2",
    }
    assert index.edges == []


def test_combined_explicitly_requests_old_project_view_when_safe(tmp_path):
    count = PROJECT_PIPELINE_THRESHOLD + 5
    paths = _render_project_dags(
        _simple_dags(count),
        [],
        out=tmp_path,
        direction="LR",
        fmt="mmd",
        explicit_collapse=None,
        combined=True,
    )

    assert (tmp_path / "goldilocks_pipeline_index.mmd") in paths
    assert (tmp_path / "goldilocks_combined.mmd") in paths


def test_combined_above_hard_threshold_is_skipped_even_when_requested(tmp_path):
    dags = []
    for pipeline_index in range(20):
        nodes = [
            DAGNode(
                id=f"p{pipeline_index}:s{node_index}",
                label=f"Snap {node_index}",
                type="script",
            )
            for node_index in range(15)
        ]
        dags.append(
            DAGModel(
                pipeline_name=f"Pipeline {pipeline_index}",
                pipeline_id=f"p{pipeline_index}",
                nodes=nodes,
                edges=[],
            )
        )

    paths = _render_project_dags(
        dags,
        [],
        out=tmp_path,
        direction="LR",
        fmt="mmd",
        explicit_collapse=None,
        combined=True,
    )

    assert (tmp_path / "goldilocks_pipeline_index.mmd") in paths
    assert not (tmp_path / "goldilocks_combined.mmd").exists()
