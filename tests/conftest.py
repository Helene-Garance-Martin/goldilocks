# tests/conftest.py
# ============================================================
# 🫧 GOLDILOCKS — shared test fixtures
# ============================================================
# NOTE ON PATHS: with the goldilocks_cli package layout, tests
# import via absolute package paths. The single repo-root insert
# below lets the suite run without installing; with
# `pip install -e .` it is redundant but harmless.
# ============================================================

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ------------------------------------------------------------
# Synthetic pipeline export fixture — NO real data.
# Exercises: multiple pipelines, a disabled snap, credential
# keys (top-level and nested), a sensitive URL (whole-value and
# embedded in free text), org names in mixed case, an accented
# org name, and a link touching a disabled snap (orphan link).
# ------------------------------------------------------------

TEST_ORG = "Acme"            # must exist in anonymiser.SENSITIVE_ORGS during tests
TEST_ORG_MIXED = "aCmE"      # same org, different casing
TEST_ORG_ACCENTED = "Zoé Fictional"  # accented entry — exercises the ensure_ascii bug


@pytest.fixture()
def synthetic_export() -> dict:
    """A minimal but adversarial project export (two pipelines)."""
    return {
        "project_name": "Acme Integration",
        "path": "/Acme/projects/demo",
        "entries": [
            {
                # Pipeline 1 — the adversarial one
                "name": "Acme Leavers Sync",
                "path": "/Acme/projects/demo/leavers",
                "class_id": "com-snaplogic-pipeline",
                "instance_id": "pipe-001",
                "create_time": {"$date": "2026-01-01T00:00:00Z"},
                "update_time": {"$date": "2026-06-01T00:00:00Z"},
                "render_map": {"ui_noise": True},  # must be stripped
                "snap_map": {
                    "snap-active": {
                        "class_id": "com-snaplogic-snaps-transform-mapper",
                        "instance_id": "snap-active",
                        "render_details": {"x": 10, "y": 20},  # must be stripped
                        "property_map": {
                            "info": {
                                "label": {"value": "Map leavers"},
                                "notes": {"value": "Ping zoe@acme-corp.example if it fails"},
                            },
                            "error": {
                                "error_behavior": {"value": "fail"},
                                "err_msg": {
                                    "value": "401 from https://acme.sharepoint.com/sites/HR?tid=tenant-guid-123"
                                },
                            },
                            "settings": {
                                "password": {"value": "hunter2"},
                                "api_key": "TOP-LEVEL-KEY-123",
                                "account_ref": {"value": {"client_secret": "NESTED-SECRET-999"}},
                                "endpoint": "https://acme.snaplogic.com/api/1/rest/feed/x",
                                "expression": {
                                    "value": "Posts to https://acme.snaplogic.com/api/1/rest/feed/x then done"
                                },
                                "note": {"value": f"Built for {TEST_ORG_MIXED} by {TEST_ORG_ACCENTED}"},
                            },
                        },
                    },
                    "snap-disabled": {
                        "class_id": "com-snaplogic-snaps-flow-filter",
                        "instance_id": "snap-disabled",
                        "property_map": {
                            "settings": {
                                "execution_mode": {"value": "Disabled"},
                                "password": {"value": "should-vanish-with-snap"},
                            }
                        },
                    },
                    "snap-second": {
                        "class_id": "com-snaplogic-snaps-flow-router",
                        "instance_id": "snap-second",
                        "property_map": {
                            "info": {"label": {"value": "Route records"}},
                            "settings": {},
                        },
                    },
                },
                "link_map": {
                    "link-live": {
                        "src_id": "snap-active",
                        "dst_id": "snap-second",
                        "src_view_id": "out0",
                        "dst_view_id": "in0",
                    },
                    "link-orphan": {
                        # touches the disabled snap → must be removed
                        "src_id": "snap-active",
                        "dst_id": "snap-disabled",
                        "src_view_id": "out1",
                        "dst_view_id": "in0",
                    },
                },
            },
            {
                # Pipeline 2 — small and clean, proves multi-entry handling
                "name": "acme Heartbeat",
                "instance_id": "pipe-002",
                "class_id": "com-snaplogic-pipeline",
                "snap_map": {
                    "snap-x": {
                        "class_id": "com-snaplogic-snaps-flow-trigger",
                        "instance_id": "snap-x",
                        "property_map": {"info": {"label": {"value": "Tick"}}, "settings": {}},
                    }
                },
                "link_map": {},
            },
        ],
    }


@pytest.fixture()
def export_file(tmp_path: Path, synthetic_export: dict) -> Path:
    """Synthetic export written to disk (ensure_ascii=True, like real exports)."""
    p = tmp_path / "export.json"
    p.write_text(json.dumps(synthetic_export, indent=2), encoding="utf-8")
    return p


@pytest.fixture()
def progress_recorder():
    """Callback that records every on_progress emission."""
    calls: list[tuple] = []

    def record(phase, current, total, message):
        calls.append((phase, current, total, message))

    record.calls = calls
    return record


# ------------------------------------------------------------
# Anonymiser isolation — the anonymiser builds fresh lookup
# tables per call (review finding G1, fixed), so there is no
# module state to reset. This fixture pins the org list to a
# known synthetic set so tests never depend on (or reveal) the
# gitignored sensitive_orgs.py contents.
# ------------------------------------------------------------

@pytest.fixture()
def clean_anonymiser(monkeypatch):
    from goldilocks_cli.core import anonymiser

    monkeypatch.setattr(
        anonymiser,
        "SENSITIVE_ORGS",
        [TEST_ORG, "acme-corp", TEST_ORG_ACCENTED],
    )
    yield anonymiser
