# ============================================================
# 🐻 GOLDILOCKS — Pipeline Visualiser
# ============================================================
# Generates Mermaid diagrams from anonymised pipeline JSON.
# ============================================================
import time
import json
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models import Snap, Pipeline, Link
from snap_resolver import resolve_snap_type
from renderer import render_diagram
from diagram_builder import build_pipeline_diagram, safe_file_name

# ------------------------------------------------------------
# MEMORY WIPE SNAP TYPES
# ------------------------------------------------------------

WIPES_CONTEXT_TYPES = [
    "httpclient",
    "script",
    "sftp_get",
    "sftp_put",
    "binarytodocument",
]

# ------------------------------------------------------------
# SNAP MODEL BUILDER
# ------------------------------------------------------------

def build_snap_model(snap_id: str, snap: dict) -> Snap:
    """Parse a raw snap dict into a typed Pydantic Snap model."""
    try:
        label = snap["property_map"]["info"]["label"]["value"]
    except (KeyError, TypeError):
        label = snap_id

    class_id  = snap.get("class_id", "unknown")
    snap_type = resolve_snap_type(class_id)

    return Snap(
        id            = snap_id,
        label         = label,
        snap_type     = snap_type,
        class_id      = class_id,
        wipes_context = snap_type in WIPES_CONTEXT_TYPES
    )


# ------------------------------------------------------------
# PARSE RAW JSON INTO PYDANTIC MODELS
# ------------------------------------------------------------

def parse_pipeline(raw: dict) -> Pipeline:
    """Parse raw pipeline JSON into typed Pydantic models."""
    snap_map = raw.get("snap_map", {})
    link_map = raw.get("link_map", {})

    snaps = [
        build_snap_model(snap_id, snap)
        for snap_id, snap in snap_map.items()
    ]

    links = [
        Link(src_id=l["src_id"], dst_id=l["dst_id"])
        for l in link_map.values()
    ]

    return Pipeline(
        name  = raw.get("name", "Unknown"),
        snaps = snaps,
        links = links,
    )


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def generate_diagrams(
    input_path: str,
    output_dir: str,
    direction:  str = "LR",
    fmt:        str = "mmd",
    single:     str = None
) -> None:

    input_file  = Path(input_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        print(f"❌ File not found: {input_path}")
        raise FileNotFoundError(f"{input_path}")

    print(f"📂 Loading: {input_path}")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return

    pipelines       = data.get("entries", [data])
    pipelines_typed = [parse_pipeline(p) for p in pipelines]

    if single:
        pipelines = [p for p in pipelines if single.lower() in p.get("name", "").lower()]
        if not pipelines:
            print(f"❌ No pipeline found matching: {single}")
            return
        print(f"🔍 Filtering to: {single}")

    count = len(pipelines)
    print(f"📦 Found {count} pipeline{'s' if count != 1 else ''}\n")

    if count > 5:
        print(f"⚠️  {count} pipelines — combined diagram may be large. Use --single to isolate.")

    # ── Combined diagram ───────────────────────────────────
    if not single:
        combined      = build_pipeline_diagram(pipelines, direction)
        combined_path = output_path / "goldilocks_combined.mmd"
        combined_path.write_text(combined, encoding='utf-8')
        print(f"✅ Combined diagram: {combined_path}")
        render_diagram(combined_path, fmt)

    # ── Individual diagrams ────────────────────────────────
    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

    with Progress(
        TextColumn("  🎨 [cyan]{task.description}[/cyan]"),
        BarColumn(bar_width=40, style="magenta", complete_style="magenta"),
        TextColumn("[cyan]{task.percentage:>3.0f}%[/cyan]"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Generating diagrams", total=count)
        for pipeline in pipelines:
            name    = safe_file_name(pipeline.get("name", "pipeline"))
            diagram = build_pipeline_diagram([pipeline], direction)
            path    = output_path / f"{name}.mmd"
            path.write_text(diagram, encoding='utf-8')
            render_diagram(path, fmt)
            progress.advance(task)
            time.sleep(0.3)

    print(f"\n🐻 Done — {count + 1} diagrams written to {output_dir}")
    print(f"💡 Tip: open diagrams/goldilocks_combined.mmd for the full system view 🎼")