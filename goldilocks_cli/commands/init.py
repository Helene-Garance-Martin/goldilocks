# commands/init.py
# ============================================================
# 🫧 GOLDILOCKS — init
# ============================================================
# One-time (and re-runnable) setup. Writes a config file so
# `fetch` stops asking you to paste the same URL every time.
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

    # --- Gitignore check ------------------------------------------------
    git_root = _find_git_root(cwd)
    if git_root:
        unignored = [
            name
            for name in ([orgs_path.name] + ([target.name] if local else []))
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
    typer.echo(f"{CYAN}next: goldilocks fetch 🫧{RESET}")
    typer.echo("")