# ============================================================
# 🫧 GOLDILOCKS — Pipeline Sanitiser
# ============================================================
# Strips UI noise, rendering data and internal SnapLogic
# metadata from pipeline exports — keeping only what
# Goldilocks needs for parsing, graphing and visualising.
# ============================================================
import json
from pathlib import Path

from goldilocks_cli.core.state import atomic_write_json


# ------------------------------------------------------------
# WHAT WE KEEP — the essential fields per pipeline
# ------------------------------------------------------------

PIPELINE_KEYS_TO_KEEP = {
    "name",
    "path",
    "class_id",
    "instance_id",
    "create_time",
    "update_time",
    "snap_map",
    "link_map",
    "property_map",
}

# ------------------------------------------------------------
# WHAT WE KEEP — per snap inside snap_map
# ------------------------------------------------------------

SNAP_KEYS_TO_KEEP = {
    "class_id",
    "instance_id",
    "property_map",
}

# ------------------------------------------------------------
# WHAT WE KEEP — per link inside link_map
# ------------------------------------------------------------

LINK_KEYS_TO_KEEP = {
    "src_id",
    "dst_id",
    "src_view_id",
    "dst_view_id",
}

# ------------------------------------------------------------
# WHAT WE KEEP — inside property_map per snap
# ------------------------------------------------------------

PROPERTY_MAP_KEYS_TO_KEEP = {
    "info",
    "error",
    "settings",
}

# ------------------------------------------------------------
# SENSITIVE SETTINGS KEYS — redacted but structure preserved
# ------------------------------------------------------------

SETTINGS_KEYS_TO_STRIP = {
    "password", "token", "secret", "api_key",
    "apikey", "client_secret", "bearer",
    "pfxPassword", "private_key", "access_token",
    "refresh_token", "client_id", "tenant_id",
}

# ------------------------------------------------------------
# LAMBDA FUNCTIONS
# ------------------------------------------------------------

filter_keys = lambda d, allowed: {k: v for k, v in d.items() if k in allowed}
is_dict     = lambda v: isinstance(v, dict) and len(v) > 0
is_list     = lambda v: isinstance(v, list) and len(v) > 0


# ------------------------------------------------------------
# SANITISE FUNCTIONS
# ------------------------------------------------------------

def is_sensitive_key(key: str) -> bool:
    """Return True when a settings key looks like it holds a secret."""
    lowered = key.lower()
    return any(
        sensitive in lowered
        for sensitive in SETTINGS_KEYS_TO_STRIP
    )


def sanitise_settings(settings):
    """Keep settings structure but redact sensitive values, at any depth.

    Walks dicts and lists. A key matching is_sensitive_key has its whole
    value replaced by the redaction marker — whatever shape that value is
    (string, dict, list) — so a secret can't hide inside a wrapper such as
    settings.account_ref.value.client_secret. Non-sensitive values are
    recursed into; leaves are returned untouched.
    """
    if isinstance(settings, dict):
        return {
            k: "***REDACTED***" if is_sensitive_key(k) else sanitise_settings(v)
            for k, v in settings.items()
        }

    if isinstance(settings, list):
        return [sanitise_settings(item) for item in settings]

    return settings

def is_disabled_snap(snap: dict) -> bool:
    """Return True when a SnapLogic snap is disabled."""
    execution_mode = (
        snap.get("property_map", {})
        .get("settings", {})
        .get("execution_mode", {})
        .get("value")
    )

    return execution_mode == "Disabled"

def sanitise_snap(snap: dict) -> dict:
    """Strip noise from a single snap — keep only essential fields."""
    clean = filter_keys(snap, SNAP_KEYS_TO_KEEP)

    if "property_map" in clean and is_dict(clean["property_map"]):
        clean["property_map"] = filter_keys(
            clean["property_map"],
            PROPERTY_MAP_KEYS_TO_KEEP
        )
        if "settings" in clean["property_map"]:
            clean["property_map"]["settings"] = sanitise_settings(
                clean["property_map"]["settings"]
            )

    return clean


def sanitise_link(link: dict) -> dict:
    """Strip noise from a single link — keep only src/dst info."""
    return filter_keys(link, LINK_KEYS_TO_KEEP)


def sanitise_pipeline(pipeline: dict) -> dict:
    """Strip noise from a full pipeline entry."""
    clean = filter_keys(pipeline, PIPELINE_KEYS_TO_KEEP)

    active_snap_ids = set()

    if "snap_map" in clean and is_dict(clean["snap_map"]):
        active_snap_ids = {
            snap_id
            for snap_id, snap in clean["snap_map"].items()
            if not is_disabled_snap(snap)
        }

        clean["snap_map"] = {
            snap_id: sanitise_snap(snap)
            for snap_id, snap in clean["snap_map"].items()
            if snap_id in active_snap_ids
        }

    if "link_map" in clean and is_dict(clean["link_map"]):
        clean["link_map"] = {
            link_id: sanitise_link(link)
            for link_id, link in clean["link_map"].items()
            if (
                link.get("src_id") in active_snap_ids
                and link.get("dst_id") in active_snap_ids
            )
        }

    return clean


def sanitise_export(
    input_path: str,
    output_path: str,
    on_progress: callable = None,
) -> dict:
    """Main function — reads, sanitises and writes clean pipeline export.

    Does no printing and no pacing: presentation belongs to the
    command layer. Facts are emitted via on_progress and the
    returned summary.

    Args:
        input_path:  Path to the raw pipeline export JSON.
        output_path: Path to write the sanitised output.
        on_progress: Optional callback(phase, current, total, message).
                     Fired at key milestones so a caller (e.g. sieve)
                     can render a progress bar. Signature stable across
                     sanitiser + anonymiser so the same callback shape
                     works for both.

    Returns:
        A summary dict: output path, original/clean sizes, whether the
        input was a project export, and per-pipeline snap/link counts.

    Raises:
        FileNotFoundError: when the input file does not exist.
    """
    input_file  = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(f"input file not found: {input_path}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if "entries" in data:
        total = len(data['entries'])

        if on_progress:
            on_progress("sanitising", 0, total, "starting")

        clean_entries = []
        for i, entry in enumerate(data["entries"]):
            clean_entries.append(sanitise_pipeline(entry))
            if on_progress:
                on_progress(
                    "sanitising",
                    i + 1,
                    total,
                    entry.get("name", "unknown"),
                )

        clean_data = {
            "project_name": data.get("project_name", ""),
            "path":         data.get("path", ""),
            "entries":      clean_entries,
        }
    else:
        if on_progress:
            on_progress("sanitising", 0, 1, "single pipeline")
        clean_data = sanitise_pipeline(data)
        if on_progress:
            on_progress("sanitising", 1, 1, "done")

    atomic_write_json(output_file, clean_data)

    original_size = input_file.stat().st_size
    clean_size    = output_file.stat().st_size

    if "entries" in data:
        pipelines = [
            {
                "name":  entry.get("name", "unknown"),
                "snaps": len(entry.get("snap_map", {})),
                "links": len(entry.get("link_map", {})),
            }
            for entry in clean_data["entries"]
        ]
    else:
        pipelines = [
            {
                "name":  clean_data.get("name", "unknown"),
                "snaps": len(clean_data.get("snap_map", {})),
                "links": len(clean_data.get("link_map", {})),
            }
        ]

    return {
        "output":        str(output_path),
        "original_size": original_size,
        "clean_size":    clean_size,
        "project":       "entries" in data,
        "pipelines":     pipelines,
    }
