# commands/visualise.py
import json
from pathlib import Path
from typing import Optional

import typer

from goldilocks_cli.colours import CYAN, GOLD, GREEN, RED, RESET
from goldilocks_cli.core.credentials import CredentialMissing
from goldilocks_cli.core.output_manager import (
    copy_mermaid_to_clipboard,
    open_rendered_file,
    print_confluence_hint,
    print_output_hint,
)
from goldilocks_cli.core.pipeline_menu import pipeline_menu
from goldilocks_cli.core.visualisation_scale import (
    HARD_NODE_THRESHOLD,
    PROJECT_PIPELINE_THRESHOLD,
    measure_scale,
)


def _read_current_graph_state() -> dict:
    """Read the graph prerequisite before menus or rendering."""
    from neo4j import GraphDatabase

    from goldilocks_cli.core.credentials import (
        NEO4J_DEFAULT_USER,
        get_credential,
        require_credential,
    )
    from goldilocks_cli.core.state import read_graph_state

    uri = require_credential("NEO4J_URI", "visualise the graph")
    user = get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
    password = require_credential("NEO4J_PASSWORD", "visualise the graph")

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            return read_graph_state(session)


def _rendered_dag_counts(dag) -> tuple[int, int]:
    """Count every node and edge the single-DAG renderer will emit."""
    call_count = sum(
        1
        for node in dag.nodes
        if node.type == "pipeexec" and node.child_pipeline
    )
    return len(dag.nodes) + call_count, len(dag.edges) + call_count


def _print_scale_header(node_count: int, edge_count: int) -> None:
    node_word = "node" if node_count == 1 else "nodes"
    edge_word = "edge" if edge_count == 1 else "edges"
    typer.echo(f"  {node_count} {node_word} · {edge_count} {edge_word}")


def _prepare_visual_dag(dag, explicit_collapse: Optional[bool]):
    from goldilocks_cli.core.diagram_builder import prepare_dag_view

    node_count, edge_count = _rendered_dag_counts(dag)
    decision = measure_scale(
        node_count,
        edge_count,
        explicit_collapse,
    )
    _print_scale_header(decision.node_count, decision.edge_count)

    if decision.collapse:
        if decision.is_large:
            typer.echo(
                f"{GOLD}  Large diagram — collapsing linear chains for readability.{RESET}"
            )
            if explicit_collapse is None:
                typer.echo("  Use --no-collapse to request the full detail.")
        else:
            typer.echo(f"{GOLD}  Collapsing linear chains by request.{RESET}")
        visual_dag = prepare_dag_view(dag, collapse=True)
        visual_count, _ = _rendered_dag_counts(visual_dag)
        if visual_count < decision.node_count:
            typer.echo(f"  {decision.node_count} nodes -> {visual_count} visual nodes")
        else:
            typer.echo(
                "  No safe linear chains could be collapsed; "
                f"the view remains at {visual_count} nodes."
            )
    else:
        visual_dag = prepare_dag_view(dag, collapse=False)
        if decision.is_large:
            typer.echo(
                f"{GOLD}  Large diagram — rendering the full pipeline because "
                f"--no-collapse was supplied.{RESET}"
            )
        else:
            typer.echo("  Rendering full pipeline.")

    return decision, visual_dag


def _hard_limit_blocks(
    *,
    original_node_count: int,
    visual_node_count: int,
    combined: bool,
    combined_requested: bool,
) -> bool:
    if combined and original_node_count >= HARD_NODE_THRESHOLD and not combined_requested:
        return True
    return visual_node_count >= HARD_NODE_THRESHOLD


def _print_hard_limit_message(*, combined: bool) -> None:
    view = "combined diagram" if combined else "diagram"
    typer.echo()
    typer.echo(
        f"{GOLD}🌾 This {view} is too large to be useful at its current level of detail.{RESET}"
    )
    typer.echo("   Try:")
    typer.echo("     goldilocks visualise --collapse")
    typer.echo("     goldilocks visualise --single")
    if combined:
        typer.echo("     or use the per-pipeline diagrams and pipeline index")
    typer.echo()


def _write_dag(
    dag,
    *,
    out: Path,
    direction: str,
    fmt: str,
    explicit_collapse: Optional[bool],
    file_name: str,
) -> Path | None:
    from goldilocks_cli.core.dag_mermaid_renderer import render_dag_mermaid
    from goldilocks_cli.core.renderer import render_diagram

    decision, visual_dag = _prepare_visual_dag(dag, explicit_collapse)
    if _hard_limit_blocks(
        original_node_count=decision.node_count,
        visual_node_count=_rendered_dag_counts(visual_dag)[0],
        combined=False,
        combined_requested=False,
    ):
        _print_hard_limit_message(combined=False)
        return None

    diagram = render_dag_mermaid(visual_dag, direction)
    mmd_path = out / file_name
    mmd_path.write_text(diagram, encoding="utf-8")
    return render_diagram(mmd_path, fmt)


def _render_combined_project(
    dags,
    calls,
    *,
    out: Path,
    direction: str,
    fmt: str,
    explicit_collapse: Optional[bool],
    combined_requested: bool,
) -> Path | None:
    from goldilocks_cli.core.dag_mermaid_renderer import render_project_mermaid
    from goldilocks_cli.core.diagram_builder import prepare_project_views
    from goldilocks_cli.core.renderer import render_diagram

    node_count = sum(len(dag.nodes) for dag in dags)
    edge_count = sum(len(dag.edges) for dag in dags) + len(calls)
    decision = measure_scale(node_count, edge_count, explicit_collapse)

    typer.echo("\n  Combined project view")
    _print_scale_header(node_count, edge_count)

    if decision.collapse:
        typer.echo(
            f"{GOLD}  Large diagram — collapsing linear chains for readability.{RESET}"
            if decision.is_large
            else f"{GOLD}  Collapsing linear chains by request.{RESET}"
        )
        if decision.is_large and explicit_collapse is None:
            typer.echo("  Use --no-collapse to request the full detail.")
    else:
        typer.echo("  Rendering full project topology.")

    visual_dags = prepare_project_views(dags, collapse=decision.collapse)
    visual_node_count = sum(len(dag.nodes) for dag in visual_dags)
    if decision.collapse:
        if visual_node_count < node_count:
            typer.echo(f"  {node_count} nodes -> {visual_node_count} visual nodes")
        else:
            typer.echo(
                "  No safe linear chains could be collapsed; "
                f"the view remains at {visual_node_count} nodes."
            )

    if _hard_limit_blocks(
        original_node_count=node_count,
        visual_node_count=visual_node_count,
        combined=True,
        combined_requested=combined_requested,
    ):
        _print_hard_limit_message(combined=True)
        return None

    diagram = render_project_mermaid(visual_dags, calls, direction)
    mmd_path = out / "goldilocks_combined.mmd"
    mmd_path.write_text(diagram, encoding="utf-8")
    return render_diagram(mmd_path, fmt)


def _render_pipeline_index(
    dags,
    calls,
    *,
    out: Path,
    fmt: str,
) -> Path:
    from goldilocks_cli.core.dag_builder import build_pipeline_index_dag
    from goldilocks_cli.core.dag_mermaid_renderer import render_dag_mermaid
    from goldilocks_cli.core.renderer import render_diagram

    index_dag = build_pipeline_index_dag(dags, calls)
    typer.echo("\n  Pipeline index")
    _print_scale_header(len(index_dag.nodes), len(index_dag.edges))
    diagram = render_dag_mermaid(
        index_dag,
        "TD",
        include_external_references=False,
    )
    path = out / "goldilocks_pipeline_index.mmd"
    path.write_text(diagram, encoding="utf-8")
    return render_diagram(path, fmt)


def _safe_file_name(name: str) -> str:
    from goldilocks_cli.core.diagram_builder import safe_file_name

    return safe_file_name(name) or "pipeline"


def _render_project_dags(
    dags,
    calls,
    *,
    out: Path,
    direction: str,
    fmt: str,
    explicit_collapse: Optional[bool],
    combined: bool,
) -> list[Path]:
    paths: list[Path] = []
    pipeline_count = len(dags)
    large_project = pipeline_count > PROJECT_PIPELINE_THRESHOLD

    typer.echo(f"\n  {pipeline_count} pipeline{'s' if pipeline_count != 1 else ''}")
    project_node_count = sum(len(dag.nodes) for dag in dags)
    project_edge_count = sum(len(dag.edges) for dag in dags) + len(calls)
    typer.echo("  Project total")
    _print_scale_header(project_node_count, project_edge_count)

    for dag in dags:
        typer.echo(f"\n  {dag.pipeline_name}")
        path = _write_dag(
            dag,
            out=out,
            direction=direction,
            fmt=fmt,
            explicit_collapse=explicit_collapse,
            file_name=f"{_safe_file_name(dag.pipeline_name)}.mmd",
        )
        if path is not None:
            paths.append(path)

    if large_project:
        paths.append(
            _render_pipeline_index(dags, calls, out=out, fmt=fmt)
        )
        if not combined:
            typer.echo()
            typer.echo(
                f"{GOLD}🌾 That's a large project, so Goldilocks created "
                f"{pipeline_count} pipeline views and one pipeline index.{RESET}"
            )
            typer.echo("   The combined all-snaps diagram was skipped.")
            typer.echo("   Use --combined to request it deliberately.")
            return paths

    combined_path = _render_combined_project(
        dags,
        calls,
        out=out,
        direction=direction,
        fmt=fmt,
        explicit_collapse=explicit_collapse,
        combined_requested=combined,
    )
    if combined_path is not None:
        paths.append(combined_path)
    return paths


def _match_pipeline(pipelines: list[dict], name: str) -> dict | None:
    exact = [
        pipeline
        for pipeline in pipelines
        if pipeline.get("name", "").casefold() == name.casefold()
    ]
    if exact:
        return exact[0]
    partial = [
        pipeline
        for pipeline in pipelines
        if name.casefold() in pipeline.get("name", "").casefold()
    ]
    if len(partial) == 1:
        return partial[0]
    return None


def _prompt_for_pipeline(pipelines: list[dict]) -> dict:
    typer.echo("  Which pipeline?\n")
    for index, pipeline in enumerate(pipelines, start=1):
        snap_count = len(pipeline.get("snap_map", {}))
        typer.echo(f"    {index}. {pipeline.get('name', 'Unknown')} ({snap_count} snaps)")
    typer.echo()
    choice = typer.prompt("  Select", default="1")
    try:
        return pipelines[int(choice) - 1]
    except (ValueError, IndexError):
        typer.echo(f"{RED}❌ Invalid selection{RESET}")
        raise typer.Exit(1)


def _load_json_pipelines(input_path: str) -> list[dict]:
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(input_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries") if isinstance(data, dict) else None
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, dict)]
    if isinstance(data, dict):
        return [data]
    raise ValueError("Pipeline export must contain a JSON object")


def _render_from_json(
    input_path: str,
    out: Path,
    direction: str,
    fmt: str,
    pipeline: str | None,
    *,
    single: bool,
    combined: bool,
    collapse: Optional[bool],
) -> list[Path]:
    from goldilocks_cli.core.dag_builder import (
        build_project_dags,
        resolve_pipeline_calls,
    )

    pipelines = _load_json_pipelines(input_path)
    if not pipelines:
        raise ValueError("No pipelines found in the export")

    selected: list[dict]
    if pipeline:
        match = _match_pipeline(pipelines, pipeline)
        if match is None:
            raise ValueError(f"No unique pipeline found matching: {pipeline}")
        selected = [match]
    elif single:
        selected = [_prompt_for_pipeline(pipelines)]
    else:
        selected = pipelines

    dags = build_project_dags(selected)
    calls = resolve_pipeline_calls(dags)

    if len(dags) == 1:
        dag = dags[0]
        typer.echo(f"\n  {dag.pipeline_name}")
        path = _write_dag(
            dag,
            out=out,
            direction=direction,
            fmt=fmt,
            explicit_collapse=collapse,
            file_name=f"{_safe_file_name(dag.pipeline_name)}.mmd",
        )
        return [path] if path is not None else []

    return _render_project_dags(
        dags,
        calls,
        out=out,
        direction=direction,
        fmt=fmt,
        explicit_collapse=collapse,
        combined=combined,
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
        help="Prepare Mermaid output for a Confluence Mermaid macro",
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
    collapse: Optional[bool] = typer.Option(
        None,
        "--collapse/--no-collapse",
        help="Collapse safe linear chains (automatic from 50 nodes)",
    ),
    single: bool = typer.Option(
        False,
        "--single",
        help="Render one pipeline, prompting when no name is supplied",
    ),
    combined: bool = typer.Option(
        False,
        "--combined",
        help="Request the combined all-snaps project view",
    ),
):
    """🎨 Render honest pipeline diagrams from traversal or JSON exports."""
    typer.echo(f"\n{CYAN}🫧 goldilocks · visualise{RESET}\n")

    if source not in {"traversal", "json"}:
        typer.echo(f"{RED}❌ Source must be 'traversal' or 'json'.{RESET}\n")
        raise typer.Exit(1)

    if single and combined:
        typer.echo(f"{RED}❌ Choose either --single or --combined, not both.{RESET}\n")
        raise typer.Exit(1)

    if source == "traversal" and combined and pipeline:
        typer.echo(
            f"{RED}❌ --combined uses the whole seeded project; "
            f"omit the pipeline name.{RESET}\n"
        )
        raise typer.Exit(1)

    if source == "traversal":
        try:
            graph_state = _read_current_graph_state()
        except CredentialMissing as error:
            typer.echo(f"{RED}{error}{RESET}\n")
            raise typer.Exit(1)
        except Exception as error:
            typer.echo(f"{RED}❌ Neo4j is unavailable: {error}{RESET}")
            typer.echo("   Next: goldilocks doctor\n")
            raise typer.Exit(1)

        if int(graph_state.get("pipeline_count") or 0) == 0:
            typer.echo(f"{GOLD}🌾 The graph has not been seeded yet.{RESET}")
            typer.echo("   Next: goldilocks seed\n")
            raise typer.Exit(1)

    out.mkdir(parents=True, exist_ok=True)

    try:
        if source == "traversal" and combined:
            paths = _render_project_from_traversal(
                out,
                direction,
                fmt,
                collapse,
            )
        elif source == "traversal":
            selected_pipeline = pipeline or pipeline_menu()
            path = _render_from_traversal(
                selected_pipeline,
                out,
                direction,
                fmt,
                collapse,
            )
            paths = [path] if path is not None else []
        else:
            paths = _render_from_json(
                input,
                out,
                direction,
                fmt,
                pipeline,
                single=single,
                combined=combined,
                collapse=collapse,
            )
    except CredentialMissing as error:
        typer.echo(f"{RED}{error}{RESET}\n")
        raise typer.Exit(1)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as error:
        typer.echo(f"{RED}❌ Failed to generate diagram: {error}{RESET}\n")
        raise typer.Exit(1)
    except Exception as error:
        typer.echo(f"{RED}❌ Failed to generate diagram: {error}{RESET}\n")
        raise typer.Exit(1)

    if not paths:
        return

    if len(paths) > 1:
        typer.echo(f"\n{GREEN}🫧 {len(paths)} diagrams written to {out.resolve()}{RESET}")
        return

    final_path = paths[0]
    typer.echo(f"\n{GREEN}🖼️  {final_path.resolve()}{RESET}")

    if confluence:
        copied = clipboard and copy_mermaid_to_clipboard(final_path)
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
    collapse: Optional[bool] = None,
) -> Path | None:
    """Traverse Neo4j and render one measured pipeline DAG."""
    from neo4j import GraphDatabase

    from goldilocks_cli.core.credentials import (
        NEO4J_DEFAULT_USER,
        get_credential,
        require_credential,
    )
    from goldilocks_cli.core.dag_builder import build_dag

    uri = require_credential("NEO4J_URI", "traverse the graph")
    user = get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
    password = require_credential("NEO4J_PASSWORD", "traverse the graph")

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            dag = build_dag(session, pipeline)

    typer.echo(f"  {pipeline}")
    return _write_dag(
        dag,
        out=out,
        direction=direction,
        fmt=fmt,
        explicit_collapse=collapse,
        file_name=f"{_safe_file_name(pipeline)}.mmd",
    )


def _render_project_from_traversal(
    out: Path,
    direction: str,
    fmt: str,
    collapse: Optional[bool],
) -> list[Path]:
    """Render a seeded project using existing graph CALLS relationships."""
    from neo4j import GraphDatabase

    from goldilocks_cli.core.credentials import (
        NEO4J_DEFAULT_USER,
        get_credential,
        require_credential,
    )
    from goldilocks_cli.core.dag_builder import (
        build_project_dags_from_graph,
        read_pipeline_calls,
    )

    uri = require_credential("NEO4J_URI", "traverse the graph")
    user = get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
    password = require_credential("NEO4J_PASSWORD", "traverse the graph")

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            dags = build_project_dags_from_graph(session)
            calls = read_pipeline_calls(session)

    return _render_project_dags(
        dags,
        calls,
        out=out,
        direction=direction,
        fmt=fmt,
        explicit_collapse=collapse,
        combined=True,
    )
