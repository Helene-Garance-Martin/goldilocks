# tests/test_anonymiser.py
# ============================================================
# 🫧 GOLDILOCKS — anonymiser tests (post-rework)
# ============================================================
# The pre-rework suite PINNED several leaks (findings A1–A5, G1,
# S2). Those are now fixed, so the same scenarios assert the safe
# behaviour and act as regression guards. Tests still marked
# "PINS CURRENT BEHAVIOUR" document remaining conscious limits.
#
# All tests use the `clean_anonymiser` fixture, which pins
# SENSITIVE_ORGS to synthetic values (never the gitignored real
# list). No network, no Neo4j, no LLM calls.
# ============================================================

import json
import re

from conftest import TEST_ORG, TEST_ORG_ACCENTED


def run_anonymise(anonymiser, export_file, tmp_path, on_progress=None, name="anon.json"):
    out = tmp_path / name
    summary = anonymiser.anonymise_pipeline(str(export_file), str(out), on_progress=on_progress)
    return out, out.read_text(encoding="utf-8") if out.exists() else "", summary


def sanitised_file(export_file, tmp_path):
    """Run the real sanitiser first — mirrors the sieve chain."""
    from goldilocks_cli.core.sanitiser import sanitise_export
    clean = tmp_path / "clean.json"
    sanitise_export(str(export_file), str(clean))
    return clean


# ------------------------------------------------------------
# Org replacement
# ------------------------------------------------------------

def test_org_replaced_case_insensitively_and_consistently(clean_anonymiser, export_file, tmp_path):
    clean = sanitised_file(export_file, tmp_path)
    _, text, summary = run_anonymise(clean_anonymiser, clean, tmp_path)
    # "Acme", "acme", "aCmE" and "acme-corp" all appear in the fixture —
    # none may survive, and each org collapses to a single token
    assert "acme" not in text.lower()
    assert "ORG_1" in text
    assert summary["orgs"] >= 2  # Acme + acme-corp actually matched


def test_org_lookup_counts_only_matched_orgs(clean_anonymiser, tmp_path):
    # REGRESSION GUARD (was G1): the summary used to report
    # len(SENSITIVE_ORGS) regardless of matches. Now a file with no
    # sensitive content reports zero replacements.
    f = tmp_path / "plain.json"
    f.write_text(json.dumps({"name": "nothing sensitive here"}), encoding="utf-8")
    _, _, summary = run_anonymise(clean_anonymiser, f, tmp_path)
    assert summary["orgs"] == 0


def test_substring_no_longer_corrupts_unrelated_words(clean_anonymiser, tmp_path):
    # REGRESSION GUARD (was A5): "Acmeister" must survive intact —
    # boundary-guarded patterns no longer mangle words that merely
    # contain an org token.
    f = tmp_path / "words.json"
    f.write_text(json.dumps({"name": "Acmeister Deluxe ships Acme parts"}), encoding="utf-8")
    _, text, _ = run_anonymise(clean_anonymiser, f, tmp_path)
    assert "Acmeister Deluxe" in text          # untouched
    assert "Acme parts" not in text            # the real org still caught
    assert "ORG_1 parts" in text


def test_org_names_are_escaped_not_regex(clean_anonymiser, tmp_path):
    # REGRESSION GUARD (was A5): dots in configured names no longer
    # match any character.
    f = tmp_path / "dots.json"
    f.write_text(json.dumps({"a": "acmeXcorp stays", "b": "acme-corp goes"}), encoding="utf-8")
    _, text, _ = run_anonymise(clean_anonymiser, f, tmp_path)
    assert "acmeXcorp stays" in text
    assert "acme-corp" not in text


def test_longest_org_wins_over_its_substring(clean_anonymiser, monkeypatch, tmp_path):
    from goldilocks_cli.core import anonymiser
    monkeypatch.setattr(anonymiser, "SENSITIVE_ORGS", ["Acme", "Acme Holdings"])
    f = tmp_path / "long.json"
    f.write_text(json.dumps({"name": "Acme Holdings annual report"}), encoding="utf-8")
    _, text, _ = run_anonymise(anonymiser, f, tmp_path)
    # the longer name is replaced as one unit, not "ORG_x Holdings"
    assert "Holdings" not in text


def test_accented_org_names_are_now_replaced(clean_anonymiser, export_file, tmp_path):
    # REGRESSION GUARD (was A2, critical): ensure_ascii=False means
    # "Zoé Fictional" appears as itself in the serialised text and the
    # pattern matches. Neither the readable nor the escaped form may
    # survive.
    clean = sanitised_file(export_file, tmp_path)
    _, text, _ = run_anonymise(clean_anonymiser, clean, tmp_path)
    assert TEST_ORG_ACCENTED not in text
    assert "Zo\\u00e9" not in text


# ------------------------------------------------------------
# URL replacement
# ------------------------------------------------------------

def test_whole_string_url_values_replaced(clean_anonymiser, export_file, tmp_path):
    clean = sanitised_file(export_file, tmp_path)
    _, text, _ = run_anonymise(clean_anonymiser, clean, tmp_path)
    data = json.loads(text)
    endpoint = data["entries"][0]["snap_map"]["snap-active"]["property_map"]["settings"]["endpoint"]
    assert endpoint.startswith("https://api.org-")


def test_urls_embedded_in_free_text_replaced(clean_anonymiser, export_file, tmp_path):
    # REGRESSION GUARD (was A1, critical): URLs inside sentences —
    # error messages, expressions — are scrubbed in the main path,
    # including hostnames and tenant/GUID paths.
    clean = sanitised_file(export_file, tmp_path)
    _, text, _ = run_anonymise(clean_anonymiser, clean, tmp_path)
    assert "sharepoint.com" not in text
    assert "snaplogic.com" not in text
    assert "tenant-guid-123" not in text


def test_same_url_gets_same_fake_everywhere(clean_anonymiser, export_file, tmp_path):
    # the fixture contains the same snaplogic feed URL twice (once as
    # a whole value, once embedded) — both must map to one fake URL
    clean = sanitised_file(export_file, tmp_path)
    _, text, summary = run_anonymise(clean_anonymiser, clean, tmp_path)
    data = json.loads(text)
    settings = data["entries"][0]["snap_map"]["snap-active"]["property_map"]["settings"]
    endpoint = settings["endpoint"]
    assert endpoint in settings["expression"]["value"]


def test_sftp_urls_replaced(clean_anonymiser, tmp_path):
    # REGRESSION GUARD (was A3): non-http schemes are now covered.
    f = tmp_path / "sftp.json"
    f.write_text(
        json.dumps({"host": "sftp://transfer.internal.example.net/outbound"}),
        encoding="utf-8",
    )
    _, text, _ = run_anonymise(clean_anonymiser, f, tmp_path)
    assert "transfer.internal.example.net" not in text
    assert "https://api.org-" in text


# ------------------------------------------------------------
# Email replacement
# ------------------------------------------------------------

def test_free_text_emails_replaced(clean_anonymiser, export_file, tmp_path):
    # REGRESSION GUARD (was A3, critical): emails of people not on
    # any list are scrubbed by shape, consistently.
    clean = sanitised_file(export_file, tmp_path)
    _, text, summary = run_anonymise(clean_anonymiser, clean, tmp_path)
    assert "zoe@" not in text
    assert "@org-" in text  # a fake email took its place
    assert summary["emails"] >= 1


def test_same_email_gets_same_fake(clean_anonymiser, tmp_path):
    f = tmp_path / "mail.json"
    f.write_text(
        json.dumps({"a": "contact pat@example-co.org", "b": "escalate to pat@example-co.org"}),
        encoding="utf-8",
    )
    _, text, _ = run_anonymise(clean_anonymiser, f, tmp_path)
    fakes = re.findall(r"user_\d+@org-\d+\.example", text)
    assert len(fakes) == 2 and len(set(fakes)) == 1


# ------------------------------------------------------------
# Credential replacement
# ------------------------------------------------------------

def test_credential_values_replaced_with_random_tokens(clean_anonymiser, tmp_path):
    # REGRESSION GUARD (was S2): tokens are token_<8 hex chars> and no
    # longer a truncated md5 of the secret, so output can't be used to
    # confirm a guessed secret offline.
    import hashlib
    f = tmp_path / "cred.json"
    f.write_text(json.dumps({"api_key": "SUPERSECRET"}), encoding="utf-8")
    _, text, _ = run_anonymise(clean_anonymiser, f, tmp_path)
    value = json.loads(text)["api_key"]
    assert re.fullmatch(r"token_[0-9a-f]{8}", value)
    assert "SUPERSECRET" not in text
    assert value != "token_" + hashlib.md5(b"SUPERSECRET").hexdigest()[:8]


def test_same_secret_same_token_within_run_different_across_runs(clean_anonymiser, tmp_path):
    f = tmp_path / "cred2.json"
    f.write_text(
        json.dumps({"a": {"password": "pw"}, "b": {"password": "pw"}}),
        encoding="utf-8",
    )
    _, text1, _ = run_anonymise(clean_anonymiser, f, tmp_path, name="r1.json")
    d1 = json.loads(text1)
    assert d1["a"]["password"] == d1["b"]["password"]      # consistent within run

    _, text2, _ = run_anonymise(clean_anonymiser, f, tmp_path, name="r2.json")
    d2 = json.loads(text2)
    assert d2["a"]["password"] != d1["a"]["password"]      # random across runs


def test_credential_key_matching_is_substring_based(clean_anonymiser, tmp_path):
    # PINS CURRENT BEHAVIOUR: keys like "tokenizer" are still treated
    # as credentials (substring match on the key). Erring on the side
    # of over-scrubbing is a defensible default for a "review before
    # sharing" tool — this test documents it as a choice, not a bug.
    f = tmp_path / "cred3.json"
    f.write_text(json.dumps({"tokenizer": "bert"}), encoding="utf-8")
    _, text, _ = run_anonymise(clean_anonymiser, f, tmp_path)
    assert json.loads(text)["tokenizer"].startswith("token_")


def test_nested_credentials_caught_by_recursive_walk(clean_anonymiser, export_file, tmp_path):
    clean = sanitised_file(export_file, tmp_path)
    _, text, _ = run_anonymise(clean_anonymiser, clean, tmp_path)
    assert "NESTED-SECRET-999" not in text


# ------------------------------------------------------------
# JSON-decode fallback path
# ------------------------------------------------------------

def test_fallback_scrubs_orgs_urls_and_emails_in_raw_text(clean_anonymiser, tmp_path, capsys):
    raw = tmp_path / "notjson.txt"
    raw.write_text(
        f"log from {TEST_ORG} at https://x.snaplogic.com/feed/1 by kim@real-place.example {{",
        encoding="utf-8",
    )
    _, text, summary = run_anonymise(clean_anonymiser, raw, tmp_path)
    assert "falling back to text scrubbing" in capsys.readouterr().out
    assert TEST_ORG not in text
    assert "snaplogic.com" not in text
    assert "kim@real-place.example" not in text
    assert summary["orgs"] == 1


def test_fallback_cannot_detect_credentials_and_skips_callbacks(
    clean_anonymiser, tmp_path, progress_recorder
):
    # PINS CURRENT BEHAVIOUR: without JSON keys there is nothing to
    # anchor credential detection to, so bare secret values survive
    # the fallback path — the fallback now says so explicitly.
    raw = tmp_path / "notjson.txt"
    raw.write_text('password: "hunter2"  {broken json', encoding="utf-8")
    _, text, _ = run_anonymise(clean_anonymiser, raw, tmp_path, on_progress=progress_recorder)
    assert "hunter2" in text
    assert progress_recorder.calls == []


# ------------------------------------------------------------
# Callback emission (main path)
# ------------------------------------------------------------

def test_callback_fires_for_both_phases(clean_anonymiser, export_file, tmp_path, progress_recorder):
    clean = sanitised_file(export_file, tmp_path)
    run_anonymise(clean_anonymiser, clean, tmp_path, on_progress=progress_recorder)
    assert progress_recorder.calls == [
        ("anonymising", 0, 2, "starting"),
        ("anonymising", 1, 2, "credentials"),
        ("anonymising", 2, 2, "organisations, URLs & emails"),
    ]


# ------------------------------------------------------------
# Per-call state — G1 fixed
# ------------------------------------------------------------

def test_runs_are_independent_and_reproducible(clean_anonymiser, export_file, tmp_path):
    # REGRESSION GUARD (was G1): lookups are per-call, so processing a
    # different file in between no longer shifts ORG/URL numbering,
    # and summary counts never accumulate.
    clean = sanitised_file(export_file, tmp_path)

    _, first, s1 = run_anonymise(clean_anonymiser, clean, tmp_path, name="a1.json")

    # process an unrelated file in between — this used to pollute the
    # shared lookups and renumber everything in the next run
    other = tmp_path / "other.json"
    other.write_text(
        json.dumps({"u": "https://elsewhere.snaplogic.com/feed", "e": "x@y-z.example"}),
        encoding="utf-8",
    )
    run_anonymise(clean_anonymiser, other, tmp_path, name="b.json")

    _, second, s2 = run_anonymise(clean_anonymiser, clean, tmp_path, name="a2.json")

    # credential tokens are random per run, so compare with them masked
    mask = lambda t: re.sub(r"token_[0-9a-f]{8}", "token_X", t)
    assert mask(first) == mask(second)
    assert (s1["orgs"], s1["urls"], s1["emails"]) == (s2["orgs"], s2["urls"], s2["emails"])


def test_summary_dict_returned(clean_anonymiser, export_file, tmp_path):
    clean = sanitised_file(export_file, tmp_path)
    _, _, summary = run_anonymise(clean_anonymiser, clean, tmp_path)
    assert set(summary) == {"orgs", "urls", "emails", "credentials", "leak_findings", "output"}
    assert summary["credentials"] >= 2   # password + nested client_secret (api_key was
                                         # already redacted by the sanitiser upstream)


# ------------------------------------------------------------
# Post-scrub leak scan
# ------------------------------------------------------------

def test_leak_scan_is_quiet_on_clean_output(clean_anonymiser, export_file, tmp_path):
    clean = sanitised_file(export_file, tmp_path)
    _, _, summary = run_anonymise(clean_anonymiser, clean, tmp_path)
    assert summary["leak_findings"] == {}


def test_leak_scan_flags_residual_shapes(clean_anonymiser):
    from goldilocks_cli.core.anonymiser import scan_for_leaks
    residue = (
        "left over: https://oops.example.com/x and pat@missed.example "
        "and 12345678-abcd-abcd-abcd-1234567890ab"
    )
    findings = scan_for_leaks(residue)
    assert set(findings) == {"urls", "emails", "guids"}


def test_leak_scan_ignores_its_own_fakes(clean_anonymiser):
    from goldilocks_cli.core.anonymiser import scan_for_leaks
    fakes = "https://api.org-1.com/endpoint-1 and user_1@org-1.example"
    assert scan_for_leaks(fakes) == {}


# ------------------------------------------------------------
# Failure mode
# ------------------------------------------------------------

def test_missing_input_raises(clean_anonymiser, tmp_path):
    # REGRESSION GUARD (was E1): missing input raises FileNotFoundError.
    import pytest
    out = tmp_path / "anon.json"
    with pytest.raises(FileNotFoundError):
        clean_anonymiser.anonymise_pipeline(str(tmp_path / "missing.json"), str(out))
    assert not out.exists()
