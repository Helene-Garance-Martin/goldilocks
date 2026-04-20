# ============================================================
# 🐻 GOLDILOCKS — Pipeline Describer
# ============================================================
# Generates plain English summaries of pipeline exports.
# No AI needed — reads snap types and describes what they do.
#
# Run:
#   python src/describer.py --input export_anonymised.json
# ============================================================

import json
import argparse
from pathlib import Path


# ------------------------------------------------------------
# SNAP DESCRIPTIONS — plain English per class_id pattern
# ------------------------------------------------------------

def get_step_description(class_id: str) -> str | None:
    c = class_id.lower()
    if "directorybrowser" in c:
        return "fetches files from SFTP"
    elif "sftp" in c and "simpleread" in c:
        return "fetches files from SFTP"
    elif "binary-simpleread" in c:
        return "reads binary file content"   # ← more accurate!
    elif "httpclient" in c:
        return "sends data via HTTP"
    elif "binarytodocument" in c or "mapper" in c:
        return "transforms data"
    elif "script-script" in c or "script" in c:
        return "runs custom logic"
    elif "pipeexec" in c:
        return "calls a child pipeline"
    return None

# ------------------------------------------------------------
# SINGLE PIPELINE DESCRIBER
# ------------------------------------------------------------

def describe_pipeline(pipeline: dict) -> str:
    """Return a plain English description of one pipeline."""
    name     = pipeline.get("name", "Unknown pipeline")
    snap_map = pipeline.get("snap_map", {})

    steps  = []
    calls  = []
    errors = []

    for snap in snap_map.values():
        class_id = snap.get("class_id", "").lower()

        # Error handling behaviour
        try:
            error = snap["property_map"]["error"]["error_behavior"]["value"]
            errors.append(error)
        except Exception:
            pass

        # Step description
        description = get_step_description(class_id)
        if description:
            steps.append(description)

        # Child pipeline calls
        if "pipeexec" in class_id:
            try:
                child = snap["property_map"]["settings"]["pipeline"]["value"]
                if child:
                    calls.append(child)
            except Exception:
                pass

    # Deduplicate
    steps = list(dict.fromkeys(steps))
    calls = list(dict.fromkeys(calls))

    # Complexity
    snap_count = len(snap_map)
    complexity = (
        "High"   if snap_count > 10 else
        "Medium" if snap_count > 5  else
        "Low"
    )

    # Error handling summary
    if errors:
        all_fail = all(e == "fail" for e in errors)
        error_summary = "All snaps stop on error ⛔" if all_fail else "Mixed error handling ⚠️"
    else:
        error_summary = "Unknown"

    # Build output
    lines = [
        f"🐻 Pipeline: {name}",
        "━" * 40,
        "",
    ]

    if steps:
        lines.append("What it does:")
        for step in steps:
            lines.append(f"  - {step}")

    lines += [
        "",
        f"Complexity:      {complexity} ({snap_count} snaps)",
        f"Error handling:  {error_summary}",
    ]

    if calls:
        lines.append("")
        lines.append("Relationships:")
        for child in calls:
            lines.append(f"  - Calls: {child}")

    return "\n".join(lines)


# ------------------------------------------------------------
# ALL PIPELINES DESCRIBER
# ------------------------------------------------------------

def describe_all_pipelines(data: dict) -> str:
    """Return plain English summaries for all pipelines in the export."""
    pipelines = data.get("entries", [data])
    divider   = "\n" + "═" * 40 + "\n"
    summaries = [describe_pipeline(p) for p in pipelines]
    return divider.join(summaries)


# ------------------------------------------------------------
# CLI ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="🐻 Goldilocks Describer — plain English pipeline summaries"
    )
    parser.add_argument("--input", default="export_anonymised.json", help="Path to anonymised pipeline JSON")
    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        print(f"❌ File not found: {args.input}")
        exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(describe_all_pipelines(data))