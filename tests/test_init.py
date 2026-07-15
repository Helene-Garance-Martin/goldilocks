# ============================================================
# 🫧 tests/test_init.py — goldilocks init + core.config
# ============================================================
# No network. tmp_path + monkeypatched HOME throughout.
# ============================================================

from pathlib import Path

import pytest
from typer.testing import CliRunner

from goldilocks_cli.cli import app
from goldilocks_cli.core import config as config_module

runner = CliRunner()


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """An isolated HOME and cwd, so nothing touches the real machine."""
    home = tmp_path / "home"
    work = tmp_path / "work"
    home.mkdir()
    work.mkdir()

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Windows
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.chdir(work)

    return {"home": home, "work": work}


def _write(path: Path, url: str = "", exports: str = "pipeline_exports") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[snaplogic]\nurl = "{url}"\n\n[paths]\n'
        f'sensitive_orgs = "sensitive_orgs.txt"\nexports_dir = "{exports}"\n',
        encoding="utf-8",
    )
    return path


# ------------------------------------------------------------
# core.config — resolution order
# ------------------------------------------------------------

def test_load_config_defaults_when_no_files(sandbox):
    config = config_module.load_config()

    assert config["snaplogic"]["url"] == ""
    assert config["paths"]["sensitive_orgs"] == "sensitive_orgs.txt"
    assert config["paths"]["exports_dir"] == "pipeline_exports"


def test_load_config_reads_home_config(sandbox):
    _write(config_module.home_config_path(), url="https://home.example.com/p")

    assert config_module.load_config()["snaplogic"]["url"] == "https://home.example.com/p"


def test_local_config_beats_home_config(sandbox):
    _write(config_module.home_config_path(), url="https://home.example.com/p")
    _write(sandbox["work"] / "goldilocks.toml", url="https://local.example.com/p")

    assert config_module.load_config()["snaplogic"]["url"] == "https://local.example.com/p"


def test_local_config_overlays_rather_than_replaces_home(sandbox):
    """A local file that sets only the URL still inherits home's other keys."""
    _write(config_module.home_config_path(), url="https://home.example.com/p", exports="home_exports")
    (sandbox["work"] / "goldilocks.toml").write_text(
        '[snaplogic]\nurl = "https://local.example.com/p"\n', encoding="utf-8"
    )

    config = config_module.load_config()

    assert config["snaplogic"]["url"] == "https://local.example.com/p"
    assert config["paths"]["exports_dir"] == "home_exports"


def test_malformed_config_falls_back_to_defaults(sandbox):
    (sandbox["work"] / "goldilocks.toml").write_text("this is not toml {{{", encoding="utf-8")

    assert config_module.load_config()["paths"]["exports_dir"] == "pipeline_exports"


def test_dumps_toml_roundtrips(sandbox):
    original = {
        "snaplogic": {"url": "https://elastic.example.com/sl/x"},
        "paths": {"sensitive_orgs": "secrets/orgs.txt", "exports_dir": "out"},
    }
    path = config_module.save_config(original, sandbox["work"] / "goldilocks.toml")

    assert config_module.read_config_file(path) == original


# ------------------------------------------------------------
# goldilocks init
# ------------------------------------------------------------

def test_init_writes_config_from_answers(sandbox):
    result = runner.invoke(
        app,
        ["init", "--local"],
        input="https://elastic.example.com/sl/proj\nsensitive_orgs.txt\npipeline_exports\n",
    )

    assert result.exit_code == 0

    config_path = sandbox["work"] / "goldilocks.toml"
    assert config_path.is_file()

    config = config_module.load_config()
    assert config["snaplogic"]["url"] == "https://elastic.example.com/sl/proj"
    assert "next: goldilocks doctor" in result.stdout  # doctor verifies before fetch


def test_init_scaffolds_sensitive_orgs_template(sandbox):
    runner.invoke(app, ["init", "--local"], input="https://x.example.com/p\n\n\n")

    orgs = sandbox["work"] / "sensitive_orgs.txt"
    assert orgs.is_file()

    body = orgs.read_text(encoding="utf-8")
    assert body.startswith("#")
    assert "One name per line" in body


def test_init_does_not_clobber_existing_sensitive_orgs(sandbox):
    orgs = sandbox["work"] / "sensitive_orgs.txt"
    orgs.write_text("Royal Ballet and Opera\n", encoding="utf-8")

    runner.invoke(app, ["init", "--local"], input="https://x.example.com/p\n\n\n")

    assert orgs.read_text(encoding="utf-8") == "Royal Ballet and Opera\n"


def test_rerunning_init_preserves_unchanged_values(sandbox):
    runner.invoke(
        app,
        ["init", "--local"],
        input="https://first.example.com/p\ncustom_orgs.txt\ncustom_exports\n",
    )

    # Second run: change nothing, just press enter three times.
    result = runner.invoke(app, ["init", "--local"], input="\n\n\n")

    assert result.exit_code == 0

    config = config_module.load_config()
    assert config["snaplogic"]["url"] == "https://first.example.com/p"
    assert config["paths"]["sensitive_orgs"] == "custom_orgs.txt"
    assert config["paths"]["exports_dir"] == "custom_exports"


def test_rerunning_init_can_edit_a_single_value(sandbox):
    runner.invoke(
        app,
        ["init", "--local"],
        input="https://first.example.com/p\ncustom_orgs.txt\ncustom_exports\n",
    )

    runner.invoke(app, ["init", "--local"], input="https://second.example.com/p\n\n\n")

    config = config_module.load_config()
    assert config["snaplogic"]["url"] == "https://second.example.com/p"
    assert config["paths"]["exports_dir"] == "custom_exports"  # untouched


def test_init_writes_to_home_by_default(sandbox):
    runner.invoke(app, ["init"], input="https://home.example.com/p\n\n\n")

    assert config_module.home_config_path().is_file()
    assert not (sandbox["work"] / "goldilocks.toml").exists()


def test_init_warns_when_gitignore_misses_sensitive_orgs(sandbox):
    (sandbox["work"] / ".git").mkdir()

    result = runner.invoke(app, ["init", "--local"], input="https://x.example.com/p\n\n\n")

    assert "Not in .gitignore" in result.stdout
    assert "sensitive_orgs.txt" in result.stdout
    assert ".env" in result.stdout  # credentials joined the check


def test_init_is_happy_when_gitignore_covers_secrets(sandbox):
    (sandbox["work"] / ".git").mkdir()
    (sandbox["work"] / ".gitignore").write_text(
        "sensitive_orgs.txt\ngoldilocks.toml\n.env\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["init", "--local"], input="https://x.example.com/p\n\n\n")

    assert ".gitignore covers your secrets" in result.stdout
    assert "Not in .gitignore" not in result.stdout


def test_init_skips_gitignore_check_outside_a_repo(sandbox):
    result = runner.invoke(app, ["init", "--local"], input="https://x.example.com/p\n\n\n")

    assert result.exit_code == 0
    assert "Not in .gitignore" not in result.stdout
    assert "covers your secrets" not in result.stdout


# ------------------------------------------------------------
# fetch integration — no network, we stop at the parse step
# ------------------------------------------------------------

def test_fetch_uses_configured_url_without_prompting(sandbox, monkeypatch):
    """
    With a URL in config, fetch must not ask for one. We prove that by
    feeding empty stdin: a prompt would abort, so reaching the parser
    means no prompt happened.
    """
    _write(sandbox["work"] / "goldilocks.toml", url="https://configured.example.com/p")

    seen = {}

    def fake_parse(url):
        seen["url"] = url
        raise RuntimeError("stop here")

    monkeypatch.setattr(
        "goldilocks_cli.core.snaplogic_url.parse_snaplogic_url", fake_parse
    )

    runner.invoke(app, ["fetch"], input="")

    assert seen["url"] == "https://configured.example.com/p"


def test_fetch_url_flag_overrides_config(sandbox, monkeypatch):
    _write(sandbox["work"] / "goldilocks.toml", url="https://configured.example.com/p")

    seen = {}

    def fake_parse(url):
        seen["url"] = url
        raise RuntimeError("stop here")

    monkeypatch.setattr(
        "goldilocks_cli.core.snaplogic_url.parse_snaplogic_url", fake_parse
    )

    runner.invoke(app, ["fetch", "--url", "https://flag.example.com/p"], input="")

    assert seen["url"] == "https://flag.example.com/p"