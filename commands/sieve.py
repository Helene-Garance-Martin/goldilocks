# commands/sieve.py
import typer
from rich.console import Console
from commands.colours import CYAN, GREEN, RED, GOLD, BOLD, RESET

console = Console()


def sieve(
    input: str = typer.Option(..., help="Path to raw export.json from SnapLogic"),
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

    # ── Step 1 — sanitise ─────────────────────────────────
    typer.echo(f"{CYAN}Step 1/2 — 🧹 Sanitising...{RESET}")
    try:
        with console.status("[magenta]Sanitising...[/magenta]", spinner="dots"):
            from sanitiser import sanitise_export
            sanitise_export(input, sanitised)
        typer.echo(f"{GREEN}✅ Sanitised{RESET}\n")
    except Exception as e:
        typer.echo(f"{RED}❌ Sanitise failed: {e}{RESET}\n")
        raise typer.Exit(1)

    # ── Step 2 — anonymise ────────────────────────────────
    typer.echo(f"{CYAN}Step 2/2 — 🔒 Anonymising...{RESET}")
    try:
        with console.status("[magenta]Anonymising...[/magenta]", spinner="dots"):
            from anonymiser import anonymise_pipeline
            anonymise_pipeline(sanitised, anonymised)
        typer.echo(f"{GREEN}✅ Anonymised — safe to share publicly!{RESET}\n")
    except Exception as e:
        typer.echo(f"{RED}❌ Anonymise failed: {e}{RESET}\n")
        raise typer.Exit(1)

    typer.echo(f"{GOLD}{BOLD}🫧 Sieve complete — data ready to seed.{RESET}\n")

    