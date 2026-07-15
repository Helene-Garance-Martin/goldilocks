# commands/visualise.py
from pathlib import Path

import typer
from goldilocks_cli.colours import CYAN, GREEN, RED, GOLD, RESET

from goldilocks_cli.core.pipeline_menu import pipeline_menu
from goldilocks_cli.core.credentials import CredentialMissing

from goldilocks_cli.core.output_manager import (
    open_rendered_file,
    print_confluence_hint,
    print_output_hint,
    copy_mermaid_to_clipboard,
)

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
        pipeline = pipeline_menu()
        
    if source == "json" and pipeline is None:
        pipeline = None

    out.mkdir(parents=True, exist_ok=True)

    try:
        if source == "traversal":
            final_path = _render_from_traversal(pipeline, out, direction, fmt)
        else:
            _render_from_json(input, str(out), direction, fmt, pipeline)
            return

    except CredentialMissing as e:
        typer.echo(f"{RED}{e}{RESET}\n")
        raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"{RED}❌ Failed to generate diagram: {e}{RESET}\n")
        raise typer.Exit(1)

    typer.echo(f"\n{GREEN}🖼️  {final_path.resolve()}{RESET}")

    if confluence:
        copied = False

        if clipboard:
            copied = copy_mermaid_to_clipboard(final_path)

        print_confluence_hint(final_path, copied=copied)
        return

    if open_after:
        open_rendered_file(final_path)
    else:
        print_output_hint(final_path)




def _render_from_traversal(
    pipeline: str,
    out: Path,
    direction: str,
    fmt: str,
) -> Path:
    """Traverse Neo4j and render Mermaid diagram."""
    from neo4j import GraphDatabase
    from goldilocks_cli.core.dag_builder import build_dag
    from goldilocks_cli.core.dag_mermaid_renderer import render_dag_mermaid
    from goldilocks_cli.core.renderer import render_diagram

    from goldilocks_cli.core.credentials import (
        require_credential, get_credential, NEO4J_DEFAULT_USER,
    )

    uri = require_credential("NEO4J_URI", "traverse the graph")
    user = get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
    password = require_credential("NEO4J_PASSWORD", "traverse the graph")

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            dag = build_dag(session, pipeline)
            diagram = render_dag_mermaid(dag, direction)

    file_name = pipeline.replace(" ", "_") + ".mmd"
    mmd_path = out / file_name
    mmd_path.write_text(diagram, encoding="utf-8")

    final = render_diagram(mmd_path, fmt)
    return final


