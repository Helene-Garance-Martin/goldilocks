# commands/seed.py

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from goldilocks_cli.colours import CYAN, GREEN, RED, GOLD, RESET

console = Console()


def _select_sieved_export() -> Path:
    """Resolve an omitted input without silently choosing among candidates."""
    from goldilocks_cli.core.config import load_config
    from goldilocks_cli.core.state import find_sieved_exports

    config = load_config()
    candidates = find_sieved_exports(config["paths"]["exports_dir"])

    if not candidates:
        typer.echo(f"{GOLD}🌾 No sieved export is ready to seed.{RESET}")
        typer.echo("   Next: goldilocks sieve\n")
        raise typer.Exit(1)

    if len(candidates) == 1:
        return candidates[0].path

    typer.echo(f"{GOLD}📦 Several sieved exports are ready:{RESET}\n")
    for index, candidate in enumerate(candidates, start=1):
        stamp = candidate.modified_at.astimezone().strftime("%Y-%m-%d %H:%M")
        marker = "marked" if candidate.state else "legacy"
        typer.echo(f"  {index}. {candidate.path}  ({stamp}, {marker})")
    typer.echo("")

    choice = typer.prompt("Which export should Goldilocks seed?", default="1")
    try:
        return candidates[int(choice) - 1].path
    except (ValueError, IndexError):
        typer.echo(f"{RED}❌ That export is not in the list.{RESET}\n")
        raise typer.Exit(1)


def _read_current_graph_state(uri: str, username: str, password: str) -> dict:
    """Read the lightweight graph state before deciding whether to re-seed."""
    from neo4j import GraphDatabase
    from goldilocks_cli.core.state import read_graph_state

    with GraphDatabase.driver(uri, auth=(username, password)) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            return read_graph_state(session)


def _warn_if_stale(input_path: Path, file_state: Optional[dict]) -> None:
    from goldilocks_cli.core.config import load_config
    from goldilocks_cli.core.state import age_in_days, is_stale, stale_after_days

    config = load_config()
    threshold = stale_after_days(config)
    timestamp = (
        file_state.get("sieved_at")
        if file_state
        else datetime.fromtimestamp(input_path.stat().st_mtime, tz=timezone.utc)
    )
    if not is_stale(timestamp, threshold):
        return

    age = age_in_days(timestamp)
    days = int(age) if age is not None else threshold + 1
    typer.echo(
        f"{GOLD}🌾 This export is {days} days old "
        f"(stale after {threshold} days).{RESET}"
    )
    typer.echo("   Seed it if intentional; fetch and sieve again for current topology.\n")


def seed(
    input: Optional[str] = typer.Option(
        None,
        "--input", "-i",
        help="Path to anonymised pipeline JSON (omit to select one)",
    ),
    uri: str = typer.Option(
        None,
        help="Neo4j Aura URI (defaults to NEO4J_URI)",
    ),
    username: str = typer.Option(
        None,
        help="Neo4j username (defaults to NEO4J_USER)",
    ),
    password: str = typer.Option(
        None,
        help="Neo4j password (defaults to NEO4J_PASSWORD)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Allow clean legacy or repeated seeding without confirmation",
    ),
):
    """
    🌱 Seed the Neo4j graph with pipeline data.
    """
    input_path = Path(input) if input else _select_sieved_export()
    if not input_path.is_file():
        typer.echo(f"{RED}❌ File not found: {input_path}{RESET}")
        typer.echo("   Next: goldilocks sieve --input <raw export>\n")
        raise typer.Exit(1)

    # ── One authoritative pre-seed safety gate ─────────────
    from goldilocks_cli.core.anonymiser import scan_for_leaks, print_leak_report
    from goldilocks_cli.core.state import read_file_state

    file_state = read_file_state(input_path)
    findings = scan_for_leaks(input_path.read_text(encoding="utf-8"))
    if findings:
        print_leak_report(findings)
        typer.echo(f"{RED}🛑 Seed refused — leak findings must be resolved first.{RESET}")
        typer.echo("   Next: goldilocks sieve --input <raw export>\n")
        raise typer.Exit(1)

    typer.echo("🔍 pre-seed check: clean")
    _warn_if_stale(input_path, file_state)

    # ── Credentials — flags win, else the central module ──
    from goldilocks_cli.core.credentials import (
        require_credential, get_credential,
        NEO4J_DEFAULT_USER, CredentialMissing,
    )

    try:
        uri = uri or require_credential("NEO4J_URI", "seed the graph")
        username = username or get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
        password = password or require_credential("NEO4J_PASSWORD", "seed the graph")
    except CredentialMissing as e:
        typer.echo(f"{RED}{e}{RESET}")
        raise typer.Exit(1)

    try:
        graph_state = _read_current_graph_state(uri, username, password)
    except Exception as e:
        typer.echo(f"{RED}❌ Neo4j is not ready for seeding: {e}{RESET}")
        typer.echo("   Next: goldilocks doctor\n")
        raise typer.Exit(1)

    # Legacy confidence and re-seed confidence are combined into one
    # decision so the user never receives two consecutive prompts.
    reasons = []
    if not file_state or file_state.get("stage") != "sieved":
        reasons.append(
            "This clean file has no Goldilocks sieve marker; it may be a legacy export."
        )

    pipeline_count = int(graph_state.get("pipeline_count") or 0)
    if pipeline_count:
        previous_source = graph_state.get("source_file")
        previous_time = graph_state.get("last_seeded")
        if previous_source:
            detail = f"Already seeded from {previous_source}"
            if previous_time:
                detail += f" on {previous_time}"
            reasons.append(detail + ".")
        else:
            reasons.append(
                f"Neo4j already contains {pipeline_count} pipeline(s) without a Goldilocks seed marker."
            )

    if reasons and not force:
        typer.echo(f"{GOLD}🌱 Before Goldilocks plants this export:{RESET}")
        for reason in reasons:
            typer.echo(f"   • {reason}")
        if not typer.confirm("Proceed with seeding?", default=False):
            typer.echo("🌾 Seeding cancelled; the graph was left unchanged.\n")
            raise typer.Exit(1)

    typer.echo(f"{CYAN}🌱 Seeding Neo4j graph...{RESET}")
    typer.echo(f"   Input: {input_path}")
    typer.echo(f"   URI:   {uri}")
    typer.echo("")

    try:
        os.environ["NEO4J_URI"] = uri
        os.environ["NEO4J_USER"] = username
        os.environ["NEO4J_PASSWORD"] = password
        os.environ["GOLDILOCKS_EXPORT_PATH"] = str(input_path)

        with console.status(
            "[magenta]Seeding graph...[/magenta]",
            spinner="dots",
        ):
            from goldilocks_cli.core.pipeline_seeder import main
            main()

        typer.echo(f"{GREEN}✅ Graph seeded successfully!{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Seeding failed: {e}{RESET}\n")
        raise typer.Exit(1)
