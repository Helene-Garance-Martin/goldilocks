# commands/visualise.py
import typer
from commands.colours import CYAN, GREEN, RED, GOLD, RESET

def visualise(
    input: str = typer.Option("export_anonymised.json", help=(
        "Path to anonymised pipeline JSON\n"
        "  💡 Run the anonymise command first to generate this file"
    )),
    output: str = typer.Option(
        "diagrams/",
        help="Folder to save Mermaid diagram files"
    ),
    direction: str = typer.Option(
        "LR",
        help="Diagram direction: LR or TD"
    ),
    fmt: str = typer.Option(
        "mmd",
        help="Output format: mmd, png or svg"
    ),
    single: str = typer.Option(
        None,
        help="Name of single pipeline to visualise"
    ),
    traversal: bool = typer.Option(
        False,
        "--traversal",
        help="Render Mermaid from Neo4j traversal DAG instead of JSON export",
    ),
):
    """
    🎨 Generate Mermaid diagrams from pipeline data.

    Creates .mmd diagram files showing pipeline architecture.
    """

    typer.echo(f"{CYAN}🎨 Generating Mermaid diagrams...{RESET}")
    typer.echo(f"   Input:     {input}")
    typer.echo(f"   Output:    {output}")
    typer.echo(f"   Direction: {direction}")
    typer.echo(f"   Format:    {fmt}")

    if single:
        typer.echo(f"   Single:    {single}")

    if traversal:
        typer.echo(f"   Mode:      Neo4j Traversal DAG")

    typer.echo("")

    try:

        # ----------------------------------------------------
        # Traversal Mermaid Path
        # ----------------------------------------------------

        if traversal:

            import os
            from pathlib import Path
            from neo4j import GraphDatabase

            from dag_builder import build_dag
            from dag_mermaid_renderer import render_dag_mermaid
            from renderer import render_diagram

            if not single:
                single = typer.prompt("Pipeline name")

            uri = os.environ["NEO4J_URI"]
            user = os.environ.get("NEO4J_USER", "neo4j")
            password = os.environ["NEO4J_PASSWORD"]

            output_path = Path(output)
            output_path.mkdir(parents=True, exist_ok=True)

            with GraphDatabase.driver(
                uri,
                auth=(user, password)
            ) as driver:

                with driver.session() as session:

                    dag = build_dag(
                        session,
                        single
                    )

                    diagram = render_dag_mermaid(
                        dag,
                        direction
                    )

            file_name = (
                single.replace(" ", "_")
                + "_dag.mmd"
            )

            out_file = output_path / file_name

            out_file.write_text(
                diagram,
                encoding="utf-8"
            )

            typer.echo(
                f"{GREEN}✅ Traversal Mermaid diagram: "
                f"{out_file}{RESET}"
            )

            render_diagram(
                out_file,
                fmt
            )

            return

        # ----------------------------------------------------
        # Existing JSON Visualiser Path
        # ----------------------------------------------------

        from visualiser import generate_diagrams

        generate_diagrams(
            input,
            output,
            direction,
            fmt,
            single
        )

        typer.echo(
            f"{GOLD}  💡 Open any .mmd file in VS Code to preview{RESET}\n"
        )

    except Exception as e:

        typer.echo(
            f"{RED}❌ Failed to generate diagram: {e}{RESET}\n"
        )

        raise typer.Exit(1)
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
    

