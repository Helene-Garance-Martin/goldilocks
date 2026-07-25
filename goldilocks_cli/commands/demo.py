# commands/demo.py
# ============================================================
# 🫧 GOLDILOCKS — Private synthetic demo mode
# ============================================================
# One guided, screen-share-friendly run of the real journey —
#   synthetic export → sieve → status → (local seed) →
#   visualise → grounded questions → reset
# — using ONLY invented data, an isolated temporary workspace,
# and no network beyond an optional LOCAL Neo4j.
#
# Boundaries enforced here, not merely promised:
#   - never reads config or the user's working directory
#   - never touches SnapLogic or any LLM (nothing that could
#     is even imported)
#   - graph phase runs only against a LOCAL Neo4j whose graph
#     is EMPTY, and reset only wipes what the demo itself
#     seeded — a remote or occupied graph is warmly skipped
#   - the workspace is a mkdtemp folder, removed on exit
#     unless --keep is passed
# ============================================================

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.table import Table

from goldilocks_cli.colours import CYAN, GOLD, GREEN, RED, BOLD, RESET

console = Console()

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


# ------------------------------------------------------------
# Small helpers — presentation only; all real work is done by
# the existing production functions imported inside demo().
# ------------------------------------------------------------

def _banner() -> None:
    typer.echo("")
    typer.echo(f"{GOLD}{BOLD}🫧 Goldilocks demo — the Marmalade Museum{RESET}")
    typer.echo(
        f"{GOLD}   ALL DATA IS FICTIONAL AND SYNTHETIC — no real organisation,"
        f" system, name or value appears anywhere in this run.{RESET}"
    )
    typer.echo("")


def _neo4j_target() -> tuple[str, str, str] | None:
    """Return (uri, user, password) only when a LOCAL graph is configured."""
    from goldilocks_cli.core.credentials import get_credential, NEO4J_DEFAULT_USER

    uri = get_credential("NEO4J_URI")
    password = get_credential("NEO4J_PASSWORD")
    if uri is None or password is None:
        typer.echo(f"{GOLD}🌾 No Neo4j credentials set — skipping the graph steps.{RESET}")
        typer.echo("   The demo continues from the sieved file alone.\n")
        return None

    host = (urlparse(uri).hostname or "").lower()
    if host not in _LOCAL_HOSTS:
        typer.echo(
            f"{GOLD}🌾 Your Neo4j is remote — the demo only ever seeds a local,"
            f" empty graph, so this step is skipped.{RESET}"
        )
        typer.echo("   Your real graph is untouched, by design.\n")
        return None

    user = get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
    return uri, user, password


def _graph_is_empty(uri: str, user: str, password: str) -> bool:
    from neo4j import GraphDatabase

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            record = session.run("MATCH (n) RETURN count(n) AS total").single()
            return int(record["total"]) == 0


def _wipe_demo_graph(uri: str, user: str, password: str) -> None:
    from neo4j import GraphDatabase

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")


def _demo_survey(workspace: Path, seeded: str) -> None:
    """A field survey of the DEMO workspace only, in the status style.

    The real `status` command scans the user's working directory and
    requires Neo4j — both outside this demo's isolation boundary — so
    the shared state helpers are reused here with an explicit cwd.
    """
    from goldilocks_cli.core.state import find_fetched_exports, find_sieved_exports

    fetched = find_fetched_exports(workspace / "exports", cwd=workspace)
    sieved = find_sieved_exports(workspace / "exports", cwd=workspace)

    table = Table(
        title="🫧 Goldilocks field survey — demo workspace",
        show_header=False,
        box=None,
        padding=(0, 2),
    )
    table.add_column("State", style="cyan", no_wrap=True)
    table.add_column("Value")
    table.add_row("Fetched", "yes (synthetic)" if fetched else "no")
    table.add_row("Sieved", "yes" if sieved else "no")
    table.add_row("Seeded", seeded)
    if sieved:
        state = sieved[0].state or {}
        table.add_row("Source file", state.get("source_file", "—"))
        table.add_row("Sieved at", state.get("sieved_at", "—"))
    console.print(table)
    typer.echo("")


def _grounded_questions(export_path: Path) -> None:
    """Two or three deterministic topology questions — no model, no
    guessing: every answer is read straight from the built DAGs."""
    import json

    from goldilocks_cli.core.dag_builder import (
        build_project_dags,
        resolve_pipeline_calls,
    )
    from goldilocks_cli.core.snap_resolver import EXTERNAL_IO_TYPES

    data = json.loads(export_path.read_text(encoding="utf-8"))
    pipelines = [e for e in data.get("entries", []) if isinstance(e, dict)]
    dags = build_project_dags(pipelines)
    calls = resolve_pipeline_calls(dags)

    typer.echo(f"{CYAN}🔍 Grounded questions — answered from the topology itself:{RESET}\n")

    typer.echo(f"{GOLD}   Which pipeline calls another?{RESET}")
    if calls:
        for call in calls:
            typer.echo(
                f"     • {call.source_pipeline_name} → {call.target_pipeline_name}"
            )
    else:
        typer.echo("     • No pipeline calls found.")

    typer.echo(f"\n{GOLD}   Where does data leave the estate?{RESET}")
    external = [
        (dag.pipeline_name, node.label, node.type)
        for dag in dags
        for node in dag.nodes
        if node.type in EXTERNAL_IO_TYPES
    ]
    for pipeline_name, label, snap_type in external:
        typer.echo(f"     • {pipeline_name} — {label} [{snap_type}]")

    typer.echo(f"\n{GOLD}   Which snaps wipe document context?{RESET}")
    wipers = [
        (dag.pipeline_name, node.label)
        for dag in dags
        for node in dag.nodes
        if node.wipes_context
    ]
    for pipeline_name, label in wipers:
        typer.echo(f"     • {pipeline_name} — {label} 🔥")
    typer.echo("")


# ------------------------------------------------------------
# Command
# ------------------------------------------------------------

def demo(
    plain: bool = typer.Option(
        False,
        "--plain",
        help="Skip the sieve animation (CI, logs, screen readers)",
    ),
    keep: bool = typer.Option(
        False,
        "--keep",
        help="Keep the temporary demo workspace instead of removing it",
    ),
):
    """
    🎬 Run a guided, fully synthetic demo of the Goldilocks journey.

    Uses an invented estate in an isolated temporary workspace.
    Makes no SnapLogic or LLM requests; seeds only a LOCAL, empty
    Neo4j graph when one is available, and offers a clean reset.
    """
    from goldilocks_cli.core.anonymiser import anonymise_pipeline, print_leak_report
    from goldilocks_cli.core.demo_estate import DEMO_ORG, write_demo_export
    from goldilocks_cli.core.sanitiser import sanitise_export

    _banner()

    workspace = Path(tempfile.mkdtemp(prefix="goldilocks-demo-"))
    exports_dir = workspace / "exports" / "marmalade_museum"
    raw_path = write_demo_export(exports_dir / "export.json")
    clean_path = workspace / "export_clean.json"
    anon_path = workspace / "export_anonymised.json"
    demo_seeded_graph = False
    graph_target: tuple[str, str, str] | None = None

    typer.echo(f"   Demo workspace: {workspace}")
    typer.echo(
        f"   Estate: four pipelines from the fictional {DEMO_ORG} —"
        f" a parent, a sibling, a shared child and a grandchild.\n"
    )

    try:
        # ── 2. Sieve — the real sanitise + anonymise path ─────────
        typer.echo(f"{GOLD}🫧 Sieving the synthetic export...{RESET}")
        if plain:
            san = sanitise_export(str(raw_path), str(clean_path))
            anon = anonymise_pipeline(
                str(clean_path), str(anon_path), source_file=raw_path.name
            )
            typer.echo(
                f"🧹 Sanitised {len(san['pipelines'])} pipeline(s); "
                f"🔒 replaced urls: {anon['urls']}, emails: {anon['emails']}, "
                f"guids: {anon['guids']}"
            )
            print_leak_report(anon["leak_findings"])
        else:
            from goldilocks_cli.core.sieveDemo import SieveAnimation

            anim = SieveAnimation()
            anim.start()
            try:
                sanitise_export(str(raw_path), str(clean_path), on_progress=anim.update)
                anon = anonymise_pipeline(
                    str(clean_path),
                    str(anon_path),
                    on_progress=anim.update,
                    source_file=raw_path.name,
                )
            except BaseException:
                anim.abort()
                raise
            anim.finish()
            from goldilocks_cli.commands.anonymise import render_anonymise_summary

            render_anonymise_summary(anon)
        typer.echo("")

        # ── 4. Seed — LOCAL and EMPTY graphs only ─────────────────
        seeded_label = "skipped"
        graph_target = _neo4j_target()
        if graph_target is not None:
            uri, user, password = graph_target
            try:
                if not _graph_is_empty(uri, user, password):
                    typer.echo(
                        f"{GOLD}🌾 Your local graph already holds data —"
                        f" the demo never overwrites it, so seeding is skipped.{RESET}\n"
                    )
                    graph_target = None
                else:
                    typer.echo(f"{CYAN}🌱 Seeding the synthetic topology locally...{RESET}\n")
                    os.environ["GOLDILOCKS_EXPORT_PATH"] = str(anon_path)
                    from goldilocks_cli.core.pipeline_seeder import main as seed_main

                    seed_main()
                    demo_seeded_graph = True
                    seeded_label = "yes (local demo graph)"
            except Exception as e:
                typer.echo(
                    f"{GOLD}🌾 The local graph was not reachable"
                    f" ({type(e).__name__}) — continuing without it.{RESET}\n"
                )
                graph_target = None

        # ── 3. Status — the demo workspace's own survey ───────────
        _demo_survey(workspace, seeded_label)

        # ── 5. Visualise — the real measured Mermaid path ─────────
        typer.echo(f"{CYAN}🎨 Visualising with the production renderer...{RESET}")
        from goldilocks_cli.commands.visualise import _render_from_json

        diagrams_dir = workspace / "diagrams"
        diagrams_dir.mkdir(parents=True, exist_ok=True)
        diagram_paths = _render_from_json(
            str(anon_path),
            diagrams_dir,
            "LR",
            "mmd",
            None,
            single=False,
            combined=False,
            collapse=None,
        )
        typer.echo("")

        # ── 6. Grounded questions — deterministic, no model ───────
        _grounded_questions(anon_path)

        # ── 7. What this demonstrated ─────────────────────────────
        typer.echo(f"{GREEN}{BOLD}🫧 What Goldilocks just demonstrated:{RESET}")
        typer.echo("   • a raw export sieved — sensitive shapes removed, then leak-scanned")
        typer.echo("   • workflow state that knows what has been fetched, sieved and seeded")
        typer.echo(
            f"   • {len(diagram_paths)} honest Mermaid diagram(s), measured before rendering"
        )
        typer.echo("   • topology questions answered from evidence, not guesswork")
        typer.echo(
            f"{GOLD}   (Org-name substitution follows your own sensitive-orgs list,"
            f" which this isolated demo deliberately does not read.){RESET}\n"
        )

    finally:
        # ── 8. Reset — always offered, never silent ───────────────
        if demo_seeded_graph and graph_target is not None:
            uri, user, password = graph_target
            if typer.confirm(
                "Remove the demo data from your local graph?", default=True
            ):
                try:
                    _wipe_demo_graph(uri, user, password)
                    typer.echo(f"{GREEN}✅ Local demo graph emptied.{RESET}")
                except Exception as e:
                    typer.echo(
                        f"{RED}❌ Could not empty the demo graph"
                        f" ({type(e).__name__}) — run the wipe manually.{RESET}"
                    )

        if keep:
            typer.echo(f"{GOLD}   Demo workspace kept: {workspace}{RESET}\n")
        elif typer.confirm("Remove the demo workspace?", default=True):
            shutil.rmtree(workspace, ignore_errors=True)
            typer.echo(f"{GREEN}✅ Demo workspace removed. Nothing else was touched.{RESET}\n")
        else:
            typer.echo(f"{GOLD}   Demo workspace kept: {workspace}{RESET}\n")
