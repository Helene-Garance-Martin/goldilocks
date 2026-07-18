# tests/test_errors.py
# ============================================================
# 🫧 GOLDILOCKS — friendly failure descriptions (finding F3)
# ============================================================
# The point of these tests is discretion: a bolt URI carries the
# host of a private database, and it must not surface in an
# answer just because the driver put it in an exception.
# ============================================================

import pytest

from goldilocks_cli.core.errors import DEBUG_ENV_VAR, debug_enabled, friendly_error


# Stand-ins named exactly like the SDK exceptions, so the tests
# don't need neo4j/anthropic error classes to be importable.
class AuthError(Exception):
    pass


class ServiceUnavailable(Exception):
    pass


class AuthenticationError(Exception):
    pass


class RateLimitError(Exception):
    pass


class WeirdInternalThing(Exception):
    pass


HOSTY = "Unable to retrieve routing information from a3cb0e28.databases.neo4j.io:7687"


@pytest.fixture(autouse=True)
def _debug_off(monkeypatch):
    monkeypatch.delenv(DEBUG_ENV_VAR, raising=False)


# ------------------------------------------------------------
# Discretion
# ------------------------------------------------------------

@pytest.mark.parametrize("exc_class", [AuthError, ServiceUnavailable, WeirdInternalThing])
def test_host_never_appears_in_the_message(exc_class):
    # REGRESSION GUARD (F3): raw driver text used to reach the user.
    message = friendly_error(exc_class(HOSTY))
    assert "databases.neo4j.io" not in message
    assert "7687" not in message


def test_password_in_an_exception_is_not_echoed():
    message = friendly_error(AuthError("auth failed for user neo4j/hunter2"))
    assert "hunter2" not in message


# ------------------------------------------------------------
# Mapping
# ------------------------------------------------------------

def test_auth_error_names_the_credentials():
    message = friendly_error(AuthError(HOSTY))
    assert "NEO4J_PASSWORD" in message
    assert "goldilocks doctor" in message


def test_unreachable_points_at_the_uri_and_doctor():
    message = friendly_error(ServiceUnavailable(HOSTY))
    assert "NEO4J_URI" in message
    assert "goldilocks doctor" in message


def test_anthropic_auth_names_its_own_key():
    message = friendly_error(AuthenticationError("401"))
    assert "ANTHROPIC_API_KEY" in message


def test_rate_limit_suggests_waiting():
    message = friendly_error(RateLimitError("429"))
    assert "moment" in message


def test_unknown_error_offers_the_debug_switch():
    message = friendly_error(WeirdInternalThing("something odd"))
    assert DEBUG_ENV_VAR in message
    assert "something odd" not in message


# ------------------------------------------------------------
# The escape hatch
# ------------------------------------------------------------

def test_debug_flag_appends_raw_detail(monkeypatch):
    monkeypatch.setenv(DEBUG_ENV_VAR, "1")
    message = friendly_error(WeirdInternalThing("the raw detail"))
    assert "the raw detail" in message
    assert "WeirdInternalThing" in message


@pytest.mark.parametrize("value,expected", [
    ("1", True), ("true", True), ("yes", True),
    ("", False), ("0", False), ("false", False), ("no", False), ("off", False),
])
def test_debug_enabled_reads_the_env_var(monkeypatch, value, expected):
    monkeypatch.setenv(DEBUG_ENV_VAR, value)
    assert debug_enabled() is expected


# ------------------------------------------------------------
# The agent uses it
# ------------------------------------------------------------

def test_agent_returns_friendly_text_not_raw_exception(monkeypatch):
    from goldilocks_cli.core import agent

    monkeypatch.setenv("NEO4J_URI", "neo4j+s://fake.invalid")
    monkeypatch.setenv("NEO4J_PASSWORD", "pw")

    def explode(*a, **k):
        raise ServiceUnavailable(HOSTY)

    monkeypatch.setattr(agent, "GraphDatabase", type("D", (), {"driver": staticmethod(explode)}))

    answer = agent.ask_goldilocks("how many pipelines are there?", graph_checked=True)
    assert "databases.neo4j.io" not in answer
    assert "goldilocks doctor" in answer
