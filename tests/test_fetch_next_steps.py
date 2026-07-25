import io
import zipfile
from pathlib import Path

from goldilocks_cli.commands import fetch as fetch_module


def _make_valid_zip() -> bytes:
    """A minimal but valid zip so zipfile.ZipFile(...) opens cleanly."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("export.json", '{"entries": []}')
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, content: bytes):
        self.content = content
        self.status_code = 200
        self.headers = {"Content-Type": "application/zip"}
        self.text = ""


def test_fetch_success_points_to_sieve(monkeypatch, tmp_path, capsys):
    exports_dir = tmp_path / "exports"

    # Config: supply a URL + exports dir so fetch never prompts.
    monkeypatch.setattr(
        fetch_module,
        "load_config",
        lambda: {
            "snaplogic": {"url": "https://elastic.snaplogic.com/demo"},
            "paths": {"exports_dir": str(exports_dir)},
        },
    )

    # URL parsing: return the shape fetch expects.
    monkeypatch.setattr(
        "goldilocks_cli.core.snaplogic_url.parse_snaplogic_url",
        lambda url: {
            "org": "MarmaladeMuseum",
            "project_path": "MarmaladeMuseum/projects/Demo",
            "export_url": "https://elastic.snaplogic.com/export",
        },
    )

    # Credentials present, so no interactive prompt.
    monkeypatch.setattr(
        "goldilocks_cli.core.credentials.get_credential",
        lambda name, *a, **k: {
            "SNAPLOGIC_USERNAME": "curls",
            "SNAPLOGIC_PASSWORD": "porridge",
        }.get(name),
    )

    # Network: a valid zip, status 200, non-JSON content type.
    monkeypatch.setattr(
        fetch_module.requests,
        "get",
        lambda *a, **k: _FakeResponse(_make_valid_zip()),
    )

    # Extraction: write the expected export.json deterministically,
    # so the test stays focused on the success message, not archive internals.
    def _fake_safe_extract(z, dest):
        (Path(dest) / "export.json").write_text('{"entries": []}')

    monkeypatch.setattr(fetch_module, "safe_extract", _fake_safe_extract)

    # url=None uses the configured URL (and dodges Typer's OptionInfo default
    # that a raw function call would otherwise leave in place).
    fetch_module.fetch(url=None)

    out = capsys.readouterr().out

    # Teaches the canonical journey…
    assert "sieve" in out
    assert "goldilocks status" in out
    # …and does not resurrect the legacy path or the fake URI placeholder.
    assert "sanitise" not in out
    assert "your-neo4j-uri" not in out