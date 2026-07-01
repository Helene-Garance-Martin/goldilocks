# commands/sieve.py
import time
import typer
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)
from commands.colours import CYAN, GREEN, RED, GOLD, BOLD, RESET

console = Console()


def sieve(
    input: str = typer.Option(..., help="Path to raw integration pipeline export"),
    sanitised: str = typer.Option("export_clean.json", help="Path for sanitised intermediate"),
    anonymised: str = typer.Option("export_anonymised.json", help="Path for final anonymised output"),
):
    """
    🫧 Sieve a raw integration pipeline export — sanitise and anonymise in one pass.

    Runs sanitisation then anonymisation, producing data that's safe
    to share publicly and ready to seed into Neo4j.

    fetch → sieve → seed
    """
    typer.echo(f"{GOLD}🫧 Sieving pipeline export...{RESET}")
    typer.echo(f"   Input:       {input}")
    typer.echo(f"   Sanitised:   {sanitised}")
    typer.echo(f"   Anonymised:  {anonymised}")
    typer.echo("")

    # ── Progress display — one context wrapping both tasks ──────────
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )

    with progress:

        # ── Step 1 — sanitise ─────────────────────────────
        typer.echo(f"{CYAN}Step 1/2 — 🧹 Sanitising...{RESET}")

        sanitise_task = progress.add_task("🧹 Sanitising", total=100)

        def sanitise_progress(phase, current, total, message=""):
            """Translate sanitiser events into progress bar updates."""
            if total > 0:
                percent = (current / total) * 100
                description = f"🧹 Sanitising — {message}" if message else "🧹 Sanitising"
                progress.update(sanitise_task, completed=percent, description=description)

        try:
            from sanitiser import sanitise_export
            sanitise_export(input, sanitised, on_progress=sanitise_progress)
            progress.update(sanitise_task, completed=100, description="🧹 Sanitised")
            time.sleep(0.4)  # let the finished bar be visible
        except Exception as e:
            typer.echo(f"{RED}❌ Sanitise failed: {e}{RESET}\n")
            raise typer.Exit(1)

        typer.echo(f"{GREEN}✅ Sanitised{RESET}\n")

        # ── Step 2 — anonymise ────────────────────────────
        typer.echo(f"{CYAN}Step 2/2 — 🔒 Anonymising...{RESET}")

        anonymise_task = progress.add_task("🔒 Anonymising", total=100)

        def anonymise_progress(phase, current, total, message=""):
            """Translate anonymiser events into progress bar updates."""
            if total > 0:
                percent = (current / total) * 100
                description = f"🔒 Anonymising — {message}" if message else "🔒 Anonymising"
                progress.update(anonymise_task, completed=percent, description=description)

        try:
            from anonymiser import anonymise_pipeline
            anonymise_pipeline(sanitised, anonymised, on_progress=anonymise_progress)
            progress.update(anonymise_task, completed=100, description="🔒 Anonymised")
            time.sleep(0.4)  # let the finished bar be visible
        except Exception as e:
            typer.echo(f"{RED}❌ Anonymise failed: {e}{RESET}\n")
            raise typer.Exit(1)

        typer.echo(f"{GREEN}✅ Anonymised — safe to share publicly!{RESET}\n")

    # ── Closing flourish (outside progress context) ─────────────────
    typer.echo(f"{GOLD}{BOLD}🫧 Sieve complete — data ready to seed.{RESET}\n")