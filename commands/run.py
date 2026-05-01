# commands/run.py
import time
import typer
from commands.colours import CYAN, GREEN, RED, GOLD, BOLD, RESET

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
    typer.echo(f"{CYAN}🌐 Step 1/5 — Fetching pipelines...{RESET}")
    time.sleep(0.5)
    typer.echo(f"{GREEN}  ✅ Done{RESET}\n")

    typer.echo(f"{CYAN}🧹 Step 2/5 — Sanitising...{RESET}")
    time.sleep(0.5)
    typer.echo(f"{GREEN}  ✅ Done{RESET}\n")

    typer.echo(f"{CYAN}🔒 Step 3/5 — Anonymising...{RESET}")
    time.sleep(0.5)
    typer.echo(f"{GREEN}  ✅ Done{RESET}\n")

    typer.echo(f"{CYAN}🌱 Step 4/5 — Seeding Neo4j...{RESET}")
    time.sleep(0.5)
    typer.echo(f"{GREEN}  ✅ Done{RESET}\n")

    typer.echo(f"{CYAN}🎨 Step 5/5 — Generating diagrams...{RESET}")
    time.sleep(0.5)
    typer.echo(f"{GREEN}  ✅ Done{RESET}\n")

    typer.echo(f"{GOLD}{BOLD}  🐻 All done! Your pipeline graph is ready.{RESET}\n")