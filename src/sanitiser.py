# ============================================================
# 🫧 GOLDILOCKS — Pipeline Sanitiser
# ============================================================
# Strips UI noise, rendering data and internal SnapLogic
# metadata from pipeline exports — keeping only what
# Goldilocks needs for parsing, graphing and visualising.
# ============================================================

import json
from pathlib import Path


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

def sanitise_settings(settings: dict) -> dict:
    """Keep settings structure but redact sensitive values."""
    if not isinstance(settings, dict):
        return settings
    return {
        k: "***REDACTED***" if any(
            sensitive in k.lower()
            for sensitive in SETTINGS_KEYS_TO_STRIP
        ) else v
        for k, v in settings.items()
    }


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

    if "snap_map" in clean and is_dict(clean["snap_map"]):
        clean["snap_map"] = {
            snap_id: sanitise_snap(snap)
            for snap_id, snap in clean["snap_map"].items()
        }

    if "link_map" in clean and is_dict(clean["link_map"]):
        clean["link_map"] = {
            link_id: sanitise_link(link)
            for link_id, link in clean["link_map"].items()
        }

    return clean


def sanitise_export(input_path: str, output_path: str) -> None:
    """Main function — reads, sanitises and writes clean pipeline export."""
    input_file  = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        print(f"❌ File not found: {input_path}")
        return

    print(f"📂 Reading: {input_path}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if "entries" in data:
        print(f"📦 Project export — found {len(data['entries'])} pipeline(s)")
        clean_entries = [sanitise_pipeline(entry) for entry in data["entries"]]
        clean_data = {
            "project_name": data.get("project_name", ""),
            "path":         data.get("path", ""),
            "entries":      clean_entries
        }
    else:
        print("📄 Single pipeline export")
        clean_data = sanitise_pipeline(data)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=2)

    original_size = input_file.stat().st_size
    clean_size    = output_file.stat().st_size

    print(f"✅ Clean file written to: {output_path}")
    print(f"\n📊 Summary:")
    print(f"   Original size:  {original_size:,} bytes")
    print(f"   Clean size:     {clean_size:,} bytes")

    if clean_size > original_size:
        difference = round((clean_size / original_size - 1) * 100)
        print(f"   Size change:    +{difference}% (settings preserved for graph intelligence)")
    else:
        reduction = round((1 - clean_size / original_size) * 100)
        print(f"   Reduced by:     {reduction}% 🌟")

    if "entries" in data:
        for i, entry in enumerate(clean_data["entries"]):
            snap_count = len(entry.get("snap_map", {}))
            link_count = len(entry.get("link_map", {}))
            print(f"\n   Pipeline {i+1}: {entry.get('name', 'unknown')}")
            print(f"     Snaps (nodes): {snap_count}")
            print(f"     Links (edges): {link_count}")


