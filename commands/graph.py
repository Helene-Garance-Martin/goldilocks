# commands/graph.py
# ------------------------------------------------------------
# GOLDILOCKS — Pipeline Graph Visualiser (Terminal)
# ------------------------------------------------------------
# Renders pipeline relationships as a beautiful Rich tree
# directly in the terminal.
# ------------------------------------------------------------

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import typer
from rich.console import Console
from rich.tree import Tree
from rich import print as rprint
from commands.colours import CYAN, GREEN, RED, GOLD, RESET

console = Console()

# Snap type icons
SNAP_ICONS = {
    "httpclient": "🌐",
    "script":     "📜",
    "pipeexec":   "📞",
    "sftp_get":   "📥",
    "sftp_put":   "📤",
    "mapper":     "🗺️",
    "filter":     "🔽",
    "trigger":    "⚡",
    "default":    "⚙️",
}

def show_graph(
    pipeline: str = typer.Option(None, help="Filter by pipeline name"),
):
    """
    🌳 Render pipeline relationships as a terminal graph.

    Shows pipeline architecture, snap types and
    parent/child relationships as a beautiful tree.
    """
    typer.echo(f"{CYAN}🌳 Building pipeline graph...{RESET}\n")

    try:
        from neo4j import GraphDatabase

        uri      = os.environ["NEO4J_URI"]
        user     = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ["NEO4J_PASSWORD"]

        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            with driver.session() as session:

                # Get all pipelines
                if pipeline:
                    pipelines = session.run(
                        "MATCH (p:Pipeline) WHERE toLower(p.name) CONTAINS toLower($name) RETURN p.name AS name, p.id AS id",
                        name=pipeline
                    )
                else:
                    pipelines = session.run(
                        "MATCH (p:Pipeline) RETURN p.name AS name, p.id AS id"
                    )

                pipelines = [dict(r) for r in pipelines]

                if not pipelines:
                    typer.echo(f"{RED}❌ No pipelines found{RESET}")
                    raise typer.Exit(1)

                # Build tree
                root = Tree("🫧 [bold gold1]Goldilocks Pipeline Graph[/bold gold1]")

                for p in pipelines:
                    # Pipeline node
                    pipe_tree = root.add(f"[cyan]📊 {p['name']}[/cyan]")

                    # Get snaps
                    snaps = session.run(
                        """
                        MATCH (p:Pipeline {id: $pid})-[:HAS_SNAP]->(s:Snap)
                        RETURN s.label AS label, s.type AS type, s.wipes_context AS wipes
                        """,
                        pid=p['id']
                    )

                    for snap in snaps:
                        icon  = SNAP_ICONS.get(snap['type'], "⚙️")
                        risk  = "⚠️ " if snap['wipes'] else "✅ "
                        pipe_tree.add(f"{risk}{icon} {snap['label']} [{snap['type']}]")

                    # Get child pipelines
                    calls = session.run(
                        """
                        MATCH (p:Pipeline {id: $pid})-[:CALLS]->(child:Pipeline)
                        RETURN child.name AS name
                        """,
                        pid=p['id']
                    )

                    for call in calls:
                        pipe_tree.add(f"[purple]📞 Calls → {call['name']}[/purple]")

                console.print(root)
                typer.echo("")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed: {e}{RESET}\n")
        raise typer.Exit(1)