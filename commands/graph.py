# ============================================================
# 🫧 GOLDILOCKS — Pipeline Graph Command
# ============================================================
# Renders pipeline relationships as a beautiful Rich tree
# directly in the terminal.
# Shows snap types, wipes_context risks and parent/child
# pipeline relationships.
# ============================================================

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import typer
from rich.console import Console
from rich.tree import Tree
from commands.colours import CYAN, GREEN, RED, GOLD, BOLD, RESET

console = Console()

SNAP_ICONS = {
    "httpclient": "🌐",
    "script":     "📜",
    "pipeexec":   "🔀",
    "sftp_get":   "📥",
    "sftp_put":   "📤",
    "mapper":     "🗺️",
    "filter":     "⚗️",
    "trigger":    "⚡",
    "default":    "⚙️",
}


def get_snap_stats(session, pipeline_id: str) -> dict:
    """Get snap count, parent and child counts for a pipeline."""
    result = session.run("""
        MATCH (p:Pipeline {id: $pid})
        OPTIONAL MATCH (p)-[:HAS_SNAP]->(s:Snap)
        OPTIONAL MATCH (p)-[:CALLS]->(child:Pipeline)
        OPTIONAL MATCH (parent:Pipeline)-[:CALLS]->(p)
        RETURN
            count(DISTINCT s)      AS snap_count,
            count(DISTINCT child)  AS children,
            count(DISTINCT parent) AS parents
    """, pid=pipeline_id).single()
    return dict(result)


def render_pipeline(session, p: dict, pipe_tree) -> None:
    """Render snaps and calls for a single pipeline into a Rich tree."""
    snaps = session.run("""
        MATCH (p:Pipeline {id: $pid})-[:HAS_SNAP]->(s:Snap)
        RETURN s.label AS label, s.type AS type, s.wipes_context AS wipes
    """, pid=p['id'])

    for snap in snaps:
        icon = SNAP_ICONS.get(snap['type'], "⚙️")
        risk = "🔥 " if snap['wipes'] else "✅ "
        pipe_tree.add(f"{risk}{icon} {snap['label']} [{snap['type']}]")

    calls = session.run("""
        MATCH (p:Pipeline {id: $pid})-[:CALLS]->(child:Pipeline)
        RETURN child.name AS name
    """, pid=p['id'])

    for call in calls:
        pipe_tree.add(f"[purple]🔀 Calls → {call['name']}[/purple]")


def show_graph(
    pipeline: str = typer.Option(None, help="Filter by pipeline name"),
):
    """
    🌳 Render pipeline relationships as a terminal graph.

    Shows pipeline architecture, snap types and
    parent/child relationships as a beautiful tree.
    Pipelines are grouped by family (parent + children).
    """
    typer.echo(f"{CYAN}🌳 Building pipeline graph...{RESET}\n")

    try:
        from neo4j import GraphDatabase

        uri      = os.environ["NEO4J_URI"]
        user     = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ["NEO4J_PASSWORD"]

        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            with driver.session() as session:

                # ── Empty graph guard ─────────────────────
                total = session.run(
                    "MATCH (p:Pipeline) RETURN count(p) AS total"
                ).single()["total"]

                if total == 0:
                    typer.echo(f"{GOLD}⚠️  Your graph is empty!{RESET}")
                    typer.echo(f"💡 Run: python pie.py seed --uri your-uri")
                    raise typer.Exit(0)

                # ── Build pipeline families ───────────────
                families_result = session.run("""
                    MATCH (parent:Pipeline)-[:CALLS]->(child:Pipeline)
                    RETURN
                        parent.name AS parent_name,
                        parent.id   AS parent_id,
                        collect({name: child.name, id: child.id}) AS children
                    ORDER BY parent.name
                """)
                families = [dict(r) for r in families_result]

                # Orphan pipelines (no parent, no children)
                orphans_result = session.run("""
                    MATCH (p:Pipeline)
                    WHERE NOT (p)-[:CALLS]->()
                    AND NOT ()-[:CALLS]->(p)
                    RETURN p.name AS name, p.id AS id
                    ORDER BY p.name
                """)
                orphans = [dict(r) for r in orphans_result]

                # ── Pipeline selector ─────────────────────
                if not pipeline:
                    typer.echo(f"{GOLD}📋 Available pipelines:{RESET}\n")

                    idx = 1
                    menu_items = []

                    # Show families
                    for family in families:
                        parent_stats = get_snap_stats(session, family['parent_id'])
                        parent_warning = " ⚠️ Large" if parent_stats['snap_count'] > 30 else ""
                        typer.echo(f"  {idx}. 🔗 {family['parent_name']}")
                        typer.echo(
                            f"      ├── 🔑 {family['parent_name']} "
                            f"({parent_stats['snap_count']} snaps · parent{parent_warning})"
                        )
                        for child in family['children']:
                            child_stats  = get_snap_stats(session, child['id'])
                            child_warning = " ⚠️ Large" if child_stats['snap_count'] > 30 else ""
                            typer.echo(
                                f"      └── 📤 {child['name']} "
                                f"({child_stats['snap_count']} snaps · child{child_warning})"
                            )
                        menu_items.append({
                            'type':   'family',
                            'parent': family,
                        })
                        idx += 1

                    # Show orphans
                    for orphan in orphans:
                        orphan_stats   = get_snap_stats(session, orphan['id'])
                        orphan_warning = " ⚠️ Large" if orphan_stats['snap_count'] > 30 else ""
                        typer.echo(
                            f"  {idx}. 📊 {orphan['name']} "
                            f"({orphan_stats['snap_count']} snaps{orphan_warning})"
                        )
                        menu_items.append({
                            'type':     'orphan',
                            'pipeline': orphan,
                        })
                        idx += 1

                    typer.echo(f"  {idx}. All pipelines")
                    typer.echo("")

                    choice = typer.prompt(
                        "Which pipeline would you like to view?",
                        default="all"
                    )

                    if choice == str(idx) or choice.lower() == "all":
                        selected_ids = (
                            [f['parent_id'] for f in families] +
                            [c['id'] for f in families for c in f['children']] +
                            [o['id'] for o in orphans]
                        )
                    else:
                        try:
                            chosen = menu_items[int(choice) - 1]
                            if chosen['type'] == 'family':
                                selected_ids = (
                                    [chosen['parent']['parent_id']] +
                                    [c['id'] for c in chosen['parent']['children']]
                                )
                            else:
                                selected_ids = [chosen['pipeline']['id']]
                        except (ValueError, IndexError):
                            selected_ids = [
                                f['parent_id'] for f in families
                                if choice.lower() in f['parent_name'].lower()
                            ]

                else:
                    result = session.run("""
                        MATCH (p:Pipeline)
                        WHERE toLower(p.name) CONTAINS toLower($name)
                        RETURN p.id AS id
                    """, name=pipeline)
                    selected_ids = [r['id'] for r in result]

                if not selected_ids:
                    typer.echo(f"{RED}❌ No pipeline found{RESET}")
                    raise typer.Exit(1)

                # ── Fetch selected pipelines ───────────────
                pipelines_result = session.run("""
                    MATCH (p:Pipeline)
                    WHERE p.id IN $ids
                    OPTIONAL MATCH (p)-[:HAS_SNAP]->(s:Snap)
                    OPTIONAL MATCH (p)-[:CALLS]->(child:Pipeline)
                    OPTIONAL MATCH (parent:Pipeline)-[:CALLS]->(p)
                    RETURN
                        p.name AS name,
                        p.id   AS id,
                        count(DISTINCT s)      AS snap_count,
                        count(DISTINCT child)  AS children,
                        count(DISTINCT parent) AS parents
                    ORDER BY p.name
                """, ids=selected_ids)
                pipelines = [dict(r) for r in pipelines_result]

                typer.echo("")

                # ── Build tree ────────────────────────────
                root = Tree("🫧 [bold gold1]Goldilocks Pipeline Graph[/bold gold1]")

                for p in pipelines:
                    snap_str   = f"{p['snap_count']} snaps"
                    parent_str = f"{p['parents']} parent{'s' if p['parents'] != 1 else ''}"
                    child_str  = f"{p['children']} child{'ren' if p['children'] != 1 else ''}"

                    # ── Size warning ──────────────────────
                    if p['snap_count'] > 30:
                        size_warning = " [yellow]⚠️  Large pipeline[/yellow]"
                    elif p['snap_count'] > 15:
                        size_warning = " [yellow]⚡ Complex[/yellow]"
                    else:
                        size_warning = ""

                    pipe_tree = root.add(
                        f"[cyan]📊 {p['name']}[/cyan] "
                        f"[dim]({snap_str} · {parent_str} · {child_str})[/dim]"
                        f"{size_warning}"
                    )
                    render_pipeline(session, p, pipe_tree)

                console.print(root)
                console.print()
                console.print()
                typer.echo("")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed: {e}{RESET}\n")
        raise typer.Exit(1)