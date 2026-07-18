# commands/fetch.py
import zipfile
import requests
import typer
from pathlib import Path
from typing import Optional
from requests.auth import HTTPBasicAuth
from rich.console import Console
from goldilocks_cli.colours import CYAN, GREEN, RED, GOLD, RESET
from goldilocks_cli.core.config import load_config
from goldilocks_cli.core.archive import safe_extract, UnsafeArchiveMember
from goldilocks_cli.core.pipeline_fetcher import REQUEST_TIMEOUT_SECONDS

console = Console()

def fetch(
    url: Optional[str] = typer.Option(
        None,
        "--url",
        help="SnapLogic project URL. Overrides the configured one.",
    ),
):
    """
    🌐 Fetch pipeline exports from SnapLogic
    """
    from goldilocks_cli.core.snaplogic_url import parse_snaplogic_url

    config = load_config()

    # --url wins, then the configured URL, then ask.
    url = url or config["snaplogic"]["url"] or typer.prompt("🫧 Paste your SnapLogic URL")

    try:
        parsed = parse_snaplogic_url(url)

        typer.echo("")
        typer.echo(f"Org:     {parsed['org']}")
        typer.echo(f"Project: {parsed['project_path']}")
        typer.echo(f"Export:  {parsed['export_url']}")
        typer.echo("")

        # Secrets flow only through core.credentials. Prefer .env:
        # prompted values vanish with the process. The password
        # prompt stays hidden (hide_input=True) as a fallback only.
        from goldilocks_cli.core.credentials import get_credential

        username = get_credential("SNAPLOGIC_USERNAME")
        password = get_credential("SNAPLOGIC_PASSWORD")
        if username is None or password is None:
            typer.echo(
                f"{GOLD}🔑 Tip: add SNAPLOGIC_USERNAME and SNAPLOGIC_PASSWORD "
                f"to your .env and Goldilocks will stop asking. "
                f"goldilocks doctor verifies the pod.{RESET}"
            )
        username = username or typer.prompt("SnapLogic username")
        password = password or typer.prompt(
            "SnapLogic password",
            hide_input=True,
        )

        project_slug = (
            parsed["project_path"]
            .replace("/", "_")
            .replace(" ", "_")
            .replace("-", "_")
            .lower()
        )

        output_dir = Path(config["paths"]["exports_dir"]) / project_slug
        zip_path   = output_dir / "export.zip"
        output_dir.mkdir(parents=True, exist_ok=True)

        typer.echo(f"   Output: {output_dir}")

        with console.status("[magenta]Downloading export...[/magenta]", spinner="dots"):
            response = requests.get(
                parsed["export_url"],
                auth=HTTPBasicAuth(username, password),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

        content_type = response.headers.get("Content-Type", "")

        if response.status_code != 200:
            typer.echo(f"{RED}❌ Export failed with status {response.status_code}{RESET}")
            typer.echo(response.text)
            raise typer.Exit(1)

        if "json" in content_type.lower():
            typer.echo(f"{RED}❌ Expected a zip, got JSON response:{RESET}")
            typer.echo(response.text)
            raise typer.Exit(1)

        with console.status("[magenta]Unzipping...[/magenta]", spinner="dots"):
            zip_path.write_bytes(response.content)
            try:
                with zipfile.ZipFile(zip_path, "r") as z:
                    safe_extract(z, output_dir)
            except zipfile.BadZipFile:
                typer.echo(f"{RED}❌ Downloaded file is not a valid zip.{RESET}")
                raise typer.Exit(1)
            except UnsafeArchiveMember as e:
                typer.echo(f"{RED}🛑 Refusing to unpack this export — {e}{RESET}")
                typer.echo("   Nothing outside the export folder was written.")
                typer.echo("   Next: check the SnapLogic URL, then goldilocks doctor\n")
                raise typer.Exit(1)

        export_json = output_dir / "export.json"

        if not export_json.exists():
            typer.echo(f"{RED}❌ export.json not found after unzip.{RESET}")
            raise typer.Exit(1)

        typer.echo(f"{GREEN}✅ Export downloaded and unzipped!{RESET}")
        typer.echo(f"{GOLD}   JSON ready: {export_json}{RESET}")
        typer.echo("")
        typer.echo(f"{CYAN}Next steps:{RESET}")
        typer.echo(f"  1. goldilocks sanitise --input {export_json} --output export_clean.json")
        typer.echo(f"  2. goldilocks anonymise --input export_clean.json --output export_anonymised.json")
        typer.echo(f"  3. goldilocks seed --uri your-neo4j-uri")
        typer.echo(f"  4. goldilocks visualise --input export_anonymised.json")

    except typer.Exit:
        # Deliberate exits already printed their own warm message —
        # typer.Exit subclasses Exception, so without this it would be
        # caught below and re-reported as "Fetch failed: 1".
        raise

    except requests.Timeout:
        typer.echo(
            f"{RED}⏳ SnapLogic didn't respond within "
            f"{REQUEST_TIMEOUT_SECONDS}s.{RESET}"
        )
        typer.echo("   Next: check the pod is reachable, then try again\n")
        raise typer.Exit(1)

    except requests.ConnectionError:
        typer.echo(f"{RED}🌐 Couldn't reach SnapLogic.{RESET}")
        typer.echo("   Next: check your connection and the URL, then try again\n")
        raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"{RED}❌ Fetch failed: {e}{RESET}")
        raise typer.Exit(1)