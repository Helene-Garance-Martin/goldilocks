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

    if source == "traversal" and pipeline is None:
        pipeline = _pipeline_menu()
        
    if source == "json" and pipeline is None:
        pipeline = None

    out.mkdir(parents=True, exist_ok=True)

    try:
        if source == "traversal":
            final_path = _render_from_traversal(pipeline, out, direction, fmt)
        else:
            _render_from_json(input, str(out), direction, fmt, pipeline)
            return

    except Exception as e:
        typer.echo(f"{RED}❌ Failed to generate diagram: {e}{RESET}\n")
        raise typer.Exit(1)

    typer.echo(f"\n{GREEN}🖼️  {final_path.resolve()}{RESET}")

    if open_after:
            if os.environ.get("CODESPACES"):
                typer.echo(
                    f"\n{GOLD}💡 remote environment — "
                    f"open the file in VS Code to preview{RESET}"
                )
            elif fmt == "mmd":
                typer.echo(
                    f"\n{GOLD}💡 open the .mmd file in VS Code, "
                    f"or use -f svg --open for browser{RESET}"
                )
            else:
                webbrowser.open(final_path.resolve().as_uri())
    else:
        typer.echo(
        f"{GOLD}💡 add --open to view immediately next time{RESET}"
        )

def _pipeline_menu() -> str:
    """Interactive pipeline selector — only shown when no name given."""
    from neo4j import GraphDatabase

    uri = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            result = session.run(
                "MATCH (p:Pipeline) RETURN p.name AS name ORDER BY name"
            )
            pipelines = [r["name"] for r in result]

    if not pipelines:
        typer.echo(f"{RED}❌ No pipelines found in Neo4j{RESET}")
        raise typer.Exit(1)

    typer.echo("  Which pipeline?\n")
    for i, name in enumerate(pipelines, 1):
        typer.echo(f"    {i}. {name}")
    typer.echo(f"    a. all pipelines")
    typer.echo("")

    choice = typer.prompt("  Select", default="1")

    if choice.lower() == "a":
        return "__all__"

    try:
        return pipelines[int(choice) - 1]
    except (ValueError, IndexError):
        typer.echo(f"{RED}❌ Invalid selection{RESET}")
        raise typer.Exit(1)


def _render_from_traversal(
    pipeline: str,
    out: Path,
    direction: str,
    fmt: str,
) -> Path:
    """Traverse Neo4j and render Mermaid diagram."""
    from neo4j import GraphDatabase
    from dag_builder import build_dag
    from dag_mermaid_renderer import render_dag_mermaid
    from renderer import render_diagram

    uri = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            dag = build_dag(session, pipeline)
            diagram = render_dag_mermaid(dag, direction)

    file_name = pipeline.replace(" ", "_") + ".mmd"
    mmd_path = out / file_name
    mmd_path.write_text(diagram, encoding="utf-8")

    render_diagram(mmd_path, fmt)

    final = mmd_path.with_suffix(f".{fmt}") if fmt != "mmd" else mmd_path
    return final


def _render_from_json(
    input: str,
    output: str,
    direction: str,
    fmt: str,
    pipeline: str | None,
) -> None:
    """Render from JSON export (existing path)."""
    from visualiser import generate_diagrams
    generate_diagrams(input, output, direction, fmt, pipeline)
    typer.echo(f"{GOLD}💡 Open any .mmd file in VS Code to preview{RESET}\n")
