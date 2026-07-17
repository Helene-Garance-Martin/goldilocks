# src/renderer.py
# ------------------------------------------------------------
# GOLDILOCKS — Diagram Renderer
# Renders .mmd files to PNG or SVG via Mermaid CLI (mmdc)
# ------------------------------------------------------------

import json
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from goldilocks_cli.core.visualisation_scale import (
    MERMAID_MAX_EDGES,
    MERMAID_MAX_TEXT_SIZE,
)


MermaidVersion = tuple[int, int, int] | None
_VERSION_RE = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)")


def find_mmdc() -> str | None:
    """Return the Mermaid CLI executable available in this environment."""
    return shutil.which("mmdc.cmd") or shutil.which("mmdc")


@lru_cache(maxsize=1)
def detect_mmdc_version() -> MermaidVersion:
    """Read the installed Mermaid CLI version without raising."""
    mmdc = find_mmdc()
    if not mmdc:
        return None
    try:
        result = subprocess.run(
            [mmdc, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    match = _VERSION_RE.search(result.stdout or result.stderr or "")
    if not match:
        return None
    return tuple(int(match.group(part)) for part in ("major", "minor", "patch"))


def build_mmdc_config(version: MermaidVersion) -> dict[str, int]:
    """Return only rendering-limit keys supported by the detected version."""
    if version is None or version < (10, 0, 0):
        return {}

    config = {"maxTextSize": MERMAID_MAX_TEXT_SIZE}
    if version >= (10, 7, 0):
        config["maxEdges"] = MERMAID_MAX_EDGES
    return config


def _mmdc_command(
    mmdc: str,
    mmd_path: Path,
    out_path: Path,
    config_path: Path | None,
) -> list[str]:
    command = [
        mmdc,
        "-i",
        str(mmd_path),
        "-o",
        str(out_path),
        "--backgroundColor",
        "white",
        "--puppeteerConfigFile",
        "puppeteer-config.json",
    ]
    if config_path is not None:
        command.extend(["--configFile", str(config_path)])
    return command


def render_diagram(mmd_path: Path, fmt: str) -> Path:
    """Render .mmd to PNG or SVG via Mermaid CLI (mmdc)."""
    if fmt == "mmd":
        return mmd_path

    mmdc = find_mmdc()
    if not mmdc:
        print("⚠️  mmdc not found — falling back to .mmd")
        print("   💡 Use .mmd preview in VS Code, or run locally for rendered output.")
        return mmd_path

    out_path = mmd_path.with_suffix(f".{fmt}")
    config = build_mmdc_config(detect_mmdc_version())

    try:
        with tempfile.TemporaryDirectory(prefix="goldilocks-mermaid-") as temp_dir:
            config_path: Path | None = None
            if config:
                config_path = Path(temp_dir) / "mermaid-config.json"
                config_path.write_text(json.dumps(config), encoding="utf-8")

            result = subprocess.run(
                _mmdc_command(mmdc, mmd_path, out_path, config_path),
                capture_output=True,
                text=True,
                check=False,
            )
    except OSError:
        print("⚠️  PNG/SVG render unavailable in this environment.")
        print("   💡 Use .mmd preview in VS Code, or run locally for rendered output.")
        return mmd_path

    if result.returncode == 0:
        print(f"🖼️  Rendered: {out_path}")
        return out_path

    print("⚠️  PNG/SVG render unavailable in this environment.")
    print("   💡 Use .mmd preview in VS Code, or run locally for rendered output.")
    return mmd_path
