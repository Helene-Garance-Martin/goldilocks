"""
anonymiser.py
-------------
Goldilocks Pipeline Intelligence Platform

Scrubs sensitive data from SnapLogic pipeline exports (.slp / JSON)
before pushing to GitHub or sharing publicly.

Replaces:
  - Organisation / tenant names  → ORG_1, ORG_2 ...
  - URLs and endpoints            → https://api.org-1.com/endpoint-1 ...
  - Credentials / tokens          → token_abc123, secret_xyz789 ...
"""
import time
import json
import re
import hashlib
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# SENSITIVE ORGS — add org names here (safe to commit)
# Colleague names live in sensitive_orgs.py (gitignored)
# ---------------------------------------------------------------------------

SENSITIVE_ORGS = [
    "RBO",
    "ROH",
    "RoyalBalletOpera",
    "royal-ballet",
    "royal_ballet",
    "helene.martin",
    "Helene.Martin",
    "Helene Martin",
    "Hélène Martin",
]

# Load colleague names from gitignored file
try:
    from sensitive_orgs import COLLEAGUE_NAMES
    SENSITIVE_ORGS += COLLEAGUE_NAMES
except ImportError:
    pass

SENSITIVE_URL_PATTERNS = [
    r"https?://[a-zA-Z0-9._-]+\.snaplogic\.com[^\s\"']*",
    r"https?://[a-zA-Z0-9._-]+\.sharepoint\.com[^\s\"']*",
    r"https?://[a-zA-Z0-9._-]+\.azure[^\s\"']*",
    r"https?://[a-zA-Z0-9._-]+\.office365[^\s\"']*",
]

CREDENTIAL_KEYS = [
    "password", "token", "secret", "api_key", "apikey",
    "client_secret", "client_id", "bearer", "Authorization",
    "access_token", "refresh_token", "private_key",
]

# ---------------------------------------------------------------------------
# LOOKUP TABLES — built at runtime so replacements are consistent
# ---------------------------------------------------------------------------

org_lookup = {}
url_lookup = {}
cred_lookup = {}

# ---------------------------------------------------------------------------
# LAMBDA FUNCTIONS
# ---------------------------------------------------------------------------

make_org_name  = lambda n: f"ORG_{n}"
make_fake_url  = lambda n: f"https://api.org-{n}.com/endpoint-{n}"
make_fake_cred = lambda val: "token_" + hashlib.md5(val.encode()).hexdigest()[:8]

is_credential_key = lambda key: any(
    cred.lower() in str(key).lower() for cred in CREDENTIAL_KEYS
)
is_url = lambda val: isinstance(val, str) and val.startswith("http")


# ---------------------------------------------------------------------------
# CORE FUNCTIONS
# ---------------------------------------------------------------------------

def anonymise_org_names(text: str) -> str:
    """Replace known org names with ORG_1, ORG_2 etc."""
    for org in SENSITIVE_ORGS:
        if org not in org_lookup:
            org_lookup[org] = make_org_name(len(org_lookup) + 1)
        text = re.sub(org, org_lookup[org], text, flags=re.IGNORECASE)
    return text


def anonymise_urls(text: str) -> str:
    """Replace sensitive URLs with fake but realistic ones."""
    for pattern in SENSITIVE_URL_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            if match not in url_lookup:
                url_lookup[match] = make_fake_url(len(url_lookup) + 1)
            text = text.replace(match, url_lookup[match])
    return text


def anonymise_credentials(obj):
    """Walk through pipeline JSON recursively and replace credential values."""
    if isinstance(obj, dict):
        return {
            k: make_fake_cred(str(v)) if is_credential_key(k)
            else anonymise_credentials(v)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [anonymise_credentials(item) for item in obj]
    elif is_url(obj):
        if obj not in url_lookup:
            url_lookup[obj] = make_fake_url(len(url_lookup) + 1)
        return url_lookup[obj]
    else:
        return obj


def anonymise_pipeline(input_path: str, output_path: str) -> None:
    """Main function — reads, scrubs, and writes the clean pipeline file."""

    input_file  = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        print(f"❌  File not found: {input_path}")
        return

    print(f"🔍  Reading: {input_path}")
    time.sleep(0.2)

    try:
        pipeline_json = json.loads(input_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("⚠️   Not valid JSON — falling back to text scrubbing.")
        raw = input_file.read_text(encoding="utf-8")
        raw = anonymise_org_names(raw)
        raw = anonymise_urls(raw)
        output_file.write_text(raw, encoding="utf-8")
        return

    print("🏢  Anonymising organisation names...")
    time.sleep(0.25)
    print("🌐  Anonymising URLs and endpoints...")
    time.sleep(0.25)
    print("🔑  Anonymising credentials and tokens...")
    time.sleep(0.25)

    pipeline_json = anonymise_credentials(pipeline_json)
    clean = json.dumps(pipeline_json, indent=2)
    clean = anonymise_org_names(clean)
    output_file.write_text(clean, encoding="utf-8")

    print(f"✅  Clean file written to: {output_path}")
    time.sleep(0.2)
    print(f"\n📊  Summary:")
    time.sleep(0.15)
    print(f"    Orgs replaced:   {len(org_lookup)}")
    time.sleep(0.1)
    print(f"    URLs replaced:   {len(url_lookup)}")
    time.sleep(0.1)
    print(f"    (Credentials replaced inline throughout)")
...
