# commands/inspect_export.py

import json
from collections import Counter
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from goldilocks_cli.colours import GREEN, RED, GOLD, RESET

console = Console()


DEV_WORDS = ["copy", "test", "try", "old"]


def inspect_export(
    input: Path = typer.Option(..., "--input", "-i", help="Path to export JSON"),
):
    """🔍 Inspect a SnapLogic export without touching Neo4j."""

    if not input.exists():
        typer.echo(f"{RED}❌ File not found: {input}{RESET}")
        raise typer.Exit(1)

    data = json.loads(input.read_text(encoding="utf-8"))

    entries = data.get("entries", [])
    primary = []
    devish = []

    for entry in entries:
        name = entry.get("name", "")
        lowered = name.lower()

        if any(word in lowered for word in DEV_WORDS):
            devish.append(entry)
        else:
            primary.append(entry)

    console.print(f"\n[gold1]🔍 Export inspection[/gold1]")
    console.print(f"[dim]File:[/dim] {input}\n")

    summary = Table(title="📦 Export Summary", border_style="gold3")
    summary.add_column("Metric", style="cyan")
    summary.add_column("Value", style="green", justify="right")

    total_snaps = sum(len(e.get("snap_map", {})) for e in entries)
    total_links = sum(len(e.get("link_map", {})) for e in entries)

    summary.add_row("Pipelines", str(len(entries)))
    summary.add_row("Snaps", str(total_snaps))
    summary.add_row("Links", str(total_links))
    summary.add_row("Likely primary", str(len(primary)))
    summary.add_row("Dev/test/copy", str(len(devish)))

    console.print(summary)

    if primary:
        table = Table(title="✅ Likely primary pipelines", border_style="green")
        table.add_column("Name", style="white")
        table.add_column("Snaps", justify="right", style="green")
        table.add_column("Links", justify="right", style="green")
        table.add_column("Path", style="dim")

        for entry in primary:
            table.add_row(
                entry.get("name", ""),
                str(len(entry.get("snap_map", {}))),
                str(len(entry.get("link_map", {}))),
                entry.get("path", ""),
            )

        console.print(table)

    if devish:
        table = Table(title="🧪 Possible dev/test/copy artefacts", border_style="yellow")
        table.add_column("Name", style="white")
        table.add_column("Snaps", justify="right", style="yellow")
        table.add_column("Path", style="dim")

        for entry in devish:
            table.add_row(
                entry.get("name", ""),
                str(len(entry.get("snap_map", {}))),
                entry.get("path", ""),
            )

        console.print(table)

    snap_types = Counter()

    for entry in entries:
        for snap in entry.get("snap_map", {}).values():
            snap_types[snap.get("class_id", "unknown")] += 1

    table = Table(title="🧩 Snap types", border_style="gold3")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Snap class", style="white")

    for snap_class, count in snap_types.most_common():
        table.add_row(str(count), snap_class)

    console.print(table)
    console.print(f"\n{GREEN}✅ Inspection complete. No graph was modified.{RESET}\n")