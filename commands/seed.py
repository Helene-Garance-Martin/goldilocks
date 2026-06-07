# commands/seed.py

import os
import typer

from rich.console import Console

from commands.colours import CYAN, GREEN, RED, RESET

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

    # ── Display configuration ──────────────────────────────

    typer.echo(f"{CYAN}🌱 Seeding Neo4j graph...{RESET}")
    typer.echo(f"   Input: {input}")
    typer.echo(f"   URI:   {uri}")
    typer.echo("")

    try:

        import sys

        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
            ),
        )

        os.environ["NEO4J_URI"] = uri
        os.environ["NEO4J_USER"] = username
        os.environ["NEO4J_PASSWORD"] = password

        with console.status(
            "[magenta]Seeding graph...[/magenta]",
            spinner="dots",
        ):
            from pipeline_seeder import main
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