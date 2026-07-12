# Goldilocks — pre-v1.0 senior engineering review

**Scope:** full codebase as uploaded (pie.py, commands/, src/, pyproject.toml).
**Method:** every file read before any finding was written; anonymiser leak claims verified empirically against a synthetic export (the same fixture now lives in `tests/conftest.py`).
**Handling note:** the uploaded zip included `src/sensitive_orgs.py` despite your exclusion plan. Its contents are not reproduced anywhere in these documents, and the tests pin `SENSITIVE_ORGS` to synthetic values so they never touch it.

**Severity legend:** *critical* = leaks, data loss, or crashes on normal input · *important* = wrong behaviour or release-embarrassing · *minor* = quality/consistency · *cosmetic* = polish.

---

## The headline

The architecture (src functions / commands wrappers / pie registration), the graph model, and the agent's layered safety are all sound. The two things standing between you and "safe to share publicly" are: **the anonymiser scrubs only what it already knows about** (findings A1–A4), and **the package as declared cannot run once pip-installed** (P1). Everything else is fixable in micro-sessions.

---

## CRITICAL

### A1 — URLs embedded in free text are never scrubbed in the main path

`SENSITIVE_URL_PATTERNS` are only applied in the JSON-decode *fallback* branch of `anonymise_pipeline`. In the normal path, a URL is caught only when a string value **is** a URL (`is_url` = `startswith("http")`, checked during the credential walk). Any URL embedded inside a sentence — mapper expressions, error messages, notes — survives, minus whatever org substrings happen to be replaced.

**Verified:** with a snap whose `err_msg` contained `https://acme.sharepoint.com/sites/HR?tid=tenant-guid-123` and whose expression contained a snaplogic.com feed URL, the anonymised output retained `sharepoint.com`, `snaplogic.com`, and the tenant GUID.

**Leak path:** SnapLogic error blocks and expressions routinely contain full endpoint URLs with org slugs, tenant IDs, and feed paths. These land verbatim in "safe to share" output.

**Fix:** in the main path, after `json.dumps`, run `anonymise_urls(clean)` alongside `anonymise_org_names(clean)`. Also extend `is_url` (or add patterns) for `sftp://`, `ftp://`, and bare internal hostnames — an `sftp://diese-style-host.internal.example` value survived entirely in my test because it doesn't start with `http`.

### A2 — accented org names can never match (`ensure_ascii` escaping)

Phase 2 serialises with `json.dumps(pipeline_json, indent=2)` — default `ensure_ascii=True` — so `é` becomes `\u00e9` in the text the regex runs over. The literal pattern `"Hélène Martin"` in `SENSITIVE_ORGS` can therefore **never** match. The name survives in escaped form and is fully readable the moment anyone parses the JSON.

**Verified:** `"built by Hélène Martin"` came out as `"built by H\u00e9l\u00e8ne Martin"` — untouched.

**Fix (one line):** `json.dumps(pipeline_json, indent=2, ensure_ascii=False)` before the org pass, and write with UTF-8 (you already do). Longer-term, anonymise structurally (walk the parsed object) rather than regexing serialised text.

### A3 — anything the anonymiser doesn't already know about survives

The anonymiser is a blocklist of known strings: configured org names, four URL domain patterns, credential-ish keys. Everything else passes through verbatim, and the sanitiser deliberately keeps `info` and `error` blocks without touching their contents. Concretely, all of these survive into "safe to share" output: email addresses of people not on the org list (**verified:** `zoe@…` in a snap's notes), internal hostnames and sftp endpoints (**verified**), tenant/site GUIDs (**verified**), field and column names inside mapper `property_map`s (employee attributes, JQL fragments, request-participant addresses), and anything a colleague ever typed into a snap label or notes field.

This is the structural gap in the promise: you can't blocklist what you haven't foreseen. A tool that says "safe to share publicly" needs at minimum: an email regex, a generic URL/hostname regex (not just four domains), and — honestly — a softened claim. Consider changing the ✅ message to "known sensitive patterns removed — review before sharing" and adding a `goldilocks audit --file` mode that greps the *output* for `@`, `http`, `sftp`, and GUID shapes (your Neo4j audit command already does exactly this for emails in the graph — the same idea pointed at the file is your best defence).

### A4 — the ORG_N pseudonymisation is publicly reversible by design

`anonymise_org_names` assigns `ORG_{len(org_lookup)+1}` in `SENSITIVE_ORGS` iteration order, and `SENSITIVE_ORGS` (minus the gitignored colleague list) is hardcoded in a public file with a comment saying "safe to commit". So anyone reading the repo can decode: ORG_1 = first list entry, ORG_2 = second, and so on — the mapping is a lookup table you've published. The committed list also *discloses the very names being hidden*, and two more internal names leak elsewhere in public source: a real pipeline name in `GRAPH_SCHEMA` ("Pipeline names may use > as separator e.g. '…Reports>Sharepoint'") and a real internal system name in `security.py`'s `safe_query` docstring example.

**Fix:** move the entire org list into the gitignored file (or an env/config file) and load it at runtime, keeping only the loading mechanism public; replace the doc/schema examples with invented names ("Orchestrator>Reports", "DEMO-PIPELINE"); and if reversibility matters, derive ORG_N from encounter order in the data rather than list order (with A2's structural approach this comes naturally).

### P1 — the package as declared cannot work once installed

Several compounding problems, any one of which breaks a pip install:

1. `src/` has **no `__init__.py`**, and `[tool.setuptools.packages.find]` only discovers packages that have one — so `src` is silently not packaged at all. `commands` has one and is.
2. Even if packaged, the runtime imports are bare (`from sanitiser import …`) and depend on `sys.path.insert` hacks pointing at a source-tree layout that doesn't exist in site-packages. The `goldilocks` console script (`pie:app`) will fail on first command.
3. `commands/visualise.py` alone uses `from src.pipeline_menu import …` — a third import style that works only from the repo root.
4. Installing top-level modules named `pie`, `commands`, and `src` pollutes the global namespace and **will** collide with other packages (a top-level `src` package on PyPI is a classic install-breaker for users).
5. Missing dependencies: `anthropic` (imported by `agent.py`, needed by `ask`) and `pyperclip` (imported at *pie import time* via `commands.visualise → src.output_manager`) are not in `[project.dependencies]`. A fresh install crashes immediately on `import pyperclip`.
6. `pyproject.toml` says `name = "goldilocks"` but the published package is `goldilocks-curls` — confirm which is intended; if the PyPI listing was made from a different pyproject, reconcile before v1.0.

**Fix (the standard shape):** one package directory, `goldilocks/` containing `__init__.py`, `cli.py` (current pie), `commands/`, and `core/` (current src); absolute imports (`from goldilocks.core.sanitiser import …`) everywhere; delete every `sys.path.insert`; entry point `goldilocks = "goldilocks.cli:app"`; add `anthropic` and `pyperclip` to dependencies. This is a mechanical rename-and-sed job, ideal for one focused session, and the test suite will verify nothing broke.

---

## IMPORTANT

### A5 — org replacement corrupts unrelated words and treats names as regex

Bare case-insensitive substring replacement means a 3-letter org token mangles ordinary words. **Verified:** with "RBO" configured, `"Turbo Sync"` → `"TuORG_1 Sync"` and `"carbon copy"` → `"caORG_1n copy"`. Separately, org strings are passed to `re.sub` unescaped, so `helene.martin` matches `heleneXmartin` (dot = any char) and any name containing regex metacharacters would break the pass. **Fix:** `re.sub(rf"\b{re.escape(org)}\b", …)`, and sort `SENSITIVE_ORGS` longest-first so long names are replaced before their substrings.

### A6 — sanitiser redaction is top-level-only

`sanitise_settings` only inspects the top level of each settings dict. A secret nested one level down (`settings.account_ref.value.client_secret`) survives into `export_clean.json`. **Verified.** The anonymiser's recursive walk catches it later — but `sanitise` is a standalone command whose output name ("export_clean") invites treating it as shareable. **Fix:** recurse (the anonymiser's `anonymise_credentials` walk is the exact shape to borrow).

### S1 — `validate_query` has both false positives and gaps, plus dead guards

The deny-list matches substrings of the uppercased query, which produces real-world false positives: the seeder stores `p.created`, and `"CREATED"` contains `"CREATE"`, so a natural question about creation dates generates Cypher the guard then rejects (pinned in tests); `n.dataset` is rejected because "dataSET". Gaps: the entry is `"CALL "` with a trailing space, so Neo4j 5's `CALL{…}` subquery syntax slips through (pinned). Dead code: `ALLOWED_OPERATIONS` and `FORBIDDEN_PATTERNS` are defined and never consulted, and `redact_sensitive_value` redacts based on the *value* containing words like "password" — inverted logic (secrets rarely contain the word "secret"); it's only used in the token analyser where it happens to always fire, making that report field permanently `***REDACTED***`. **Fix:** word-boundary regex for the deny-list (`re.search(rf"\b{op}\b", query, re.I)`); either enforce or delete the unused constants; retire or invert `redact_sensitive_value`. The layered *design* (prompt rules → validate → safe_query) is right — keep it, sharpen the middle layer.

### S2 — credential "anonymisation" is a truncated unsalted MD5

`token_ + md5(value)[:8]` is deterministic and unsalted, so anyone can *confirm a guessed secret* offline against published output, and weak passwords fall to a dictionary in seconds. It also means the same secret produces the same token across every file you ever publish — a correlation channel. **Fix:** random token per unique value, kept consistent via a lookup (you already have `cred_lookup` sitting unused — it looks like this was the original intent).

### E1 — modules print-and-return on missing files; wrappers then announce success

`sanitise_export` and `anonymise_pipeline` both handle a missing input by printing ❌ and returning `None`. The command wrappers' `try/except` never fires, so `goldilocks sanitise` prints "✅ Done!" over a failure, and — worse — `sieve --plain` on a nonexistent input prints "🫧 Sieve complete — data ready to seed." with exit code 0 (pinned in tests). **Fix:** raise `FileNotFoundError` in the src functions; the wrappers already convert exceptions into warm messages and exit code 1. One-line change per module, then flip the two pinned tests.

### E2 — a failing animated sieve leaves the terminal wrecked

The exception path in `commands/sieve.py` calls `anim._stop.set()` (a private attribute) but never restores the terminal — the process exits with the alternate screen active and the cursor hidden. You already wrote the correct method: call `anim.abort()`, which joins the thread *and* restores. Related: malformed JSON escapes `sanitise_export` as a raw `JSONDecodeError` (the anonymiser has a fallback; the sanitiser should at least fail warmly).

### G1 — module-level lookup dicts are hidden shared state

`org_lookup` / `url_lookup` persist for the life of the process. Consequences, all pinned in tests: `anonymise_org_names` inserts *every* configured org whether or not it appears, so "Orgs replaced: N" always equals the full list length (with the colleague file loaded, it prints the same number for every file — a misleading summary); on a second call the counts are cumulative and URL numbering depends on every file processed earlier, so outputs are not reproducible across differing process histories; and any library user (sieve today, tests, v2.0 ontology tomorrow) shares the state invisibly. **Fix:** an `Anonymiser` class holding its lookups, or explicit `reset_lookups()` called at the top of `anonymise_pipeline`. Choose the contract deliberately — the test documents whichever you pick.

### P2 — `run` is dead code that collects passwords and fakes work

`commands/run.py` prompts for SnapLogic and Neo4j passwords, asks for confirmation, then runs five `time.sleep(0.5)` spinners and prints success — it does nothing. It's commented out of `pie.py`, but it ships in the package, and `fetch`'s next-steps hint still says "Or run everything: goldilocks run", pointing users at a command that doesn't exist. Shipping a placeholder that harvests two passwords into memory and pretends to run is exactly the kind of thing a public-repo reader screenshots. **Fix:** delete the file and the hint (or implement it — but not before v1.0).

### C2 — `pipeline_processor.py` is broken against the current API

It aliases `build_pipeline_diagram` as `data_processing_workflow` and calls it with `(name, components, connections)` — the function's signature is `(pipelines: list, direction: str)`. Every code path in the module would crash or emit garbage; it's a stale module from an earlier signature that was never updated. **Fix:** delete it (nothing imports it) or update it in a dedicated session.

---

## MINOR

### C1 — dependency direction and import-style drift

`src/output_manager.py` and `src/pipeline_menu.py` import `typer` and `commands.colours` — src (the library) depending on commands (the CLI) is inverted; it also drags `pyperclip` into the import of `pie` itself. Three import styles coexist (bare `from sanitiser import`, `from src.pipeline_menu import`, and `sys.path.insert` in six separate files), and `pipeline_seeder.py` has CRLF line endings while everything else is LF. All of this dissolves naturally when P1 is done; the dependency direction (colours/console utilities belong in the package's own `ui` module, importable by both layers) is the one design decision to make first.

### C3 — presentation logic and sleeps inside library functions

The src modules mix `print`, `typer.echo`, and Rich, and `sanitise_export`/`anonymise_pipeline`/`generate_diagrams` contain `time.sleep` calls for reveal pacing. This is the exact conflict that sank the Rich progress-bar attempt, it fights the `on_progress` design (the callback is the right pattern — lean into it and move *all* printing to the callers), and it has a measurable cost: the 77-test suite spends most of its 42 seconds asleep. Suggestion that preserves the aesthetic: keep the pacing in the *command* layer, emit facts from src via callbacks/returns.

### C4 — two CLASSDEFS constants, and one of them mis-names its classes

`snap_resolver.py` and `mermaid_styles.py` each define `CLASSDEFS`. The diagram builders import the `mermaid_styles` one, whose classes are named `http`/`sftp` — but nodes are tagged `:::httpclient`, `:::sftp_get`, `:::sftp_put`. Result: HTTP and SFTP nodes silently render unstyled in every diagram. **Fix:** rename the classdefs to match snap types exactly and delete the duplicate in `snap_resolver.py`.

### C5 — `audit.py` defines `_print_findings` twice

The first (incomplete) definition is shadowed by the second; ~45 lines of dead copy-paste. Delete the first.

### C6 — small dead/odd spots

`visualiser.generate_diagrams` builds `pipelines_typed` from the Pydantic models and never uses it (the Pydantic layer deserves to be either wired in or removed); `cred_lookup` is declared and unused (see S2 — it wants to exist); `generate_diagrams` calls `input()` directly, making a library function interactive and untestable (move the prompt to the command layer); `renderer.py` hardcodes a relative `puppeteer-config.json`, so svg/png rendering only works from the repo root; `requests.get` in both fetch paths has no timeout (a dead SnapLogic endpoint hangs forever — add `timeout=30`); `agent.ask_goldilocks` reads `os.environ["NEO4J_URI"]` *before* its try block, so missing env vars surface as a raw `'NEO4J_URI'` KeyError message rather than the warm guidance `doctor`/`seed` give; and `agent.py` constructs the Anthropic client and imports the Neo4j driver at module import time, coupling the three pure helper functions to both SDKs (works today because the SDK is lazy about keys — pin: tests import it fine without a key — but move the pure functions or lazy-init the client).

---

## COSMETIC

`on_progress: callable = None` should be `Optional[Callable[[str, int, int, str], None]]` (the docstrings are lovely — let the types match); the `input` parameter name shadows the builtin throughout the commands (harmless with Typer, mildly confusing in tests); `welcome` still prints the 🐻 from before the 🫧 rebrand; the welcome copy says "From RAGs to DAGs to Riches" while the site says "from DAG to RAG to riches" — pick one canonical direction; and `FUN_TRIGGERS` includes a private handle of yours in public source (plus the trigger "curls" fires on any question containing that word, e.g. legitimate questions about the cURL tool) — worth a deliberate keep/remove decision before the repo is public.

---

## v2.0 ontology-readiness (flags only, no design)

Three things in current code will make the `:Onto:` layer harder than it needs to be. First, the anonymiser's module-level state (G1): a curation workflow that calls sanitise/anonymise repeatedly in one process inherits the accumulation problem — fix G1 and this disappears. Second, presentation-in-library (C3): the propose-verify-approve loop will want machine-readable results (counts, mappings, findings) returned from functions, not printed; returning a small result object from `sanitise_export`/`anonymise_pipeline` now costs little and pays twice. Third, the duplicate/mismatched CLASSDEFS (C4) will fight a third, ontology-flavoured style namespace — consolidate to one style source first. The seeder itself is in good shape for extension: parameterised Cypher throughout, MERGE-based idempotence, and clean summary dicts.

---

## What's genuinely good

Worth saying plainly, because the defect list above is long and the codebase isn't bad — it's a solo project with strong instincts. The layered agent safety (prompt rules → validate → `safe_query`) is the right architecture even where the middle layer needs sharpening; every Cypher statement in the seeder and query paths is parameterised — there is no injection surface in the data path. The `on_progress` callback with a stable signature across both modules is a clean design that made the sieve animation nearly free, and the animation itself degrades honestly with `--plain`. The sanitiser's allow-list-of-keys approach (keep what you need rather than strip what you recognise) is the correct shape for that problem — notice it's the opposite philosophy from the anonymiser's blocklist, and it's the stronger of the two. The audit command's email-detection Cypher is a genuinely smart post-hoc leak check — pointing that same idea at the anonymised *file* is your cheapest big win under A3. The recursive credential walk catches nested keys correctly (verified). And the CLI's warmth is consistent and real: doctor is thorough, fetch fails honestly, seed validates before it connects.
