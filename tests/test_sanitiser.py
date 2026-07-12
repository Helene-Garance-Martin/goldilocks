# tests/test_sanitiser.py
# ============================================================
# 🫧 GOLDILOCKS — sanitiser tests
# ============================================================
# Pure file-in/file-out unit tests. No network, no Neo4j.
# Tests marked "PINS CURRENT BEHAVIOUR" document behaviour the
# review flags as a bug — fix the code, then flip the assert.
# ============================================================

import json

import pytest

from goldilocks_cli.core.sanitiser import (
    sanitise_export,
    sanitise_settings,
    sanitise_pipeline,
    is_disabled_snap,
)


def run_sanitise(export_file, tmp_path, on_progress=None):
    out = tmp_path / "clean.json"
    sanitise_export(str(export_file), str(out), on_progress=on_progress)
    return out, json.loads(out.read_text(encoding="utf-8"))


# ------------------------------------------------------------
# Key filtering
# ------------------------------------------------------------

def test_pipeline_keeps_only_allowed_keys(export_file, tmp_path):
    _, clean = run_sanitise(export_file, tmp_path)
    entry = clean["entries"][0]
    assert "render_map" not in entry
    assert {"name", "instance_id", "snap_map", "link_map"} <= set(entry)


def test_snap_keeps_only_allowed_keys(export_file, tmp_path):
    _, clean = run_sanitise(export_file, tmp_path)
    snap = clean["entries"][0]["snap_map"]["snap-active"]
    assert "render_details" not in snap
    assert set(snap) <= {"class_id", "instance_id", "property_map"}


def test_link_keeps_only_src_dst_views(export_file, tmp_path):
    _, clean = run_sanitise(export_file, tmp_path)
    link = clean["entries"][0]["link_map"]["link-live"]
    assert set(link) <= {"src_id", "dst_id", "src_view_id", "dst_view_id"}


def test_project_wrapper_preserved(export_file, tmp_path):
    _, clean = run_sanitise(export_file, tmp_path)
    assert clean["project_name"] == "Acme Integration"
    assert len(clean["entries"]) == 2


# ------------------------------------------------------------
# Disabled snap + orphan link removal
# ------------------------------------------------------------

def test_disabled_snap_removed(export_file, tmp_path):
    _, clean = run_sanitise(export_file, tmp_path)
    snap_map = clean["entries"][0]["snap_map"]
    assert "snap-disabled" not in snap_map
    assert "snap-active" in snap_map
    assert "snap-second" in snap_map


def test_orphan_link_removed_with_disabled_snap(export_file, tmp_path):
    _, clean = run_sanitise(export_file, tmp_path)
    link_map = clean["entries"][0]["link_map"]
    assert "link-orphan" not in link_map
    assert "link-live" in link_map


def test_is_disabled_snap_detection():
    disabled = {"property_map": {"settings": {"execution_mode": {"value": "Disabled"}}}}
    enabled = {"property_map": {"settings": {"execution_mode": {"value": "Validate & Execute"}}}}
    bare = {}
    assert is_disabled_snap(disabled) is True
    assert is_disabled_snap(enabled) is False
    assert is_disabled_snap(bare) is False


# ------------------------------------------------------------
# Sensitive-settings redaction
# ------------------------------------------------------------

def test_top_level_sensitive_settings_redacted(export_file, tmp_path):
    _, clean = run_sanitise(export_file, tmp_path)
    settings = clean["entries"][0]["snap_map"]["snap-active"]["property_map"]["settings"]
    assert settings["password"] == "***REDACTED***"
    assert settings["api_key"] == "***REDACTED***"


def test_redaction_matches_key_substrings():
    settings = {"pfxPassword": "x", "MY_API_KEY": "y", "harmless": "z"}
    out = sanitise_settings(settings)
    assert out["pfxPassword"] == "***REDACTED***"
    assert out["MY_API_KEY"] == "***REDACTED***"
    assert out["harmless"] == "z"


def test_nested_secrets_NOT_redacted(export_file, tmp_path):
    # PINS CURRENT BEHAVIOUR — review finding A6 / E-adjacent:
    # sanitise_settings only inspects top-level keys, so a secret
    # nested one level down (settings.account_ref.value.client_secret)
    # survives into export_clean.json. The anonymiser later catches it,
    # but sanitise is a standalone command whose output can be treated
    # as "clean". Fix: recurse. Then flip this assertion.
    _, clean = run_sanitise(export_file, tmp_path)
    settings = clean["entries"][0]["snap_map"]["snap-active"]["property_map"]["settings"]
    assert settings["account_ref"]["value"]["client_secret"] == "NESTED-SECRET-999"


def test_info_and_error_blocks_pass_through_unredacted(export_file, tmp_path):
    # PINS CURRENT BEHAVIOUR — review finding A3:
    # info.notes and error.err_msg are kept verbatim (emails, URLs,
    # tenant IDs). Sanitiser intentionally keeps these blocks, but
    # nothing downstream scrubs free text inside them except known
    # org-name strings.
    _, clean = run_sanitise(export_file, tmp_path)
    pm = clean["entries"][0]["snap_map"]["snap-active"]["property_map"]
    assert "zoe@acme-corp.example" in pm["info"]["notes"]["value"]
    assert "tenant-guid-123" in pm["error"]["err_msg"]["value"]


# ------------------------------------------------------------
# Size summary logic
# ------------------------------------------------------------

def test_size_summary_reports_growth_when_clean_is_larger(export_file, tmp_path, capsys):
    # indent=2 output of an already-lean input grows → "+N%" branch
    run_sanitise(export_file, tmp_path)
    out = capsys.readouterr().out
    assert "Size change:" in out or "Reduced by:" in out
    assert "📊 Summary:" in out


def test_size_summary_reports_reduction_for_noisy_input(tmp_path, capsys, synthetic_export):
    # Fatten the raw export with UI noise so the clean file is smaller
    synthetic_export["entries"][0]["render_map"] = {"blob": "x" * 20000}
    raw = tmp_path / "noisy.json"
    raw.write_text(json.dumps(synthetic_export), encoding="utf-8")
    out = tmp_path / "clean.json"
    sanitise_export(str(raw), str(out))
    printed = capsys.readouterr().out
    assert "Reduced by:" in printed


def test_per_pipeline_counts_printed(export_file, tmp_path, capsys):
    run_sanitise(export_file, tmp_path)
    out = capsys.readouterr().out
    assert "Pipeline 1: Acme Leavers Sync" in out
    assert "Snaps (nodes): 2" in out   # disabled snap already removed
    assert "Links (edges): 1" in out   # orphan link already removed


# ------------------------------------------------------------
# Callback emission
# ------------------------------------------------------------

def test_callback_sequence_for_project_export(export_file, tmp_path, progress_recorder):
    run_sanitise(export_file, tmp_path, on_progress=progress_recorder)
    calls = progress_recorder.calls
    assert calls[0] == ("sanitising", 0, 2, "starting")
    assert calls[1] == ("sanitising", 1, 2, "Acme Leavers Sync")
    assert calls[2] == ("sanitising", 2, 2, "acme Heartbeat")
    assert len(calls) == 3


def test_callback_sequence_for_single_pipeline(tmp_path, synthetic_export, progress_recorder):
    single = synthetic_export["entries"][1]
    raw = tmp_path / "single.json"
    raw.write_text(json.dumps(single), encoding="utf-8")
    sanitise_export(str(raw), str(tmp_path / "clean.json"), on_progress=progress_recorder)
    assert progress_recorder.calls == [
        ("sanitising", 0, 1, "single pipeline"),
        ("sanitising", 1, 1, "done"),
    ]


def test_no_callback_means_no_crash(export_file, tmp_path):
    run_sanitise(export_file, tmp_path, on_progress=None)  # default path


# ------------------------------------------------------------
# Failure modes
# ------------------------------------------------------------

def test_missing_input_raises_and_writes_nothing(tmp_path):
    # REGRESSION GUARD (was E1): a missing input raises, so the CLI
    # wrappers report failure honestly instead of printing "✅ Done!".
    out = tmp_path / "clean.json"
    with pytest.raises(FileNotFoundError):
        sanitise_export(str(tmp_path / "nope.json"), str(out))
    assert not out.exists()


def test_malformed_json_raises(tmp_path):
    # PINS CURRENT BEHAVIOUR — review finding E2:
    # malformed JSON escapes as a raw json.JSONDecodeError. The CLI
    # catches it generically; a warmer message would be kinder.
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        sanitise_export(str(bad), str(tmp_path / "clean.json"))


def test_pipeline_without_snap_map_drops_all_links():
    # PINS CURRENT BEHAVIOUR — edge case worth a conscious decision:
    # when snap_map is absent, active_snap_ids stays empty, so every
    # link is treated as orphaned and removed.
    pipeline = {
        "name": "linky",
        "link_map": {"l1": {"src_id": "a", "dst_id": "b"}},
    }
    clean = sanitise_pipeline(pipeline)
    assert clean["link_map"] == {}
