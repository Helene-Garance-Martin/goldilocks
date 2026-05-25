# commands/audit.py

import json
import typer

from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from commands.colours import CYAN, GREEN, RED, RESET

console = Console()


def audit(
    input: str = typer.Option(
        "export_anonymised.json",
        help="Path to anonymised pipeline JSON",
    ),
    output: str = typer.Option(
        "goldilocks_audit",
        help="Output filename (without extension)",
    ),
):
    """
    🔐 Security audit — scan all pipelines for token risks.

    Generates Rich terminal tables plus saves to JSON and Markdown.
    """

    typer.echo(f"{CYAN}🔐 Running Goldilocks Security Audit...{RESET}\n")

    try:
        data = json.loads(Path(input).read_text(encoding="utf-8"))
        pipelines = data.get("entries", [data])

        from token_analyser import find_token_references

        all_findings = [
            {
                "pipeline": pipeline.get("name", "Unknown"),
                **finding,
            }
            for pipeline in pipelines
            for finding in find_token_references(pipeline)
        ]

        grouped_findings = defaultdict(list)

        for finding in all_findings:
            grouped_findings[finding["pipeline"]].append(finding)

        for pipeline_name, findings in grouped_findings.items():
            pipeline_risks = [
                finding
                for finding in findings
                if finding["wipes_context"]
            ]

            pipeline_safe = [
                finding
                for finding in findings
                if not finding["wipes_context"]
            ]

            console.print(
                f"\n📦 [bold cyan]{pipeline_name}[/bold cyan]"
            )
            console.print(f"   Findings: {len(findings)}")
            console.print(f"   Risks:    {len(pipeline_risks)}")
            console.print(f"   Safe:     {len(pipeline_safe)}\n")

            table = Table(
                show_header=True,
                header_style="bold yellow",
            )

            table.add_column("Snap", style="white")
            table.add_column("Type", style="blue")
            table.add_column("Risk", style="bold red")
            table.add_column("Tokens", style="yellow")
            table.add_column("Value", style="dim")

            for finding in findings:
                risk_style = (
                    "bold red"
                    if finding["wipes_context"]
                    else "green"
                )

                table.add_row(
                    finding["snap_label"],
                    finding["snap_type"],
                    Text(
                        finding["risk"],
                        style=risk_style,
                    ),
                    ", ".join(finding["token_patterns"][:2]),
                    finding["token_value"],
                )

            console.print(table)
            console.print()

        risks = [
            finding
            for finding in all_findings
            if finding["wipes_context"]
        ]

        safe = [
            finding
            for finding in all_findings
            if not finding["wipes_context"]
        ]

        summary = Table(
            title="🔎 Audit Summary",
            show_header=True,
            header_style="bold yellow",
        )

        summary.add_column("Metric", style="cyan")
        summary.add_column(
            "Count",
            style="green",
            justify="right",
            width=6,
        )

        summary.add_row("Pipelines", str(len(pipelines)))
        summary.add_row("Findings", str(len(all_findings)))
        summary.add_row("Risks", str(len(risks)))
        summary.add_row("Safe findings", str(len(safe)))

        console.print(summary)
        console.print()
        console.print()

        json_path = Path(f"{output}.json")
        json_path.write_text(
            json.dumps(all_findings, indent=2),
            encoding="utf-8",
        )

        typer.echo(f"💾 {GREEN}Saved: {json_path}{RESET}")

        md_lines = ["# 🔐 Goldilocks Security Audit\n"]

        for pipeline_name, findings in grouped_findings.items():
            md_lines += [
                f"## {pipeline_name}",
                "",
                "| Snap | Type | Risk | Tokens |",
                "|------|------|------|--------|",
            ]

            md_lines += [
                (
                    f"| {finding['snap_label']} "
                    f"| {finding['snap_type']} "
                    f"| {finding['risk']} "
                    f"| {', '.join(finding['token_patterns'][:2])} |"
                )
                for finding in findings
            ]

            md_lines.append("")

        md_lines += [
            "## Summary",
            f"- Pipelines scanned: {len(pipelines)}",
            f"- Total findings: {len(all_findings)}",
            f"- Risks: {len(risks)}",
            f"- Safe: {len(safe)}",
        ]

        md_path = Path(f"{output}.md")
        md_path.write_text(
            "\n".join(md_lines),
            encoding="utf-8",
        )

        typer.echo(f"💾 {GREEN}Saved: {md_path}{RESET}\n")

    except Exception as e:
        typer.echo(f"{RED}❌ Audit failed: {e}{RESET}\n")
        raise typer.Exit(1)