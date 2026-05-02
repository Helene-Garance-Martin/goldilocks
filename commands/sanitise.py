# commands/sanitise.py
import typer
from rich.console import Console
from commands.colours import CYAN, GREEN, RED, RESET

console = Console()

def sanitise(
    input: str = typer.Option(..., help="Path to raw export.json from SnapLogic"),
    output: str = typer.Option("export_clean.json", help="Path to write sanitised output"),
):
    """
    🧹 Sanitise a raw SnapLogic export.

    Strips UI noise, rendering data and internal metadata —
    keeping only what Goldilocks needs for parsing and graphing.
    """
    typer.echo(f"{CYAN}🧹 Sanitising pipeline export...{RESET}")
    typer.echo(f"   Input:  {input}")
    typer.echo(f"   Output: {output}")
    typer.echo("")

    try:
        with console.status("[magenta]Sanitising...[/magenta]", spinner="dots"):
            from sanitiser import sanitise_export
            sanitise_export(input, output)
        typer.echo(f"{GREEN}✅ Done!{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed: {e}{RESET}\n")
        raise typer.Exit(1)