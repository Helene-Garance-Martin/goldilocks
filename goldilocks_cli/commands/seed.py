# commands/seed.py

import os
import typer

from rich.console import Console

from goldilocks_cli.colours import CYAN, GREEN, RED, RESET

console = Console()


def seed(
    input: str = typer.Option(
        "export_anonymised.json",
        help="Path to anonymised pipeline JSON",
    ),
    uri: str = typer.Option(
        None,
        help="Neo4j Aura URI (defaults to NEO4J_URI)",
    ),
    username: str = typer.Option(
        None,
        help="Neo4j username (defaults to NEO4J_USER)",
    ),
    password: str = typer.Option(
        None,
        help="Neo4j password (defaults to NEO4J_PASSWORD)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Skip the pre-seed leak check prompt (automation)",
    ),
):
    """
    🌱 Seed the Neo4j graph with pipeline data.
    """

    # ── Credentials — flags win, else the central module ──
    from goldilocks_cli.core.credentials import (
        require_credential, get_credential,
        NEO4J_DEFAULT_USER, CredentialMissing,
    )

    try:
        uri = uri or require_credential("NEO4J_URI", "seed the graph")
        username = (
            username or get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
        )
        password = (
            password or require_credential("NEO4J_PASSWORD", "seed the graph")
        )
    except CredentialMissing as e:
        typer.echo(f"{RED}{e}{RESET}")
        raise typer.Exit(1)

    # ── Pre-seed leak gate ─────────────────────────────────
    # Seeding is the point of no return into the graph, so the
    # input gets one last leak scan before any connection is made.

    from pathlib import Path
    from goldilocks_cli.core.anonymiser import scan_for_leaks, print_leak_report

    input_path = Path(input)
    if not input_path.exists():
        typer.echo(f"{RED}❌ File not found: {input}{RESET}")
        typer.echo("Sieve an export first: goldilocks sieve --input <raw export>")
        raise typer.Exit(1)

    findings = scan_for_leaks(input_path.read_text(encoding="utf-8"))
    if findings and not force:
        print_leak_report(findings)
        if not typer.confirm("⚠️  Findings above — seed anyway?", default=False):
            typer.echo("🌱 Seeding cancelled — sieve the file first: goldilocks sieve --input <raw export>\n")
            raise typer.Exit(1)
    elif not findings:
        typer.echo("🔍 pre-seed check: clean")

    # ── Display configuration ──────────────────────────────

    typer.echo(f"{CYAN}🌱 Seeding Neo4j graph...{RESET}")
    typer.echo(f"   Input: {input}")
    typer.echo(f"   URI:   {uri}")
    typer.echo("")

    try:

        import sys

        # Hand flag overrides to pipeline_seeder via the environment —
        # env is the source of truth, so this is the sanctioned channel.
        os.environ["NEO4J_URI"] = uri
        os.environ["NEO4J_USER"] = username
        os.environ["NEO4J_PASSWORD"] = password

        with console.status(
            "[magenta]Seeding graph...[/magenta]",
            spinner="dots",
        ):
            from goldilocks_cli.core.pipeline_seeder import main
            os.environ["GOLDILOCKS_EXPORT_PATH"] = input
            
            main()

        typer.echo(
            f"{GREEN}✅ Graph seeded successfully!{RESET}\n"
        )

    except Exception as e:

        typer.echo(
            f"{RED}❌ Seeding failed: {e}{RESET}\n"
        )

        raise typer.Exit(1)