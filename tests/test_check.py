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

def _invoke_seed(
    monkeypatch,
    tmp_path,
    content: dict,
    *,
    marked=False,
    graph_state=None,
    args=None,
    input_text=None,
):
    calls = []
    import goldilocks_cli.core.pipeline_seeder as seeder
    import goldilocks_cli.commands.seed as seed_command
    from goldilocks_cli.core.state import embed_file_state

    monkeypatch.setattr(seeder, "main", lambda: calls.append(True))
    monkeypatch.setattr(
        seed_command,
        "_read_current_graph_state",
        lambda *a, **k: graph_state or {"pipeline_count": 0},
    )

    f = tmp_path / "in.json"
    payload = embed_file_state(content, "export.json", version="test") if marked else content
    f.write_text(json.dumps(payload))
    argv = ["--input", str(f), "--uri", "neo4j+s://fake", "--password", "pw"]
    if args:
        argv += args
    result = runner.invoke(make_seed_app(), argv, input=input_text)
    return result, calls


def test_seed_marked_clean_input_proceeds(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch,
        tmp_path,
        {"name": "ORG_1", "u": "https://api.org-1.com/endpoint-1"},
        marked=True,
    )
    assert result.exit_code == 0
    assert "pre-seed check: clean" in result.output
    assert calls


def test_seed_clean_legacy_input_prompts_and_defaults_no(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch,
        tmp_path,
        {"name": "ORG_1", "u": "https://api.org-1.com/endpoint-1"},
        input_text="n\n",
    )
    assert result.exit_code == 1
    assert "no Goldilocks sieve marker" in result.output
    assert "Proceed with seeding?" in result.output
    assert not calls


def test_seed_clean_legacy_input_proceeds_on_yes(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch,
        tmp_path,
        {"name": "ORG_1", "u": "https://api.org-1.com/endpoint-1"},
        input_text="y\n",
    )
    assert result.exit_code == 0
    assert calls


def test_seed_dirty_input_is_hard_refusal(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch,
        tmp_path,
        {"note": "mail pat@real-place.example"},
        input_text="y\n",
    )
    assert result.exit_code == 1
    assert "Post-scrub audit found" in result.output
    assert "Seed refused" in result.output
    assert "seed anyway" not in result.output.lower()
    assert not calls


def test_seed_force_never_bypasses_leak_refusal(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch,
        tmp_path,
        {"note": "mail pat@real-place.example"},
        args=["--force"],
    )
    assert result.exit_code == 1
    assert "Seed refused" in result.output
    assert not calls


def test_seed_force_allows_clean_legacy_input(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch,
        tmp_path,
        {"name": "ORG_1"},
        args=["--force"],
    )
    assert result.exit_code == 0
    assert "Proceed with seeding?" not in result.output
    assert calls


def test_seed_combines_legacy_and_reseed_into_one_prompt(monkeypatch, tmp_path):
    result, calls = _invoke_seed(
        monkeypatch,
        tmp_path,
        {"name": "ORG_1"},
        graph_state={
            "pipeline_count": 2,
            "source_file": "in.json",
            "last_seeded": "2026-07-17T10:00:00Z",
        },
        input_text="n\n",
    )
    assert result.exit_code == 1
    assert "no Goldilocks sieve marker" in result.output
    assert "Already seeded from in.json" in result.output
    assert result.output.count("Proceed with seeding?") == 1
    assert not calls


def test_seed_missing_input_fails_warm(monkeypatch, tmp_path):
    result = runner.invoke(
        make_seed_app(),
        ["--input", str(tmp_path / "nope.json"), "--uri", "neo4j+s://fake", "--password", "pw"],
    )
    assert result.exit_code == 1
    assert "File not found" in result.output
    assert "sieve" in result.output
