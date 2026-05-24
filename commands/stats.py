# commands/stats.py

import os
import typer

from rich.console import Console
from rich.table import Table
from commands.colours import CYAN, GREEN, RED, RESET

console = Console()


def stats(
    uri: str = typer.Option(
        os.getenv("NEO4J_URI", ""),
        help="Neo4j Aura URI",
    ),
    username: str = typer.Option(
        os.getenv("NEO4J_USER", "neo4j"),
        help="Neo4j username",
    ),
    password: str = typer.Option(
        os.getenv("NEO4J_PASSWORD", ""),
        help="Neo4j password",
    ),
):
    """
    📊 Show graph topology statistics.
    """

    if not uri:
        typer.echo(f"{RED}❌ NEO4J_URI not configured.{RESET}")
        raise typer.Exit(1)

    if not password:
        typer.echo(f"{RED}❌ NEO4J_PASSWORD not configured.{RESET}")
        raise typer.Exit(1)

    try:
        from neo4j import GraphDatabase

        with GraphDatabase.driver(uri, auth=(username, password)) as driver:
            driver.verify_connectivity()

            with driver.session() as session:
                pipeline_count = session.run(
                    "MATCH (p:Pipeline) RETURN count(p) AS count"
                ).single()["count"]

                snap_count = session.run(
                    "MATCH (s:Snap) RETURN count(s) AS count"
                ).single()["count"]

                has_snap_count = session.run(
                    "MATCH ()-[r:HAS_SNAP]->() RETURN count(r) AS count"
                ).single()["count"]

                connects_to_count = session.run(
                    "MATCH ()-[r:CONNECTS_TO]->() RETURN count(r) AS count"
                ).single()["count"]

                calls_count = session.run(
                    "MATCH ()-[r:CALLS]->() RETURN count(r) AS count"
                ).single()["count"]

                snap_types = session.run(
                    """
                    MATCH (:Pipeline)-[:HAS_SNAP]->(s:Snap)
                    RETURN s.type AS snap_type, count(s) AS count
                    ORDER BY count DESC
                    """
                )

                router_pipelines = session.run(
                    """
                    MATCH (p:Pipeline)-[:HAS_SNAP]->(s:Snap)
                    WHERE toLower(s.type) = "router"
                    RETURN count(DISTINCT p) AS count
                    """
                ).single()["count"]

                pipeexec_pipelines = session.run(
                    """
                    MATCH (p:Pipeline)-[:HAS_SNAP]->(s:Snap)
                    WHERE toLower(s.type) = "pipeexec"
                    RETURN count(DISTINCT p) AS count
                    """
                ).single()["count"]

        typer.echo(f"{CYAN}📊 Goldilocks Graph Stats{RESET}\n")

        summary = Table(show_header=True, header_style="bold magenta")
        summary.add_column("Metric", style="cyan")
        summary.add_column("Count", style="green", justify="right")

        summary.add_row("Pipelines", str(pipeline_count))
        summary.add_row("Snaps", str(snap_count))
        summary.add_row("HAS_SNAP", str(has_snap_count))
        summary.add_row("CONNECTS_TO", str(connects_to_count))
        summary.add_row("CALLS", str(calls_count))
        summary.add_row("Pipelines using Router", str(router_pipelines))
        summary.add_row("Pipelines using PipeExec", str(pipeexec_pipelines))

        console.print(summary)
        console.print()

        type_table = Table(
            title="Snap types",
            show_header=True,
            header_style="bold magenta",
        )
        type_table.add_column("Snap type", style="cyan")
        type_table.add_column("Count", style="green", justify="right")

        for row in snap_types:
            type_table.add_row(
                row["snap_type"] or "unknown",
                str(row["count"]),
            )

        console.print(type_table)
        console.print()

        typer.echo(f"{GREEN}✅ Stats complete.{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Stats failed: {e}{RESET}\n")
        raise typer.Exit(1)