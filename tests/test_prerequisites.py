# ============================================================
# 🫧 tests/test_prerequisites.py — command unhappy paths
# ============================================================

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import typer
from typer.testing import CliRunner

from goldilocks_cli.core.state import atomic_write_json, embed_file_state

runner = CliRunner()


def _app(command):
    app = typer.Typer()
    app.command()(command)
    return app


def test_sieve_before_fetch_stops_with_next_command(tmp_path, monkeypatch):
    from goldilocks_cli.commands.sieve import sieve
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(_app(sieve), ["--plain"])

    assert result.exit_code == 1
    assert "Nothing has been fetched" in result.output
    assert "goldilocks fetch" in result.output


def test_sieve_prompts_when_multiple_exports_exist(tmp_path, monkeypatch, clean_anonymiser):
    from goldilocks_cli.commands.sieve import sieve
    monkeypatch.chdir(tmp_path)
    exports = tmp_path / "pipeline_exports"
    for name in ["alpha", "beta"]:
        raw = exports / name / "export.json"
        raw.parent.mkdir(parents=True)
        raw.write_text(json.dumps({"name": name, "instance_id": name}), encoding="utf-8")

    result = runner.invoke(
        _app(sieve),
        [
            "--plain",
            "--sanitised", str(tmp_path / "clean.json"),
            "--anonymised", str(tmp_path / "anon.json"),
        ],
        input="2\n",
    )

    assert result.exit_code == 0
    assert "Several fetched exports" in result.output
    assert "Which export" in result.output
    assert (tmp_path / "anon.json").exists()


def test_re_sieving_marked_file_defaults_no(tmp_path):
    from goldilocks_cli.commands.sieve import sieve
    marked = tmp_path / "already.json"
    atomic_write_json(marked, embed_file_state({"entries": []}, "export.json", version="test"))

    result = runner.invoke(
        _app(sieve),
        ["--input", str(marked), "--plain"],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "already carries a sieved marker" in result.output
    assert "Sieve it again?" in result.output
    assert "Sieve left as it was" in result.output


def test_seed_before_sieve_stops_without_credentials(tmp_path, monkeypatch):
    from goldilocks_cli.commands.seed import seed
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(_app(seed), [])

    assert result.exit_code == 1
    assert "No sieved export" in result.output
    assert "goldilocks sieve" in result.output


def test_seed_warns_on_stale_marked_export(tmp_path, monkeypatch):
    import goldilocks_cli.commands.seed as seed_command
    import goldilocks_cli.core.pipeline_seeder as seeder

    old = datetime.now(timezone.utc) - timedelta(days=9)
    marked = tmp_path / "old_anonymised.json"
    atomic_write_json(
        marked,
        embed_file_state({"name": "ORG_1", "instance_id": "p1"}, "export.json", sieved_at=old, version="test"),
    )
    monkeypatch.setattr(seed_command, "_read_current_graph_state", lambda *a: {"pipeline_count": 0})
    monkeypatch.setattr(seeder, "main", lambda: None)

    result = runner.invoke(
        _app(seed_command.seed),
        ["--input", str(marked), "--uri", "neo4j+s://fake", "--password", "pw"],
    )

    assert result.exit_code == 0
    assert "9 days old" in result.output
    assert "stale after 7 days" in result.output


def test_ask_before_seed_stops_before_agent(monkeypatch):
    import goldilocks_cli.commands.ask as ask_command
    import goldilocks_cli.core.agent as agent
    monkeypatch.setattr(ask_command, "_read_current_graph_state", lambda: {"pipeline_count": 0})
    called = []
    monkeypatch.setattr(agent, "ask_goldilocks", lambda q: called.append(q))

    result = runner.invoke(_app(ask_command.ask), ["How many pipelines?"])

    assert result.exit_code == 1
    assert "graph has not been seeded" in result.output
    assert "goldilocks seed" in result.output
    assert not called


def test_visualise_before_seed_stops_before_menu(monkeypatch):
    import goldilocks_cli.commands.visualise as visualise_command
    monkeypatch.setattr(visualise_command, "_read_current_graph_state", lambda: {"pipeline_count": 0})
    monkeypatch.setattr(
        visualise_command,
        "pipeline_menu",
        lambda: (_ for _ in ()).throw(AssertionError("menu should not open")),
    )

    result = runner.invoke(_app(visualise_command.visualise), [])

    assert result.exit_code == 1
    assert "graph has not been seeded" in result.output
    assert "goldilocks seed" in result.output


def test_show_graph_before_seed_uses_shared_graph_state(monkeypatch):
    from goldilocks_cli.commands.graph import show_graph
    import neo4j

    session = MagicMock()
    session.run.return_value.single.return_value = {
        "pipeline_count": 0,
        "namespace": None,
        "schema_version": None,
        "last_seeded": None,
        "recorded_pipeline_count": None,
        "source_file": None,
        "source_sieved_at": None,
        "tool_version": None,
    }
    driver = MagicMock()
    driver.__enter__.return_value = driver
    driver.session.return_value.__enter__.return_value = session
    monkeypatch.setattr(neo4j.GraphDatabase, "driver", lambda *a, **k: driver)
    monkeypatch.setenv("NEO4J_URI", "neo4j+s://fake")
    monkeypatch.setenv("NEO4J_PASSWORD", "pw")

    result = runner.invoke(_app(show_graph), [])

    assert result.exit_code == 1
    assert "graph has not been seeded" in result.output
    assert "goldilocks seed" in result.output
