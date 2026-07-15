# commands/init.py
# ============================================================
# 🫧 GOLDILOCKS — init
# ============================================================
# One-time (and re-runnable) setup, in two acts:
#   1. Config questions — writes goldilocks.toml so `fetch`
#      stops asking you to paste the same URL every time.
#   2. Credentials — reports what's set, scaffolds a .env with
#      commented placeholders for what isn't, and folds .env
#      into the .gitignore check below.
#
# init NEVER accepts a secret value — no prompts for passwords
# or keys, visible or hidden. You fill the .env in your editor;
# init explains, doctor verifies.
# ============================================================

from pathlib import Path

import typer

from goldilocks_cli.colours import CYAN, GOLD, GREEN, RED, RESET, YELLOW
from goldilocks_cli.core.config import (
    home_config_path,
    load_config,
    local_config_path,
    save_config,
    scaffold_sensitive_orgs,
)


# ------------------------------------------------------------
# Git helpers
# ------------------------------------------------------------

def _find_git_root(start: Path) -> Path | None:
    """Walk upwards looking for a .git directory. None if not in a repo."""
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def _gitignore_covers(git_root: Path, filename: str) -> bool:
    """
    Cheap literal check of .gitignore. We are not reimplementing gitignore
    pattern matching — we only want to know whether the obvious line is there.
    """
    gitignore = git_root / ".gitignore"
    if not gitignore.is_file():
        return False

    name = Path(filename).name
    for raw in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lstrip("/") in (name, filename) or line in (f"*{Path(name).suffix}",):
            return True
    return False


# ------------------------------------------------------------
# Credential helpers — act two of init
# ------------------------------------------------------------

# Placeholder lines for the .env scaffold — comments only,
# never values. Grouped by service, matching doctor's report.
ENV_TEMPLATE_LINES: dict[str, list[str]] = {
    "NEO4J_URI": [
        "# Neo4j — used by seed / ask / visualise / show-graph / audit / stats / ping",
        "# NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io",
    ],
    "NEO4J_PASSWORD": [
        "# NEO4J_USER=neo4j            # optional, defaults to neo4j",
        "# NEO4J_PASSWORD=",
    ],
    "SNAPLOGIC_USERNAME": [
        "",
        "# SnapLogic — used by fetch (HTTP basic auth against the pod)",
        "# SNAPLOGIC_USERNAME=",
    ],
    "SNAPLOGIC_PASSWORD": [
        "# SNAPLOGIC_PASSWORD=",
    ],
    "ANTHROPIC_API_KEY": [
        "",
        "# Anthropic — used by ask (the graph agent)",
        "# ANTHROPIC_API_KEY=",
    ],
}

ENV_HEADER = [
    "# 🫧 Goldilocks credentials — fill in and keep OUT of git.",
    "# Real environment variables always win over this file.",
    "",
]


def _report_credentials() -> None:
    """Echo present / not-set per credential. Informational only —
    the live verification is doctor's job."""
    from goldilocks_cli.core.credentials import (
        KNOWN_CREDENTIALS, get_credential,
    )

    typer.echo(f"{CYAN}   Credentials (init explains, doctor verifies):{RESET}")
    for name, meta in KNOWN_CREDENTIALS.items():
        if get_credential(name) is not None:
            typer.echo(f"{GREEN}     ✅ {meta['label']} ({name}) — present{RESET}")
        else:
            typer.echo(f"{YELLOW}     ◻️  {meta['label']} ({name}) — not set{RESET}")


def _scaffold_env(env_path: Path) -> bool:
    """Ensure .env exists and mentions every known credential —
    commented placeholders only, idempotent, never destructive.
    Returns True when the file was created or extended."""
    from goldilocks_cli.core.credentials import KNOWN_CREDENTIALS

    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")
        additions: list[str] = []
        for name in KNOWN_CREDENTIALS:
            if name not in existing:
                additions.extend(ENV_TEMPLATE_LINES.get(name, [f"# {name}="]))
        if not additions:
            return False
        env_path.write_text(
            existing.rstrip("\n") + "\n\n" + "\n".join(additions) + "\n",
            encoding="utf-8",
        )
        return True

    lines = list(ENV_HEADER)
    for name in KNOWN_CREDENTIALS:
        lines.extend(ENV_TEMPLATE_LINES.get(name, [f"# {name}="]))
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


# ------------------------------------------------------------
# Command
# ------------------------------------------------------------

def init(
    local: bool = typer.Option(
        False,
        "--local",
        help="Write ./goldilocks.toml in this directory instead of your home config.",
    ),
):
    """
    🫧 Set up Goldilocks — config, sensitive orgs, first run
    """
    cwd = Path.cwd()
    current = load_config()
    target = local_config_path(cwd) if local else home_config_path()

    typer.echo("")
    typer.echo(f"{YELLOW}🫧 Setting up Goldilocks{RESET}")
    typer.echo(f"   Config: {target}")
    if target.exists():
        typer.echo(f"{CYAN}   Existing values shown as defaults — press enter to keep them.{RESET}")
    typer.echo("")

    # --- SnapLogic URL -------------------------------------------------
    url = typer.prompt(
        "SnapLogic project URL",
        default=current["snaplogic"]["url"] or "",
        show_default=bool(current["snaplogic"]["url"]),
    ).strip()

    # --- Paths ---------------------------------------------------------
    sensitive_orgs = typer.prompt(
        "Sensitive orgs file",
        default=current["paths"]["sensitive_orgs"],
    ).strip()

    exports_dir = typer.prompt(
        "Exports directory",
        default=current["paths"]["exports_dir"],
    ).strip()

    config = {
        "snaplogic": {"url": url},
        "paths": {
            "sensitive_orgs": sensitive_orgs,
            "exports_dir": exports_dir,
        },
    }

    save_config(config, target)
    typer.echo("")
    typer.echo(f"{GREEN}✅ Config saved: {target}{RESET}")

    # --- Sensitive orgs scaffold ---------------------------------------
    orgs_path = Path(sensitive_orgs)
    if not orgs_path.is_absolute():
        orgs_path = cwd / orgs_path

    if scaffold_sensitive_orgs(orgs_path):
        typer.echo(f"{GREEN}✅ Created template: {orgs_path}{RESET}")
    else:
        typer.echo(f"{GOLD}   Kept existing: {orgs_path}{RESET}")

    # --- Credentials (act two) -------------------------------------------
    typer.echo("")
    _report_credentials()

    env_path = cwd / ".env"
    if _scaffold_env(env_path):
        typer.echo(f"{GREEN}✅ .env placeholders ready: {env_path}{RESET}")
        typer.echo(f"{GOLD}   Fill in your values there — goldilocks doctor verifies them.{RESET}")
    else:
        typer.echo(f"{GOLD}   Kept existing: {env_path}{RESET}")

    # --- Gitignore check ------------------------------------------------
    git_root = _find_git_root(cwd)
    if git_root:
        unignored = [
            name
            for name in ([orgs_path.name, ".env"] + ([target.name] if local else []))
            if not _gitignore_covers(git_root, name)
        ]
        if unignored:
            typer.echo("")
            typer.echo(f"{RED}⚠️  Not in .gitignore: {', '.join(unignored)}{RESET}")
            typer.echo(f"{GOLD}   Add to {git_root / '.gitignore'}:{RESET}")
            for name in unignored:
                typer.echo(f"     {name}")
        else:
            typer.echo(f"{GREEN}✅ .gitignore covers your secrets{RESET}")

    # --- Next step -------------------------------------------------------
    typer.echo("")
    typer.echo(f"{CYAN}next: goldilocks doctor, then goldilocks fetch 🫧{RESET}")
    typer.echo("")