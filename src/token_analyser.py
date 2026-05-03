# src/token_analyser.py
# ------------------------------------------------------------
# GOLDILOCKS — Token Flow Analyser
# ------------------------------------------------------------
# Scans pipelines for access token references and flags
# potential "wipes_context" risks based on snap sequence.
#
# Based on the Goldilocks SnapLogic Grammar:
# $ = document field (flows through pipeline)
# _ = pipeline parameter (passed in)
# $entity = snap-level entity (wiped by certain snaps)
# ------------------------------------------------------------

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
from snap_resolver import resolve_snap_type
from security import redact_sensitive_value

# ------------------------------------------------------------
# TOKEN PATTERNS TO SCAN FOR
# ------------------------------------------------------------

TOKEN_PATTERNS = [
    "$entity.access_token",
    "$entity.token",
    "_spAccessToken",
    "$spAccessToken",
    "_accessToken",
    "$accessToken",
    "_bearerToken",
    "$bearerToken",
    "Bearer",
    "Authorization",
    "access_token",
    "api_key",
    "apikey",
    "password",
    "secret",
    "credential",
]

# ------------------------------------------------------------
# MEMORY WIPE SNAP TYPES
# ------------------------------------------------------------

WIPES_CONTEXT_TYPES = [
    "httpclient",
    "script",
    "sftp_get",
    "sftp_put",
    "binarytodocument",
    "filereader",
]


# ------------------------------------------------------------
# SNAP SCANNER
# ------------------------------------------------------------

def build_finding(snap_id: str, snap: dict) -> dict | None:
    """
    Scan a single snap for token references.
    Returns a finding dict or None if no tokens found.
    """
    try:
        label = snap["property_map"]["info"]["label"]["value"]
    except (KeyError, TypeError):
        label = snap_id

    class_id  = snap.get("class_id", "unknown")
    snap_type = resolve_snap_type(class_id)

    # Scan entire snap config as string
    snap_str = json.dumps(snap).lower()

    found_patterns = [
        p for p in TOKEN_PATTERNS
        if p.lower() in snap_str
    ]

    if not found_patterns:
        return None

    wipes = snap_type in WIPES_CONTEXT_TYPES

    return {
        "snap_id":        snap_id,
        "snap_label":     label,
        "snap_type":      snap_type,
        "token_patterns": found_patterns,
        "token_value": redact_sensitive_value(str(snap)),
        "wipes_context":  wipes,
        "risk":           "⚠️  Wipes context after this snap" if wipes else "✅ Safe",
        "recommendation": "Re-inject token via Mapper after this snap" if wipes else "Token flow looks safe here",
    }


# ------------------------------------------------------------
# PIPELINE TOKEN ANALYSER
# ------------------------------------------------------------

def find_token_references(pipeline: dict) -> list[dict]:
    """
    Scan a pipeline for all token/credential references.
    Flags memory wipe risks based on snap type.

    Returns a list of findings — one per snap with token references.
    """
    snap_map = pipeline.get("snap_map", {})

    return [
        finding
        for snap_id, snap in snap_map.items()
        if (finding := build_finding(snap_id, snap)) is not None
    ]


# ------------------------------------------------------------
# REPORT FORMATTER
# ------------------------------------------------------------

def format_token_report(pipeline_name: str, findings: list[dict]) -> str:
    """Format token analysis findings as a readable report."""
    if not findings:
        return f"✅ No token references found in {pipeline_name}"

    lines = [
        f"🔍 Token flow analysis: {pipeline_name}",
        "━" * 40,
        "",
    ]

    for f in findings:
        lines += [
            f"  {f['risk']}",
            f"  Snap:    {f['snap_label']} [{f['snap_type']}]",
            f"  Tokens:  {', '.join(f['token_patterns'])}",
            f"  Value:   {f['token_value']}",
            f"  💡 {f['recommendation']}",
            "",
        ]

    return "\n".join(lines)


# ------------------------------------------------------------
# MAIN — for direct testing
# ------------------------------------------------------------

if __name__ == "__main__":
    import json
    from pathlib import Path

    export = Path("export_anonymised.json")
    if not export.exists():
        print("❌ export_anonymised.json not found")
    else:
        data      = json.loads(export.read_text())
        pipelines = data.get("entries", [data])

        for pipeline in pipelines:
            findings = find_token_references(pipeline)
            report   = format_token_report(pipeline.get("name", "Unknown"), findings)
            print(report)
            print()