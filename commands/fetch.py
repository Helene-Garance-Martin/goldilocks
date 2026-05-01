# commands/fetch.py
import os
import zipfile
import requests
import typer
from pathlib import Path
from requests.auth import HTTPBasicAuth
from commands.colours import CYAN, GREEN, RED, GOLD, RESET

def fetch():
    """
    🌐 Fetch pipeline exports from SnapLogic
    """
    from snaplogic_url import parse_snaplogic_url

    url = typer.prompt("🐻 Paste your SnapLogic URL")

    try:
        parsed = parse_snaplogic_url(url)

        typer.echo("")
        typer.echo(f"Org:     {parsed['org']}")
        typer.echo(f"Project: {parsed['project_path']}")
        typer.echo(f"Export:  {parsed['export_url']}")
        typer.echo("")

        username = os.getenv("SNAPLOGIC_USERNAME") or typer.prompt("SnapLogic username")
        password = os.getenv("SNAPLOGIC_PASSWORD") or typer.prompt(
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

        output_dir = Path("pipeline_exports") / project_slug
        zip_path   = output_dir / "export.zip"
        output_dir.mkdir(parents=True, exist_ok=True)

        typer.echo(f"{CYAN}🌐 Downloading export...{RESET}")
        typer.echo(f"   Output: {output_dir}")

        response = requests.get(
            parsed["export_url"],
            auth=HTTPBasicAuth(username, password),
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

        zip_path.write_bytes(response.content)

        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(output_dir)
        except zipfile.BadZipFile:
            typer.echo(f"{RED}❌ Downloaded file is not a valid zip.{RESET}")
            raise typer.Exit(1)

        export_json = output_dir / "export.json"

        if not export_json.exists():
            typer.echo(f"{RED}❌ export.json not found after unzip.{RESET}")
            raise typer.Exit(1)

        typer.echo(f"{GREEN}✅ Export downloaded and unzipped!{RESET}")
        typer.echo(f"{GOLD}   JSON ready: {export_json}{RESET}")
        typer.echo("")
        typer.echo(f"{CYAN}Next:{RESET}")
        typer.echo(f"  python pie.py visualise --input {export_json}")

    except Exception as e:
        typer.echo(f"{RED}❌ Fetch failed: {e}{RESET}")
        raise typer.Exit(1)