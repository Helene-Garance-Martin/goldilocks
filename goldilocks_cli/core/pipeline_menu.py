import os
import typer

from neo4j import GraphDatabase

from goldilocks_cli.colours import RED, RESET



def pipeline_menu() -> str:
    """Interactive pipeline selector, shown only when no name is given."""
    from neo4j import GraphDatabase

    from goldilocks_cli.core.credentials import (
        require_credential, get_credential, NEO4J_DEFAULT_USER,
    )

    uri = require_credential("NEO4J_URI", "list your pipelines")
    user = get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
    password = require_credential("NEO4J_PASSWORD", "list your pipelines")

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (p:Pipeline)
                OPTIONAL MATCH (p)-[:HAS_SNAP]->(s:Snap)
                OPTIONAL MATCH (p)-[:CALLS]->(child:Pipeline)
                OPTIONAL MATCH (parent:Pipeline)-[:CALLS]->(p)
                RETURN
                    p.name AS name,
                    count(DISTINCT s) AS snap_count,
                    count(DISTINCT child) AS children,
                    count(DISTINCT parent) AS parents
                ORDER BY name
                """
            )
            pipelines = [dict(r) for r in result]

    if not pipelines:
        typer.echo(f"{RED}❌ No pipelines found in Neo4j{RESET}")
        raise typer.Exit(1)

    typer.echo("  Which pipeline?\n")

    for i, pipeline in enumerate(pipelines, 1):
        snap_str = f"{pipeline['snap_count']} snaps"
        parent_str = f"{pipeline['parents']} parent{'s' if pipeline['parents'] != 1 else ''}"
        child_str = f"{pipeline['children']} child{'ren' if pipeline['children'] != 1 else ''}"

        suffix = f"{snap_str} · {parent_str} · {child_str}"

        typer.echo(
            f"    {i}. {pipeline['name']} "
            f"({suffix})"
        )

    typer.echo("")

    choice = typer.prompt("  Select", default="1")

    try:
        return pipelines[int(choice) - 1]["name"]
    except (ValueError, IndexError):
        typer.echo(f"{RED}❌ Invalid selection{RESET}")
        raise typer.Exit(1)
