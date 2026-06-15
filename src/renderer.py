# src/renderer.py
# ------------------------------------------------------------
# GOLDILOCKS — Diagram Renderer
# Renders .mmd files to PNG or SVG via Mermaid CLI (mmdc)
# ------------------------------------------------------------

import shutil
import subprocess
from pathlib import Path


def render_diagram(mmd_path: Path, fmt: str) -> Path:
    """Render .mmd to PNG or SVG via Mermaid CLI (mmdc)."""
    if fmt == "mmd":
        return mmd_path

    if not shutil.which("mmdc"):
        print("⚠️  mmdc not found — falling back to .mmd")
        print("   💡 Use .mmd preview in VS Code, or run locally for rendered output.")
        return mmd_path

    out_path = mmd_path.with_suffix(f".{fmt}")

    result = subprocess.run(
        [
            "mmdc",
            "-i",
            str(mmd_path),
            "-o",
            str(out_path),
            "--backgroundColor",
            "white",
            "--puppeteerConfigFile",
            "puppeteer-config.json",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"🖼️  Rendered: {out_path}")
        return out_path

    print("⚠️  PNG/SVG render unavailable in this environment.")
    print("   💡 Use .mmd preview in VS Code, or run locally for rendered output.")
    return mmd_path