# commands/ping.py
import os
import typer
from rich.console import Console
from commands.colours import CYAN, GREEN, RED, GOLD, RESET

console = Console()

def ping():
    """
    🏓 Ping Neo4j — check the instance is alive and warm.

    Run this every few days to prevent Aura Free tier
    from deleting your instance due to inactivity!
    """
    typer.echo(f"{CYAN}🏓 Pinging Neo4j...{RESET}\n")

    try:
        from neo4j import GraphDatabase

        uri      = os.environ["NEO4J_URI"]
        user     = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ["NEO4J_PASSWORD"]

        with console.status("[magenta]Connecting to Neo4j...[/magenta]", spinner="dots"):
            with GraphDatabase.driver(uri, auth=(user, password)) as driver:
                driver.verify_connectivity()
                with driver.session() as session:
                    total = session.run("MATCH (n) RETURN count(n) AS total").single()["total"]
                    pipes = session.run("MATCH (p:Pipeline) RETURN count(p) AS total").single()["total"]
                    snaps = session.run("MATCH (s:Snap) RETURN count(s) AS total").single()["total"]

        typer.echo(f"{GREEN}✅ Neo4j instance is alive!{RESET}\n")
        typer.echo(f"   Total nodes:  {total}")
        typer.echo(f"   Pipelines:    {pipes}")
        typer.echo(f"   Snaps:        {snaps}")
        typer.echo(f"\n{GOLD}  Instance kept warm 🌟{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Neo4j unreachable: {e}{RESET}\n")
        raise typer.Exit(1)