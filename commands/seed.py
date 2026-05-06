# commands/seed.py
import typer
from rich.console import Console
from commands.colours import CYAN, GREEN, RED, RESET

console = Console()

def seed(
    input: str = typer.Option("export_anonymised.json", help="Path to anonymised pipeline JSON"),
    uri: str = typer.Option(..., help="Neo4j Aura URI"),
    username: str = typer.Option("neo4j", help="Neo4j username"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Neo4j password"),
):
    """
    🌱 Seed the Neo4j graph with pipeline data.
    """
    typer.echo(f"{CYAN}🌱 Seeding Neo4j graph...{RESET}")
    typer.echo(f"   Input: {input}")
    typer.echo(f"   URI:   {uri}")
    typer.echo("")

    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

        os.environ["NEO4J_URI"]      = uri
        os.environ["NEO4J_USER"]     = username
        os.environ["NEO4J_PASSWORD"] = password

        with console.status("[magenta]Seeding graph...[/magenta]", spinner="dots"):
            from pipeline_seeder import main
            main()

        typer.echo(f"{GREEN}✅ Graph seeded successfully!{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Seeding failed: {e}{RESET}\n")
        raise typer.Exit(1)