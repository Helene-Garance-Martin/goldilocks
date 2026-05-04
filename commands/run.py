# commands/run.py
import time
import typer
from rich.console import Console
from commands.colours import CYAN, GREEN, RED, GOLD, BOLD, RESET

console = Console()

def run(
    org: str = typer.Option(..., help="Your SnapLogic org name"),
    project: str = typer.Option(..., help="Your SnapLogic project path"),
    username: str = typer.Option(..., help="Your SnapLogic username"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Your SnapLogic password"),
    neo4j_uri: str = typer.Option(..., help="Neo4j Aura URI"),
    neo4j_password: str = typer.Option(..., prompt=True, hide_input=True, help="Neo4j password"),
):
    """
    🚀 Run the full Goldilocks pipeline end to end.

    fetch → sanitise → anonymise → seed → visualise

    The recommended way to run Goldilocks in one command.
    """
    typer.echo(f"{GOLD}  Running full Goldilocks pipeline...{RESET}\n")

    proceed = typer.confirm("  Are you happy to proceed?")
    if not proceed:
        typer.echo(f"\n{RED}  Cancelled.{RESET}\n")
        raise typer.Exit()

    typer.echo("")

    steps = [
        ("🌐 Fetching pipelines",    "Fetching..."),
        ("🧹 Sanitising",            "Sanitising..."),
        ("🔒 Anonymising",           "Anonymising..."),
        ("🌱 Seeding Neo4j",         "Seeding graph..."),
        ("🎨 Generating diagrams",   "Generating..."),
    ]

    for i, (label, spinner_text) in enumerate(steps, 1):
        typer.echo(f"{CYAN}  Step {i}/5 — {label}...{RESET}")
        with console.status(f"[magenta]{spinner_text}[/magenta]", spinner="dots"):
            time.sleep(0.5)
        typer.echo(f"{GREEN}  ✅ Done{RESET}\n")

    typer.echo(f"{GOLD}{BOLD}  🐻 All done! Your pipeline graph is ready.{RESET}\n")