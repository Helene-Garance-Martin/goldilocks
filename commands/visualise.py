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
    pipeline: str = typer.Option(
        None,
        "--pipeline",
        "-p",
        "--single",
        help="Name of single pipeline to visualise",
    ),
):
    """
    🎨 Generate Mermaid diagrams from pipeline data.
    """
    typer.echo(f"{CYAN}🎨 Generating Mermaid diagrams...{RESET}")
    typer.echo(f"   Input:     {input}")
    typer.echo(f"   Output:    {output}")
    typer.echo(f"   Direction: {direction}")
    typer.echo(f"   Format:    {fmt}")
    if pipeline:
        typer.echo(f"   Pipeline:  {pipeline}")
    typer.echo("")

    try:
        from visualiser import generate_diagrams
        generate_diagrams(input, output, direction, fmt, pipeline)
        typer.echo(f"{GOLD}  💡 Open any .mmd file in VS Code to preview{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed to generate diagram: {e}{RESET}\n")
        raise typer.Exit(1)