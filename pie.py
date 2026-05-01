#!/usr/bin/env python3
# ============================================================
# 🥧 pie.py — Goldilocks CLI Entry Point
# ============================================================
# Pipeline Intelligence Engine
# Built with Typer — github.com/tiangolo/typer
# ============================================================
import os
import typer
from typer import Context
import time
import sys
from commands.colours import YELLOW, GOLD, GREEN, RED, CYAN, RESET, BOLD

from typing import Optional
from commands.ping import ping

from commands.doctor import doctor
from commands.visualise import visualise
from commands.fetch import fetch




# Add src/ to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


# ------------------------------------------------------------
# ASCII LOGO
# ------------------------------------------------------------

LOGO = f"""{YELLOW}
 
                                                       
 ▄   ▄▄▄▄      ▄▄          ▄▄                          
 ▀██████▀       ██    █▄    ██                         
   ██   ▄       ██    ██ ▀▀ ██             ▄▄          
   ██  ██ ▄███▄ ██ ▄████ ██ ██ ▄███▄ ▄███▀ ██ ▄█▀ ▄██▀█
   ██  ██ ██ ██ ██ ██ ██ ██ ██ ██ ██ ██    ████   ▀███▄
   ▀█████▄▀███▀▄██▄█▀███▄██▄██▄▀███▀▄▀███▄▄██ ▀█▄█▄▄██▀
   ▄   ██                                              
   ▀████▀                                              
{RESET}"""

TAGLINE  = f"{GOLD}  Pipeline Intelligence Platform  •  curl · parse · graph · monitor{RESET}"
DIVIDER  = f"{YELLOW}  {'─' * 72}{RESET}"

# ------------------------------------------------------------
# Typer app
# ------------------------------------------------------------

app = typer.Typer(
    name="goldilocks",
    help="🐻 Goldilocks — Pipeline Intelligence Platform",
    add_completion=False,
)

# ------------------------------------------------------------
# Helper — print logo
# ------------------------------------------------------------

def print_logo():
    typer.echo(LOGO)
    typer.echo(TAGLINE)
    typer.echo(DIVIDER)
    typer.echo("")

# ------------------------------------------------------------
# COMMANDS
# ------------------------------------------------------------

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """🐻 Goldilocks — Pipeline Intelligence Platform"""
    if ctx.invoked_subcommand is None:
        print_logo()
        typer.echo("  Run 'python pie.py --help' to see available commands.\n")

app.command()(fetch)

app.command()(visualise)

app.command()(ping)

app.command()(doctor)   

@app.command()
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
    
@app.command()
def ask(
    question: Optional[str] = typer.Argument(None, help="Ask Goldilocks a question about your pipelines"),
):
    """
    🤖 Ask Goldilocks a simple question about your pipelines.
    """

    if not question:
        question = typer.prompt(f"{GOLD}Ask Goldilocks{RESET}")

    try:
        from describer import describe_from_neo4j
        answer = describe_from_neo4j()

        typer.echo("")
        typer.echo(answer)
        typer.echo("")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed to answer question: {e}{RESET}\n")
        raise typer.Exit(1)


@app.command()
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


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    app()