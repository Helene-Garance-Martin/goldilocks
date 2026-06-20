# commands/audit.py

import os
import typer

from rich.console import Console
from rich.table import Table

from commands.colours import CYAN, GREEN, RED, YELLOW, RESET

console = Console()


def audit():
    """
    🔐 Security and topology audit — inspect the Neo4j pipeline graph.
    """

    typer.echo(f"{CYAN}🔐 Running Goldilocks Graph Audit...{RESET}\n")

    try:
        from neo4j import GraphDatabase

        uri = os.environ["NEO4J_URI"]
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ["NEO4J_PASSWORD"]

        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            with driver.session() as session:
                findings = _collect_findings(session)
                _print_findings(findings)

        typer.echo(f"\n{GREEN}✅ Audit complete.{RESET}\n")

    except KeyError:
        typer.echo(
            f"{YELLOW}⚠️  Neo4j env vars not set "
            f"(NEO4J_URI, NEO4J_PASSWORD){RESET}\n"
        )

    except Exception as e:
        typer.echo(f"{RED}❌ Audit failed: {e}{RESET}\n")


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
    """Render PipeExec child pipeline references with status styling."""

    console.print()

    if not rows:
        console.print("[green]✅ 🔀 PipeExec calls: none found[/green]")
        return

    table = Table(
        title="🔀 PipeExec calls · child pipeline references",
        show_header=True,
        header_style="bold gold1",
        border_style="gold3",
        row_styles=["", "dim"],
    )

    table.add_column("Pipeline", style="white")
    table.add_column("Snap", style="bright_blue")
    table.add_column("Child Pipeline", style="white")
    table.add_column("Resolved Child", style="gold1")
    table.add_column("Status")

    for row in rows:
        status = row.get("status", "")

        if status == "resolved":
            status_text = "[green]🔗 found in graph[/green]"
        else:
            status_text = "[red]❌ missing from graph[/red]"

        table.add_row(
            str(row.get("pipeline", "") or ""),
            str(row.get("snap", "") or ""),
            str(row.get("child_pipeline", "") or ""),
            str(row.get("resolved_child", "") or "—"),
            status_text,
        )

    console.print(table)

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