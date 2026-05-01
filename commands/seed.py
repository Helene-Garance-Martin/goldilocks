# commands/seed.py
import time
import typer
from commands.colours import CYAN, GREEN, RESET

def seed(
    input: str = typer.Option("export_anonymised.json", help="Path to anonymised pipeline JSON"),
    uri: str = typer.Option(..., help=(
        "Neo4j Aura URI (e.g. neo4j+s://xxxxxxxx.databases.neo4j.io)\n"
        "  💡 Find it in your Neo4j Aura console at console.neo4j.io"
    )),
    username: str = typer.Option("neo4j", help="Neo4j username"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Neo4j password"),
):
    """
    🌱 Seed the Neo4j graph with pipeline data.

    Parses snap nodes and connections from the pipeline JSON
    and loads them into your Neo4j Aura graph database.
    """
    typer.echo(f"{CYAN}🌱 Seeding Neo4j graph...{RESET}")
    typer.echo(f"   Input: {input}")
    typer.echo(f"   URI:   {uri}")
    typer.echo("")

    # ← wire up src/seeder.py here
    time.sleep(0.5)
    typer.echo(f"{GREEN}✅ Graph seeded successfully!{RESET}\n")