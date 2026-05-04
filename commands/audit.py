# commands/audit.py
import json
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from commands.colours import CYAN, GREEN, RED, GOLD, BOLD, RESET

console = Console()

def audit(
    input: str = typer.Option("export_anonymised.json", help="Path to anonymised pipeline JSON"),
    output: str = typer.Option("goldilocks_audit", help="Output filename (without extension)"),
):
    """
    🔐 Security audit — scan all pipelines for token risks.

    Generates a Rich terminal table plus saves to JSON and Markdown.
    """
    typer.echo(f"{CYAN}🔐 Running Goldilocks Security Audit...{RESET}\n")

    try:
        data      = json.loads(Path(input).read_text())
        pipelines = data.get("entries", [data])

        # ── Collect all findings ───────────────────────────
        from token_analyser import find_token_references

        all_findings = [
            {
                "pipeline": pipeline.get("name", "Unknown"),
                **finding,
            }
            for pipeline in pipelines
            for finding in find_token_references(pipeline)
        ]

        # ── Rich table ─────────────────────────────────────
        table = Table(
            title="🔐 Goldilocks Security Audit",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Pipeline",    style="cyan",  no_wrap=True)
        table.add_column("Snap",        style="white")
        table.add_column("Type",        style="blue")
        table.add_column("Risk",        style="white")
        table.add_column("Tokens",      style="yellow")
        table.add_column("Value",       style="dim")

        for f in all_findings:
            table.add_row(
                f["pipeline"],
                f["snap_label"],
                f["snap_type"],
                f["risk"],
                ", ".join(f["token_patterns"][:2]),
                f["token_value"],
            )

        console.print(table)

        # ── Summary ────────────────────────────────────────
        risks  = [f for f in all_findings if f["wipes_context"]]
        safe   = [f for f in all_findings if not f["wipes_context"]]

        typer.echo(f"\n📊 {BOLD}Summary:{RESET}")
        typer.echo(f"   Pipelines scanned: {len(pipelines)}")
        typer.echo(f"   Total findings:    {len(all_findings)}")
        typer.echo(f"   ⚠️  Risks:          {len(risks)}")
        typer.echo(f"   ✅ Safe:            {len(safe)}")

        # ── Save JSON ──────────────────────────────────────
        json_path = Path(f"{output}.json")
        json_path.write_text(json.dumps(all_findings, indent=2))
        typer.echo(f"\n💾 {GREEN}Saved: {json_path}{RESET}")

        # ── Save Markdown ──────────────────────────────────
        md_lines = [
            "# 🔐 Goldilocks Security Audit\n",
            "| Pipeline | Snap | Type | Risk | Tokens |",
            "|----------|------|------|------|--------|",
        ]
        md_lines += [
            f"| {f['pipeline']} | {f['snap_label']} | {f['snap_type']} | {f['risk']} | {', '.join(f['token_patterns'][:2])} |"
            for f in all_findings
        ]
        md_lines += [
            f"\n## Summary",
            f"- Pipelines scanned: {len(pipelines)}",
            f"- Total findings: {len(all_findings)}",
            f"- Risks: {len(risks)}",
            f"- Safe: {len(safe)}",
        ]

        md_path = Path(f"{output}.md")
        md_path.write_text("\n".join(md_lines))
        typer.echo(f"💾 {GREEN}Saved: {md_path}{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Audit failed: {e}{RESET}\n")
        raise typer.Exit(1)