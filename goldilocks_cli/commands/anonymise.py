# commands/anonymise.py
import time

import typer
from rich.console import Console
from goldilocks_cli.colours import CYAN, GREEN, RED, GOLD, RESET

console = Console()


def render_anonymise_summary(summary: dict) -> None:
    """The reveal — counts, leak report, honest advisory. Same pacing
    the core used to carry."""
    from goldilocks_cli.core.anonymiser import print_leak_report

    if summary["fallback"]:
        typer.echo(f"{GOLD}⚠️   Input was not valid JSON — fell back to text scrubbing.{RESET}")
        typer.echo("    (Credential values cannot be detected without JSON keys.)")

    typer.echo(f"✅  Anonymised file written to: {summary['output']}")
    time.sleep(0.2)
    typer.echo("\n📊  Summary:")
    time.sleep(0.15)
    typer.echo(f"    Orgs replaced:        {summary['orgs']}")
    time.sleep(0.1)
    typer.echo(f"    URLs replaced:        {summary['urls']}")
    time.sleep(0.1)
    typer.echo(f"    Emails replaced:      {summary['emails']}")
    time.sleep(0.1)
    typer.echo(f"    Credentials replaced: {summary['credentials']}")
    time.sleep(0.1)
    typer.echo(f"    GUIDs replaced:       {summary['guids']}")
    time.sleep(0.1)

    print_leak_report(summary["leak_findings"])
    typer.echo("    Automated scrubbing catches known patterns only —")
    typer.echo("    give the file ten adversarial minutes before sharing.")


def anonymise(
    input: str = typer.Option(..., help="Path to sanitised export_clean.json"),
    output: str = typer.Option("export_anonymised.json", help="Path to write anonymised output"),
):
    """
    🔒 Anonymise a sanitised export.

    Replaces org names, URLs, emails and credentials with
    consistent fake values, then leak-scans the result.
    Automated scrubbing catches known patterns only —
    review the output before sharing.
    """
    typer.echo(f"{CYAN}🔒 Anonymising pipeline export...{RESET}")
    typer.echo(f"   Input:  {input}")
    typer.echo(f"   Output: {output}")
    typer.echo("")

    try:
        with console.status("[magenta]Anonymising...[/magenta]", spinner="dots"):
            from goldilocks_cli.core.anonymiser import anonymise_pipeline
            summary = anonymise_pipeline(input, output)
        render_anonymise_summary(summary)
        typer.echo(f"\n{GREEN}✅ Done — known sensitive patterns removed. Review before sharing.{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Failed: {e}{RESET}\n")
        raise typer.Exit(1)
