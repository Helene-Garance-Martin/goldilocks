# commands/sanitise.py
import time

import typer
from rich.console import Console
from goldilocks_cli.colours import CYAN, GREEN, RED, RESET

console = Console()


def render_sanitise_summary(summary: dict) -> None:
    """The reveal — same lines and pacing the core used to print."""
    if summary["project"]:
        typer.echo(f"📦 Project export — found {len(summary['pipelines'])} pipeline(s)")
    else:
        typer.echo("📄 Single pipeline export")

    typer.echo(f"✅ Clean file written to: {summary['output']}")
    time.sleep(0.2)
    typer.echo("\n📊 Summary:")
    time.sleep(0.15)
    typer.echo(f"   Original size:  {summary['original_size']:,} bytes")
    time.sleep(0.1)
    typer.echo(f"   Clean size:     {summary['clean_size']:,} bytes")
    time.sleep(0.1)

    if summary["clean_size"] > summary["original_size"]:
        difference = round((summary["clean_size"] / summary["original_size"] - 1) * 100)
        typer.echo(f"   Size change:    +{difference}% (settings preserved for graph intelligence)")
    else:
        reduction = round((1 - summary["clean_size"] / summary["original_size"]) * 100)
        typer.echo(f"   Reduced by:     {reduction}% 🌟")

    if summary["project"]:
        for i, p in enumerate(summary["pipelines"]):
            time.sleep(0.2)
            typer.echo(f"\n   Pipeline {i + 1}: {p['name']}")
            time.sleep(0.1)
            typer.echo(f"     Snaps (nodes): {p['snaps']}")
            time.sleep(0.1)
            typer.echo(f"     Links (edges): {p['links']}")


def sanitise(
    input: str = typer.Option(..., help="Path to raw integration pipeline export"),
    output: str = typer.Option("export_clean.json", help="Path to write sanitised output"),
):
    """
    🧹 Sanitise a raw integration pipeline export.

    Strips UI noise, rendering data and internal metadata —
    keeping only what Goldilocks needs for parsing and graphing.
    """
    typer.echo(f"{CYAN}🧹 Sanitising pipeline export...{RESET}")
    typer.echo(f"   Input:  {input}")
    typer.echo(f"   Output: {output}")
    typer.echo("")

    try:
        with console.status("[magenta]Sanitising...[/magenta]", spinner="dots"):
            from goldilocks_cli.core.sanitiser import sanitise_export
            summary = sanitise_export(input, output)
        render_sanitise_summary(summary)
        typer.echo(f"\n{GREEN}✅ Done!{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed: {e}{RESET}\n")
        raise typer.Exit(1)
