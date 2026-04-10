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

Usage:
  python anonymiser.py --input my_pipeline.json --output clean_pipeline.json
"""

import json
import re
import argparse
import hashlib
from pathlib import Path


# ---------------------------------------------------------------------------
# CONFIGURATION — add your real values here (this file is .gitignored!)
# ---------------------------------------------------------------------------

SENSITIVE_ORGS = [
    "RBO",
    "ROH",
    "RoyalBalletOpera",
    "royal-ballet",
    "royal_ballet",
]

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
# e.g. "RBO" always becomes "ORG_1" throughout the whole file
# ---------------------------------------------------------------------------

org_lookup = {}
url_lookup = {}
cred_lookup = {}


# ---------------------------------------------------------------------------
# LAMBDA FUNCTIONS — small, inline transformation rules
# ---------------------------------------------------------------------------

# Lambda 1: generate a consistent org placeholder
# A lambda is a tiny one-line function — perfect for simple transformations
# Instead of: def make_org_name(n): return f"ORG_{n}"
# We write:
make_org_name = lambda n: f"ORG_{n}"

# Lambda 2: generate a fake but realistic URL
make_fake_url = lambda n: f"https://api.org-{n}.com/endpoint-{n}"

# Lambda 3: generate a fake credential using a short hash for realism
# hashlib gives us a consistent fake value based on the original
make_fake_cred = lambda val: "token_" + hashlib.md5(val.encode()).hexdigest()[:8]

# Lambda 4: check if a dictionary key looks like a credential field
is_credential_key = lambda key: any(
    cred.lower() in str(key).lower() for cred in CREDENTIAL_KEYS
)

# Lambda 5: check if a string looks like a URL
is_url = lambda val: isinstance(val, str) and val.startswith("http")


# ---------------------------------------------------------------------------
# CORE FUNCTIONS
# ---------------------------------------------------------------------------

def anonymise_org_names(text: str) -> str:
    """Replace known org names with ORG_1, ORG_2 etc."""
    for org in SENSITIVE_ORGS:
        if org not in org_lookup:
            # Give each new org the next number in sequence
            org_lookup[org] = make_org_name(len(org_lookup) + 1)
        # re.IGNORECASE so "rbo" and "RBO" both get caught
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
    """
    Walk through the pipeline JSON recursively.
    When a key looks like a credential, replace its value.
    This is why we use recursion — pipeline JSON can be deeply nested.
    """
    if isinstance(obj, dict):
        # Dictionary comprehension + lambda — very Pythonic!
        # For each key-value pair: if the key looks like a credential,
        # replace the value; otherwise keep it (but still recurse into it)
        return {
            k: make_fake_cred(str(v)) if is_credential_key(k)
            else anonymise_credentials(v)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        # Recurse into lists too
        return [anonymise_credentials(item) for item in obj]
    elif is_url(obj):
        # Catch any URL values not already caught by anonymise_urls
        if obj not in url_lookup:
            url_lookup[obj] = make_fake_url(len(url_lookup) + 1)
        return url_lookup[obj]
    else:
        return obj


def anonymise_pipeline(input_path: str, output_path: str) -> None:
    """Main function — reads, scrubs, and writes the clean pipeline file."""

    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        print(f"❌  File not found: {input_path}")
        return

    print(f"🔍  Reading: {input_path}")
    raw = input_file.read_text(encoding="utf-8")

    # Step 1 — scrub org names from raw text first
    print("🏢  Anonymising organisation names...")
    raw = anonymise_org_names(raw)

    # Step 2 — scrub URLs from raw text
    print("🌐  Anonymising URLs and endpoints...")
    raw = anonymise_urls(raw)

    # Step 3 — parse JSON and scrub credential values
    print("🔑  Anonymising credentials and tokens...")
    try:
        pipeline_json = json.loads(raw)
        pipeline_json = anonymise_credentials(pipeline_json)
        clean = json.dumps(pipeline_json, indent=2)
    except json.JSONDecodeError:
        # If it's not valid JSON, just use the text-scrubbed version
        print("⚠️   Not valid JSON — text scrubbing only.")
        clean = raw

    # Step 4 — write output
    output_file.write_text(clean, encoding="utf-8")
    print(f"✅  Clean file written to: {output_path}")
    print(f"\n📊  Summary:")
    print(f"    Orgs replaced:   {len(org_lookup)}")
    print(f"    URLs replaced:   {len(url_lookup)}")
    print(f"    (Credentials replaced inline throughout)")


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="🐻 Goldilocks Anonymiser — scrub sensitive data from pipeline exports"
    )
    parser.add_argument("--input",  required=True, help="Path to raw pipeline JSON file")
    parser.add_argument("--output", required=True, help="Path to write clean output file")
    args = parser.parse_args()

    anonymise_pipeline(args.input, args.output)
