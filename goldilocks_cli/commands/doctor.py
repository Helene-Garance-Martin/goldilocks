# commands/doctor.py
import os
import subprocess
import shutil
import sys
import typer
from goldilocks_cli.colours import CYAN, GREEN, RED, YELLOW, BOLD, RESET


def _run_version(command_path: str, flag: str = "--version") -> tuple[bool, str]:
    """Run a version command safely across Windows, macOS and Linux."""
    try:
        result = subprocess.run(
            [command_path, flag],
            capture_output=True,
            text=True,
            timeout=10,
            shell=sys.platform.startswith("win"),
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except Exception as e:
        return False, str(e)


# ------------------------------------------------------------
# Credential checkers — each returns True when nothing is
# actively broken (missing or rejected). "Present but
# unverified" counts as OK-with-a-note: the credential is set;
# only the live check couldn't complete (e.g. offline).
# ------------------------------------------------------------

def _missing_line(name: str) -> None:
    from goldilocks_cli.core.credentials import CredentialMissing
    typer.echo(f"{RED}  ❌ {CredentialMissing(name)}{RESET}")


def _check_neo4j() -> bool:
    from goldilocks_cli.core.credentials import get_credential, NEO4J_DEFAULT_USER

    uri = get_credential("NEO4J_URI")
    password = get_credential("NEO4J_PASSWORD")
    if uri is None or password is None:
        for name, value in (("NEO4J_URI", uri), ("NEO4J_PASSWORD", password)):
            if value is None:
                _missing_line(name)
        return False

    user = get_credential("NEO4J_USER") or NEO4J_DEFAULT_USER
    try:
        from neo4j import GraphDatabase
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            driver.verify_connectivity()
        typer.echo(f"{GREEN}  ✅ Neo4j — verified (connected as {user}){RESET}")
        return True
    except Exception as e:
        typer.echo(
            f"{YELLOW}  ⚠️  Neo4j — present but unverified: "
            f"{type(e).__name__} while connecting. "
            f"Check NEO4J_URI and that the instance is awake.{RESET}"
        )
        return True


def _check_anthropic() -> bool:
    from goldilocks_cli.core.credentials import get_credential

    api_key = get_credential("ANTHROPIC_API_KEY")
    if api_key is None:
        _missing_line("ANTHROPIC_API_KEY")
        return False

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        # models.list() is the SDK's cheapest live call — no
        # tokens consumed, just proves the key is accepted.
        client.models.list()
        typer.echo(f"{GREEN}  ✅ Anthropic — verified (key accepted){RESET}")
        return True
    except Exception as e:
        if type(e).__name__ in ("AuthenticationError", "PermissionDeniedError"):
            typer.echo(
                f"{RED}  ❌ Anthropic — key set but rejected by the API. "
                f"Check ANTHROPIC_API_KEY in your .env.{RESET}"
            )
            return False
        typer.echo(
            f"{YELLOW}  ⚠️  Anthropic — present but unverified: "
            f"{type(e).__name__} during the live check.{RESET}"
        )
        return True


def _check_snaplogic() -> bool:
    from goldilocks_cli.core.credentials import get_credential
    from goldilocks_cli.core.snaplogic_url import SNAPLOGIC_EXPORT_BASE

    username = get_credential("SNAPLOGIC_USERNAME")
    password = get_credential("SNAPLOGIC_PASSWORD")
    if username is None or password is None:
        for name, value in (
            ("SNAPLOGIC_USERNAME", username),
            ("SNAPLOGIC_PASSWORD", password),
        ):
            if value is None:
                _missing_line(name)
        return False

    try:
        import requests
        from requests.auth import HTTPBasicAuth

        response = requests.get(
            SNAPLOGIC_EXPORT_BASE,
            auth=HTTPBasicAuth(username, password),
            timeout=15,
        )
        if response.status_code in (401, 403):
            typer.echo(
                f"{RED}  ❌ SnapLogic — credentials set but rejected by the pod "
                f"(HTTP {response.status_code}). Check SNAPLOGIC_USERNAME / "
                f"SNAPLOGIC_PASSWORD.{RESET}"
            )
            return False
        typer.echo(
            f"{GREEN}  ✅ SnapLogic — verified (pod reachable, "
            f"credentials not rejected){RESET}"
        )
        return True
    except Exception as e:
        typer.echo(
            f"{YELLOW}  ⚠️  SnapLogic — present but unverified: "
            f"{type(e).__name__} reaching the pod.{RESET}"
        )
        return True


def doctor():
    """
    🩺 Check all Goldilocks dependencies are installed and reachable.
    """
    typer.echo(f"{CYAN}🩺 Running Goldilocks health check...{RESET}\n")

    all_ok = True

    # ── Python ────────────────────────────────────────────
    major, minor = sys.version_info.major, sys.version_info.minor
    if major == 3 and minor >= 10:
        typer.echo(f"{GREEN}  ✅ Python {major}.{minor}{RESET}")
    else:
        typer.echo(f"{RED}  ❌ Python {major}.{minor} — 3.10+ required{RESET}")
        all_ok = False

    # ── Node.js ───────────────────────────────────────────
    node = shutil.which("node")
    if node:
        ok, version = _run_version(node)
        if ok:
            typer.echo(f"{GREEN}  ✅ Node.js {version}{RESET}")
        else:
            typer.echo(f"{YELLOW}  ⚠️  Node.js found but could not run: {version}{RESET}")
            all_ok = False
    else:
        typer.echo(f"{RED}  ❌ Node.js not found — install from nodejs.org{RESET}")
        all_ok = False

    # ── mmdc ─────────────────────────────────────────────
    mmdc = shutil.which("mmdc.cmd") or shutil.which("mmdc")

    if mmdc:
        try:
            result = subprocess.run(
                [mmdc, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=sys.platform.startswith("win"),
            )
            version = result.stdout.strip() or result.stderr.strip()

            if result.returncode == 0:
                typer.echo(f"{GREEN}  ✅ mmdc {version}{RESET}")
            else:
                typer.echo(f"{YELLOW}  ⚠️  mmdc found but version check failed{RESET}")
                all_ok = False

        except Exception as e:
            typer.echo(f"{YELLOW}  ⚠️  mmdc found but could not run: {e}{RESET}")
            all_ok = False
    else:
        typer.echo(f"{RED}  ❌ mmdc not found — run: npm install -g @mermaid-js/mermaid-cli{RESET}")
        all_ok = False

    # ── Credentials — three states per set ────────────────
    # missing → name the variable + one-line fix
    # present-but-unverified → set, but the live check could not complete
    # verified → cheap live check succeeded
    # No part of any secret is ever printed — not even masked.
    typer.echo(f"\n{CYAN}  Credentials{RESET}")

    all_ok = _check_neo4j() and all_ok
    all_ok = _check_anthropic() and all_ok
    all_ok = _check_snaplogic() and all_ok

    # ── Summary ───────────────────────────────────────────
    typer.echo("")
    if all_ok:
        typer.echo(f"{GREEN}{BOLD}  🫧 All systems go!{RESET}\n")
    else:
        typer.echo(f"{YELLOW}{BOLD}  🫧 Some issues found — see above{RESET}\n")