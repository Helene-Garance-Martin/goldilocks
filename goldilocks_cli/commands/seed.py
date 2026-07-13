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
        os.getenv("NEO4J_URI", ""),
        help="Neo4j Aura URI",
    ),
    username: str = typer.Option(
        os.getenv("NEO4J_USER", "neo4j"),
        help="Neo4j username",
    ),
    password: str = typer.Option(
        os.getenv("NEO4J_PASSWORD", ""),
        help="Neo4j password",
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

    # ── Validation ─────────────────────────────────────────

    if not uri:
        typer.echo(
            f"{RED}❌ NEO4J_URI not configured.{RESET}"
        )
        typer.echo(
            "Set it in your environment or pass --uri"
        )
        raise typer.Exit(1)

    if not password:
        typer.echo(
            f"{RED}❌ NEO4J_PASSWORD not configured.{RESET}"
        )
        typer.echo(
            "Set it in your environment or pass --password"
        )
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