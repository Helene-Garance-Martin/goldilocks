# ============================================================
# 🫧 tests/test_state.py — workflow state markers
# ============================================================

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

from goldilocks_cli.core.state import (
    FILE_STATE_KEY,
    FILE_STATE_NAMESPACE,
    GRAPH_STATE_NAMESPACE,
    atomic_write_json,
    build_file_state,
    embed_file_state,
    find_fetched_exports,
    find_sieved_exports,
    is_stale,
    read_file_state,
    read_graph_state,
    stale_after_days,
    text_without_file_state,
    write_graph_state,
)


def test_header_round_trip(tmp_path):
    path = tmp_path / "anon.json"
    moment = datetime(2026, 7, 17, 9, 30, tzinfo=timezone.utc)
    data = embed_file_state(
        {"entries": [{"name": "ORG_1"}]},
        "/private/raw/export.json",
        sieved_at=moment,
        version="1.2.3",
    )

    atomic_write_json(path, data)
    state = read_file_state(path)

    assert state == {
        "namespace": FILE_STATE_NAMESPACE,
        "schema_version": 1,
        "stage": "sieved",
        "sieved_at": "2026-07-17T09:30:00Z",
        "tool_version": "1.2.3",
        "source_file": "export.json",
    }
    assert json.loads(path.read_text())["entries"][0]["name"] == "ORG_1"


def test_missing_header_returns_none(tmp_path):
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps({"entries": []}), encoding="utf-8")
    assert read_file_state(path) is None


def test_metadata_compatibility_keeps_unknown_fields(tmp_path):
    path = tmp_path / "future.json"
    path.write_text(
        json.dumps({
            "entries": [],
            FILE_STATE_KEY: {
                "stage": "sieved",
                "schema_version": 99,
                "future_ontology_hint": {"shape": "curl"},
            },
        }),
        encoding="utf-8",
    )

    state = read_file_state(path)
    assert state["schema_version"] == 99
    assert state["future_ontology_hint"] == {"shape": "curl"}


def test_leak_scan_input_ignores_metadata_block():
    text = json.dumps({
        "entries": [{"name": "ORG_1"}],
        FILE_STATE_KEY: {
            "stage": "sieved",
            "future_url": "https://metadata.example.org/private",
        },
    })
    stripped = text_without_file_state(text)
    assert "metadata.example.org" not in stripped
    assert "ORG_1" in stripped


def test_candidate_discovery_is_newest_first_and_supports_legacy(tmp_path):
    exports = tmp_path / "pipeline_exports"
    older = exports / "alpha" / "export.json"
    newer = exports / "beta" / "export.json"
    older.parent.mkdir(parents=True)
    newer.parent.mkdir(parents=True)
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")
    old_time = datetime.now(timezone.utc) - timedelta(days=2)
    new_time = datetime.now(timezone.utc) - timedelta(days=1)
    older.touch()
    newer.touch()
    import os
    os.utime(older, (old_time.timestamp(), old_time.timestamp()))
    os.utime(newer, (new_time.timestamp(), new_time.timestamp()))

    legacy = tmp_path / "export_anonymised.json"
    legacy.write_text("{}", encoding="utf-8")

    fetched = find_fetched_exports(exports, cwd=tmp_path)
    sieved = find_sieved_exports(exports, cwd=tmp_path)

    assert [item.path.name for item in fetched] == ["export.json", "export.json"]
    assert fetched[0].path.parent.name == "beta"
    assert [item.path.name for item in sieved] == ["export_anonymised.json"]


def test_staleness_threshold_is_configurable():
    now = datetime(2026, 7, 17, tzinfo=timezone.utc)
    old = now - timedelta(days=8)
    assert stale_after_days({"workflow": {"stale_after_days": "9"}}) == 9
    assert stale_after_days({"workflow": {"stale_after_days": "not-a-number"}}) == 7
    assert is_stale(old, 7, now=now)
    assert not is_stale(old, 9, now=now)


def test_build_file_state_uses_filename_only():
    state = build_file_state("/Users/helene/private/export.json", version="0.2.0")
    assert state["source_file"] == "export.json"
    assert "/Users" not in json.dumps(state)


def test_read_graph_state_uses_one_inexpensive_query():
    session = MagicMock()
    session.run.return_value.single.return_value = {
        "namespace": GRAPH_STATE_NAMESPACE,
        "schema_version": 1,
        "last_seeded": "2026-07-17T10:00:00Z",
        "recorded_pipeline_count": 3,
        "source_file": "anon.json",
        "source_sieved_at": "2026-07-17T09:00:00Z",
        "tool_version": "0.2.0",
        "pipeline_count": 3,
    }

    state = read_graph_state(session)

    assert state["pipeline_count"] == 3
    assert session.run.call_count == 1
    assert session.run.call_args.kwargs["namespace"] == GRAPH_STATE_NAMESPACE


def test_write_graph_state_is_namespaced_and_filename_only():
    tx = MagicMock()
    tx.run.return_value.single.return_value = {
        "namespace": GRAPH_STATE_NAMESPACE,
        "pipeline_count": 2,
        "source_file": "anon.json",
    }

    result = write_graph_state(
        tx,
        source_file="/private/work/anon.json",
        pipeline_count=2,
        last_seeded=datetime(2026, 7, 17, 11, tzinfo=timezone.utc),
        source_sieved_at="2026-07-17T10:00:00Z",
        version="0.2.0",
    )

    kwargs = tx.run.call_args.kwargs
    assert kwargs["namespace"] == GRAPH_STATE_NAMESPACE
    assert kwargs["schema_version"] == 1
    assert kwargs["source_file"] == "anon.json"
    assert result["pipeline_count"] == 2
