# commands/ping.py
import typer
from rich.console import Console
from goldilocks_cli.colours import CYAN, GREEN, RED, GOLD, RESET

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

        from goldilocks_cli.core.credentials import (
            require_credential, get_credential,
            NEO4J_DEFAULT_USER, CredentialMissing,
        )

        uri      = require_credential("NEO4J_URI", "ping your graph")
        user     = get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
        password = require_credential("NEO4J_PASSWORD", "ping your graph")

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

    except CredentialMissing as e:
        typer.echo(f"{RED}{e}{RESET}\n")
        raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"{RED}❌ Neo4j unreachable: {e}{RESET}\n")
        raise typer.Exit(1)