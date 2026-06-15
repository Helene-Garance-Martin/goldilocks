# commands/doctor.py
import os
import subprocess
import shutil
import sys
import typer
from commands.colours import CYAN, GREEN, RED, YELLOW, BOLD, RESET


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

    # ── Neo4j ─────────────────────────────────────────────
    try:
        from neo4j import GraphDatabase
        uri = os.environ["NEO4J_URI"]
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ["NEO4J_PASSWORD"]

        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            driver.verify_connectivity()

        typer.echo(f"{GREEN}  ✅ Neo4j reachable{RESET}")

    except KeyError:
        typer.echo(f"{YELLOW}  ⚠️  Neo4j env vars not set (NEO4J_URI, NEO4J_PASSWORD){RESET}")
        all_ok = False
    except Exception as e:
        typer.echo(f"{RED}  ❌ Neo4j unreachable: {e}{RESET}")
        all_ok = False

    # ── Summary ───────────────────────────────────────────
    typer.echo("")
    if all_ok:
        typer.echo(f"{GREEN}{BOLD}  🫧 All systems go!{RESET}\n")
    else:
        typer.echo(f"{YELLOW}{BOLD}  🫧 Some issues found — see above{RESET}\n")