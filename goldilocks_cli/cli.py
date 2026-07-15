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
from goldilocks_cli.colours import YELLOW, GOLD, GREEN, RED, CYAN, RESET, BOLD

from typing import Optional
from goldilocks_cli.commands.ping import ping

from goldilocks_cli.commands.doctor import doctor
from goldilocks_cli.commands.visualise import visualise
from goldilocks_cli.commands.fetch import fetch
from goldilocks_cli.commands.ask import ask
from goldilocks_cli.commands.seed import seed
from goldilocks_cli.commands.check import check
from goldilocks_cli.commands.sanitise import sanitise
from goldilocks_cli.commands.anonymise import anonymise
from goldilocks_cli.commands.audit import audit
from goldilocks_cli.commands.graph import show_graph
from goldilocks_cli.commands.stats import stats
from goldilocks_cli.commands.sieve import sieve
from goldilocks_cli.commands.inspect_export import inspect_export
from goldilocks_cli.commands.init import init



# Add src/ to path so we can import our modules


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
    # ── Credentials: load .env (env always wins), guard the configs ──
    from goldilocks_cli.core.credentials import (
        load_env_file,
        check_config_for_secrets,
    )
    from goldilocks_cli.core.config import config_paths

    load_env_file()
    for config_file in config_paths():
        for warning in check_config_for_secrets(config_file):
            typer.echo(f"{RED}{warning}{RESET}")

    if ctx.invoked_subcommand is None:
        print_logo()
        typer.echo(
            "  Run 'goldilocks welcome' to begin, or 'goldilocks --help' to see available commands.\n"
        )
app.command()(init)
app.command()(fetch)

app.command()(visualise)

app.command()(sanitise)
app.command()(check)

app.command()(ping)

app.command()(doctor)

app.command()(seed)

app.command()(ask)


app.command()(sieve)

app.command()(anonymise)

app.command()(audit)

app.command(name="show-graph")(show_graph)

app.command()(stats)

app.command("inspect-export")(inspect_export)


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    app()