# commands/anonymise.py
import typer
from rich.console import Console
from goldilocks_cli.colours import CYAN, GREEN, RED, RESET

console = Console()

def anonymise(
    input: str = typer.Option(..., help="Path to sanitised export_clean.json"),
    output: str = typer.Option("export_anonymised.json", help="Path to write anonymised output"),
):
    """
    🔒 Anonymise a sanitised export.

    Replaces org names, URLs, emails and credentials with
    consistent fake values, then leak-scans the result.
    Automated scrubbing catches known patterns only —
    review the output before sharing.
    """
    typer.echo(f"{CYAN}🔒 Anonymising pipeline export...{RESET}")
    typer.echo(f"   Input:  {input}")
    typer.echo(f"   Output: {output}")
    typer.echo("")

    try:
        with console.status("[magenta]Anonymising...[/magenta]", spinner="dots"):
            from goldilocks_cli.core.anonymiser import anonymise_pipeline
            anonymise_pipeline(input, output)
        typer.echo(f"{GREEN}✅ Done — known sensitive patterns removed. Review before sharing.{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed: {e}{RESET}\n")
        raise typer.Exit(1)