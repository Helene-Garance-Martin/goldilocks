# src/renderer.py
# ------------------------------------------------------------
# GOLDILOCKS — Diagram Renderer
# Renders .mmd files to PNG or SVG via Mermaid CLI (mmdc)
# ------------------------------------------------------------

import subprocess
import shutil
from pathlib import Path


def render_diagram(mmd_path: Path, fmt: str) -> None:
    """Render .mmd to png or svg via Mermaid CLI (mmdc)."""
    if fmt == "mmd":
        return
    if not shutil.which("mmdc"):
        print("⚠️  mmdc not found — install with: npm install -g @mermaid-js/mermaid-cli")
        return
    out_path = mmd_path.with_suffix(f".{fmt}")
    result = subprocess.run(
        ["mmdc", "-i", str(mmd_path), "-o", str(out_path),
         "--backgroundColor", "white",
         "--puppeteerConfigFile", "puppeteer-config.json"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"🖼️  Rendered: {out_path}")
    else:
        print(f"⚠️  PNG render unavailable in this environment (Codespaces/Linux missing Chrome libs)")
        print(f"   💡 Use .mmd preview in VS Code, or run locally for PNG output")