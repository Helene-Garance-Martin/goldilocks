# tests/test_credentials.py
# ============================================================
# 🫧 GOLDILOCKS — credential pattern tests
# ============================================================
# One module owns all secret access (core/credentials.py).
# These tests pin:
#   • the hierarchy: env beats .env beats absent
#   • require_credential's warm fix-it text
#   • the goldilocks.toml "no secrets in config" guard
#   • point-of-use failure: warm 🔑 message, exit 1, no traceback
#   • doctor's three states (live checks mocked)
#   • sieve never ingests a .env as pipeline input
# No test here needs a real service — live checks follow the
# RUN_INTEGRATION spirit by being mocked instead of skipped.
# ============================================================

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from goldilocks_cli.core.credentials import (
    CredentialMissing,
    check_config_for_secrets,
    get_credential,
    load_env_file,
    require_credential,
)

runner = CliRunner()

CRED_VARS = (
    "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD",
    "SNAPLOGIC_USERNAME", "SNAPLOGIC_PASSWORD",
    "ANTHROPIC_API_KEY",
)


@pytest.fixture(autouse=True)
def pristine_environ():
    """Snapshot/restore os.environ — load_dotenv writes to it directly,
    outside monkeypatch's bookkeeping."""
    saved = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(saved)


@pytest.fixture()
def no_credentials(monkeypatch):
    for name in CRED_VARS:
        monkeypatch.delenv(name, raising=False)


# ------------------------------------------------------------
# The hierarchy — env beats .env beats absent
# ------------------------------------------------------------

class TestHierarchy:
    def test_env_var_beats_dotenv(self, tmp_path, monkeypatch, no_credentials):
        (tmp_path / ".env").write_text(
            "NEO4J_PASSWORD=from-dotenv\n", encoding="utf-8"
        )
        monkeypatch.setenv("NEO4J_PASSWORD", "from-env")

        assert load_env_file(tmp_path) is True
        assert get_credential("NEO4J_PASSWORD") == "from-env"

    def test_dotenv_fills_gap_when_env_absent(self, tmp_path, no_credentials):
        (tmp_path / ".env").write_text(
            "NEO4J_PASSWORD=from-dotenv\n", encoding="utf-8"
        )

        assert load_env_file(tmp_path) is True
        assert get_credential("NEO4J_PASSWORD") == "from-dotenv"

    def test_absent_returns_none(self, tmp_path, no_credentials):
        assert load_env_file(tmp_path) is False  # no .env at all
        assert get_credential("NEO4J_PASSWORD") is None

    def test_blank_env_var_counts_as_absent(self, monkeypatch, no_credentials):
        monkeypatch.setenv("NEO4J_PASSWORD", "   ")
        assert get_credential("NEO4J_PASSWORD") is None


# ------------------------------------------------------------
# require_credential — the warm error
# ------------------------------------------------------------

class TestRequireCredential:
    def test_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("NEO4J_PASSWORD", "s3kr3t")
        assert require_credential("NEO4J_PASSWORD") == "s3kr3t"

    def test_missing_raises_with_fix_text(self, no_credentials):
        with pytest.raises(CredentialMissing) as excinfo:
            require_credential("NEO4J_PASSWORD", "seed the graph")

        message = str(excinfo.value)
        assert "🔑" in message
        assert "NEO4J_PASSWORD" in message
        assert ".env" in message
        assert "goldilocks doctor" in message
        assert "seed the graph" in message

    def test_error_never_contains_a_value(self, no_credentials):
        # Structural pin: the exception is built before any value
        # exists, so it can only ever carry names, never secrets.
        exc = CredentialMissing("ANTHROPIC_API_KEY", "ask questions")
        assert "ANTHROPIC_API_KEY" in exc.fix_text
        assert exc.fix_text == str(exc)


# ------------------------------------------------------------
# goldilocks.toml — config never holds secrets
# ------------------------------------------------------------

class TestConfigSecretGuard:
    def test_secret_shaped_keys_warn(self, tmp_path):
        toml = tmp_path / "goldilocks.toml"
        toml.write_text(
            '[output]\ndirectory = "diagrams"\n\n'
            '[neo4j]\npassword = "oops"\n\n'
            '[anthropic]\napi_key = "oops"\n',
            encoding="utf-8",
        )
        warnings = check_config_for_secrets(toml)
        joined = "\n".join(warnings)
        assert len(warnings) == 2
        assert "password" in joined
        assert "api_key" in joined
        assert "never holds secrets" in joined
        # key NAMES only — the values must not be echoed
        assert "oops" not in joined

    def test_clean_config_is_silent(self, tmp_path):
        toml = tmp_path / "goldilocks.toml"
        toml.write_text(
            '[output]\ndirectory = "diagrams"\nformat = "mmd"\n',
            encoding="utf-8",
        )
        assert check_config_for_secrets(toml) == []

    def test_missing_config_is_silent(self, tmp_path):
        assert check_config_for_secrets(tmp_path / "goldilocks.toml") == []


# ------------------------------------------------------------
# Point of use — warm failure, exit 1, no traceback
# ------------------------------------------------------------

class TestPointOfUse:
    def test_neo4j_command_without_creds_fails_warm(
        self, tmp_path, monkeypatch, no_credentials
    ):
        monkeypatch.chdir(tmp_path)  # no stray .env
        from goldilocks_cli.cli import app

        result = runner.invoke(app, ["stats"])

        assert result.exit_code == 1
        assert "🔑" in result.output
        assert "NEO4J_URI" in result.output
        assert "goldilocks doctor" in result.output
        assert "Traceback" not in result.output
        assert "KeyError" not in result.output


# ------------------------------------------------------------
# doctor — three states, live checks mocked
# ------------------------------------------------------------

def _invoke_doctor(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from goldilocks_cli.cli import app
    return runner.invoke(app, ["doctor"])


class TestDoctorStates:
    def test_missing_state_names_each_variable(
        self, tmp_path, monkeypatch, no_credentials
    ):
        result = _invoke_doctor(tmp_path, monkeypatch)

        for name in ("NEO4J_URI", "NEO4J_PASSWORD",
                     "SNAPLOGIC_USERNAME", "SNAPLOGIC_PASSWORD",
                     "ANTHROPIC_API_KEY"):
            assert name in result.output
        assert "🔑" in result.output
        assert "Traceback" not in result.output

    def test_verified_state_never_prints_secrets(
        self, tmp_path, monkeypatch, no_credentials
    ):
        monkeypatch.setenv("NEO4J_URI", "neo4j+s://unit.test")
        monkeypatch.setenv("NEO4J_PASSWORD", "NEO-SECRET-VALUE")
        monkeypatch.setenv("SNAPLOGIC_USERNAME", "helene@unit.test")
        monkeypatch.setenv("SNAPLOGIC_PASSWORD", "SNAP-SECRET-VALUE")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ANT-SECRET-VALUE")

        monkeypatch.setattr("neo4j.GraphDatabase", MagicMock())
        monkeypatch.setattr("anthropic.Anthropic", MagicMock())
        ok_response = MagicMock(status_code=200)
        monkeypatch.setattr("requests.get", MagicMock(return_value=ok_response))

        result = _invoke_doctor(tmp_path, monkeypatch)

        assert "Neo4j — verified" in result.output
        assert "Anthropic — verified" in result.output
        assert "SnapLogic — verified" in result.output
        # the hard rule: no part of any secret, ever
        for secret in ("NEO-SECRET-VALUE", "SNAP-SECRET-VALUE",
                       "ANT-SECRET-VALUE"):
            assert secret not in result.output

    def test_present_but_unverified_when_checks_cannot_complete(
        self, tmp_path, monkeypatch, no_credentials
    ):
        monkeypatch.setenv("NEO4J_URI", "neo4j+s://unit.test")
        monkeypatch.setenv("NEO4J_PASSWORD", "x")
        monkeypatch.setenv("SNAPLOGIC_USERNAME", "u")
        monkeypatch.setenv("SNAPLOGIC_PASSWORD", "x")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "x")

        neo_mock = MagicMock()
        neo_mock.driver.side_effect = ConnectionError("offline")
        monkeypatch.setattr("neo4j.GraphDatabase", neo_mock)

        anthropic_mock = MagicMock()
        anthropic_mock.return_value.models.list.side_effect = (
            ConnectionError("offline")
        )
        monkeypatch.setattr("anthropic.Anthropic", anthropic_mock)

        monkeypatch.setattr(
            "requests.get", MagicMock(side_effect=ConnectionError("offline"))
        )

        result = _invoke_doctor(tmp_path, monkeypatch)

        assert result.output.count("present but unverified") == 3
        assert "Traceback" not in result.output


# ------------------------------------------------------------
# Hard rule 4 — a .env in the working directory is never read
# by sieve/anonymise as pipeline input
# ------------------------------------------------------------

class TestSieveDotenvIsolation:
    MARKER = "SUPER-SECRET-DOTENV-MARKER-XYZ"

    def test_sieve_never_ingests_dotenv(
        self, tmp_path, monkeypatch, synthetic_export, no_credentials
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text(
            f"FAKE_SECRET={self.MARKER}\n", encoding="utf-8"
        )
        export = tmp_path / "export.json"
        export.write_text(json.dumps(synthetic_export), encoding="utf-8")

        from goldilocks_cli.cli import app

        result = runner.invoke(app, [
            "sieve", "--plain",
            "--input", str(export),
            "--sanitised", str(tmp_path / "clean.json"),
            "--anonymised", str(tmp_path / "anon.json"),
        ])

        assert result.exit_code == 0
        assert self.MARKER not in result.output
        for produced in ("clean.json", "anon.json"):
            content = (tmp_path / produced).read_text(encoding="utf-8")
            assert self.MARKER not in content
        # and the .env itself was left untouched
        assert self.MARKER in (tmp_path / ".env").read_text(encoding="utf-8")
