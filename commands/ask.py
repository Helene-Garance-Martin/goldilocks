# commands/ask.py
import typer
from typing import Optional
from commands.colours import CYAN, GREEN, RED, GOLD, RESET

def ask(
    question: Optional[str] = typer.Argument(None, help="Ask Goldilocks a question about your pipelines"),
):
    """
    🤖 Ask Goldilocks a simple question about your pipelines.
    """
    if not question:
        question = typer.prompt(f"{GOLD}Ask Goldilocks{RESET}")

    try:
        from describer import describe_from_neo4j
        answer = describe_from_neo4j()

        typer.echo("")
        typer.echo(answer)
        typer.echo("")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed to answer question: {e}{RESET}\n")
        raise typer.Exit(1)