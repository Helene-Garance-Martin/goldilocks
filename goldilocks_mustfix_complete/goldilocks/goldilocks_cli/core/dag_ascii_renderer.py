from rich.tree import Tree

from goldilocks_cli.core.dag_models import DAGModel
from goldilocks_cli.core.snap_resolver import get_icon


def build_node_lookup(dag: DAGModel) -> dict:
    """
    Build quick lookup:
    node_id -> DAGNode
    """
    return {
        node.id: node
        for node in dag.nodes
    }

def get_branch_label(index: int, next_id: str, node_lookup: dict) -> str:
    """
    Build a readable branch label using the first snap in that branch.
    """
    child = node_lookup[next_id]
    return f"🌿 Branch {index} → {child.label}"


def render_node(
    node_id: str,
    node_lookup: dict,
    tree,
    visited: set,
):
    """
    Recursively render DAG flow.
    """

    node = node_lookup[node_id]

    icon = get_icon(node.type)
    risk = "🔥 " if node.wipes_context else "✅ "

    # Prevent infinite repeats / merges
    if node_id in visited:
        tree.add(f"↩️ {risk}{icon} {node.label}")
        return

    visited.add(node_id)

    branch = tree.add(f"{risk}{icon} {node.label}")

    if len(node.next_ids) > 1:
        for index, next_id in enumerate(node.next_ids, start=1):
            branch_tree = branch.add(
            f"\n{get_branch_label(index, next_id, node_lookup)}\n"
            )
            render_node(
                next_id,
                node_lookup,
                branch_tree,
                visited,
            )
    else:
        for next_id in node.next_ids:
            render_node(
                next_id,
                node_lookup,
                branch,
                visited,
            )


def render_dag_ascii(dag: DAGModel) -> Tree:
    """
    Render a DAGModel as a Rich tree.
    """

    root = Tree(f"📊 {dag.pipeline_name}")

    node_lookup = build_node_lookup(dag)

    visited = set()

    if dag.external_references:
        root.add("")

        refs = root.add("📎 Referenced pipelines")

        for ref in dag.external_references:
            refs.add(f"⚪ {ref}")

        root.add("")

    for entry_id in dag.entry_points:
        render_node(
            entry_id,
            node_lookup,
            root,
            visited,
        )

    return root