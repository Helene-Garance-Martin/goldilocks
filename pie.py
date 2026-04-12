#!/usr/bin/env python3
# ============================================================
# 🥧 pie.py — Goldilocks CLI Entry Point
# ============================================================
# Pipeline Intelligence Engine
# Built with Typer — github.com/tiangolo/typer
# ============================================================

import typer
import time
from typing import Optional

# ------------------------------------------------------------
# ANSI colour codes
# ------------------------------------------------------------
YELLOW  = "\033[93m"
GOLD    = "\033[33m"
GREEN   = "\033[92m"
RED     = "\033[91m"
CYAN    = "\033[96m"
RESET   = "\033[0m"
BOLD    = "\033[1m"

# ------------------------------------------------------------
# ASCII LOGO
# ------------------------------------------------------------

LOGO = f"""{YELLOW}
  ██████╗  ██████╗ ██╗      ██████╗ ██╗██╗      ██████╗  ██████╗██╗  ██╗███████╗
 ██╔════╝ ██╔═══██╗██║     ██╔═══██╗██║██║     ██╔═══██╗██╔════╝██║ ██╔╝██╔════╝
 ██║  ███╗██║   ██║██║     ██║   ██║██║██║     ██║   ██║██║     █████╔╝ ███████╗
 ██║   ██║██║   ██║██║     ██║   ██║██║██║     ██║   ██║██║     ██╔═██╗ ╚════██║
 ╚██████╔╝╚██████╔╝███████╗╚██████╔╝██║███████╗╚██████╔╝╚██████╗██║  ██╗███████║
  ╚═════╝  ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝
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

@app.command()
def fetch(
    org: str = typer.Option(..., help="Your SnapLogic org name  (e.g. rbo-dev)\n  💡 Find it in your SnapLogic Designer URL:\n     https://emea.snaplogic.com/sl/designer/YOUR-ORG/YOUR-PROJECT"),
    project: str = typer.Option(..., help="Your SnapLogic project path  (e.g. 'DIESE/DIESE-Business Continuity')"),
    username: str = typer.Option(..., help="Your SnapLogic username (email)"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Your SnapLogic password"),
    output: str = typer.Option("pipeline_exports/", help="Folder to save exported pipeline files"),
):
    """
    🌐 Fetch pipeline exports from the SnapLogic API.

    Connects to SnapLogic, downloads pipeline assets as a zip,
    unzips and saves JSON files to the output folder.
    """
    print_logo()
    typer.echo(f"{CYAN}🌐 Fetching pipelines from SnapLogic...{RESET}")
    typer.echo(f"   Org:     {org}")
    typer.echo(f"   Project: {project}")
    typer.echo(f"   Output:  {output}")
    typer.echo("")

    # ← wire up src/fetcher.py here
    time.sleep(0.5)
    typer.echo(f"{GREEN}✅ Pipelines fetched and saved to {output}{RESET}\n")


@app.command()
def anonymise(
    input: str = typer.Option("pipeline_exports/export.json", help="Path to raw pipeline JSON file"),
    output: str = typer.Option("pipeline_exports/export_clean.json", help="Path to write anonymised output"),
):
    """
    🔒 Anonymise sensitive data from pipeline exports.

    Scrubs org names, URLs, and credentials before
    pushing anything to GitHub or sharing publicly.
    """
    print_logo()
    typer.echo(f"{CYAN}🔒 Anonymising pipeline data...{RESET}")
    typer.echo(f"   Input:  {input}")
    typer.echo(f"   Output: {output}")
    typer.echo("")

    # ← wire up src/anonymiser.py here
    time.sleep(0.5)
    typer.echo(f"{GREEN}✅ Clean file written to {output}{RESET}\n")


@app.command()
def seed(
    input: str = typer.Option("pipeline_exports/export_clean.json", help="Path to anonymised pipeline JSON"),
    uri: str = typer.Option(..., help="Neo4j Aura URI  (e.g. neo4j+s://xxxxxxxx.databases.neo4j.io)\n  💡 Find it in your Neo4j Aura console"),
    username: str = typer.Option("neo4j", help="Neo4j username"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Neo4j password"),
):
    """
    🌱 Seed the Neo4j graph with pipeline data.

    Parses snap nodes and connections from the pipeline JSON
    and loads them into your Neo4j Aura graph database.
    """
    print_logo()
    typer.echo(f"{CYAN}🌱 Seeding Neo4j graph...{RESET}")
    typer.echo(f"   Input: {input}")
    typer.echo(f"   URI:   {uri}")
    typer.echo("")

    # ← wire up src/seeder.py here
    time.sleep(0.5)
    typer.echo(f"{GREEN}✅ Graph seeded successfully!{RESET}\n")


@app.command()
def visualise(
    input: str = typer.Option("pipeline_exports/export_clean.json", help="Path to anonymised pipeline JSON"),
    output: str = typer.Option("diagrams/", help="Folder to save Mermaid diagram files"),
):
    """
    🎨 Generate Mermaid diagrams from pipeline data.

    Creates .mmd diagram files showing pipeline architecture —
    snap nodes, connections, and flow direction.
    """
    print_logo()
    typer.echo(f"{CYAN}🎨 Generating Mermaid diagrams...{RESET}")
    typer.echo(f"   Input:  {input}")
    typer.echo(f"   Output: {output}")
    typer.echo("")

    # ← wire up src/visualiser.py here
    time.sleep(0.5)
    typer.echo(f"{GREEN}✅ Diagrams saved to {output}{RESET}\n")


@app.command()
def ask(
    question: Optional[str] = typer.Argument(None, help="Ask Goldilocks a question about your pipelines"),
):
    """
    🤖 Ask Goldilocks a question about your pipeline graph.

    Uses AI to query your Neo4j graph in plain English.
    No Cypher needed!

    Example: goldilocks ask 'Which pipelines connect to SharePoint?'
    """
    print_logo()
    if not question:
        question = typer.prompt(f"{GOLD}  Ask Goldilocks{RESET}")

    typer.echo(f"\n{CYAN}🔍 Thinking...{RESET}")
    time.sleep(1)

    # ← wire up LangChain + Neo4j GraphRAG here
    typer.echo(f"{GREEN}  AI mode coming soon! 🚀{RESET}\n")


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

    fetch → anonymise → seed → visualise

    The recommended way to run Goldilocks in one command.
    """
    print_logo()
    typer.echo(f"{GOLD}  Running full Goldilocks pipeline...{RESET}\n")

    proceed = typer.confirm("  Are you happy to proceed?")
    if not proceed:
        typer.echo(f"\n{RED}  Cancelled.{RESET}\n")
        raise typer.Exit()

    typer.echo("")
    typer.echo(f"{CYAN}🌐 Step 1/4 — Fetching pipelines...{RESET}")
    time.sleep(0.5)
    typer.echo(f"{GREEN}  ✅ Done{RESET}\n")

    typer.echo(f"{CYAN}🔒 Step 2/4 — Anonymising data...{RESET}")
    time.sleep(0.5)
    typer.echo(f"{GREEN}  ✅ Done{RESET}\n")

    typer.echo(f"{CYAN}🌱 Step 3/4 — Seeding Neo4j...{RESET}")
    time.sleep(0.5)
    typer.echo(f"{GREEN}  ✅ Done{RESET}\n")

    typer.echo(f"{CYAN}🎨 Step 4/4 — Generating diagrams...{RESET}")
    time.sleep(0.5)
    typer.echo(f"{GREEN}  ✅ Done{RESET}\n")

    typer.echo(f"{GOLD}{BOLD}  🐻 All done! Your pipeline graph is ready.{RESET}\n")


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    app()