# commands/check.py
from pathlib import Path

import typer

from goldilocks_cli.colours import CYAN, GREEN, RED, RESET


def check(
    input: str = typer.Option(..., "--input", help="Path to the file to leak-scan"),
):
    """
    🔍 Leak-scan a file for residual sensitive shapes.

    Looks for real URLs, email addresses and GUIDs that survived
    anonymisation. Exit code 0 when quiet, 1 when findings exist,
    so it can gate scripts and CI. A quiet scan is evidence, not
    proof — give shared files ten adversarial minutes too.
    """
    from goldilocks_cli.core.anonymiser import scan_for_leaks, print_leak_report

    path = Path(input)
    if not path.exists():
        typer.echo(f"{RED}❌ File not found: {input}{RESET}\n")
        raise typer.Exit(1)

    typer.echo(f"{CYAN}🔍 Checking: {input}{RESET}\n")
    findings = scan_for_leaks(path.read_text(encoding="utf-8"))
    print_leak_report(findings)

    if findings:
        typer.echo(f"\n{RED}Findings above — review before sharing.{RESET}\n")
        raise typer.Exit(1)

    typer.echo(f"{GREEN}A quiet scan is evidence, not proof — but it's a good sign. 🫧{RESET}\n")
