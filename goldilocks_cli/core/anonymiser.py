"""
anonymiser.py
-------------
Goldilocks Pipeline Intelligence Platform

Scrubs sensitive data from pipeline exports (.slp / JSON)
before pushing to GitHub or sharing publicly.

Replaces:
  - Organisation / tenant names   → ORG_1, ORG_2 ...
  - URLs (http/https/sftp/ftp)    → https://api.org-1.com/endpoint-1 ...
  - Email addresses               → user_1@org-1.example ...
  - Credential values             → token_9f2a1c4e ... (random per run)
  - GUIDs (instance ids etc.)     → 00000001-0000-4000-8000-000000000001 ...

Design notes (v1.0 rework):
  - No module-level state: every call to anonymise_pipeline()
    builds fresh lookup tables, so runs are reproducible and
    library callers (sieve, tests, v2 curation) share nothing.
  - Org names are matched with escaped, boundary-guarded,
    case-insensitive patterns — "Turbo" no longer becomes
    "TuORG_1" when a short org token is on the list.
  - The serialised JSON is written with ensure_ascii=False so
    accented names ("Hélène") actually match their patterns.
  - Credential tokens are RANDOM (consistent within a run via
    lookup, different across runs) — a truncated md5 lets anyone
    confirm a guessed secret offline; random tokens don't.
  - Org names live in sensitive_orgs.py (gitignored) or the
    GOLDILOCKS_SENSITIVE_ORGS env var — never in this public
    file, which would both disclose the names and make the
    ORG_N mapping reversible from source.
  - Automated scrubbing catches known patterns only, so the
    output is leak-scanned after writing and the summary says
    "review before sharing", not "safe".
"""
import json
import re
import secrets
from pathlib import Path

# ---------------------------------------------------------------------------
# SENSITIVE ORGS — do NOT add names here (this file is public AND packaged).
# Names load from outside the package so they can never end up in a wheel:
#   1. GOLDILOCKS_ORGS_FILE env var → path to a text file, one name per line
#   2. ./sensitive_orgs.txt (gitignored, next to where you run goldilocks)
#   3. ~/.config/goldilocks/orgs.txt
#   4. GOLDILOCKS_SENSITIVE_ORGS env var → comma-separated names
# ---------------------------------------------------------------------------

import os as _os


def _load_sensitive_orgs() -> list[str]:
    orgs: list[str] = []

    candidates = [
        _os.environ.get("GOLDILOCKS_ORGS_FILE"),
        "sensitive_orgs.txt",
        str(Path.home() / ".config" / "goldilocks" / "orgs.txt"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    orgs.append(line)
            break  # first file found wins

    env_orgs = _os.environ.get("GOLDILOCKS_SENSITIVE_ORGS", "")
    if env_orgs:
        orgs += [o.strip() for o in env_orgs.split(",") if o.strip()]

    return orgs


SENSITIVE_ORGS: list[str] = _load_sensitive_orgs()


# ---------------------------------------------------------------------------
# PATTERNS
# ---------------------------------------------------------------------------

# Any URL, any scheme we care about, whole-value OR embedded in free
# text (expressions, error messages, notes). In serialised JSON a
# string's quote is escaped as \" so stopping at " or \ ends cleanly.
URL_PATTERN = re.compile(
    r"(?:https?|sftp|ftps?)://[^\s\"'\\<>]+",
    re.IGNORECASE,
)

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

CREDENTIAL_KEYS = [
    "password", "token", "secret", "api_key", "apikey",
    "client_secret", "client_id", "bearer", "Authorization",
    "access_token", "refresh_token", "private_key",
]

# GUID / long-hex shapes for the post-scrub leak scan
GUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)

# ---------------------------------------------------------------------------
# LAMBDA FUNCTIONS
# ---------------------------------------------------------------------------

make_org_name   = lambda n: f"ORG_{n}"
make_fake_url   = lambda n: f"https://api.org-{n}.com/endpoint-{n}"
make_fake_email = lambda n: f"user_{n}@org-{n}.example"

is_credential_key = lambda key: any(
    cred.lower() in str(key).lower() for cred in CREDENTIAL_KEYS
)

is_fake_url   = lambda url: url.startswith("https://api.org-")
is_fake_email = lambda addr: bool(re.fullmatch(r"user_\d+@org-\d+\.example", addr))

# fake GUIDs are valid UUID-shaped but visibly synthetic: counter in the
# first and last groups, fixed 0000-4000-8000 core (v4-plausible shape)
make_fake_guid = lambda n: f"{n:08x}-0000-4000-8000-{n:012x}"
is_fake_guid   = lambda g: bool(re.fullmatch(r"[0-9a-f]{8}-0000-4000-8000-[0-9a-f]{12}", g))


# ---------------------------------------------------------------------------
# LOOKUPS — one fresh set per anonymise_pipeline() call
# ---------------------------------------------------------------------------

def new_lookups() -> dict:
    """Fresh replacement tables — nothing survives between runs."""
    return {"orgs": {}, "urls": {}, "emails": {}, "creds": {}, "guids": {}}


# ---------------------------------------------------------------------------
# CORE FUNCTIONS — each takes its lookup explicitly
# ---------------------------------------------------------------------------

def anonymise_org_names(text: str, org_lookup: dict, orgs: list[str] | None = None) -> str:
    """Replace known org names with ORG_1, ORG_2 ...

    Patterns are re.escape()d (dots in "first.last" no longer match
    any character), boundary-guarded (a 3-letter org token no longer
    mangles unrelated words), matched case-insensitively, and applied
    longest-first (so "acme-group-intl" wins over "acme-group").
    ORG_N is assigned on first *match*, so the summary counts are
    honest and the numbering follows the data, not the list order.
    """
    if orgs is None:
        orgs = SENSITIVE_ORGS

    for org in sorted(orgs, key=len, reverse=True):
        if not org:
            continue
        pattern = re.compile(
            rf"(?<!\w){re.escape(org)}(?!\w)",
            re.IGNORECASE,
        )

        def replace(match, _org=org):
            if _org not in org_lookup:
                org_lookup[_org] = make_org_name(len(org_lookup) + 1)
            return org_lookup[_org]

        text = pattern.sub(replace, text)
    return text


def anonymise_urls(text: str, url_lookup: dict) -> str:
    """Replace every URL — whole-value or embedded — with a fake one.

    One mechanism for both cases keeps the lookup consistent: the
    same real URL always becomes the same fake URL within a run.
    Already-faked URLs are left alone so the pass is idempotent.
    """
    def replace(match):
        url = match.group(0)
        if is_fake_url(url):
            return url
        if url not in url_lookup:
            url_lookup[url] = make_fake_url(len(url_lookup) + 1)
        return url_lookup[url]

    return URL_PATTERN.sub(replace, text)


def anonymise_emails(text: str, email_lookup: dict) -> str:
    """Replace every email address with a fake, consistent one."""
    def replace(match):
        addr = match.group(0)
        if is_fake_email(addr):
            return addr
        if addr not in email_lookup:
            email_lookup[addr] = make_fake_email(len(email_lookup) + 1)
        return email_lookup[addr]

    return EMAIL_PATTERN.sub(replace, text)


def anonymise_guids(text: str, guid_lookup: dict) -> str:
    """Replace every GUID with a fake, consistent one.

    SnapLogic instance_ids are GUIDs and appear both as JSON keys
    (snap_map) and as values (link src_id/dst_id, pipeline ids) —
    the text pass replaces them consistently, so links still resolve
    and the seeded graph keeps its integrity, just with fictional
    identifiers untraceable to the source tenant.
    """
    def replace(match):
        guid = match.group(0)
        if is_fake_guid(guid):
            return guid
        key = guid.lower()
        if key not in guid_lookup:
            guid_lookup[key] = make_fake_guid(len(guid_lookup) + 1)
        return guid_lookup[key]

    return GUID_PATTERN.sub(replace, text)


def anonymise_credentials(obj, cred_lookup: dict):
    """Walk the pipeline JSON recursively and replace credential values.

    Tokens are random (secrets.token_hex) but consistent within the
    run via the lookup — the same secret maps to the same token in
    one file, and to a different token tomorrow. Unlike a truncated
    md5, a random token cannot be used to confirm a guessed secret.
    """
    if isinstance(obj, dict):
        return {
            k: _fake_cred(str(v), cred_lookup) if is_credential_key(k)
            else anonymise_credentials(v, cred_lookup)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [anonymise_credentials(item, cred_lookup) for item in obj]
    else:
        return obj


def _fake_cred(value: str, cred_lookup: dict) -> str:
    if value not in cred_lookup:
        cred_lookup[value] = "token_" + secrets.token_hex(4)
    return cred_lookup[value]


def anonymise_text(text: str, lookups: dict, orgs: list[str] | None = None) -> str:
    """The full text pass, in leak-safe order:
    URLs first (org names and GUIDs inside URLs vanish with the URL),
    then emails, then GUIDs, then org names."""
    text = anonymise_urls(text, lookups["urls"])
    text = anonymise_emails(text, lookups["emails"])
    text = anonymise_guids(text, lookups["guids"])
    text = anonymise_org_names(text, lookups["orgs"], orgs)
    return text


# ---------------------------------------------------------------------------
# POST-SCRUB LEAK SCAN
# ---------------------------------------------------------------------------

def scan_for_leaks(text: str) -> dict:
    """Scan anonymised output for shapes that should not have survived.

    Automated scrubbing only catches known patterns, so this is the
    honest second look: real URLs, real emails and GUIDs remaining
    after the pass. Returns {kind: [samples]} — empty dict = quiet.
    """
    findings: dict[str, list[str]] = {}

    urls = [u for u in URL_PATTERN.findall(text) if not is_fake_url(u)]
    if urls:
        findings["urls"] = sorted(set(urls))[:10]

    emails = [e for e in EMAIL_PATTERN.findall(text) if not is_fake_email(e)]
    if emails:
        findings["emails"] = sorted(set(emails))[:10]

    guids = [g for g in GUID_PATTERN.findall(text) if not is_fake_guid(g)]
    if guids:
        findings["guids"] = sorted(set(guids))[:10]

    return findings


def print_leak_report(findings: dict) -> None:
    if not findings:
        print("🔍  Post-scrub audit: no residual URLs, emails or GUIDs found.")
        return

    print("⚠️   Post-scrub audit found shapes worth a look:")
    for kind, samples in findings.items():
        print(f"    {kind}: {len(samples)} distinct (showing up to 10)")
        for sample in samples:
            print(f"      · {sample}")
    print("    Review these before sharing the file.")


# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------

def anonymise_pipeline(
    input_path: str,
    output_path: str,
    on_progress: callable = None,
) -> dict:
    """Main function — reads, scrubs, writes, then leak-scans the result.

    Args:
        input_path:  Path to the sanitised pipeline JSON.
        output_path: Path to write the anonymised output.
        on_progress: Optional callback(phase, current, total, message).
                     Fires twice — once after the credential walk,
                     once after the text pass — matching the two
                     actual work phases in the code.

    Returns:
        A summary dict — replacement counts, leak findings and the
        output path.

    Raises:
        FileNotFoundError: when the input file does not exist.
    """

    input_file  = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(f"input file not found: {input_path}")

    lookups = new_lookups()

    try:
        pipeline_json = json.loads(input_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Not valid JSON — fall back to text scrubbing. Without JSON
        # keys, credential values cannot be detected; the command
        # layer warns the user (summary carries fallback=True).
        raw = input_file.read_text(encoding="utf-8")
        raw = anonymise_text(raw, lookups)
        output_file.write_text(raw, encoding="utf-8")
        findings = scan_for_leaks(raw)
        return _summary(lookups, findings, output_path, fallback=True)

    if on_progress:
        on_progress("anonymising", 0, 2, "starting")

    # ── Phase 1: credential values (recursive walk over keys) ────────
    pipeline_json = anonymise_credentials(pipeline_json, lookups["creds"])
    if on_progress:
        on_progress("anonymising", 1, 2, "credentials")

    # ── Phase 2: URLs, emails, org names (text pass) ─────────────────
    # ensure_ascii=False so accented names ("Hélène") appear as
    # themselves in the text, not as \u escapes the patterns miss.
    clean = json.dumps(pipeline_json, indent=2, ensure_ascii=False)
    clean = anonymise_text(clean, lookups)
    if on_progress:
        on_progress("anonymising", 2, 2, "organisations, URLs & emails")

    output_file.write_text(clean, encoding="utf-8")

    findings = scan_for_leaks(clean)
    return _summary(lookups, findings, output_path, fallback=False)


def _summary(lookups: dict, findings: dict, output_path: str, fallback: bool) -> dict:
    return {
        "orgs":        len(lookups["orgs"]),
        "urls":        len(lookups["urls"]),
        "emails":      len(lookups["emails"]),
        "credentials": len(lookups["creds"]),
        "guids":       len(lookups["guids"]),
        "leak_findings": findings,
        "output": str(output_path),
        "fallback": fallback,
    }
