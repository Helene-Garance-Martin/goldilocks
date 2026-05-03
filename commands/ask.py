# commands/ask.py
import typer
import json
from pathlib import Path
from typing import Optional
from commands.colours import CYAN, GREEN, RED, GOLD, RESET

def ask(
    question: Optional[str] = typer.Argument(None, help="Ask Goldilocks a question about your pipelines"),
    input: str = typer.Option("export_anonymised.json", help="Path to anonymised pipeline JSON"),
):
    """
    🤖 Ask Goldilocks a question about your pipelines.
    """
    if not question:
        question = typer.prompt(f"{GOLD}Ask Goldilocks{RESET}")

    typer.echo(f"{CYAN}🤖 Thinking...{RESET}\n")

    # ── Token risk queries (local — no Neo4j needed) ──────
    if any(word in question.lower() for word in ["token", "risk", "wipes", "credential", "bearer"]):
        try:
            data      = json.loads(Path(input).read_text())
            pipelines = data.get("entries", [data])

            # Filter by pipeline name if mentioned in question
            matching = [
                p for p in pipelines
                if p.get("name", "").lower() in question.lower()
            ] or pipelines

            from describer import describe_token_risks
            for pipeline in matching:
                name   = pipeline.get("name", "Unknown")
                report = describe_token_risks(name, pipeline)
                typer.echo(report)
            return

        except Exception as e:
            typer.echo(f"{RED}❌ Failed: {e}{RESET}\n")
            raise typer.Exit(1)

    # ── Neo4j queries (requires connectivity) ─────────────
    try:
        from describer import describe_from_neo4j
        answer = describe_from_neo4j()
        
        typer.echo(answer)


    except Exception as e:
        typer.echo(f"{RED}❌ Failed to answer question: {e}{RESET}\n")
        raise typer.Exit(1)