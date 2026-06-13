# commands/visualise.py
import os
import webbrowser
from pathlib import Path

import typer
from commands.colours import CYAN, GREEN, RED, GOLD, RESET


def visualise(
    pipeline: str = typer.Argument(
        None,
        help="Pipeline name (omit for interactive menu)",
    ),
    fmt: str = typer.Option(
        "mmd",
        "--format", "-f",
        help="Output format: mmd, svg, png",
    ),
    out: Path = typer.Option(
        Path("diagrams"),
        "--out", "-o",
        help="Output directory",
    ),
    direction: str = typer.Option(
        "LR",
        "--direction", "-d",
        help="Diagram direction: LR or TD",
    ),
    open_after: bool = typer.Option(
        False,
        "--open",
        help="Open diagram after rendering",
    ),
    source: str = typer.Option(
        "traversal",
        "--source", "-s",
        help="Data source: traversal (Neo4j) or json (export file)",
    ),
    input: str = typer.Option(
        "export_anonymised.json",
        "--input", "-i",
        help="Path to anonymised JSON (only used with --source json)",
    ),
):
    """
    🎨 Render pipeline diagrams from graph traversal or JSON export.

    Examples:
      goldilocks visualise                          # interactive menu
      goldilocks visualise my_pipeline              # direct, skip menu
      goldilocks visualise my_pipeline -f svg       # render as SVG
      goldilocks visualise my_pipeline --open       # render and open
      goldilocks visualise --source json            # from JSON export
    """

    typer.echo(f"\n{CYAN}🫧 goldilocks · visualise{RESET}\n")

    # --------------------------------------------------------
    # Step 1 — resolve pipeline (menu fills the gap)
    # --------------------------------------------------------

    if source == "traversal" and pipeline is None:
        pipeline = _pipeline_menu()

    if source == "json" and pipeline is None:
        pipeline = None  # JSON path handles its own selection via generate_diagrams

    # --------------------------------------------------------
    # Step 2 — ensure output directory
    # --------------------------------------------------------

    out.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # Step 3 — render
    # --------------------------------------------------------

    try:
        if source == "traversal":
            final_path = _render_from_traversal(pipeline, out, direction, fmt)
        else:
            _render_from_json(input, str(out), direction, fmt, pipeline)
            return

    except Exception as e:
        typer.echo(f"{RED}❌ Failed to generate diagram: {e}{RESET}\n")
        raise typer.Exit(1)

    # --------------------------------------------------------
    # Step 4 — feedback
    # --------------------------------------------------------

    typer.echo(f"\n{GREEN}🖼️  {final_path.resolve()}{RESET}")

    # --------------------------------------------------------
    # Step 5 — open (environment-aware)
    # --------------------------------------------------------

    if open_after:
        if os.environ.get("CODESPACES"):
            typer.echo(
                f"\n{GOLD}💡 remote environment detected — "
                f"open the file in VS Code to preview{RESET}"
            )
        else:
            webbrowser.open(final_path.resolve().as_uri())
    else:
        typer.echo(
            f"{GOLD}💡 add --open to view immediately next time{RESET}"
        )


# ================================================================
# PRIVATE HELPERS
# ================================================================

def _pipeline_menu() -> str:
    """Interactive pipeline selector — only shown when no name given."""
    from neo4j import GraphDatabase

    uri = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session: