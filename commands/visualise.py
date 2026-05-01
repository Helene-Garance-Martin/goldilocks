# commands/visualise.py
import typer
from commands.colours import CYAN, GREEN, RED, GOLD, RESET

def visualise(
    input: str = typer.Option("export_anonymised.json", help=(
        "Path to anonymised pipeline JSON\n"
        "  💡 Run the anonymise command first to generate this file"
    )),
    output: str = typer.Option("diagrams/", help="Folder to save Mermaid diagram files"),
    direction: str = typer.Option("LR", help="Diagram direction: LR or TD"),
    fmt: str = typer.Option("mmd", help="Output format: mmd, png or svg"),
    single: str = typer.Option(None, help="Name of single pipeline to visualise"),
):
    """
    🎨 Generate Mermaid diagrams from pipeline data.

    Creates .mmd diagram files showing pipeline architecture —
    snap nodes with icons, connections, subgraphs and colour coding.

    Colours represent Snap type. Icons show what each snap does.
    """
    typer.echo(f"{CYAN}🎨 Generating Mermaid diagrams...{RESET}")
    typer.echo(f"   Input:     {input}")
    typer.echo(f"   Output:    {output}")
    typer.echo(f"   Direction: {direction}")
    typer.echo(f"   Format:    {fmt}")
    if single:
        typer.echo(f"   Single:    {single}")
    typer.echo("")

    try:
        from visualiser import generate_diagrams
        generate_diagrams(input, output, direction, fmt, single)
        typer.echo(f"{GOLD}  💡 Open any .mmd file in VS Code to preview{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed to generate diagram: {e}{RESET}\n")
        raise typer.Exit(1)