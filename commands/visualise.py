# commands/visualise.py
import os
import webbrowser
from pathlib import Path

import pyperclip
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

    confluence: bool = typer.Option(
        False,
        "--confluence",
        help="Prepare Mermaid output for pasting into a Confluence Mermaid macro",
    ),

    clipboard: bool = typer.Option(
        False,
        "--clipboard",
        help="Copy Mermaid output to clipboard",
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

    if confluence:
        copied = False

        if clipboard:
            copied = _copy_mermaid_to_clipboard(final_path)

        _print_confluence_hint(final_path, copied=copied)
        return

    if open_after:
        _open_rendered_file(final_path)
    else:
        _print_output_hint(final_path)


def _pipeline_menu() -> str:
    """Interactive pipeline selector, shown only when no name is given."""
    from neo4j import GraphDatabase

    uri = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (p:Pipeline)
                OPTIONAL MATCH (p)-[:HAS_SNAP]->(s:Snap)
                OPTIONAL MATCH (p)-[:CALLS]->(child:Pipeline)
                RETURN
                    p.name AS name,
                    count(DISTINCT s) AS steps,
                    count(DISTINCT child) AS children
                ORDER BY name
                """
            )
            pipelines = [dict(r) for r in result]

    if not pipelines:
        typer.echo(f"{RED}❌ No pipelines found in Neo4j{RESET}")
        raise typer.Exit(1)

    typer.echo("  Which pipeline?\n")

    for i, pipeline in enumerate(pipelines, 1):
        suffix = f"{pipeline['steps']} steps"

        child_count = pipeline["children"]

        if child_count == 1:
            suffix += " · 1 child"
        elif child_count > 1:
            suffix += f" · {child_count} children"

        typer.echo(
            f"    {i}. {pipeline['name']} "
            f"({suffix})"
        )

    typer.echo("")

    choice = typer.prompt("  Select", default="1")

    try:
        return pipelines[int(choice) - 1]["name"]
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

    final = render_diagram(mmd_path, fmt)
    return final

def _open_rendered_file(path: Path) -> None:
    """Open rendered diagram when supported."""

    if path.suffix not in [".svg", ".png"]:
        typer.echo(
            f"{GOLD}💡 --open currently supports svg/png outputs{RESET}"
        )
        return

    if os.environ.get("CODESPACES"):
        typer.echo(
            f"\n{GOLD}💡 remote environment — "
            f"open the rendered file from VS Code{RESET}"
        )
        return

    webbrowser.open(path.resolve().as_uri())

def _open_rendered_file(path: Path) -> None:
    """Open rendered diagram when supported."""

    if path.suffix not in [".svg", ".png"]:
        typer.echo(
            f"{GOLD}💡 --open currently supports svg/png outputs{RESET}"
        )
        return

    if os.environ.get("CODESPACES"):
        typer.echo(
            f"\n{GOLD}💡 remote environment — "
            f"open the rendered file from VS Code{RESET}"
        )
        return

    webbrowser.open(path.resolve().as_uri())


def _print_confluence_hint(path: Path, copied: bool = False) -> None:
    """Print Confluence paste instructions for Mermaid output."""

    if path.suffix != ".mmd":
        typer.echo(
            f"{GOLD}💡 Confluence Mermaid works best with .mmd output{RESET}"
        )
        return

    typer.echo(
        f"\n{GREEN}✅ Ready to paste into Confluence Mermaid macro.{RESET}"
    )

    if copied:
        typer.echo(f"{GREEN}📋 Mermaid code copied to clipboard.{RESET}")
    else:
        typer.echo(
            f"{GOLD}💡 Open this file and copy the Mermaid code:{RESET}"
        )
        typer.echo(f"   {path.resolve()}")

def _print_output_hint(path):
    """Print where the rendered diagram was saved."""
    typer.echo(f"{GREEN}✅ Diagram written to: {path}{RESET}")

def _copy_mermaid_to_clipboard(path: Path) -> bool:
    """Copy Mermaid file contents to clipboard."""

    if path.suffix != ".mmd":
        return False

    try:
        text = path.read_text(encoding="utf-8")
        pyperclip.copy(text)
        return True

    except Exception as e:
        typer.echo(
            f"{GOLD}💡 Could not copy to clipboard: {e}{RESET}"
        )
        return False
    
