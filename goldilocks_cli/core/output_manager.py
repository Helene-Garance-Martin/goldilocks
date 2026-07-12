# src/output_manager.py
from pathlib import Path
import os
import webbrowser

import pyperclip
import typer

from goldilocks_cli.colours import GOLD, GREEN, RED, RESET


def open_rendered_file(path: Path) -> None:
    """Open rendered diagram when supported."""

    if path.suffix not in [".svg", ".png"]:
        typer.echo(
            f"{GOLD}💡 --open currently supports svg/png outputs{RESET}"
        )
        return

    if os.environ.get("CODESPACES"):
        typer.echo(
            f"\n{GOLD}💡 remote environment — "
            f"open the rendered file from VS Code{RESET}"
        )
        return

    webbrowser.open(path.resolve().as_uri())


def print_confluence_hint(path: Path, copied: bool = False) -> None:
    """Print Confluence paste instructions for Mermaid output."""

    if path.suffix != ".mmd":
        typer.echo(
            f"{GOLD}💡 Confluence Mermaid works best with .mmd output{RESET}"
        )
        return

    typer.echo(
        f"\n{GREEN}✅ Ready to paste into Confluence Mermaid macro.{RESET}"
    )

    if copied:
        typer.echo(f"{GREEN}📋 Mermaid code copied to clipboard.{RESET}")
    else:
        typer.echo(
            f"{GOLD}💡 Use --clipboard to copy Mermaid code automatically.{RESET}"
        )


def print_output_hint(path: Path) -> None:
    """Print where the rendered diagram was saved."""
    typer.echo(f"{GREEN}✅ Diagram written to: {path}{RESET}")


def copy_mermaid_to_clipboard(path: Path) -> bool:
    """Copy Mermaid source to clipboard if output is .mmd."""

    if path.suffix != ".mmd":
        typer.echo(
            f"{GOLD}💡 Clipboard copy only applies to .mmd output{RESET}"
        )
        return False

    try:
        pyperclip.copy(path.read_text(encoding="utf-8"))
        return True
    except Exception as e:
        typer.echo(f"{RED}❌ Clipboard copy failed: {e}{RESET}")
        return False