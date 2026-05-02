# commands/anonymise.py
import typer
from rich.console import Console
from commands.colours import CYAN, GREEN, RED, RESET

console = Console()

def anonymise(
    input: str = typer.Option(..., help="Path to sanitised export_clean.json"),
    output: str = typer.Option("export_anonymised.json", help="Path to write anonymised output"),
):
    """
    🔒 Anonymise a sanitised SnapLogic export.

    Strips org names, URLs and credentials —
    safe to share publicly or commit to GitHub.
    """
    typer.echo(f"{CYAN}🔒 Anonymising pipeline export...{RESET}")
    typer.echo(f"   Input:  {input}")
    typer.echo(f"   Output: {output}")
    typer.echo("")

    try:
        with console.status("[magenta]Anonymising...[/magenta]", spinner="dots"):
            from anonymiser import anonymise_pipeline
            anonymise_pipeline(input, output)
        typer.echo(f"{GREEN}✅ Done — safe to share publicly!{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed: {e}{RESET}\n")
        raise typer.Exit(1)