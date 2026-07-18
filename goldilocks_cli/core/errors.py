# ============================================================
# 🫧 GOLDILOCKS — Friendly failure descriptions
# ============================================================
# Driver and SDK exceptions are written for developers reading
# stack traces, not for someone who just asked a question about
# their pipelines. Left raw they are unhelpful ("Unable to
# retrieve routing information") and occasionally indiscreet:
# a bolt URI carries the host of a private database.
#
# friendly_error() turns an exception into a warm sentence that
# names the next command and never echoes a host, path or
# credential. Raw detail stays available behind GOLDILOCKS_DEBUG
# for whoever actually needs it.
# ============================================================

from __future__ import annotations

import os

DEBUG_ENV_VAR = "GOLDILOCKS_DEBUG"

_FALSEY = {"", "0", "false", "no", "off"}


def debug_enabled() -> bool:
    """True when GOLDILOCKS_DEBUG asks for raw failure detail."""
    return os.environ.get(DEBUG_ENV_VAR, "").strip().lower() not in _FALSEY


# Matched on class name so this module never imports the neo4j
# or anthropic SDKs just to describe a failure.
_NEO4J_AUTH = {"AuthError", "AuthenticationRateLimit"}
_NEO4J_UNREACHABLE = {
    "ServiceUnavailable",
    "SessionExpired",
    "ConfigurationError",
    "IncompleteCommit",
}
_ANTHROPIC_AUTH = {"AuthenticationError", "PermissionDeniedError"}
_ANTHROPIC_REACH = {"APIConnectionError", "APITimeoutError"}
_ANTHROPIC_LIMIT = {"RateLimitError", "OverloadedError"}


def friendly_error(exc: BaseException) -> str:
    """Describe a failure warmly, without hosts, paths or secrets."""
    name = type(exc).__name__

    if name in _NEO4J_AUTH:
        message = (
            "🔑 Neo4j refused those credentials — check NEO4J_USER and "
            "NEO4J_PASSWORD.\n   Next: goldilocks doctor"
        )
    elif name in _NEO4J_UNREACHABLE:
        message = (
            "🌾 The graph is unreachable — check NEO4J_URI and that the "
            "instance is awake.\n   Next: goldilocks doctor"
        )
    elif name in _ANTHROPIC_AUTH:
        message = (
            "🔑 Anthropic refused that API key — check ANTHROPIC_API_KEY.\n"
            "   Next: goldilocks doctor"
        )
    elif name in _ANTHROPIC_REACH:
        message = (
            "🤖 Couldn't reach Anthropic — check your connection.\n"
            "   Next: try again in a moment"
        )
    elif name in _ANTHROPIC_LIMIT:
        message = (
            "🤖 Anthropic is rate-limiting or overloaded right now.\n"
            "   Next: try again in a moment"
        )
    elif name == "ClientError":
        message = (
            "🌾 Neo4j rejected that query.\n"
            "   Next: rephrase the question, or goldilocks doctor"
        )
    else:
        message = (
            "❌ Something went wrong while answering.\n"
            f"   Next: set {DEBUG_ENV_VAR}=1 for the raw detail"
        )

    if debug_enabled():
        message = f"{message}\n   [{DEBUG_ENV_VAR}] {name}: {exc}"

    return message
