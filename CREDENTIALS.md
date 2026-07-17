# 🔑 Credentials — the pattern

*Written 2026-07-14; re-applied 2026-07-16 against the current repo (post item-25: `core/config.py`, two-act `init`, `check`).*

One module owns every secret: `goldilocks_cli/core/credentials.py`.
Nothing else reads a credential from the environment directly.

## The hierarchy (highest wins)

1. **Process environment variables** — the source of truth.
2. **A gitignored `.env` at the working root** — developer convenience,
   loaded once at CLI startup (`cli.py` callback) via python-dotenv with
   `override=False`, so a real env var always beats `.env`.
3. **Absent** — `get_credential(name)` returns `None`;
   `require_credential(name, purpose)` raises `CredentialMissing`, whose
   `str()` is the warm, ready-to-echo fix-it message. Every command
   catches it, echoes it, exits 1. No tracebacks, ever.

`goldilocks.toml` **never** holds a secret — `check_config_for_secrets()`
warns loudly at startup on secret-shaped key names (the future item-25
config loader must also call it). OS keychain (keyring) is designed but
deliberately stubbed — see the note at the top of `credentials.py`.

## The journey

```
goldilocks init     # act one: config questions (item 25)
                    # act two: credential status + .env placeholder
                    #   scaffold (idempotent, comments only) + .env
                    #   folded into init's .gitignore check
(edit .env)         # you type secrets in your editor, never a prompt
goldilocks doctor   # verifies — three states per credential set
goldilocks fetch    # just works
```

The `.env` scaffold never prompts (so `init`'s pinned input sequences
stay valid) and never destroys — it only creates or appends commented
placeholders for variables the file doesn't yet mention. The
`goldilocks.toml` secret-key guard runs at CLI startup over both config
locations (`core.config.config_paths()`): home and local.

Doctor's three states: **missing** (names the variable + one-line fix),
**present but unverified** (set, but the live check couldn't complete —
e.g. offline), **verified** (Neo4j `verify_connectivity`; Anthropic
`models.list()` — the SDK's zero-token call; SnapLogic GET against the
pod's export base with basic auth, 401/403 → rejected).

## Hard rules

- No secret is ever echoed, logged, written to config, or included in
  any error message — doctor prints nothing of a value, not even a
  masked prefix.
- Interactive secret entry (fetch's fallback only) uses
  `hide_input=True`; `.env` guidance is always offered first.
- `.env` loading never overrides an explicitly set env var.
- A `.env` in the working directory is never read by sieve/anonymise as
  pipeline input (pinned by `TestSieveDotenvIsolation`).

## The variables

| Variable | Used by | Notes |
|---|---|---|
| `NEO4J_URI` | seed, ask, visualise, show-graph, audit, stats, ping | |
| `NEO4J_USER` | same | optional, defaults to `neo4j` — a setting, not a secret |
| `NEO4J_PASSWORD` | same | |
| `SNAPLOGIC_USERNAME` | fetch | HTTP basic auth against the pod |
| `SNAPLOGIC_PASSWORD` | fetch | |
| `ANTHROPIC_API_KEY` | ask | client is now lazily constructed — importing the agent no longer demands a key |

---

# Inventory — as found before this session (2026-07-14)

SnapLogic auth as actually implemented: **HTTP basic auth**
(`requests.auth.HTTPBasicAuth`) against the public project-export API
(`SNAPLOGIC_EXPORT_BASE`, pod hardcoded to `emea.snaplogic.com`). No
bearer tokens anywhere.

| Where | What was there |
|---|---|
| `commands/fetch.py` | `SNAPLOGIC_*` env reads with prompt fallback (password correctly hidden) |
| `core/pipeline_fetcher.py` | creds as params; `__main__` used `getpass` |
| `commands/seed.py` | `NEO4J_*` as Typer defaults **read at import time** (before any `.env` load could ever apply); wrote creds back into `os.environ` for the seeder |
| `commands/stats.py` | same import-time default pattern |
| `commands/doctor.py` | raw `os.environ[...]`, **Neo4j only** — SnapLogic and Anthropic never checked |
| `commands/ping.py` | raw reads → missing var surfaced as `❌ Neo4j unreachable: 'NEO4J_URI'` |
| `commands/graph.py` | same raw-KeyError shape |
| `commands/audit.py` | KeyError → ⚠️ but **exited 0** on missing creds (now exits 1) |
| `commands/visualise.py` | raw reads inside `_render_from_traversal` |
| `core/pipeline_menu.py`, `core/pipeline_seeder.py`, `core/describer.py` (×2), `core/agent.py` | raw `os.environ[...]` in core |
| `core/agent.py` | module-level `anthropic.Anthropic()` — read the key implicitly **at import time**, exploding even for local token-risk questions |

Leak audit: no path echoed a secret value. Remaining documented
exposures: `--password` on argv for seed/stats (flags kept for
compatibility; env/.env is the recommended path), and fetch echoing
server response bodies on non-200.
