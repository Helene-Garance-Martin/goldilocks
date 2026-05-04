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
from commands.ask import ask
from commands.seed import seed
from commands.run import run
from commands.sanitise import sanitise
from commands.anonymise import anonymise
from commands.audit import audit



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

app.command()(sanitise)

app.command()(ping)

app.command()(doctor)

app.command()(seed)

app.command()(ask)

app.command()(run)

app.command()(anonymise)

app.command()(audit)


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    app()