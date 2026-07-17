# ============================================================
# 🫧 tests/test_status.py — status / survey command
# ============================================================

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from goldilocks_cli.core.state import atomic_write_json, embed_file_state

runner = CliRunner()


def make_app():
    from goldilocks_cli.commands.status import status
    app = typer.Typer()
    app.command()(status)
    return app


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    home = tmp_path / "home"
    work = tmp_path / "work"
    home.mkdir()
    work.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.chdir(work)
    (work / "goldilocks.toml").write_text(
        '[paths]\nexports_dir = "pipeline_exports"\n'
        'sensitive_orgs = "sensitive_orgs.txt"\n\n'
        '[workflow]\nstale_after_days = "7"\n',
        encoding="utf-8",
    )
    return work


def _mock_graph(monkeypatch, **overrides):
    import goldilocks_cli.commands.status as status_command
    state = {
        "pipeline_count": 0,
        "source_file": None,
        "last_seeded": None,
        "source_sieved_at": None,
    }
    state.update(overrides)
    monkeypatch.setattr(status_command, "_read_neo4j_state", lambda: state)


def test_status_nothing_fetched_recommends_fetch(workspace, monkeypatch):
    _mock_graph(monkeypatch)
    result = runner.invoke(make_app(), [])
    assert result.exit_code == 0
    assert "Fetched" in result.output and "no" in result.output
    assert "Next: goldilocks fetch" in result.output


def test_status_fetched_only_recommends_sieve(workspace, monkeypatch):
    raw = workspace / "pipeline_exports" / "alpha" / "export.json"
    raw.parent.mkdir(parents=True)
    raw.write_text("{}", encoding="utf-8")
    _mock_graph(monkeypatch)

    result = runner.invoke(make_app(), [])

    assert result.exit_code == 0
    assert "Sieved" in result.output
    assert f"goldilocks sieve --input {raw}" in result.output


def test_status_sieved_only_recommends_seed(workspace, monkeypatch):
    sieved = workspace / "export_anonymised.json"
    atomic_write_json(
        sieved,
        embed_file_state({"entries": []}, "export.json", version="test"),
    )
    _mock_graph(monkeypatch)

    result = runner.invoke(make_app(), [])

    assert result.exit_code == 0
    assert f"goldilocks seed --input {sieved}" in result.output


def test_status_seeded_and_ready(workspace, monkeypatch):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _mock_graph(
        monkeypatch,
        pipeline_count=4,
        source_file="export_anonymised.json",
        last_seeded=now,
        source_sieved_at=now,
    )

    result = runner.invoke(make_app(), [])

    assert result.exit_code == 0
    assert "Seeded and ready" in result.output
    assert "Pipeline count" in result.output
    assert "4" in result.output
    assert "goldilocks ask" in result.output


def test_status_seeded_but_stale(workspace, monkeypatch):
    old = (datetime.now(timezone.utc) - timedelta(days=9)).isoformat().replace("+00:00", "Z")
    _mock_graph(
        monkeypatch,
        pipeline_count=2,
        source_file="old.json",
        last_seeded=old,
        source_sieved_at=old,
    )

    result = runner.invoke(make_app(), [])

    assert result.exit_code == 0
    assert "Seeded, but stale" in result.output
    assert "threshold 7 days" in result.output
    assert "Next: goldilocks fetch" in result.output


def test_status_lists_ambiguous_exports_without_choosing(workspace, monkeypatch):
    for name in ["alpha", "beta"]:
        raw = workspace / "pipeline_exports" / name / "export.json"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text("{}", encoding="utf-8")
    _mock_graph(monkeypatch)

    result = runner.invoke(make_app(), [])

    assert result.exit_code == 0
    assert "ambiguous (2 exports)" in result.output
    assert "Fetched exports need an explicit choice" in result.output
    assert "<choose-one-export>" in result.output


def test_status_fails_warmly_when_neo4j_unavailable(workspace, monkeypatch):
    import goldilocks_cli.commands.status as status_command
    monkeypatch.setattr(
        status_command,
        "_read_neo4j_state",
        lambda: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    result = runner.invoke(make_app(), [])

    assert result.exit_code == 1
    assert "could not survey Neo4j" in result.output
    assert "goldilocks doctor" in result.output


def test_survey_alias_is_registered(workspace, monkeypatch):
    from goldilocks_cli.cli import app
    import goldilocks_cli.commands.status as status_command
    monkeypatch.setattr(status_command, "_read_neo4j_state", lambda: {"pipeline_count": 0})

    result = runner.invoke(app, ["survey"])

    assert result.exit_code == 0
    assert "Goldilocks field" in result.output
    assert "survey" in result.output
