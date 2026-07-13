# tests/test_check.py
# ============================================================
# 🫧 GOLDILOCKS — check command + pre-seed gate tests (item 24)
# ============================================================
import json

import typer
from typer.testing import CliRunner

runner = CliRunner()


def make_check_app():
    from goldilocks_cli.commands.check import check
    app = typer.Typer()
    app.command()(check)
    return app


def make_seed_app():
    from goldilocks_cli.commands.seed import seed
    app = typer.Typer()
    app.command()(seed)
    return app


# ------------------------------------------------------------
# goldilocks check
# ------------------------------------------------------------

def test_check_clean_file_exits_zero(tmp_path):
    f = tmp_path / "anon.json"
    f.write_text(json.dumps({"name": "ORG_1 pipeline", "url": "https://api.org-1.com/endpoint-1"}))
    result = runner.invoke(make_check_app(), ["--input", str(f)])
    assert result.exit_code == 0
    assert "no residual" in result.output


def test_check_dirty_file_exits_one_with_report(tmp_path):
    f = tmp_path / "leaky.json"
    f.write_text(json.dumps({
        "note": "mail pat@real-place.example about https://real.sharepoint.com/x",
    }))
    result = runner.invoke(make_check_app(), ["--input", str(f)])
    assert result.exit_code == 1
    assert "Post-scrub audit found" in result.output
    assert "review before sharing" in result.output.lower()


def test_check_missing_file_fails_warm(tmp_path):
    result = runner.invoke(make_check_app(), ["--input", str(tmp_path / "nope.json")])
    assert result.exit_code == 1
    assert "File not found" in result.output


# ------------------------------------------------------------
# pre-seed gate (seeder itself mocked — no Neo4j)
# ------------------------------------------------------------

def _invoke_seed(monkeypatch, tmp_path, content: dict, args=None, input_text=None):
    calls = []
    import goldilocks_cli.core.pipeline_seeder as seeder
    monkeypatch.setattr(seeder, "main", lambda: calls.append(True))
    f = tmp_path / "in.json"
    f.write_text(json.dumps(content))
    argv = ["--input", str(f), "--uri", "neo4j+s://fake", "--password", "pw"]
    if args:
        argv += args
    result = runner.invoke(make_seed_app(), argv, input=input_text)
    return result, calls


def test_seed_clean_input_proceeds(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch, tmp_path, {"name": "ORG_1", "u": "https://api.org-1.com/endpoint-1"}
    )
    assert result.exit_code == 0
    assert "pre-seed check: clean" in result.output
    assert calls  # seeder ran


def test_seed_dirty_input_prompts_and_cancels_on_no(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch, tmp_path,
        {"note": "mail pat@real-place.example"},
        input_text="n\n",
    )
    assert result.exit_code == 1
    assert "Post-scrub audit found" in result.output
    assert "Seeding cancelled" in result.output
    assert not calls  # seeder never ran


def test_seed_dirty_input_proceeds_on_yes(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch, tmp_path,
        {"note": "mail pat@real-place.example"},
        input_text="y\n",
    )
    assert result.exit_code == 0
    assert calls


def test_seed_force_skips_prompt(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch, tmp_path,
        {"note": "mail pat@real-place.example"},
        args=["--force"],
    )
    assert result.exit_code == 0
    assert "seed anyway" not in result.output
    assert calls


def test_seed_missing_input_fails_warm(monkeypatch, tmp_path):
    import goldilocks_cli.core.pipeline_seeder as seeder
    monkeypatch.setattr(seeder, "main", lambda: None)
    result = runner.invoke(
        make_seed_app(),
        ["--input", str(tmp_path / "nope.json"), "--uri", "neo4j+s://fake", "--password", "pw"],
    )
    assert result.exit_code == 1
    assert "File not found" in result.output
    assert "sieve" in result.output  # points at the next step
