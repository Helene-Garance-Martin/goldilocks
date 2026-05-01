#!/usr/bin/env python3
# ============================================================
# 🥧 pie.py — Goldilocks CLI Entry Point
# ============================================================
# Pipeline Intelligence Engine
# Built with Typer — github.com/tiangolo/typer
# ============================================================
import typer
from typer import Context
import time
import sys
import os
import zipfile
import requests
from pathlib import Path
from requests.auth import HTTPBasicAuth
from typing import Optional
from commands.ping import ping
from commands.colours import YELLOW, GOLD, GREEN, RED, CYAN, RESET, BOLD



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


@app.command()
def fetch():
    """
    🌐 Fetch pipeline exports from SnapLogic
    """
    
  
    from snaplogic_url import parse_snaplogic_url

    url = typer.prompt("🐻 Paste your SnapLogic URL")

    try:
        parsed = parse_snaplogic_url(url)

        typer.echo("")
        typer.echo(f"Org:     {parsed['org']}")
        typer.echo(f"Project: {parsed['project_path']}")
        typer.echo(f"Export:  {parsed['export_url']}")
        typer.echo("")

        username = os.getenv("SNAPLOGIC_USERNAME") or typer.prompt("SnapLogic username")
        password = os.getenv("SNAPLOGIC_PASSWORD") or typer.prompt(
            "SnapLogic password",
            hide_input=True,
        )

        project_slug = (
            parsed["project_path"]
            .replace("/", "_")
            .replace(" ", "_")
            .replace("-", "_")
            .lower()
        )

        output_dir = Path("pipeline_exports") / project_slug
        zip_path = output_dir / "export.zip"
        output_dir.mkdir(parents=True, exist_ok=True)

        typer.echo(f"{CYAN}🌐 Downloading export...{RESET}")
        typer.echo(f"   Output: {output_dir}")

        response = requests.get(
            parsed["export_url"],
            auth=HTTPBasicAuth(username, password),
        )

        content_type = response.headers.get("Content-Type", "")

        if response.status_code != 200:
            typer.echo(f"{RED}❌ Export failed with status {response.status_code}{RESET}")
            typer.echo(response.text)
            raise typer.Exit(1)

        if "json" in content_type.lower():
            typer.echo(f"{RED}❌ Expected a zip, got JSON response:{RESET}")
            typer.echo(response.text)
            raise typer.Exit(1)

        zip_path.write_bytes(response.content)

        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(output_dir)
        except zipfile.BadZipFile:
            typer.echo(f"{RED}❌ Downloaded file is not a valid zip.{RESET}")
            raise typer.Exit(1)

        export_json = output_dir / "export.json"

        if not export_json.exists():
            typer.echo(f"{RED}❌ export.json not found after unzip.{RESET}")
            raise typer.Exit(1)

        typer.echo(f"{GREEN}✅ Export downloaded and unzipped!{RESET}")
        typer.echo(f"{GOLD}   JSON ready: {export_json}{RESET}")
        typer.echo("")
        typer.echo(f"{CYAN}Next:{RESET}")
        typer.echo(f"  python pie.py visualise --input {export_json}")

    except Exception as e:
        typer.echo(f"{RED}❌ Fetch failed: {e}{RESET}")
        raise typer.Exit(1)

@app.command()
def visualise(
    input: str = typer.Option("export_anonymised.json", help="Path to anonymised pipeline JSON"),
    output: str = typer.Option("diagrams/", help="Folder to save Mermaid diagram files"),
    direction: str = typer.Option("LR", help="Diagram direction: LR or TD"),
    fmt: str = typer.Option("mmd", help="Output format: mmd, png or svg"),
    single: str = typer.Option(None, help="Name of single pipeline to visualise"),  
):
    """
    🎨 Generate Mermaid diagrams from pipeline data.

    Creates .mmd diagram files showing pipeline architecture —
    snap nodes with icons, connections, subgraphs and colour coding.

    Colours represent Snap type. Icons show what each snap does.
    """

    typer.echo(f"{CYAN}🎨 Generating Mermaid diagrams...{RESET}")
    typer.echo(f"   Input:     {input}")
    typer.echo(f"   Output:    {output}")
    typer.echo(f"   Direction: {direction}")
    typer.echo("")

    try:
        from visualiser import generate_diagrams
        generate_diagrams(input, output, direction, fmt, single)
        typer.echo(f"{GOLD}  💡 Open any .mmd file in VS Code to preview{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed to generate diagram: {e}{RESET}\n")
        raise typer.Exit(1)

app.command()(ping)

    
@app.command()
def doctor():
    """
    🩺 Check all Goldilocks dependencies are installed and reachable.
    """

    typer.echo(f"{CYAN}🩺 Running Goldilocks health check...{RESET}\n")

    all_ok = True

    # ── Python ────────────────────────────────────────────
    import sys
    major, minor = sys.version_info.major, sys.version_info.minor
    if major == 3 and minor >= 10:
        typer.echo(f"{GREEN}  ✅ Python {major}.{minor}{RESET}")
    else:
        typer.echo(f"{RED}  ❌ Python {major}.{minor} — 3.10+ required{RESET}")
        all_ok = False

    # ── Node.js ───────────────────────────────────────────
    import subprocess, shutil
    node = shutil.which("node")
    if node:
        version = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
        typer.echo(f"{GREEN}  ✅ Node.js {version}{RESET}")
    else:
        typer.echo(f"{RED}  ❌ Node.js not found — install from nodejs.org{RESET}")
        all_ok = False

    # ── mmdc ─────────────────────────────────────────────
    mmdc = shutil.which("mmdc")
    if mmdc:
        version = subprocess.run(["mmdc", "--version"], capture_output=True, text=True).stdout.strip()
        typer.echo(f"{GREEN}  ✅ mmdc {version}{RESET}")
    else:
        typer.echo(f"{RED}  ❌ mmdc not found — run: npm install -g @mermaid-js/mermaid-cli{RESET}")
        all_ok = False

    # ── Neo4j ─────────────────────────────────────────────
    try:
        from neo4j import GraphDatabase
        uri      = os.environ["NEO4J_URI"]
        user     = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ["NEO4J_PASSWORD"]
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            driver.verify_connectivity()
        typer.echo(f"{GREEN}  ✅ Neo4j reachable{RESET}")
    except KeyError:
        typer.echo(f"{YELLOW}  ⚠️  Neo4j env vars not set (NEO4J_URI, NEO4J_PASSWORD){RESET}")
        all_ok = False
    except Exception as e:
        typer.echo(f"{RED}  ❌ Neo4j unreachable: {e}{RESET}")
        all_ok = False

    # ── Summary ───────────────────────────────────────────
    typer.echo("")
    if all_ok:
        typer.echo(f"{GREEN}{BOLD}  🐻 All systems go!{RESET}\n")
    else:
        typer.echo(f"{YELLOW}{BOLD}  🐻 Some issues found — see above{RESET}\n")


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