# ============================================================
# 🫧 GOLDILOCKS — Credentials
# ============================================================
# The single point of access for every secret Goldilocks
# touches. Nothing else in the codebase reads a credential
# from the environment directly.
#
# The hierarchy (highest wins):
#   1. Process environment variables — the source of truth.
#   2. A gitignored .env at the working root — developer
#      convenience, loaded once at CLI startup with
#      override=False so a real env var ALWAYS beats .env.
#   3. Absent → get_credential returns None;
#      require_credential raises CredentialMissing carrying
#      warm fix-it text.
#
# goldilocks.toml NEVER holds a secret — that file is for
# preferences, not passwords. check_config_for_secrets()
# enforces this by warning loudly on secret-shaped keys;
# the (future, item 25) config loader must call it.
#
# OS keychain (keyring) — designed but deliberately stubbed:
#   a `keyring` backend would slot in between env and .env
#   as an *opt-in* source (get_credential consulting
#   keyring.get_password("goldilocks", name) when a
#   GOLDILOCKS_USE_KEYRING flag is set). It is NOT the
#   default path: it adds a dependency, varies wildly across
#   OSes/headless CI, and muddies the "env is truth" mental
#   model. Revisit post-1.0 if users ask.
# ============================================================

from __future__ import annotations

import os
from pathlib import Path


# ------------------------------------------------------------
# The registry — every credential Goldilocks knows about.
# label:   how the variable is described to a human
# verify:  what `goldilocks doctor` checks for this set
# ------------------------------------------------------------

KNOWN_CREDENTIALS: dict[str, dict[str, str]] = {
    "NEO4J_URI": {
        "label": "Neo4j URI",
        "verify": "the connection",
    },
    "NEO4J_PASSWORD": {
        "label": "Neo4j password",
        "verify": "the connection",
    },
    "SNAPLOGIC_USERNAME": {
        "label": "SnapLogic username",
        "verify": "the pod",
    },
    "SNAPLOGIC_PASSWORD": {
        "label": "SnapLogic password",
        "verify": "the pod",
    },
    "ANTHROPIC_API_KEY": {
        "label": "Anthropic API key",
        "verify": "the client",
    },
}

# NEO4J_USER is a setting with a sensible default, not a secret.
NEO4J_DEFAULT_USER = "neo4j"


# ------------------------------------------------------------
# The one exception
# ------------------------------------------------------------

class CredentialMissing(Exception):
    """A required credential is not set.

    Carries warm fix-it text so every command can fail the
    same way: catch, echo str(exc), exit 1. The message NEVER
    contains a secret value — only the variable's name.
    """

    def __init__(self, name: str, purpose: str = ""):
        self.name = name
        self.purpose = purpose
        meta = KNOWN_CREDENTIALS.get(name, {})
        label = meta.get("label", name)
        verify = meta.get("verify", "the setup")
        for_clause = f" (needed to {purpose})" if purpose else ""
        self.fix_text = (
            f"🔑 {label} not set{for_clause} — add {name} to your .env "
            f"or environment, then re-run. "
            f"goldilocks doctor verifies {verify}."
        )
        super().__init__(self.fix_text)

    def __str__(self) -> str:
        return self.fix_text


# ------------------------------------------------------------
# .env loading — called once at CLI startup (cli.py callback)
# ------------------------------------------------------------

def load_env_file(directory: Path | None = None) -> bool:
    """Load .env from the working root as developer convenience.

    override=False is the load-bearing detail: a variable
    already in the process environment is NEVER replaced by
    the .env value. Env is the source of truth; .env fills
    gaps. Returns True when a .env file was found and loaded.
    """
    from dotenv import load_dotenv

    root = directory or Path.cwd()
    env_path = root / ".env"
    if not env_path.is_file():
        return False
    return load_dotenv(dotenv_path=env_path, override=False)


# ------------------------------------------------------------
# Access
# ------------------------------------------------------------

def get_credential(name: str) -> str | None:
    """Return the credential, or None when unset/blank.

    Empty strings count as absent — an `export NEO4J_PASSWORD=`
    typo should behave like a missing variable, not sail into
    a driver as "".
    """
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return None
    return value


def require_credential(name: str, purpose: str = "") -> str:
    """Return the credential or raise CredentialMissing.

    The exception's str() is the warm, ready-to-echo message.
    """
    value = get_credential(name)
    if value is None:
        raise CredentialMissing(name, purpose)
    return value


# ------------------------------------------------------------
# goldilocks.toml guard — secrets never live in config
# ------------------------------------------------------------

# Key-name fragments that look like they hold a secret.
SECRET_SHAPED_FRAGMENTS = (
    "password", "passwd", "token", "secret",
    "api_key", "apikey", "key", "credential",
)


def check_config_for_secrets(config_path: Path) -> list[str]:
    """Scan goldilocks.toml for secret-shaped key names.

    goldilocks.toml holds preferences, never secrets — by
    design. Returns warning strings (one per offending key,
    nested keys included) for the caller to echo loudly.
    Values are never inspected or included, only key names.

    On Python 3.10 (no stdlib tomllib) the check degrades to
    a line-based key scan rather than adding a toml dependency.
    """
    if not config_path.is_file():
        return []

    def is_secret_shaped(key: str) -> bool:
        k = key.lower()
        return any(fragment in k for fragment in SECRET_SHAPED_FRAGMENTS)

    offenders: list[str] = []

    try:
        import tomllib

        def walk(table: dict, prefix: str = "") -> None:
            for key, value in table.items():
                dotted = f"{prefix}{key}"
                if is_secret_shaped(key):
                    offenders.append(dotted)
                if isinstance(value, dict):
                    walk(value, prefix=f"{dotted}.")

        with config_path.open("rb") as fh:
            walk(tomllib.load(fh))

    except ImportError:  # Python 3.10 — degrade gracefully
        for line in config_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip().strip('"')
            if is_secret_shaped(key):
                offenders.append(key)

    return [
        (
            f"⚠️  goldilocks.toml contains a secret-shaped key: '{key}'. "
            f"Config never holds secrets — move it to your .env or "
            f"environment and remove it from the toml."
        )
        for key in offenders
    ]
