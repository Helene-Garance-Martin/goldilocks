# Goldilocks — before v1.0 ships publicly

> **2026-07-06:** anonymiser block (items 1–8) completed in the Fable 5 session —
> all leak scenarios re-verified fixed, 86 tests green. Item 7's file audit is
> built into `anonymise_pipeline` itself (post-scrub scan + `scan_for_leaks()`),
> and the org list now loads from `sensitive_orgs.py` (`ORG_NAMES`) or the
> `GOLDILOCKS_SENSITIVE_ORGS` env var. `anonymise_pipeline` now also *returns a
> summary dict* — a head start on item 18.

> **2026-07-06 (later):** packaging block (items 9–11) also done — layout is now
> `goldilocks_cli/` (cli.py + commands/ + core/), absolute imports, zero
> sys.path hacks, dist name `goldilocks-curls`, console script `goldilocks`,
> `python -m goldilocks_cli` works, deps include anthropic + pyperclip.
> Sensitive names now live in gitignored `sensitive_orgs.txt` (loader:
> GOLDILOCKS_ORGS_FILE → ./sensitive_orgs.txt → ~/.config/goldilocks/orgs.txt →
> GOLDILOCKS_SENSITIVE_ORGS) — the old .py module would have been BUNDLED INTO
> THE WHEEL on publish. Release ritual: always `rm -rf build dist *.egg-info`
> before building (a stale build/ re-leaked the module once during this session)
> and run the full-bytes wheel scan. Fresh-venv install + end-to-end sieve
> verified from /tmp. 86 tests green.

> **2026-07-06 (evening):** must-fix block complete — items 12–16 done.
> Missing inputs now raise (wrappers + plain sieve report honestly, exit 1);
> a crashing animated sieve restores the terminal via `anim.abort()`;
> `run.py` and `pipeline_processor.py` deleted along with the stale fetch
> hint; `validate_query` uses word-boundary matching (p.created / n.dataset
> pass, `CALL{` blocked), FORBIDDEN_PATTERNS + ALLOWED_OPERATIONS +
> `redact_sensitive_value` retired, token_analyser's always-redacted field
> removed. Every must-fix item on this list is now ticked. 85 tests green,
> verified through the installed CLI.

> **2026-07-13 (Fable session):** items 18 + 24 done together. Core
> sanitiser/anonymiser are silent — facts return as summary dicts,
> presentation + pacing live in the command wrappers (identical user
> output; suite dropped 57s → ~3s). Animated sieve now prints the
> anonymise summary + leak report AFTER the animation, into scrollback.
> NEW: `goldilocks check <file>` (exit 0/1 leak scan) + pre-seed gate in
> seed (scan → confirm, default No, --force to skip). Visualiser's
> prints/input() deliberately deferred to item 20 where its interactive
> selection is being relocated anyway. 128 tests green.

Ordered so each item is one micro-session (or less). IDs reference REVIEW.md.
Rule of thumb: everything in **Must fix** blocks the public release; **Nice to fix** can land in 1.0.x.

## Must fix — anonymiser (the "safe to share" promise)

- [x] **1. `ensure_ascii=False`** in the Phase-2 `json.dumps` (A2). One line. Flip `test_accented_org_names_survive_via_ascii_escaping`. *(~10 min)*
- [x] **2. Run `anonymise_urls` in the main path** over the serialised JSON, next to `anonymise_org_names` (A1). Flip `test_urls_embedded_in_free_text_survive`. *(~20 min)*
- [x] **3. Word boundaries + `re.escape`** in `anonymise_org_names`; sort org list longest-first (A5). Flip `test_substring_matches_corrupt_unrelated_words`. *(~20 min)*
- [x] **4. Add an email regex pass** (→ `user_N@org-N.example`) and extend URL handling to `sftp://` + generic hostname shapes (A3). Add tests as you go. *(1 session)*
- [x] **5. Move ALL org names into the gitignored/runtime config**; scrub the real pipeline name from `GRAPH_SCHEMA` and the real system name from the `safe_query` docstring (A4). *(~30 min, grep for both)*
- [x] **6. Random credential tokens** via the existing (unused) `cred_lookup` instead of truncated md5 (S2). Update the two hashing tests. *(~30 min)*
- [x] **7. Soften the ✅ message** ("known sensitive patterns removed — review before sharing") and add a file-audit pass (grep output for `@`, `http`, `sftp`, GUID shapes — reuse the audit command's idea) (A3). *(1 session)*
- [x] **8. Kill the global-state hazard**: `reset_lookups()` at the top of `anonymise_pipeline` (or an `Anonymiser` class) + only insert orgs on actual match so the summary is honest (G1). Update the two pinned G1 tests. *(1 session)*

## Must fix — packaging (the install has to work)

- [x] **9. Repackage**: `goldilocks/` package with `__init__.py`, absolute imports, delete all six `sys.path.insert`s, entry point `goldilocks.cli:app` (P1). Mechanical but touchy — do it in one sitting with the test suite as the safety net. *(1–2 sessions)*
- [x] **10. Dependencies**: add `anthropic` and `pyperclip` to `[project.dependencies]`; reconcile `name = "goldilocks"` vs the PyPI listing `goldilocks-curls` (P1.5–6). *(~15 min)*
- [x] **11. Verify install**: `pip install .` into a fresh venv, run `goldilocks doctor`, `sanitise`, `sieve --plain` end to end. *(~20 min)*

## Must fix — honest failures

- [x] **12. Raise `FileNotFoundError`** in `sanitise_export` / `anonymise_pipeline` instead of print-and-return (E1). Flip `test_missing_input_*` and `test_plain_sieve_missing_input_still_reports_success`. *(~20 min)*
- [x] **13. `anim.abort()`** in the sieve exception path so a crash restores the terminal (E2). *(~5 min)*
- [x] **14. Delete `commands/run.py`** and the "goldilocks run" hint in fetch (P2). *(~10 min)*
- [x] **15. Delete or fix `src/pipeline_processor.py`** — currently calls `build_pipeline_diagram` with a stale signature (C2). Deleting is fine; nothing imports it. *(~5 min)*

## Must fix — agent guard

- [x] **16. Word-boundary deny-list** in `validate_query` (fixes the `p.created` / `dataset` false positives AND the `CALL{` gap); enforce or delete `FORBIDDEN_PATTERNS` / `ALLOWED_OPERATIONS`; retire `redact_sensitive_value` (S1). Flip the four pinned S1 tests. *(1 session)*

## Journey additions (from later sessions)

- [x] **24. `goldilocks check` + pre-seed leak gate** — done in the same Fable session as 18.
- [x] **24b. GUID anonymisation** — instance_ids replaced with consistent fake UUIDs (links/keys stay resolvable); leak scan now genuinely quiet on clean output, fixing first-real-run alarm fatigue.

## Nice to fix (1.0.x territory)

- [ ] **17. Recurse in `sanitise_settings`** so nested secrets are redacted at the sanitise stage too (A6). Flip `test_nested_secrets_NOT_redacted`. *(~20 min)*
- [x] **18. Move printing/sleeps out of src functions** — emit via `on_progress`/return values, pace in the command layer (C3). Bonus: the test suite drops from ~42 s to ~2 s. *(1–2 sessions)*
- [ ] **19. One CLASSDEFS source**, class names matching snap types (`httpclient`, `sftp_get`, `sftp_put`) so those nodes stop rendering unstyled (C4). *(~20 min)*
- [ ] **20. Delete the dead first `_print_findings`** in audit.py; delete unused `pipelines_typed` in visualiser (or wire the Pydantic layer in); move the `input()` prompt from `generate_diagrams` to the command (C5, C6). *(~30 min)*
- [ ] **21. `timeout=30` on both `requests.get` calls**; move `os.environ["NEO4J_URI"]` inside the try in `ask_goldilocks`; make `renderer.py` locate `puppeteer-config.json` relative to the package (C6). *(~30 min)*
- [ ] **22. Sweep the cosmetics**: `Optional[Callable]` hints, 🐻→🫧 in welcome, one canonical "DAGs to riches" direction, decide on the FUN_TRIGGERS private-handle entry, rename the `input` params (cosmetic). *(~30 min, pleasant Friday task)*
- [ ] **23. Lazy-init the Anthropic client** / move `clean_answer`+`clean_cypher` so pure helpers don't import two SDKs (C6, testability). *(~20 min)*

## Ship gate

- [ ] All "pinned bug" tests flipped to assert the fixed behaviour — `grep -rn "PINS CURRENT BEHAVIOUR" tests/` returns only entries you've consciously decided to keep as documented contracts.
- [ ] Fresh-venv install test (item 11) green.
- [ ] Run your own anonymiser on a real export, then run the item-7 file audit on the result and read it with adversarial eyes for ten minutes. If it's boring, ship.

## Security audit follow-up (2026-07-18)

- [x] **F1 — archive extraction hardened.** `core/archive.py` added; both
      extraction sites now refuse escaping members explicitly.
      **Severity corrected:** the original HIGH was overstated. CPython's
      `extractall()` already sanitises member names, so the `fetch`
      command was NOT exploitable. The genuine escape was the hand-built
      `Path(dest) / member` in `fetch_and_save` (an absolute member
      replaces the destination) — reachable only via that module's own
      `__main__`, not the CLI. Real severity: LOW-MEDIUM, not a release
      blocker. Guard kept for defence in depth and honest refusal.
- [x] **F2 — fetch timeouts.** `REQUEST_TIMEOUT_SECONDS = 30` applied to
      both request sites; `requests.Timeout` / `ConnectionError` now fail
      warm with a next step, no raw detail.
- [x] **F3 — warm failure descriptions.** `core/errors.py` added.
      Driver/SDK exceptions no longer reach the user raw — no host, no
      path, no credential. Raw detail behind `GOLDILOCKS_DEBUG=1`.
      Applied in `agent.ask_goldilocks` and both handlers in `ask`.
- [x] **BONUS — `typer.Exit` swallowed in fetch.** `typer.Exit` subclasses
      `Exception`, so the blanket handler caught deliberate exits and
      re-reported them as "❌ Fetch failed: 1". Now re-raised first.

Suite: 235 → **283 passed, 3 skipped**.
Still open from the audit: F0 (workplace artefacts in docs/ + history
purge before public tag), F4–F7 (cosmetics, fold into item 22).

### F4–F7 (same day, corrected classification)

The original audit grouped these as "all cosmetic, fold into item 22".
On inspection three of the four were not cosmetic:

- [x] **F7 — `config_example.py` deleted.** Not a hostname to genericise:
      nothing referenced the file, and it documented a `config_real.py`
      mechanism superseded by `.env` + `goldilocks.toml`. A new user
      following it would create a file nothing reads. Journey defect.
- [x] **F6 — fun triggers were misrouting.** Substring matching sent
      "how do I install goldilocks-curls?" and "is this sizing just right
      for prod?" to the playful path — and spent a temperature-1.0
      Anthropic call doing it. Now `is_fun_trigger()` fires only when the
      phrase is essentially the whole question (≤2 words of framing).
      "curls" retired (it's the package name); "boucles d'or" kept.
- [x] **F5 — egress notice.** `ask` now states plainly which path it took:
      "Reading your local export — nothing leaves this machine" vs
      "Thinking — sending anonymised graph results to Anthropic". For a
      tool that sieves data so it *can* be shared, saying when it actually
      is matters. Docs equivalent still owed in item 27.
- [x] **F4 — Cypher transparency promoted, not tidied away.** The core
      print became an `on_query` callback (same design language as
      `on_progress`); the command layer renders it. Core is silent,
      the user still sees exactly what was asked of their database.
      `describer`'s only print is inside its `__main__` entry — legitimate,
      left alone.

**Deliberately NOT changed — product decision, for the UX audit:**
`ask` routes to its local file path whenever the question contains
"token", "risk", "wipes", "credential" or "bearer". So "which pipelines
are at risk?" silently skips the graph and reads
`export_anonymised.json`. Same bug class as F6, but the right fix is a
routing design question, not a patch.

Suite: 283 → **299 passed, 3 skipped**.
