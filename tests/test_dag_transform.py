from goldilocks_cli.core.dag_models import DAGEdge, DAGModel, DAGNode
from goldilocks_cli.core.dag_transform import collapse_linear_chains
from goldilocks_cli.core.visualisation_scale import COLLAPSE_MIN_CHAIN


def _dag(types: list[str] | None = None) -> DAGModel:
    types = types or ["default"] * 6
    nodes = [
        DAGNode(id=f"n{i}", label=f"Node {i}", type=node_type)
        for i, node_type in enumerate(types)
    ]
    edges = [
        DAGEdge(source=f"n{i}", target=f"n{i + 1}")
        for i in range(len(nodes) - 1)
    ]
    for index, node in enumerate(nodes[:-1]):
        node.next_ids = [nodes[index + 1].id]
    return DAGModel(
        pipeline_name="Synthetic",
        nodes=nodes,
        edges=edges,
        entry_points=[nodes[0].id],
        exit_points=[nodes[-1].id],
    )


def _collapsed_nodes(dag: DAGModel) -> list[DAGNode]:
    return [node for node in dag.nodes if node.synthetic_kind == "linear_chain"]


def test_exact_minimum_chain_is_collapsed():
    dag = _dag(["trigger", "mapper", "mapper", "mapper", "mapper", "script"])
    collapsed = collapse_linear_chains(dag)

    chains = _collapsed_nodes(collapsed)
    assert len(chains) == 1
    assert chains[0].snap_count == COLLAPSE_MIN_CHAIN


def test_chain_below_minimum_is_untouched():
    dag = _dag(["trigger", "mapper", "mapper", "mapper", "script"])
    collapsed = collapse_linear_chains(dag)

    assert not _collapsed_nodes(collapsed)
    assert [node.id for node in collapsed.nodes] == [node.id for node in dag.nodes]


def test_maximal_chain_longer_than_minimum_becomes_one_node():
    dag = _dag(["trigger"] + ["mapper"] * 7 + ["script"])
    collapsed = collapse_linear_chains(dag)

    chains = _collapsed_nodes(collapsed)
    assert len(chains) == 1
    assert chains[0].snap_count == 7


def test_entry_edge_into_collapsed_chain_is_preserved():
    dag = _dag(["trigger", "mapper", "mapper", "mapper", "mapper", "script"])
    collapsed = collapse_linear_chains(dag)
    chain = _collapsed_nodes(collapsed)[0]

    assert DAGEdge(source="n0", target=chain.id) in collapsed.edges


def test_exit_edge_from_collapsed_chain_is_preserved():
    dag = _dag(["trigger", "mapper", "mapper", "mapper", "mapper", "script"])
    collapsed = collapse_linear_chains(dag)
    chain = _collapsed_nodes(collapsed)[0]

    assert DAGEdge(source=chain.id, target="n5") in collapsed.edges


def test_branch_points_are_never_absorbed():
    dag = _dag(["trigger", "mapper", "mapper", "mapper", "mapper", "default", "script"])
    dag.nodes.append(DAGNode(id="branch", label="Branch", type="default"))
    dag.edges.append(DAGEdge(source="n5", target="branch"))
    dag.nodes[5].next_ids.append("branch")

    collapsed = collapse_linear_chains(dag)

    assert any(node.id == "n5" for node in collapsed.nodes)
    assert all("n5" not in node.collapsed_snap_ids for node in _collapsed_nodes(collapsed))


def test_join_nodes_are_never_absorbed():
    dag = _dag(["trigger", "mapper", "mapper", "mapper", "mapper", "default", "script"])
    dag.nodes.append(DAGNode(id="other", label="Other", type="trigger", next_ids=["n5"]))
    dag.edges.append(DAGEdge(source="other", target="n5"))

    collapsed = collapse_linear_chains(dag)

    assert any(node.id == "n5" for node in collapsed.nodes)
    assert all("n5" not in node.collapsed_snap_ids for node in _collapsed_nodes(collapsed))


def test_error_routing_structure_is_preserved():
    dag = _dag(["trigger", "mapper", "mapper", "mapper", "mapper", "script"])
    dag.nodes.append(DAGNode(id="error", label="Error Handler", type="script"))
    error_edge = DAGEdge(source="n2", target="error", relationship="ERRORS_TO")
    dag.edges.append(error_edge)

    collapsed = collapse_linear_chains(dag)

    assert error_edge in collapsed.edges
    assert any(node.id == "n2" for node in collapsed.nodes)


def test_pipeexec_calls_node_is_never_absorbed():
    dag = _dag(["trigger", "mapper", "mapper", "pipeexec", "mapper", "mapper", "script"])
    dag.nodes[3].child_pipeline = "../shared/Child"

    collapsed = collapse_linear_chains(dag, min_length=2)

    assert any(node.id == "n3" for node in collapsed.nodes)
    assert all("n3" not in node.collapsed_snap_ids for node in _collapsed_nodes(collapsed))


def test_audit_significant_snap_is_never_absorbed():
    dag = _dag(["trigger", "mapper", "mapper", "httpclient", "mapper", "mapper", "script"])

    collapsed = collapse_linear_chains(dag, min_length=2)

    assert any(node.id == "n3" for node in collapsed.nodes)
    assert all("n3" not in node.collapsed_snap_ids for node in _collapsed_nodes(collapsed))


def test_ordered_ids_and_names_are_retained():
    dag = _dag(["trigger", "mapper", "mapper", "mapper", "mapper", "script"])
    collapsed = collapse_linear_chains(dag)
    chain = _collapsed_nodes(collapsed)[0]

    assert chain.collapsed_snap_ids == ["n1", "n2", "n3", "n4"]
    assert chain.collapsed_snap_names == ["Node 1", "Node 2", "Node 3", "Node 4"]


def test_first_last_and_count_metadata_are_correct():
    dag = _dag(["trigger", "mapper", "mapper", "mapper", "mapper", "script"])
    chain = _collapsed_nodes(collapse_linear_chains(dag))[0]

    assert chain.first_snap_id == "n1"
    assert chain.first_snap_name == "Node 1"
    assert chain.last_snap_id == "n4"
    assert chain.last_snap_name == "Node 4"
    assert chain.snap_count == 4


def test_multiple_independent_chains_collapse_independently():
    nodes = [
        DAGNode(id="a", label="A", type="trigger"),
        *[DAGNode(id=f"x{i}", label=f"X{i}", type="mapper") for i in range(4)],
        DAGNode(id="b", label="B", type="script"),
        DAGNode(id="c", label="C", type="trigger"),
        *[DAGNode(id=f"y{i}", label=f"Y{i}", type="mapper") for i in range(5)],
        DAGNode(id="d", label="D", type="script"),
    ]
    edges = []
    for chain in [["a", "x0", "x1", "x2", "x3", "b"], ["c", "y0", "y1", "y2", "y3", "y4", "d"]]:
        edges.extend(
            DAGEdge(source=source, target=target)
            for source, target in zip(chain, chain[1:])
        )
    dag = DAGModel(pipeline_name="Two chains", nodes=nodes, edges=edges)

    collapsed = collapse_linear_chains(dag)

    assert sorted(node.snap_count for node in _collapsed_nodes(collapsed)) == [4, 5]


def test_collapse_does_not_mutate_original_dag():
    dag = _dag(["trigger", "mapper", "mapper", "mapper", "mapper", "script"])
    before = dag.model_dump()

    collapsed = collapse_linear_chains(dag)

    assert dag.model_dump() == before
    assert collapsed is not dag
