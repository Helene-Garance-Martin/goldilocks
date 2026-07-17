"""Pure DAG transformations used by Goldilocks visualisation."""

from collections import defaultdict

from goldilocks_cli.core.dag_models import DAGEdge, DAGModel, DAGNode
from goldilocks_cli.core.snap_resolver import is_visualisation_protected
from goldilocks_cli.core.visualisation_scale import COLLAPSE_MIN_CHAIN


STRUCTURAL_RELATIONSHIP = "CONNECTS_TO"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def collapse_linear_chains(
    dag: DAGModel,
    min_length: int = COLLAPSE_MIN_CHAIN,
) -> DAGModel:
    """
    Collapse maximal ordered runs of safe 1-in/1-out nodes.

    The transformation is non-mutating. Branches, joins, non-structural
    relationships, CALLS-related snaps, and protected snap classifications
    remain visible.
    """
    if min_length < 2:
        raise ValueError("min_length must be at least 2")

    nodes_by_id = {node.id: node for node in dag.nodes}
    structural_predecessors: dict[str, list[str]] = defaultdict(list)
    structural_successors: dict[str, list[str]] = defaultdict(list)
    non_structural_incident: set[str] = set()

    for edge in dag.edges:
        if edge.relationship == STRUCTURAL_RELATIONSHIP:
            structural_successors[edge.source].append(edge.target)
            structural_predecessors[edge.target].append(edge.source)
        else:
            non_structural_incident.add(edge.source)
            non_structural_incident.add(edge.target)

    eligible: set[str] = set()
    for node in dag.nodes:
        if node.synthetic_kind:
            continue
        if len(structural_predecessors[node.id]) != 1:
            continue
        if len(structural_successors[node.id]) != 1:
            continue
        if node.id in non_structural_incident:
            continue
        if is_visualisation_protected(
            node.type,
            wipes_context=node.wipes_context,
            child_pipeline=node.child_pipeline,
        ):
            continue
        eligible.add(node.id)

    chains: list[list[str]] = []
    visited: set[str] = set()

    for node in dag.nodes:
        node_id = node.id
        if node_id not in eligible or node_id in visited:
            continue

        predecessor = structural_predecessors[node_id][0]
        if predecessor in eligible:
            continue

        chain: list[str] = []
        current = node_id
        while current in eligible and current not in visited:
            chain.append(current)
            visited.add(current)
            successor = structural_successors[current][0]
            if successor not in eligible:
                break
            current = successor

        if len(chain) >= min_length:
            chains.append(chain)

    if not chains:
        return dag.model_copy(deep=True)

    replacement_by_node: dict[str, str] = {}
    synthetic_by_first: dict[str, DAGNode] = {}

    for index, chain in enumerate(chains, start=1):
        first = nodes_by_id[chain[0]]
        last = nodes_by_id[chain[-1]]
        synthetic_id = f"collapsed:{index}:{first.id}:{last.id}"
        names = [nodes_by_id[node_id].label for node_id in chain]

        synthetic = DAGNode(
            id=synthetic_id,
            label=f"⋯ {len(chain)} snaps ⋯",
            type="collapsed_chain",
            synthetic_kind="linear_chain",
            collapsed_snap_ids=list(chain),
            collapsed_snap_names=names,
            first_snap_id=first.id,
            first_snap_name=first.label,
            last_snap_id=last.id,
            last_snap_name=last.label,
            snap_count=len(chain),
        )
        synthetic_by_first[first.id] = synthetic
        for node_id in chain:
            replacement_by_node[node_id] = synthetic_id

    transformed_nodes: list[DAGNode] = []
    collapsed_members = set(replacement_by_node)
    for node in dag.nodes:
        if node.id in synthetic_by_first:
            transformed_nodes.append(synthetic_by_first[node.id])
        elif node.id not in collapsed_members:
            transformed_nodes.append(node.model_copy(deep=True))

    transformed_edges: list[DAGEdge] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for edge in dag.edges:
        source = replacement_by_node.get(edge.source, edge.source)
        target = replacement_by_node.get(edge.target, edge.target)
        if source == target:
            continue
        key = (source, target, edge.relationship)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        transformed_edges.append(
            DAGEdge(source=source, target=target, relationship=edge.relationship)
        )

    next_ids_by_node: dict[str, list[str]] = defaultdict(list)
    structural_targets: set[str] = set()
    for edge in transformed_edges:
        if edge.relationship != STRUCTURAL_RELATIONSHIP:
            continue
        next_ids_by_node[edge.source].append(edge.target)
        structural_targets.add(edge.target)

    for node in transformed_nodes:
        node.next_ids = _dedupe(next_ids_by_node.get(node.id, []))

    transformed_entry_points = _dedupe(
        [replacement_by_node.get(node_id, node_id) for node_id in dag.entry_points]
    )
    if not transformed_entry_points:
        transformed_entry_points = [
            node.id for node in transformed_nodes if node.id not in structural_targets
        ]

    transformed_exit_points = _dedupe(
        [replacement_by_node.get(node_id, node_id) for node_id in dag.exit_points]
    )
    if not transformed_exit_points:
        transformed_exit_points = [
            node.id for node in transformed_nodes if not node.next_ids
        ]

    transformed_branches: list[list[str]] = []
    for branch in dag.branches:
        mapped = _dedupe(
            [replacement_by_node.get(node_id, node_id) for node_id in branch]
        )
        if mapped:
            transformed_branches.append(mapped)

    return DAGModel(
        pipeline_name=dag.pipeline_name,
        pipeline_id=dag.pipeline_id,
        nodes=transformed_nodes,
        edges=transformed_edges,
        entry_points=transformed_entry_points,
        exit_points=transformed_exit_points,
        branches=transformed_branches,
        external_references=list(dag.external_references),
        complexity=dag.complexity,
    )
