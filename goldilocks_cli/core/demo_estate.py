# ============================================================
# 🫧 GOLDILOCKS — Synthetic demo estate
# ============================================================
# A tiny, wholly fictional SnapLogic-style export for the
# `goldilocks demo` command. Every name, domain, address and
# value here is invented; domains use the reserved .example
# TLD so nothing can ever resolve to a real system.
#
# Pure functions only — no printing, no prompting. Writing
# happens solely through write_demo_export(path), called by
# the demo command with an explicit isolated workspace path.
# ============================================================

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEMO_ORG = "Marmalade Museum"
DEMO_BANNER_NOTE = "All names, systems and values are fictional and synthetic."

# Fake sensitive shapes, present ON PURPOSE so the sieve has
# honest work to show: the real sanitiser redacts the password,
# the real anonymiser replaces the URL, email and GUID, and the
# real leak scanner confirms the output is quiet.
_FAKE_URL = "https://api.marmalade-museum.example/opening-hours"
_FAKE_EMAIL = "keeper@marmalade-museum.example"
_FAKE_GUID = "0f9d2c4e-1a2b-4c3d-8e5f-a1b2c3d4e5f6"
_FAKE_PASSWORD = "pot-of-honey"


def _snap(
    label: str,
    class_id: str,
    *,
    settings: dict[str, Any] | None = None,
    error_behavior: str | None = None,
) -> dict[str, Any]:
    property_map: dict[str, Any] = {
        "info": {"label": {"value": label}},
        "settings": settings or {},
    }
    if error_behavior:
        property_map["error"] = {"error_behavior": {"value": error_behavior}}
    return {"class_id": class_id, "property_map": property_map}


def _links(pairs: list[tuple[str, str]]) -> dict[str, dict[str, str]]:
    return {
        f"link{i}": {"src_id": src, "dst_id": dst}
        for i, (src, dst) in enumerate(pairs)
    }


def orchestrator_pipeline() -> dict[str, Any]:
    """Trigger → mappers → filter → router (two routes) → union
    → HTTP Client → PipeExec call to the loader pipeline."""
    snap_map = {
        "s_trigger": _snap("Doors Open Trigger", "com-snaplogic-snaps-trigger"),
        "s_map1": _snap("Shape Visitor Counts", "com-snaplogic-snaps-transform-mapper"),
        "s_map2": _snap("Label Galleries", "com-snaplogic-snaps-transform-mapper"),
        "s_filter": _snap("Keep Open Galleries", "com-snaplogic-snaps-flow-filter"),
        "s_router": _snap("Route by Wing", "com-snaplogic-snaps-flow-router"),
        "s_east": _snap("East Wing Notes", "com-snaplogic-snaps-transform-mapper"),
        "s_west": _snap("West Wing Notes", "com-snaplogic-snaps-transform-mapper"),
        "s_union": _snap("Merge Wings", "com-snaplogic-snaps-flow-union"),
        "s_http": _snap(
            "Publish Opening Hours",
            "com-snaplogic-snaps-rest-httpclient",
            settings={
                "serviceUrl": _FAKE_URL,
                "contact": _FAKE_EMAIL,
                "password": _FAKE_PASSWORD,
            },
            error_behavior="Route Error Data to Error View",
        ),
        "s_pipeexec": _snap(
            "Call Ticket Ledger",
            "com-snaplogic-snaps-flow-pipeexec",
            settings={
                "pipeline": {
                    "value": f"/{DEMO_ORG}/projects/Loader — Ticket Ledger"
                }
            },
        ),
    }
    link_map = _links(
        [
            ("s_trigger", "s_map1"),
            ("s_map1", "s_map2"),
            ("s_map2", "s_filter"),
            ("s_filter", "s_router"),
            ("s_router", "s_east"),
            ("s_router", "s_west"),
            ("s_east", "s_union"),
            ("s_west", "s_union"),
            ("s_union", "s_http"),
            ("s_http", "s_pipeexec"),
        ]
    )
    return {
        "name": "Orchestrator — Opening Hours",
        "path": f"/{DEMO_ORG}/projects/Orchestrator — Opening Hours",
        "instance_id": _FAKE_GUID,
        "snap_map": snap_map,
        "link_map": link_map,
    }


def loader_pipeline() -> dict[str, Any]:
    """Mapper → script → writer → PipeExec to the archivist.

    Called by TWO parents (orchestrator and curator). It also calls
    the archivist — SnapLogic's ONLY coupling idiom is the call, so
    where the Airflow twin publishes a Dataset the grandchild
    subscribes to, this side must express the same family tie as a
    PipeExec. That asymmetry is deliberate: it is the loss table in
    fixture form."""
    snap_map = {
        "s_shape": _snap("Shape Ledger Rows", "com-snaplogic-snaps-transform-mapper"),
        "s_script": _snap("Stamp the Ledger", "com-snaplogic-snaps-script-script"),
        "s_write": _snap("Write Ledger File", "com-snaplogic-snaps-binary-filewriter"),
        "s_call_audit": _snap(
            "Call Nightly Audit",
            "com-snaplogic-snaps-flow-pipeexec",
            settings={
                "pipeline": {
                    "value": f"/{DEMO_ORG}/projects/Archivist — Nightly Audit"
                }
            },
        ),
    }
    link_map = _links(
        [
            ("s_shape", "s_script"),
            ("s_script", "s_write"),
            ("s_write", "s_call_audit"),
        ]
    )
    return {
        "name": "Loader — Ticket Ledger",
        "path": f"/{DEMO_ORG}/projects/Loader — Ticket Ledger",
        "snap_map": snap_map,
        "link_map": link_map,
    }


def curator_pipeline() -> dict[str, Any]:
    """SIBLING of the orchestrator — its own trigger, then calls the
    shared loader (second parent → the family diamond).

    The Airflow twin also WAITS on the orchestrator via an
    ExternalTaskSensor; SnapLogic has no inverse-coupling idiom, so
    that relation simply cannot be mirrored here. Documented loss."""
    snap_map = {
        "s_clock": _snap("Gift Shop Clock", "com-snaplogic-snaps-trigger"),
        "s_tally": _snap("Tally Gift Shop", "com-snaplogic-snaps-transform-mapper"),
        "s_reconcile": _snap(
            "Reconcile Tickets", "com-snaplogic-snaps-transform-mapper"
        ),
        "s_call_ledger": _snap(
            "Call Ticket Ledger",
            "com-snaplogic-snaps-flow-pipeexec",
            settings={
                "pipeline": {
                    "value": f"/{DEMO_ORG}/projects/Loader — Ticket Ledger"
                }
            },
        ),
    }
    link_map = _links(
        [
            ("s_clock", "s_tally"),
            ("s_tally", "s_reconcile"),
            ("s_reconcile", "s_call_ledger"),
        ]
    )
    return {
        "name": "Curator — Gift Shop Sync",
        "path": f"/{DEMO_ORG}/projects/Curator — Gift Shop Sync",
        "snap_map": snap_map,
        "link_map": link_map,
    }


def archivist_pipeline() -> dict[str, Any]:
    """GRANDCHILD — called by the loader. The Airflow twin is
    dataset-driven (nobody calls it); SnapLogic's nearest faithful
    shape is a called child. translated_with_assumptions, in reverse."""
    snap_map = {
        "s_audit": _snap("Audit Ledger", "com-snaplogic-snaps-transform-mapper"),
        "s_shelve": _snap("Shelve in Archive", "com-snaplogic-snaps-transform-mapper"),
    }
    link_map = _links([("s_audit", "s_shelve")])
    return {
        "name": "Archivist — Nightly Audit",
        "path": f"/{DEMO_ORG}/projects/Archivist — Nightly Audit",
        "snap_map": snap_map,
        "link_map": link_map,
    }


def build_demo_export() -> dict[str, Any]:
    """The complete fictional estate as a SnapLogic-style project export.

    Mirrors the synthetic Airflow estate as far as SnapLogic semantics
    allow: parent, sibling, shared child with two parents, grandchild.
    Where the platforms genuinely differ (sensors, datasets), the
    difference is preserved and documented rather than papered over."""
    return {
        "entries": [
            orchestrator_pipeline(),
            curator_pipeline(),
            loader_pipeline(),
            archivist_pipeline(),
        ]
    }


def write_demo_export(path: Path | str) -> Path:
    """Write the synthetic export to an explicit path and return it."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(build_demo_export(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return destination
