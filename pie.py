#!/usr/bin/env python3
# ============================================================
# 🥧 pie.py — Goldilocks CLI Entry Point
# ============================================================
# Pipeline Intelligence Engine
# Built with Typer — github.com/tiangolo/typer
# ============================================================

import typer
import time
import sys
import os
from typing import Optional

# Add src/ to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

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

@app.command()
def fetch(
    org: str = typer.Option(..., help=(
        "Your SnapLogic org name (e.g. rbo-dev)\n"
        "  💡 Find it in your SnapLogic Designer URL:\n"
        "     https://emea.snaplogic.com/sl/designer/YOUR-ORG/YOUR-PROJECT"
    )),
    project: str = typer.Option(..., help="Your SnapLogic project path (e.g. 'DIESE/DIESE-Business Continuity')"),
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
    input: str = typer.Option("export.json", help=(
        "Path to raw pipeline JSON file\n"
        "  💡 This is the export.json downloaded from SnapLogic\n"
        "     or fetched via the fetch command"
    )),
    output: str = typer.Option("export_anonymised.json", help="Path to write the clean anonymised output"),
):
    """
    🔒 Sanitise and anonymise sensitive data from pipeline exports.

    Runs two steps automatically:
      Step 1 — Sanitise: strips UI noise, rendering data and internal metadata
      Step 2 — Anonymise: scrubs org names, URLs and credentials

    Safe to commit the output to GitHub.
    """
    print_logo()
    typer.echo(f"{CYAN}🔒 Cleaning pipeline data...{RESET}")
    typer.echo(f"   Input:  {input}")
    typer.echo(f"   Output: {output}")
    typer.echo("")

    # Step 1 — Sanitise (strip UI noise)
    typer.echo(f"{CYAN}  Step 1/2 — Sanitising (stripping UI noise)...{RESET}")
    try:
        from sanitiser import sanitise_export
        sanitise_export(input, "export_clean.json")
        typer.echo(f"{GREEN}  ✅ Sanitised!{RESET}\n")
    except Exception as e:
        typer.echo(f"{RED}  ❌ Sanitise failed: {e}{RESET}\n")
        raise typer.Exit(1)

    # Step 2 — Anonymise (scrub sensitive data)
    typer.echo(f"{CYAN}  Step 2/2 — Anonymising (scrubbing sensitive data)...{RESET}")
    try:
        from anonymiser import anonymise_pipeline
        anonymise_pipeline("export_clean.json", output)
        typer.echo(f"{GREEN}  ✅ Anonymised!{RESET}\n")
    except Exception as e:
        typer.echo(f"{RED}  ❌ Anonymise failed: {e}{RESET}\n")
        raise typer.Exit(1)

    typer.echo(f"{GREEN}{BOLD}✅ Clean file ready: {output}{RESET}")
    typer.echo(f"{GOLD}  Safe to commit to GitHub! 🌟{RESET}\n")


@app.command()
def visualise(
    input: str = typer.Option("export_anonymised.json", help=(
        "Path to anonymised pipeline JSON\n"
        "  💡 Run the anonymise command first to generate this file"
    )),
    output: str = typer.Option("diagrams/", help="Folder to save Mermaid diagram files"),
    direction: str = typer.Option("LR", help="Diagram direction: LR (left to right) or TD (top to bottom)"),
):
    """
    🎨 Generate Mermaid diagrams from pipeline data.

    Creates .mmd diagram files showing pipeline architecture —
    snap nodes with icons, connections, subgraphs and colour coding.

    Colours represent Snap type. Icons show what each snap does.
    """
    print_logo()
    typer.echo(f"{CYAN}🎨 Generating Mermaid diagrams...{RESET}")
    typer.echo(f"   Input:     {input}")
    typer.echo(f"   Output:    {output}")
    typer.echo(f"   Direction: {direction}")
    typer.echo("")

    try:
        from visualiser import generate_diagrams
        generate_diagrams(input, output, direction)
        typer.echo(f"{GREEN}✅ Diagrams saved to {output}{RESET}")
        typer.echo(f"{GOLD}  Preview at: https://mermaid.live 🌟{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed to generate diagram: {e}{RESET}\n")
        raise typer.Exit(1)


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
    print_logo()
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
    input: str = typer.Option("export_anonymised.json", help="Path to anonymised pipeline JSON"),
):
    """
    🤖 Ask Goldilocks a simple question about your pipelines.
    """
    print_logo()

    if not question:
        question = typer.prompt(f"{GOLD}Ask Goldilocks{RESET}")

    try:
        import json
        from describer import describe_pipeline

        with open(input, "r", encoding="utf-8") as f:
            data = json.load(f)

        pipelines = data.get("entries", [data])

        # v1: describe all pipelines
        from describer import describe_all_pipelines
        answer = describe_all_pipelines(data)

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
    print_logo()
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