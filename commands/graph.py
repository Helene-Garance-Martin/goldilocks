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
import time
from rich.text import Text
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

def get_upstream_names(session, pipeline_id: str) -> list[str]:
    result = session.run("""
        MATCH (parent:Pipeline)-[:CALLS]->(p:Pipeline {id: $pid})
        RETURN parent.name AS name
        ORDER BY parent.name
    """, pid=pipeline_id)
    return [r["name"] for r in result]


def get_downstream_calls(session, pipeline_id: str) -> list[dict]:
    result = session.run("""
        MATCH (p:Pipeline {id: $pid})-[:HAS_SNAP]->(s:Snap)
        WHERE s.child_pipeline IS NOT NULL
          AND s.child_pipeline <> ""

        WITH split(s.child_pipeline, "/")[-1] AS child_name,
             count(*) AS occurrences

        MATCH (child:Pipeline)
        WHERE child.name = child_name
           OR child.path ENDS WITH "/" + child_name

        RETURN child.name AS name,
               occurrences
        ORDER BY child.name
    """, pid=pipeline_id)
    return [dict(r) for r in result]

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

    calls = get_downstream_calls(session, p["id"])

    if calls:
        pipe_tree.add("[dim]── topology[/dim]")

    for call in calls:
        suffix = f" ×{call['occurrences']}" if call["occurrences"] > 1 else ""
        pipe_tree.add(
            f"[purple]🔀 Calls → {call['name']}{suffix}[/purple]"
        )


def show_graph(
    pipeline: str = typer.Option(None, help="Filter by pipeline name"),
    reveal: bool = typer.Option(False, "--reveal", help="Reveal graph line by line"),
    delay: float = typer.Option(0.035, "--delay", help="Delay between revealed lines"),
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

        uri = os.environ["NEO4J_URI"]
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ["NEO4J_PASSWORD"]

        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            with driver.session() as session:
                total = session.run(
                    "MATCH (p:Pipeline) RETURN count(p) AS total"
                ).single()["total"]

                if total == 0:
                    typer.echo(f"{GOLD}⚠️  Your graph is empty!{RESET}")
                    typer.echo("💡 Run: goldilocks seed --uri your-uri")
                    raise typer.Exit(0)

                families_result = session.run("""
                    MATCH (parent:Pipeline)-[:CALLS]->(child:Pipeline)
                    RETURN
                        parent.name AS parent_name,
                        parent.id   AS parent_id,
                        collect({name: child.name, id: child.id}) AS children
                    ORDER BY parent.name
                """)
                families = [dict(r) for r in families_result]

                orphans_result = session.run("""
                    MATCH (p:Pipeline)
                    WHERE NOT (p)-[:CALLS]->()
                      AND NOT ()-[:CALLS]->(p)
                    RETURN p.name AS name, p.id AS id
                    ORDER BY p.name
                """)
                orphans = [dict(r) for r in orphans_result]

                if not pipeline:
                    typer.echo(f"{GOLD}📋 Available pipelines:{RESET}\n")

                    idx = 1
                    menu_items = []

                    for family in families:
                        parent_stats = get_snap_stats(session, family["parent_id"])
                        parent_warning = (
                            " ⚠️ Large" if parent_stats["snap_count"] > 30 else ""
                        )

                        children = family["children"]
                        child_count = len(children)

                        typer.echo(f"  {idx}. 🔗 {family['parent_name']}")
                        typer.echo(
                            f"      ├── 📊 {parent_stats['snap_count']} snaps"
                            f"{parent_warning}"
                        )
                        typer.echo(
                            f"      ├── 📤 Calls: {child_count}"
                        )
                        typer.echo(
                            f"      ├── 📥 Called by: 0"
                        )

                        for i, child in enumerate(children):
                            branch = "└──" if i == len(children) - 1 else "├──"
                            child_stats = get_snap_stats(session, child["id"])
                            child_warning = (
                                " ⚠️ Large" if child_stats["snap_count"] > 30 else ""
                            )
                            typer.echo(
                                f"      {branch} 📤 {child['name']} "
                                f"({child_stats['snap_count']} snaps{child_warning})"
                            )
                            
                        menu_items.append({
                            "type": "family",
                            "parent": family,
                        })
                        idx += 1

                    for orphan in orphans:
                        orphan_stats = get_snap_stats(session, orphan["id"])
                        orphan_warning = (
                            " ⚠️ Large" if orphan_stats["snap_count"] > 30 else ""
                        )
                        typer.echo(
                            f"  {idx}. 📊 {orphan['name']} "
                            f"({orphan_stats['snap_count']} snaps{orphan_warning})"
                        )
                        menu_items.append({
                            "type": "orphan",
                            "pipeline": orphan,
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
                            [f["parent_id"] for f in families]
                            + [c["id"] for f in families for c in f["children"]]
                            + [o["id"] for o in orphans]
                        )
                    else:
                        try:
                            chosen = menu_items[int(choice) - 1]
                            if chosen["type"] == "family":
                                selected_ids = (
                                    [chosen["parent"]["parent_id"]]
                                    + [c["id"] for c in chosen["parent"]["children"]]
                                )
                            else:
                                selected_ids = [chosen["pipeline"]["id"]]
                        except (ValueError, IndexError):
                            selected_ids = [
                                f["parent_id"]
                                for f in families
                                if choice.lower() in f["parent_name"].lower()
                            ]

                else:
                    result = session.run("""
                        MATCH (p:Pipeline)
                        WHERE toLower(p.name) CONTAINS toLower($name)
                        RETURN p.id AS id
                    """, name=pipeline)
                    selected_ids = [r["id"] for r in result]

                if not selected_ids:
                    typer.echo(f"{RED}❌ No pipeline found{RESET}")
                    raise typer.Exit(1)

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

                root = Tree("🫧 [bold gold1]Goldilocks Pipeline Graph[/bold gold1]")

                for p in pipelines:
                    snap_str = f"{p['snap_count']} snaps"
                    parent_str = f"{p['parents']} parent{'s' if p['parents'] != 1 else ''}"
                    child_str = f"{p['children']} child{'ren' if p['children'] != 1 else ''}"

                    if p["snap_count"] > 30:
                        size_warning = " [yellow]⚠️  Large pipeline[/yellow]"
                    elif p["snap_count"] > 15:
                        size_warning = " [yellow]⚡ Complex[/yellow]"
                    else:
                        size_warning = ""

                    pipe_tree = root.add(
                        f"[cyan]📊 {p['name']}[/cyan]{size_warning}"
                    )

                    pipe_tree.add(f"[dim]📊 {snap_str}[/dim]")
                    pipe_tree.add(f"[dim]📤 Calls: {p['children']}[/dim]")
                    pipe_tree.add(f"[dim]📥 Called by: {p['parents']}[/dim]")

                    upstream = get_upstream_names(session, p["id"])
                    downstream = get_downstream_calls(session, p["id"])

                    if upstream:
                        upstream_branch = pipe_tree.add("[green]🌿 Upstream[/green]")

                        for name in upstream:
                            upstream_branch.add(f"[dim]{name}[/dim]")

                    if downstream:
                        downstream_branch = pipe_tree.add("[magenta]🌿 Downstream[/magenta]")

                        for d in downstream:
                            label = (
                                f"{d['name']} ×{d['occurrences']}"
                                if d["occurrences"] > 1
                                else d["name"]
                            )
                            downstream_branch.add(f"[dim]{label}[/dim]")

                    render_pipeline(session, p, pipe_tree)

                
                if reveal:
                    with console.capture() as capture:
                        console.print(root)

                    text = capture.get()

                    for line in text.splitlines():
                        console.print(Text.from_ansi(line))
                        time.sleep(delay)
                else:
                    console.print(root)

                console.print()
                console.print()
                typer.echo("")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed: {e}{RESET}\n")
        raise typer.Exit(1)