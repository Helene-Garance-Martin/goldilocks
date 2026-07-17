# commands/sieve.py
from pathlib import Path
from typing import Optional

import typer

from goldilocks_cli.colours import CYAN, GREEN, RED, GOLD, BOLD, RESET


def _select_fetched_export() -> Path:
    """Resolve an omitted input without silently choosing among exports."""
    from goldilocks_cli.core.config import load_config
    from goldilocks_cli.core.state import find_fetched_exports

    config = load_config()
    candidates = find_fetched_exports(config["paths"]["exports_dir"])

    if not candidates:
        typer.echo(f"{GOLD}🌾 Nothing has been fetched yet.{RESET}")
        typer.echo("   Next: goldilocks fetch\n")
        raise typer.Exit(1)

    if len(candidates) == 1:
        return candidates[0].path

    typer.echo(f"{GOLD}📦 Several fetched exports are waiting in the field:{RESET}\n")
    for index, candidate in enumerate(candidates, start=1):
        stamp = candidate.modified_at.astimezone().strftime("%Y-%m-%d %H:%M")
        typer.echo(f"  {index}. {candidate.path}  ({stamp})")
    typer.echo("")

    choice = typer.prompt("Which export should Goldilocks sieve?", default="1")
    try:
        return candidates[int(choice) - 1].path
    except (ValueError, IndexError):
        typer.echo(f"{RED}❌ That export is not in the list.{RESET}\n")
        raise typer.Exit(1)


def sieve(
    input: Optional[str] = typer.Option(
        None,
        "--input", "-i",
        help="Path to raw export.json (omit to select a fetched export)",
    ),
    sanitised: str = typer.Option("export_clean.json", help="Sanitised intermediate"),
    anonymised: str = typer.Option("export_anonymised.json", help="Final anonymised output"),
    plain: bool = typer.Option(False, "--plain", help="Skip animation (CI/logs)"),
):
    """
    🫧 Sieve a raw pipeline export — sanitise and anonymise in one pass.

    fetch → sieve → seed
    """
    from goldilocks_cli.core.state import read_file_state

    input_path = Path(input) if input else _select_fetched_export()
    if not input_path.is_file():
        typer.echo(f"{RED}❌ Fetched export not found: {input_path}{RESET}")
        typer.echo("   Next: goldilocks fetch\n")
        raise typer.Exit(1)

    file_state = read_file_state(input_path)
    if file_state and file_state.get("stage") == "sieved":
        when = file_state.get("sieved_at", "an earlier run")
        typer.echo(f"{GOLD}🫧 This file already carries a sieved marker ({when}).{RESET}")
        if not typer.confirm("Sieve it again?", default=False):
            typer.echo("🌾 Sieve left as it was.\n")
            raise typer.Exit(0)

    input = str(input_path)
    typer.echo(f"{GOLD}🫧 Sieving pipeline export...{RESET}")
    typer.echo(f"   Input:       {input}")
    typer.echo(f"   Anonymised:  {anonymised}\n")

    from goldilocks_cli.core.sanitiser import sanitise_export
    from goldilocks_cli.core.anonymiser import anonymise_pipeline

    if plain:
        try:
            san = sanitise_export(input, sanitised)
            anon = anonymise_pipeline(
                sanitised,
                anonymised,
                source_file=input_path.name,
            )
        except Exception as e:
            typer.echo(f"{RED}❌ Sieve failed: {e}{RESET}\n")
            raise typer.Exit(1)
        typer.echo(
            f"🧹 Sanitised {len(san['pipelines'])} pipeline(s) → {san['output']}"
        )
        typer.echo(
            f"🔒 Anonymised — orgs: {anon['orgs']}, urls: {anon['urls']}, "
            f"emails: {anon['emails']}, credentials: {anon['credentials']}, guids: {anon['guids']}"
        )
        from goldilocks_cli.core.anonymiser import print_leak_report
        print_leak_report(anon["leak_findings"])
        typer.echo(f"{GREEN}🫧 Sieve complete — data ready to seed.{RESET}\n")
        return

    from goldilocks_cli.core.sieveDemo import SieveAnimation

    anim = SieveAnimation()
    anim.start()

    try:
        sanitise_export(input, sanitised, on_progress=anim.update)
        anon = anonymise_pipeline(
            sanitised,
            anonymised,
            on_progress=anim.update,
            source_file=input_path.name,
        )
    except Exception as e:
        anim.abort()
        typer.echo(f"\n{RED}❌ Sieve failed: {e}{RESET}\n")
        raise typer.Exit(1)

    anim.finish()
    from goldilocks_cli.commands.anonymise import render_anonymise_summary
    render_anonymise_summary(anon)
    typer.echo(f"\n{GOLD}{BOLD}   data ready to seed — fetch → sieve → seed{RESET}\n")
