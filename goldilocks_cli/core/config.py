# ============================================================
# 🫧 GOLDILOCKS — Config
# ============================================================
# Pure functions. No printing, no prompting, no side effects
# beyond writing when explicitly asked to.
#
# Resolution order (later wins):
#   defaults  <  ~/.config/goldilocks/config.toml  <  ./goldilocks.toml
# ============================================================

from pathlib import Path
from typing import Any, Dict, Optional

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # Python 3.10 — see _parse_flat_toml below
    tomllib = None  # type: ignore


LOCAL_CONFIG_NAME = "goldilocks.toml"
HOME_CONFIG_RELPATH = Path(".config") / "goldilocks" / "config.toml"

DEFAULTS: Dict[str, Dict[str, str]] = {
    "snaplogic": {
        # The project URL you would otherwise paste into `goldilocks fetch`.
        "url": "",
    },
    "paths": {
        "sensitive_orgs": "sensitive_orgs.txt",
        "exports_dir": "pipeline_exports",
    },
    "workflow": {
        "stale_after_days": "7",
    },
}


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

def home_config_path() -> Path:
    """~/.config/goldilocks/config.toml"""
    return Path.home() / HOME_CONFIG_RELPATH


def local_config_path(start_dir: Optional[Path] = None) -> Path:
    """./goldilocks.toml, relative to start_dir (default: cwd)."""
    base = Path(start_dir) if start_dir else Path.cwd()
    return base / LOCAL_CONFIG_NAME


def config_paths(start_dir: Optional[Path] = None) -> list:
    """Config files in ascending order of precedence."""
    return [home_config_path(), local_config_path(start_dir)]


# ------------------------------------------------------------
# Reading
# ------------------------------------------------------------

def _parse_flat_toml(text: str) -> Dict[str, Dict[str, str]]:
    """
    Minimal TOML reader for Python 3.10, where stdlib `tomllib` does not
    exist. Handles exactly the shape Goldilocks writes: [sections] of
    `key = "string"` pairs, plus # comments and blank lines. Anything
    fancier belongs in a real parser — on 3.11+ we use tomllib and this
    function is never called.
    """
    data: Dict[str, Dict[str, str]] = {}
    section: Optional[str] = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            data.setdefault(section, {})
            continue
        if "=" not in line or section is None:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        data[section][key.strip()] = value

    return data


def read_config_file(path: Path) -> Dict[str, Any]:
    """Parse one TOML file. Returns {} if it is missing or unreadable."""
    path = Path(path)
    if not path.is_file():
        return {}

    try:
        if tomllib is not None:
            with path.open("rb") as fh:
                return tomllib.load(fh)
        return _parse_flat_toml(path.read_text(encoding="utf-8"))
    except Exception:
        # A malformed config should not take the CLI down; callers fall
        # back to defaults and `init` can rewrite it.
        return {}


def _merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Section-aware merge: overlay wins, key by key."""
    out = {section: dict(values) for section, values in base.items()}
    for section, values in overlay.items():
        if not isinstance(values, dict):
            continue
        out.setdefault(section, {})
        for key, value in values.items():
            if value is not None:
                out[section][key] = value
    return out


def load_config(start_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Defaults, overlaid with the home config, overlaid with the local one.
    Always returns every default key, so callers never need .get() chains.
    """
    config = {section: dict(values) for section, values in DEFAULTS.items()}
    for path in config_paths(start_dir):
        config = _merge(config, read_config_file(path))
    return config


def active_config_path(start_dir: Optional[Path] = None) -> Optional[Path]:
    """The file that currently wins, or None if no config exists yet."""
    for path in reversed(config_paths(start_dir)):
        if Path(path).is_file():
            return path
    return None


# ------------------------------------------------------------
# Writing
# ------------------------------------------------------------

def _escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def dumps_toml(config: Dict[str, Any]) -> str:
    """
    Serialise our flat section/string config to TOML. The stdlib reads
    TOML but does not write it, and the schema here is small enough that
    a dependency would cost more than it saves.
    """
    lines = ["# 🫧 Goldilocks config — written by `goldilocks init`", ""]
    for section in DEFAULTS:
        lines.append(f"[{section}]")
        for key in DEFAULTS[section]:
            value = config.get(section, {}).get(key, DEFAULTS[section][key])
            lines.append(f'{key} = "{_escape(value)}"')
        lines.append("")
    return "\n".join(lines)


def save_config(config: Dict[str, Any], path: Path) -> Path:
    """Write config to path, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_toml(config), encoding="utf-8")
    return path


# ------------------------------------------------------------
# Sensitive orgs scaffold
# ------------------------------------------------------------

SENSITIVE_ORGS_TEMPLATE = """\
# 🫧 Goldilocks — sensitive organisation names
#
# One name per line. Anything listed here is scrubbed by
# `goldilocks sanitise` and `goldilocks sieve`.
# Lines starting with # are ignored.
#
# Keep this file out of version control.
"""


def scaffold_sensitive_orgs(path: Path) -> bool:
    """
    Create a commented template at path if nothing is there yet.
    Returns True if a file was written, False if one already existed.
    """
    path = Path(path)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SENSITIVE_ORGS_TEMPLATE, encoding="utf-8")
    return True