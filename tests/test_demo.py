# tests/test_demo.py
# ============================================================
# 🫧 GOLDILOCKS — synthetic demo mode tests
# ============================================================
# The demo's promises are boundaries, so the tests are boundary
# tests: isolation from the user's workspace, synthetic-only
# provenance, no network reach, no remote-graph contact, and a
# clean reset. Run in --plain mode, matching the sieve tests'
# honest unit-testable path.
# ============================================================

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

runner = CliRunner()


def make_demo_app():
    from goldilocks_cli.commands.demo import demo

    app = typer.Typer()
    app.command()(demo)
    return app


@pytest.fixture
def no_credentials(monkeypatch):
    for name in (
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "SNAPLOGIC_USERNAME",
        "SNAPLOGIC_PASSWORD",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def no_network(monkeypatch):
    """Any HTTP attempt fails the test — the demo must never reach out."""
    import requests

    def _forbidden(*args, **kwargs):  # pragma: no cover - failure path
        raise AssertionError("demo attempted a network request")

    monkeypatch.setattr(requests, "get", _forbidden)
    monkeypatch.setattr(requests, "post", _forbidden)
    monkeypatch.setattr(requests.Session, "request", _forbidden)


def _run_demo(args, cwd, monkeypatch):
    monkeypatch.chdir(cwd)
    return runner.invoke(make_demo_app(), args, input="y\n")


# ------------------------------------------------------------
# The synthetic estate itself
# ------------------------------------------------------------

def test_demo_estate_is_synthetic_and_sieves_quiet(tmp_path):
    """Fixture domains are reserved .example only, and the REAL
    sieve leaves its output leak-quiet."""
    from goldilocks_cli.core.anonymiser import anonymise_pipeline, scan_for_leaks
    from goldilocks_cli.core.demo_estate import build_demo_export, write_demo_export
    from goldilocks_cli.core.sanitiser import sanitise_export

    raw_text = json.dumps(build_demo_export())
    assert ".example" in raw_text
    assert ".com" not in raw_text and ".co.uk" not in raw_text and ".org/" not in raw_text

    raw = write_demo_export(tmp_path / "export.json")
    clean = tmp_path / "clean.json"
    anon = tmp_path / "anon.json"
    sanitise_export(str(raw), str(clean))
    summary = anonymise_pipeline(str(clean), str(anon), source_file=raw.name)

    assert summary["leak_findings"] == {}
    assert scan_for_leaks(anon.read_text(encoding="utf-8")) == {}
    # provenance: the sieved output carries the real marker
    marker = json.loads(anon.read_text(encoding="utf-8"))["_goldilocks"]
    assert marker["stage"] == "sieved"
    assert marker["source_file"] == "export.json"


# ------------------------------------------------------------
# Isolation and network avoidance
# ------------------------------------------------------------

def test_demo_runs_offline_and_leaves_cwd_untouched(
    tmp_path, monkeypatch, no_credentials, no_network
):
    before = set(Path(tmp_path).iterdir())
    result = _run_demo(["--plain"], tmp_path, monkeypatch)

    assert result.exit_code == 0, result.output
    assert "FICTIONAL AND SYNTHETIC" in result.output
    assert "no residual" in result.output          # real leak scan ran
    assert "Grounded questions" in result.output
    assert "Orchestrator — Opening Hours" in result.output
    assert set(Path(tmp_path).iterdir()) == before  # nothing written to cwd


def test_demo_never_reuses_existing_workspace_data(
    tmp_path, monkeypatch, no_credentials, no_network
):
    """A user's own export in cwd must be invisible to the demo."""
    decoy = tmp_path / "export_anonymised.json"
    decoy.write_text(json.dumps({"name": "USER DECOY PIPELINE", "snap_map": {}}))

    result = _run_demo(["--plain"], tmp_path, monkeypatch)

    assert result.exit_code == 0, result.output
    assert "USER DECOY PIPELINE" not in result.output
    assert decoy.read_text() == json.dumps(
        {"name": "USER DECOY PIPELINE", "snap_map": {}}
    )


def test_demo_skips_remote_neo4j_without_connecting(
    tmp_path, monkeypatch, no_credentials, no_network
):
    monkeypatch.setenv("NEO4J_URI", "neo4j+s://real-instance.databases.neo4j.io")
    monkeypatch.setenv("NEO4J_PASSWORD", "not-a-real-password")

    import neo4j

    def _forbidden(*args, **kwargs):  # pragma: no cover - failure path
        raise AssertionError("demo attempted to contact a remote graph")

    monkeypatch.setattr(neo4j.GraphDatabase, "driver", _forbidden)

    result = _run_demo(["--plain"], tmp_path, monkeypatch)

    assert result.exit_code == 0, result.output
    assert "remote" in result.output
    assert "untouched" in result.output


# ------------------------------------------------------------
# Reset behaviour
# ------------------------------------------------------------

def test_demo_reset_removes_workspace(tmp_path, monkeypatch, no_credentials, no_network):
    result = _run_demo(["--plain"], tmp_path, monkeypatch)

    assert result.exit_code == 0, result.output
    assert "Demo workspace removed" in result.output
    workspace = _workspace_path_from(result.output)
    assert workspace is not None and not workspace.exists()


def test_demo_keep_retains_workspace_with_artefacts(
    tmp_path, monkeypatch, no_credentials, no_network
):
    result = _run_demo(["--plain", "--keep"], tmp_path, monkeypatch)

    assert result.exit_code == 0, result.output
    workspace = _workspace_path_from(result.output)
    assert workspace is not None and workspace.exists()
    assert (workspace / "export_anonymised.json").is_file()
    diagrams = list((workspace / "diagrams").glob("*.mmd"))
    assert diagrams, "expected at least one Mermaid diagram in the demo workspace"

    import shutil

    shutil.rmtree(workspace, ignore_errors=True)  # tidy after ourselves


def _workspace_path_from(output: str) -> Path | None:
    for line in output.splitlines():
        if "Demo workspace" in line or "workspace kept" in line:
            candidate = line.split(":", 1)[-1].strip()
            if "goldilocks-demo-" in candidate:
                return Path(candidate)
    return None
