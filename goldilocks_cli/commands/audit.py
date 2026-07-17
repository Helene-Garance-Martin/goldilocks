# commands/audit.py

import typer

from rich.console import Console
from rich.table import Table

from collections import defaultdict
from rich.tree import Tree

from goldilocks_cli.colours import CYAN, GREEN, RED, YELLOW, RESET

console = Console()


def audit():
    """
    🔐 Security and topology audit — inspect the Neo4j pipeline graph.
    """

    typer.echo(f"{CYAN}🔐 Running Goldilocks Graph Audit...{RESET}\n")

    try:
        from neo4j import GraphDatabase

        from goldilocks_cli.core.credentials import (
            require_credential, get_credential,
            NEO4J_DEFAULT_USER, CredentialMissing,
        )

        uri = require_credential("NEO4J_URI", "audit the graph")
        user = get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
        password = require_credential("NEO4J_PASSWORD", "audit the graph")

        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            with driver.session() as session:
                findings = _collect_findings(session)
                _print_findings(findings)

        typer.echo(f"\n{GREEN}✅ Audit complete.{RESET}\n")

    except CredentialMissing as e:
        typer.echo(f"{RED}{e}{RESET}\n")
        raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"{RED}❌ Audit failed: {e}{RESET}\n")
        raise typer.Exit(1)


def _collect_findings(session) -> dict:
    """Collect graph-native audit findings from Neo4j."""

    findings = {
        "summary": _query_one(
            session,
            """
            MATCH (p:Pipeline)
            OPTIONAL MATCH (p)-[:HAS_SNAP]->(s:Snap)
            RETURN
                count(DISTINCT p) AS pipelines,
                count(DISTINCT s) AS snaps
            """
        ),
        "large_pipelines": _query_all(
            session,
            """
            MATCH (p:Pipeline)-[:HAS_SNAP]->(s:Snap)
            WITH p, count(s) AS snap_count
            WHERE snap_count >= 25
            RETURN p.name AS pipeline, snap_count
            ORDER BY snap_count DESC
            """
        ),
        "http_snaps": _query_all(
            session,
            """
            MATCH (p:Pipeline)-[:HAS_SNAP]->(s:Snap)
            WHERE s.type = "httpclient"
            RETURN p.name AS pipeline, s.label AS snap
            ORDER BY pipeline, snap
            """
        ),
        "script_snaps": _query_all(
            session,
            """
            MATCH (p:Pipeline)-[:HAS_SNAP]->(s:Snap)
            WHERE s.type = "script"
            RETURN p.name AS pipeline, s.label AS snap
            ORDER BY pipeline, snap
            """
        ),
        "pipeexec_snaps": _query_all(
            session,
            """
            MATCH (p:Pipeline)-[:HAS_SNAP]->(s:Snap)
            WHERE s.type = "pipeexec"
            OPTIONAL MATCH (p)-[:CALLS]->(child:Pipeline)
            WHERE s.child_pipeline CONTAINS child.name
               OR child.name CONTAINS s.child_pipeline
            RETURN
                p.name AS pipeline,
                s.label AS snap,
                s.child_pipeline AS child_pipeline,
                child.name AS resolved_child,
                CASE
                    WHEN child.name IS NULL THEN "missing"
                    ELSE "resolved"
                END AS status
            ORDER BY pipeline, snap
            """
        ),
        "router_pipelines": _query_all(
            session,
            """
            MATCH (p:Pipeline)-[:HAS_SNAP]->(s:Snap)
            WHERE s.type = "router"
            WITH p, count(s) AS router_count
            RETURN p.name AS pipeline, router_count
            ORDER BY router_count DESC, pipeline
            """
        ),
        "context_wiping_snaps": _query_all(
            session,
            """
            MATCH (p:Pipeline)-[:HAS_SNAP]->(s:Snap)
            WHERE s.wipes_context = true
            RETURN p.name AS pipeline, s.label AS snap, s.type AS type
            ORDER BY pipeline, snap
            """
        ),
        "emails": _query_all(
            session,
            """
            MATCH (n)
            UNWIND keys(n) AS property
            WITH labels(n) AS labels, property, toString(n[property]) AS value
            WHERE value CONTAINS "@"
            RETURN labels, property, value
            LIMIT 50
            """
        ),
    }

    for row in findings["pipeexec_snaps"]:
        row["child_pipeline"] = _clean_child_pipeline(
            row.get("child_pipeline")
        )
        row["resolved_child"] = row.get("resolved_child") or ""

    return findings

def _query_one(session, cypher: str) -> dict:
    """Run a Cypher query expected to return one row."""
    result = session.run(cypher)
    row = result.single()
    return dict(row) if row else {}


def _query_all(session, cypher: str) -> list[dict]:
    """Run a Cypher query and return all rows as dictionaries."""
    return [dict(row) for row in session.run(cypher)]


def _print_findings(findings: dict) -> None:
    """Render audit findings as Rich tables."""

    summary = findings["summary"]

    summary_table = Table(
        title="🔎 Graph Audit Summary",
        show_header=True,
        header_style="bold yellow",
    )
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green", justify="right")

    summary_table.add_row("Pipelines", str(summary.get("pipelines", 0)))
    summary_table.add_row("Snaps", str(summary.get("snaps", 0)))
    summary_table.add_row("Large pipelines", str(len(findings["large_pipelines"])))
    summary_table.add_row("HTTP snaps", str(len(findings["http_snaps"])))
    summary_table.add_row("Script snaps", str(len(findings["script_snaps"])))
    summary_table.add_row("PipeExec snaps", str(len(findings["pipeexec_snaps"])))
    summary_table.add_row("Router pipelines", str(len(findings["router_pipelines"])))
    summary_table.add_row("Context-wiping snaps", str(len(findings["context_wiping_snaps"])))

    console.print(summary_table)

    _print_simple_table(
        "⚠️ Large pipelines",
        findings["large_pipelines"],
        ["pipeline", "snap_count"],
    )

    _print_simple_table(
        "🌐 HTTP snaps",
        findings["http_snaps"],
        ["pipeline", "snap"],
    )

    _print_simple_table(
        "📜 Script snaps",
        findings["script_snaps"],
        ["pipeline", "snap"],
    )
def _print_findings(findings: dict) -> None:
    """Render audit findings as Rich tables."""

    summary = findings["summary"]

    summary_table = Table(
        title="🔎 Graph Audit Summary",
        show_header=True,
        header_style="bold yellow",
    )
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green", justify="right")

    summary_table.add_row("Pipelines", str(summary.get("pipelines", 0)))
    summary_table.add_row("Snaps", str(summary.get("snaps", 0)))
    summary_table.add_row("Large pipelines", str(len(findings["large_pipelines"])))
    summary_table.add_row("HTTP snaps", str(len(findings["http_snaps"])))
    summary_table.add_row("Script snaps", str(len(findings["script_snaps"])))
    summary_table.add_row("PipeExec snaps", str(len(findings["pipeexec_snaps"])))
    summary_table.add_row("Router pipelines", str(len(findings["router_pipelines"])))
    summary_table.add_row(
        "Context-wiping snaps",
        str(len(findings["context_wiping_snaps"])),
    )

    console.print(summary_table)

    _print_simple_table(
        "⚠️ Large pipelines",
        findings["large_pipelines"],
        ["pipeline", "snap_count"],
    )

    _print_simple_table(
        "🌐 HTTP snaps",
        findings["http_snaps"],
        ["pipeline", "snap"],
    )

    _print_simple_table(
        "📜 Script snaps",
        findings["script_snaps"],
        ["pipeline", "snap"],
    )

    _print_pipeexec_table(findings["pipeexec_snaps"])

    _print_simple_table(
        "🧭 Router pipelines",
        findings["router_pipelines"],
        ["pipeline", "router_count"],
    )

    _print_simple_table(
        "🔥 Context-wiping snaps",
        findings["context_wiping_snaps"],
        ["pipeline", "snap", "type"],
    )

    _print_simple_table(
        "📧 Possible emails",
        findings["emails"],
        ["labels", "property", "value"],
    )


def _print_pipeexec_table(rows: list[dict]) -> None:
    """Render PipeExec child pipeline references grouped by parent pipeline."""

    console.print()

    if not rows:
        console.print("[green]✅ 🔀 Pipeline calls: none found[/green]")
        return

    grouped = defaultdict(list)

    for row in rows:
        grouped[row.get("pipeline", "Unknown")].append(row)

    tree = Tree("[bold gold1]🔀 Pipeline Calls[/bold gold1]")

    for pipeline, calls in grouped.items():
        pipeline_branch = tree.add(
            f"[bold white]{pipeline}[/bold white]"
        )

        collapsed = defaultdict(list)

        for row in calls:
            key = (
                row.get("snap", "") or "Unknown snap",
                row.get("resolved_child", "")
                or row.get("child_pipeline", "")
                or "Unknown child",
                row.get("status", "") or "missing",
            )
            collapsed[key].append(row)

        for (snap, child, status), grouped_rows in collapsed.items():
            count = len(grouped_rows)

            snap_branch = pipeline_branch.add(
                f"[bright_blue]↳ {snap}[/bright_blue]"
            )

            suffix = (
                f" [dim]({count} references)[/dim]"
                if count > 1
                else ""
            )

            child_branch = snap_branch.add(
                f"[gold1]↳ {child}[/gold1]{suffix}"
            )

            if status == "resolved":
                child_branch.add(
                    "[green]🔗 found in graph[/green]"
                )
            else:
                child_branch.add(
                    "[red]❌ missing from graph[/red]"
                )

    console.print(tree)

    found = sum(1 for row in rows if row.get("status") == "resolved")
    missing = sum(1 for row in rows if row.get("status") == "missing")

    summary = Table.grid(padding=(0, 3))
    summary.add_column(style="gold1")
    summary.add_column(style="white")

    summary.add_row("🔀 Child references", str(len(rows)))
    summary.add_row("🔗 Found in graph", f"[green]{found}[/green]")
    summary.add_row("❌ Missing from graph", f"[red]{missing}[/red]")

    console.print()
    console.print(summary)
    
    
def _clean_child_pipeline(value: str | None) -> str:
    """Return a readable child pipeline name from a stored PipeExec path."""
    if not value:
        return ""

    return value.replace("\\", "/").split("/")[-1]

def _print_simple_table(
    title: str,
    rows: list[dict],
    columns: list[str],
) -> None:
    """Print a table if rows exist, otherwise print a quiet empty state."""

    console.print()

    if not rows:
        console.print(f"[green]✅ {title}: none found[/green]")
        return

    table = Table(
        title=title,
        show_header=True,
        header_style="bold yellow",
    )

    for column in columns:
        table.add_column(column.replace("_", " ").title())

    for row in rows:
        table.add_row(
            *[
                str(row.get(column, "") or "")
                for column in columns
            ]
        )

    console.print(table)