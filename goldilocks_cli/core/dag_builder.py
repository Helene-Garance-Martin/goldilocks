"""Build Goldilocks DAG models from Neo4j traversal or pipeline JSON."""

from collections import defaultdict

from goldilocks_cli.core.dag_models import (
    DAGEdge,
    DAGModel,
    DAGNode,
    PipelineCall,
)
from goldilocks_cli.core.snap_resolver import resolve_snap_type, snap_wipes_context


STRUCTURAL_RELATIONSHIP = "CONNECTS_TO"


def _entry_and_exit_points(
    nodes: list[DAGNode],
    edges: list[DAGEdge],
) -> tuple[list[str], list[str]]:
    targets = {
        edge.target
        for edge in edges
        if edge.relationship == STRUCTURAL_RELATIONSHIP
    }
    outgoing = {
        edge.source
        for edge in edges
        if edge.relationship == STRUCTURAL_RELATIONSHIP
    }
    return (
        [node.id for node in nodes if node.id not in targets],
        [node.id for node in nodes if node.id not in outgoing],
    )


def build_dag(session, pipeline_name: str) -> DAGModel:
    """Build a DAGModel from Neo4j traversal data."""
    result = session.run(
        """
        MATCH (p:Pipeline)
        WHERE p.name = $name

        MATCH (p)-[:HAS_SNAP]->(s:Snap)
        OPTIONAL MATCH (s)-[:CONNECTS_TO]->(next:Snap)

        RETURN
            p.id AS pipeline_id,
            p.name AS pipeline,
            s.id AS id,
            s.label AS label,
            s.type AS type,
            s.wipes_context AS wipes_context,
            s.child_pipeline AS child_pipeline,
            s.error AS error_behavior,
            collect(next.id) AS next_ids
        """,
        name=pipeline_name,
    )

    rows = list(result)
    if not rows:
        raise ValueError(f"No pipeline found: {pipeline_name}")

    pipeline = rows[0]["pipeline"]
    pipeline_id = rows[0]["pipeline_id"]
    nodes: list[DAGNode] = []
    edges: list[DAGEdge] = []
    external_references: list[str] = []

    for row in rows:
        next_ids = [node_id for node_id in row["next_ids"] if node_id]
        child_pipeline = row["child_pipeline"]
        node = DAGNode(
            id=row["id"],
            label=row["label"],
            type=row["type"],
            wipes_context=bool(row["wipes_context"]),
            next_ids=next_ids,
            child_pipeline=child_pipeline,
            error_behavior=row["error_behavior"] or "unknown",
        )
        nodes.append(node)

        if node.type == "pipeexec" and child_pipeline:
            if child_pipeline not in external_references:
                external_references.append(child_pipeline)

        edges.extend(
            DAGEdge(source=node.id, target=next_id)
            for next_id in next_ids
        )

    entry_points, exit_points = _entry_and_exit_points(nodes, edges)
    return DAGModel(
        pipeline_name=pipeline,
        pipeline_id=pipeline_id,
        nodes=nodes,
        edges=edges,
        entry_points=entry_points,
        exit_points=exit_points,
        external_references=external_references,
        complexity="simple",
    )


def _snap_label(snap_id: str, snap: dict) -> str:
    try:
        return snap["property_map"]["info"]["label"]["value"]
    except (KeyError, TypeError):
        return snap_id


def _error_behavior(snap: dict) -> str:
    try:
        return snap["property_map"]["error"]["error_behavior"]["value"]
    except (KeyError, TypeError):
        return "unknown"


def _child_pipeline(snap: dict, snap_type: str) -> str | None:
    if snap_type != "pipeexec":
        return None
    try:
        return snap["property_map"]["settings"]["pipeline"]["value"] or None
    except (KeyError, TypeError):
        return None


def build_dag_from_pipeline(pipeline: dict) -> DAGModel:
    """Build a DAGModel from one anonymised SnapLogic pipeline entry."""
    pipeline_name = pipeline.get("name", "Unknown")
    pipeline_id = str(
        pipeline.get("instance_id")
        or pipeline.get("id")
        or pipeline_name
    )
    snap_map = pipeline.get("snap_map", {})
    link_map = pipeline.get("link_map", {})

    nodes: list[DAGNode] = []
    edges: list[DAGEdge] = []
    external_references: list[str] = []
    next_ids_by_node: dict[str, list[str]] = defaultdict(list)

    def qualified(snap_id: str) -> str:
        return f"{pipeline_id}:{snap_id}"

    for link in link_map.values():
        try:
            source = qualified(link["src_id"])
            target = qualified(link["dst_id"])
        except (KeyError, TypeError):
            continue
        relationship = str(link.get("relationship") or "CONNECTS_TO")
        edges.append(
            DAGEdge(source=source, target=target, relationship=relationship)
        )
        if relationship == STRUCTURAL_RELATIONSHIP:
            next_ids_by_node[source].append(target)

    for snap_id, snap in snap_map.items():
        class_id = snap.get("class_id", "unknown")
        snap_type = resolve_snap_type(class_id)
        child_pipeline = _child_pipeline(snap, snap_type)
        if child_pipeline and child_pipeline not in external_references:
            external_references.append(child_pipeline)

        node_id = qualified(snap_id)
        nodes.append(
            DAGNode(
                id=node_id,
                label=_snap_label(snap_id, snap),
                type=snap_type,
                wipes_context=snap_wipes_context(snap_type, class_id),
                next_ids=list(next_ids_by_node.get(node_id, [])),
                child_pipeline=child_pipeline,
                error_behavior=_error_behavior(snap),
            )
        )

    entry_points, exit_points = _entry_and_exit_points(nodes, edges)
    return DAGModel(
        pipeline_name=pipeline_name,
        pipeline_id=pipeline_id,
        nodes=nodes,
        edges=edges,
        entry_points=entry_points,
        exit_points=exit_points,
        external_references=external_references,
        complexity="simple",
    )


def build_project_dags(pipelines: list[dict]) -> list[DAGModel]:
    """Build ordered per-pipeline DAGs from a project export."""
    return [build_dag_from_pipeline(pipeline) for pipeline in pipelines]


def _normalise_pipeline_ref(ref: str) -> str:
    return (ref or "").replace("\\", "/").split("/")[-1].strip()


def resolve_pipeline_calls(dags: list[DAGModel]) -> list[PipelineCall]:
    """Resolve PipeExec child references using the seeded project's name rules."""
    by_name = {dag.pipeline_name: dag for dag in dags}
    calls: list[PipelineCall] = []
    seen: set[tuple[str, str, str | None]] = set()

    for dag in dags:
        for node in dag.nodes:
            if node.type != "pipeexec" or not node.child_pipeline:
                continue
            child_name = _normalise_pipeline_ref(node.child_pipeline)
            target = by_name.get(child_name)
            if target is None:
                target = next(
                    (
                        candidate
                        for candidate in dags
                        if child_name in candidate.pipeline_name
                        or candidate.pipeline_name in child_name
                    ),
                    None,
                )
            if target is None or target.pipeline_name == dag.pipeline_name:
                continue

            source_id = dag.pipeline_id or dag.pipeline_name
            target_id = target.pipeline_id or target.pipeline_name
            key = (source_id, target_id, node.id)
            if key in seen:
                continue
            seen.add(key)
            calls.append(
                PipelineCall(
                    source_pipeline_id=source_id,
                    source_pipeline_name=dag.pipeline_name,
                    target_pipeline_id=target_id,
                    target_pipeline_name=target.pipeline_name,
                    source_snap_id=node.id,
                )
            )
    return calls


def build_pipeline_index_dag(
    dags: list[DAGModel],
    calls: list[PipelineCall],
) -> DAGModel:
    """Build the pipeline-only index DAG. No Snap nodes are included."""
    nodes = [
        DAGNode(
            id=dag.pipeline_id or dag.pipeline_name,
            label=dag.pipeline_name,
            type="pipeline",
        )
        for dag in dags
    ]
    edges = [
        DAGEdge(
            source=call.source_pipeline_id,
            target=call.target_pipeline_id,
            relationship="CALLS",
        )
        for call in calls
    ]
    entry_points, exit_points = _entry_and_exit_points(nodes, [])
    return DAGModel(
        pipeline_name="Goldilocks Pipeline Index",
        pipeline_id="goldilocks-pipeline-index",
        nodes=nodes,
        edges=edges,
        entry_points=entry_points,
        exit_points=exit_points,
        complexity="project",
    )


def build_project_dags_from_graph(session) -> list[DAGModel]:
    """Build every seeded pipeline DAG in name order."""
    rows = session.run(
        """
        MATCH (p:Pipeline)
        RETURN p.name AS name
        ORDER BY name
        """
    )
    names = [row["name"] for row in rows]
    return [build_dag(session, name) for name in names]


def read_pipeline_calls(session) -> list[PipelineCall]:
    """Read the graph's existing pipeline-level CALLS relationships."""
    rows = session.run(
        """
        MATCH (parent:Pipeline)-[:CALLS]->(child:Pipeline)
        RETURN
            parent.id AS source_id,
            parent.name AS source_name,
            child.id AS target_id,
            child.name AS target_name
        ORDER BY source_name, target_name
        """
    )
    return [
        PipelineCall(
            source_pipeline_id=row["source_id"],
            source_pipeline_name=row["source_name"],
            target_pipeline_id=row["target_id"],
            target_pipeline_name=row["target_name"],
        )
        for row in rows
    ]
