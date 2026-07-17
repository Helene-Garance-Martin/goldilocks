# commands/status.py
# ============================================================
# 🫧 Goldilocks workflow status
# ============================================================

from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from goldilocks_cli.colours import CYAN, GOLD, GREEN, RED, RESET
from goldilocks_cli.core.credentials import CredentialMissing

console = Console()


def _read_neo4j_state() -> dict:
    """Read one lightweight graph-state record using configured credentials."""
    from neo4j import GraphDatabase
    from goldilocks_cli.core.credentials import (
        require_credential,
        get_credential,
        NEO4J_DEFAULT_USER,
    )
    from goldilocks_cli.core.state import read_graph_state

    uri = require_credential("NEO4J_URI", "survey Goldilocks state")
    user = get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
    password = require_credential("NEO4J_PASSWORD", "survey Goldilocks state")

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            return read_graph_state(session)


def _age_label(value) -> str:
    from goldilocks_cli.core.state import age_in_days

    age = age_in_days(value)
    if age is None:
        return "unknown"
    days = int(age)
    if days == 0:
        return "today"
    if days == 1:
        return "1 day"
    return f"{days} days"


def _file_state_label(candidates, noun: str) -> str:
    if not candidates:
        return "no"
    if len(candidates) == 1:
        return "yes"
    return f"ambiguous ({len(candidates)} {noun})"


def _print_candidates(title: str, candidates) -> None:
    if len(candidates) < 2:
        return
    typer.echo(f"\n{GOLD}{title}:{RESET}")
    for candidate in candidates:
        stamp = candidate.modified_at.astimezone().strftime("%Y-%m-%d %H:%M")
        typer.echo(f"  • {candidate.path}  ({stamp})")


def _graph_is_stale(graph_state: dict, fetched, threshold: int) -> bool:
    from goldilocks_cli.core.state import is_stale, parse_timestamp

    if int(graph_state.get("pipeline_count") or 0) == 0:
        return False

    source_time = graph_state.get("source_sieved_at") or graph_state.get("last_seeded")
    if is_stale(source_time, threshold) or is_stale(graph_state.get("last_seeded"), threshold):
        return True

    # Any newer fetch means the graph no longer represents the latest
    # known source, even when several exports require an explicit choice.
    if fetched:
        seeded_at = parse_timestamp(graph_state.get("last_seeded"))
        if seeded_at and any(candidate.modified_at > seeded_at for candidate in fetched):
            return True

    return False


def _next_step(fetched, sieved, graph_state: dict, stale: bool) -> str:
    seeded = int(graph_state.get("pipeline_count") or 0) > 0

    if not seeded:
        if not sieved:
            if not fetched:
                return "goldilocks fetch"
            if len(fetched) == 1:
                return f"goldilocks sieve --input {fetched[0].path}"
            return "goldilocks sieve --input <choose-one-export>"
        if len(sieved) == 1:
            return f"goldilocks seed --input {sieved[0].path}"
        return "goldilocks seed --input <choose-one-sieved-export>"

    if stale:
        return "goldilocks fetch"

    return 'goldilocks ask "What should I inspect?"'


def status():
    """
    🌾 Show where Goldilocks is in the fetch → sieve → seed workflow.
    """
    from goldilocks_cli.core.config import load_config
    from goldilocks_cli.core.state import (
        find_fetched_exports,
        find_sieved_exports,
        stale_after_days,
    )

    config = load_config()
    fetched = find_fetched_exports(config["paths"]["exports_dir"])
    sieved = find_sieved_exports(config["paths"]["exports_dir"])
    threshold = stale_after_days(config)

    try:
        graph_state = _read_neo4j_state()
    except CredentialMissing as e:
        typer.echo(f"{RED}{e}{RESET}\n")
        typer.echo("   Next: goldilocks doctor\n")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"{RED}❌ Goldilocks could not survey Neo4j: {e}{RESET}")
        typer.echo("   Next: goldilocks doctor\n")
        raise typer.Exit(1)

    pipeline_count = int(graph_state.get("pipeline_count") or 0)
    seeded = pipeline_count > 0
    stale = _graph_is_stale(graph_state, fetched, threshold)

    if len(fetched) == 1:
        displayed_age = _age_label(fetched[0].modified_at)
    elif len(sieved) == 1:
        displayed_age = _age_label(
            (sieved[0].state or {}).get("sieved_at") or sieved[0].modified_at
        )
    else:
        displayed_age = "—"
    source_file = graph_state.get("source_file")
    if not source_file and len(sieved) == 1:
        source_file = sieved[0].path.name
    if not source_file and len(fetched) == 1:
        source_file = fetched[0].path.name

    table = Table(
        title="🫧 Goldilocks field survey",
        show_header=False,
        box=None,
        padding=(0, 2),
    )
    table.add_column("State", style="cyan", no_wrap=True)
    table.add_column("Value")
    table.add_row("Fetched", _file_state_label(fetched, "exports"))
    table.add_row("Age", displayed_age)
    table.add_row("Sieved", _file_state_label(sieved, "files"))
    table.add_row("Seeded", "yes" if seeded else "no")
    table.add_row("Source file", source_file or "—")
    table.add_row("Pipeline count", str(pipeline_count))
    table.add_row("Seed time", graph_state.get("last_seeded") or "—")

    console.print(table)

    if stale:
        source_age = _age_label(
            graph_state.get("source_sieved_at") or graph_state.get("last_seeded")
        )
        typer.echo(
            f"\n{GOLD}🌾 Seeded, but stale: the graph source is {source_age} old "
            f"(threshold {threshold} days).{RESET}"
        )
    elif seeded:
        typer.echo(f"\n{GREEN}🌱 Seeded and ready.{RESET}")

    _print_candidates("Fetched exports need an explicit choice", fetched)
    _print_candidates("Sieved exports need an explicit choice", sieved)

    typer.echo(f"\n{CYAN}Next: {_next_step(fetched, sieved, graph_state, stale)}{RESET}\n")
