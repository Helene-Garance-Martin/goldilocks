# tests/test_fetch.py
# ============================================================
# 🫧 GOLDILOCKS — fetch hardening (findings F1, F2)
# ============================================================
# CLI-level tests. No network: requests.get is replaced in the
# command's namespace, so nothing leaves the machine.
# ============================================================

import io
import zipfile

import pytest
import requests
import typer
from typer.testing import CliRunner

runner = CliRunner()

DEMO_URL = "https://example.invalid/sl/designer/DemoOrg/demo-project"


def make_app():
    from goldilocks_cli.commands.fetch import fetch
    app = typer.Typer()
    app.command()(fetch)
    return app


class FakeResponse:
    def __init__(self, content=b"", status_code=200, content_type="application/zip"):
        self.content = content
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        self.text = "response body"


def zip_bytes(members: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for name, content in members.items():
            z.writestr(name, content)
    return buffer.getvalue()


@pytest.fixture()
def fetch_env(tmp_path, monkeypatch):
    """Config pointing at tmp_path, credentials present, no network."""
    import goldilocks_cli.commands.fetch as fetch_module

    monkeypatch.setattr(
        fetch_module,
        "load_config",
        lambda *a, **k: {
            "snaplogic": {"url": DEMO_URL},
            "paths": {"exports_dir": str(tmp_path / "exports")},
        },
    )
    monkeypatch.setenv("SNAPLOGIC_USERNAME", "demo-user")
    monkeypatch.setenv("SNAPLOGIC_PASSWORD", "demo-password")
    return fetch_module


# ------------------------------------------------------------
# F1 — hostile archive
# ------------------------------------------------------------

def test_fetch_refuses_traversal_archive(fetch_env, tmp_path, monkeypatch):
    # REGRESSION GUARD (F1): a tampered export naming "../" must not
    # write outside the export folder, and must fail warmly.
    payload = zip_bytes({"../escaped.json": "{}"})
    monkeypatch.setattr(
        fetch_env.requests, "get", lambda *a, **k: FakeResponse(payload)
    )

    result = runner.invoke(make_app(), [])

    assert result.exit_code == 1
    assert "Refusing to unpack" in result.output
    assert "Nothing outside the export folder was written" in result.output
    assert not (tmp_path / "escaped.json").exists()


def test_fetch_accepts_benign_archive(fetch_env, tmp_path, monkeypatch):
    payload = zip_bytes({"export.json": '{"entries": []}'})
    monkeypatch.setattr(
        fetch_env.requests, "get", lambda *a, **k: FakeResponse(payload)
    )

    result = runner.invoke(make_app(), [])

    assert result.exit_code == 0
    assert "Export downloaded and unzipped" in result.output
    written = list((tmp_path / "exports").rglob("export.json"))
    assert written, "benign member should still be extracted"


# ------------------------------------------------------------
# F2 — network failure modes
# ------------------------------------------------------------

def test_fetch_times_out_warmly(fetch_env, monkeypatch):
    def raise_timeout(*a, **k):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(fetch_env.requests, "get", raise_timeout)
    result = runner.invoke(make_app(), [])

    assert result.exit_code == 1
    assert "didn't respond" in result.output
    assert "Traceback" not in result.output


def test_fetch_connection_error_is_warm(fetch_env, monkeypatch):
    def raise_conn(*a, **k):
        raise requests.ConnectionError("no route")

    monkeypatch.setattr(fetch_env.requests, "get", raise_conn)
    result = runner.invoke(make_app(), [])

    assert result.exit_code == 1
    assert "Couldn't reach SnapLogic" in result.output
    assert "no route" not in result.output  # raw detail stays out


def test_request_carries_a_timeout(fetch_env, monkeypatch):
    # REGRESSION GUARD (F2): requests defaults to waiting forever.
    seen = {}

    def capture(*a, **k):
        seen.update(k)
        return FakeResponse(zip_bytes({"export.json": "{}"}))

    monkeypatch.setattr(fetch_env.requests, "get", capture)
    runner.invoke(make_app(), [])

    assert seen.get("timeout"), "fetch must pass a timeout"


# ------------------------------------------------------------
# Bonus defect found while hardening: typer.Exit subclasses
# Exception, so the blanket handler used to swallow deliberate
# exits and re-report them as "Fetch failed: 1".
# ------------------------------------------------------------

def test_http_error_reports_once_not_as_fetch_failed(fetch_env, monkeypatch):
    monkeypatch.setattr(
        fetch_env.requests,
        "get",
        lambda *a, **k: FakeResponse(b"", status_code=403, content_type="text/plain"),
    )

    result = runner.invoke(make_app(), [])

    assert result.exit_code == 1
    assert "Export failed with status 403" in result.output
    assert "Fetch failed: 1" not in result.output
