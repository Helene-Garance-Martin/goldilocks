# commands/ask.py
import json
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from commands.colours import CYAN, GREEN, RED, GOLD, RESET

console = Console()

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
            matching  = [
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

    # ── AI agent queries (Neo4j + Anthropic) ──────────────
    try:
        with console.status("[magenta]Consulting the graph...[/magenta]", spinner="dots"):
            from agent import ask_goldilocks
            answer = ask_goldilocks(question)

        typer.echo(answer)
        typer.echo("")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed to answer question: {e}{RESET}\n")
        raise typer.Exit(1)