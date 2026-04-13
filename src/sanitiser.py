# ============================================================
# 🐻 GOLDILOCKS — Pipeline Sanitiser
# ============================================================
# Strips UI noise, rendering data and internal SnapLogic
# metadata from pipeline exports — keeping only what
# Goldilocks needs for parsing, graphing and visualising.
#
# Run:
#   python sanitiser.py --input export.json --output export_clean.json
# ============================================================

import json
import argparse
from pathlib import Path


# ------------------------------------------------------------
# WHAT WE KEEP — the essential fields per pipeline
# ------------------------------------------------------------

PIPELINE_KEYS_TO_KEEP = {
    "name",             # pipeline name
    "path",             # where it lives in SnapLogic
    "class_id",         # type of asset
    "instance_id",      # unique pipeline ID
    "create_time",      # when created
    "update_time",      # last modified
    "create_user_id",   # who created it
    "update_user_id",   # who last edited it
    "snap_map",         # THE NODES 🌟
    "link_map",         # THE EDGES 🌟
    "property_map",     # pipeline-level settings
}

# ------------------------------------------------------------
# WHAT WE KEEP — per snap inside snap_map
# ------------------------------------------------------------

SNAP_KEYS_TO_KEEP = {
    "class_id",         # snap type (httpclient, script etc.)
    "instance_id",      # unique snap ID
    "property_map",     # snap settings (label, config, error handling)
}

# ------------------------------------------------------------
# WHAT WE KEEP — per link inside link_map
# ------------------------------------------------------------

LINK_KEYS_TO_KEEP = {
    "src_id",           # source snap ID
    "dst_id",           # destination snap ID
    "src_view_id",      # output view name
    "dst_view_id",      # input view name
}

# ------------------------------------------------------------
# WHAT WE KEEP — inside property_map per snap
# ------------------------------------------------------------

PROPERTY_MAP_KEYS_TO_KEEP = {
    "info",             # contains the human-readable label
    "settings",         # snap configuration (URLs, queries etc.)
    "error",            # error handling behaviour
}


# ------------------------------------------------------------
# LAMBDA FUNCTIONS — small, focused transformations
# ------------------------------------------------------------

# Keep only allowed keys from a dictionary
filter_keys = lambda d, allowed: {k: v for k, v in d.items() if k in allowed}

# Check if a value is a non-empty dict
is_dict = lambda v: isinstance(v, dict) and len(v) > 0

# Check if a value is a non-empty list
is_list = lambda v: isinstance(v, list) and len(v) > 0


# ------------------------------------------------------------
# SANITISE FUNCTIONS
# ------------------------------------------------------------

def sanitise_snap(snap: dict) -> dict:
    """
    Strip noise from a single snap — keep only essential fields.
    Also cleans up property_map to remove rendering data.
    """
    # Keep only essential snap keys
    clean = filter_keys(snap, SNAP_KEYS_TO_KEEP)

    # Clean up property_map inside the snap
    if "property_map" in clean and is_dict(clean["property_map"]):
        clean["property_map"] = filter_keys(
            clean["property_map"],
            PROPERTY_MAP_KEYS_TO_KEEP
        )

    return clean


def sanitise_link(link: dict) -> dict:
    """
    Strip noise from a single link — keep only src/dst info.
    """
    return filter_keys(link, LINK_KEYS_TO_KEEP)


def sanitise_pipeline(pipeline: dict) -> dict:
    """
    Strip noise from a full pipeline entry.
    Cleans snap_map, link_map and top-level metadata.
    """
    # Keep only essential pipeline keys
    clean = filter_keys(pipeline, PIPELINE_KEYS_TO_KEEP)

    # Clean each snap inside snap_map
    if "snap_map" in clean and is_dict(clean["snap_map"]):
        clean["snap_map"] = {
            snap_id: sanitise_snap(snap)
            for snap_id, snap in clean["snap_map"].items()
        }

    # Clean each link inside link_map
    if "link_map" in clean and is_dict(clean["link_map"]):
        clean["link_map"] = {
            link_id: sanitise_link(link)
            for link_id, link in clean["link_map"].items()
        }

    return clean


def sanitise_export(input_path: str, output_path: str) -> None:
    """
    Main function — reads export.json, sanitises all pipelines,
    writes clean version to output_path.
    """
    input_file  = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        print(f"❌ File not found: {input_path}")
        return

    print(f"📂 Reading: {input_path}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both single pipeline and project export (with entries[])
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

    # Write clean output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=2)

    # Summary
    original_size = input_file.stat().st_size
    clean_size    = output_file.stat().st_size
    reduction     = round((1 - clean_size / original_size) * 100)

    print(f"✅ Clean file written to: {output_path}")
    print(f"\n📊 Summary:")
    print(f"   Original size:  {original_size:,} bytes")
    print(f"   Clean size:     {clean_size:,} bytes")
    print(f"   Reduced by:     {reduction}% 🌟")

    if "entries" in data:
        for i, entry in enumerate(clean_data["entries"]):
            snap_count = len(entry.get("snap_map", {}))
            link_count = len(entry.get("link_map", {}))
            print(f"\n   Pipeline {i+1}: {entry.get('name', 'unknown')}")
            print(f"     Snaps (nodes): {snap_count}")
            print(f"     Links (edges): {link_count}")


# ------------------------------------------------------------
# CLI ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="🐻 Goldilocks Sanitiser — strip UI noise from pipeline exports"
    )
    parser.add_argument("--input",  required=True, help="Path to raw export.json")
    parser.add_argument("--output", required=True, help="Path to write clean output")
    args = parser.parse_args()

    sanitise_export(args.input, args.output)
