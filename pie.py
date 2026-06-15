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
from rich.console import Console
from rich.panel import Panel
import time
import sys
from commands.colours import YELLOW, GOLD, GREEN, RED, CYAN, RESET, BOLD

from typing import Optional
from commands.ping import ping

from commands.doctor import doctor
from commands.visualise import visualise
from commands.fetch import fetch
from commands.ask import ask
from commands.seed import seed
from commands.run import run
from commands.sanitise import sanitise
from commands.anonymise import anonymise
from commands.audit import audit
from commands.graph import show_graph
from commands.stats import stats



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

TAGLINE  = f"{GOLD} Semantic Topology • traverse · graph · discover{RESET}"
DIVIDER  = f"{YELLOW}  {'─' * 72}{RESET}"

# ------------------------------------------------------------
# Typer app
# ------------------------------------------------------------

app = typer.Typer(
    name="goldilocks",
    help="🫧 Goldilocks — Pipeline Intelligence Platform",
    add_completion=False,
)

console = Console()

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
def welcome():

    console.print("\n🐻 Welcome to\n")
    time.sleep(0.15)

    print_logo()
    time.sleep(0.45)

    for line in [
        "Pipeline Intelligence Platform",
        "",
        "Semantic Topology for Integration Pipelines",
        "",
        "From RAGs to DAGs to Riches 🍓",
        "",
        "Get started:",
        "  goldilocks doctor",
        "",
        "Need help?",
        "  goldilocks --help",
    ]:
        console.print(line)
        time.sleep(0.12)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """🫧 Goldilocks — Pipeline Intelligence Platform"""
    if ctx.invoked_subcommand is None:
        print_logo()
        typer.echo(
            "  Run 'goldilocks welcome' to begin, or 'goldilocks --help' to see available commands.\n"
        )

app.command()(fetch)

app.command()(visualise)

app.command()(sanitise)

app.command()(ping)

app.command()(doctor)

app.command()(seed)

app.command()(ask)

# app.command()(run)

app.command()(anonymise)

app.command()(audit)

app.command(name="show-graph")(show_graph)

app.command()(stats)


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    app()