# ============================================================
# 🫧 GOLDILOCKS — Pipeline Fetcher
# ============================================================
# Connects to SnapLogic API, exports pipeline assets,
# unzips the response and saves files locally.
# ============================================================

import requests
import getpass
import zipfile
import io
from pathlib import Path
from requests.auth import HTTPBasicAuth

from goldilocks_cli.core.archive import safe_extract

# ------------------------------------------------------------
# Network
# ------------------------------------------------------------

# requests defaults to waiting forever; a hung pod should fail,
# not hang a terminal behind a spinner.
REQUEST_TIMEOUT_SECONDS = 30

# ------------------------------------------------------------
# Lambda functions — small, reusable transformation steps
# ------------------------------------------------------------

fetch_export   = lambda url, auth: requests.get(
    url,
    params={"asset_types": "Pipeline"},
    auth=auth,
    timeout=REQUEST_TIMEOUT_SECONDS,
)
is_success     = lambda r: r.status_code == 200
is_zip         = lambda r: "zip" in r.headers.get("Content-Type", "")
unzip_response = lambda r: zipfile.ZipFile(io.BytesIO(r.content))
decode_file    = lambda z, name: z.read(name).decode("utf-8")
save_file      = lambda path, content: Path(path).write_text(content, encoding="utf-8")


# ------------------------------------------------------------
# Main function — fetch, unzip and save pipeline exports
# ------------------------------------------------------------

def fetch_and_save(url, username, password, output_dir):
    """
    Fetches pipeline exports from SnapLogic API.
    fetch → check success → check zip → unzip → decode → save
    """
    auth = HTTPBasicAuth(username, password)

    print(f"🌐 Fetching pipelines from SnapLogic...")
    response = fetch_export(url, auth)

    print(f"   Status:       {response.status_code}")
    print(f"   Content-Type: {response.headers.get('Content-Type')}")

    if not is_success(response):
        print(f"❌ Failed: {response.status_code}")
        return

    if not is_zip(response):
        print("❌ Unexpected format — expected zip")
        return

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    z = unzip_response(response)
    print(f"📦 Files inside zip: {z.namelist()}")

    # safe_extract refuses any member that would land outside
    # output_dir (see core/archive.py) and creates nested folders
    # for the ones that are legitimate.
    for path in safe_extract(z, Path(output_dir)):
        print(f"✅ Saved: {path.name}")

    print(f"\n🫧 Done! Files saved to: {output_dir}")


# ------------------------------------------------------------
# CLI ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    USERNAME   = input("SnapLogic username: ")
    PASSWORD   = getpass.getpass("SnapLogic password: ")
    URL        = "https://emea.snaplogic.com/api/1/rest/public/project/export"
    OUTPUT_DIR = "pipeline_exports/"
    fetch_and_save(URL, USERNAME, PASSWORD, OUTPUT_DIR)