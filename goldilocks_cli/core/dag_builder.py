from goldilocks_cli.core.dag_models import DAGModel, DAGNode, DAGEdge


def build_dag(session, pipeline_name: str) -> DAGModel:
    """
    Build a DAGModel from Neo4j traversal data.
    """

    result = session.run(
        """
        MATCH (p:Pipeline)
        WHERE p.name = $name

        MATCH (p)-[:HAS_SNAP]->(s:Snap)

        OPTIONAL MATCH (s)-[:CONNECTS_TO]->(next:Snap)

        RETURN
            p.name AS pipeline,
            s.id AS id,
            s.label AS label,
            s.type AS type,
            s.wipes_context AS wipes_context,
            s.child_pipeline AS child_pipeline,
            collect(next.id) AS next_ids
        """,
        name=pipeline_name
    )

    rows = list(result)

    if not rows:
        raise ValueError(f"No pipeline found: {pipeline_name}")

    pipeline = rows[0]["pipeline"]

    nodes = []
    edges = []
    external_references = []

    all_targets = set()

    for row in rows:

        next_ids = [n for n in row["next_ids"] if n]

        node = DAGNode(
            id=row["id"],
            label=row["label"],
            type=row["type"],
            wipes_context=row["wipes_context"],
            next_ids=next_ids,
            child_pipeline=row["child_pipeline"],
        )

        nodes.append(node)

        if row["type"] == "pipeexec":
            ref = row["child_pipeline"]
            if ref and ref not in external_references:
                external_references.append(ref)

        for next_id in next_ids:
            edges.append(
                DAGEdge(
                    source=row["id"],
                    target=next_id,
                )
            )
            all_targets.add(next_id)

    entry_points = [
        node.id
        for node in nodes
        if node.id not in all_targets
    ]

    exit_points = [
        node.id
        for node in nodes
        if not node.next_ids
    ]

    return DAGModel(
        pipeline_name=pipeline,
        nodes=nodes,
        edges=edges,
        entry_points=entry_points,
        exit_points=exit_points,
        external_references=external_references,
        complexity="simple",
    )