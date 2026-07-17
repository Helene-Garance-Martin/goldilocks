# ============================================================
# 🫧 GOLDILOCKS — Workflow state
# ============================================================
# Pure state readers and writers. No printing or prompting.
# ============================================================

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Iterable, Optional


FILE_STATE_KEY = "_goldilocks"
FILE_STATE_NAMESPACE = "goldilocks.file_state"
GRAPH_STATE_NAMESPACE = "goldilocks.graph_state"
STATE_SCHEMA_VERSION = 1
DEFAULT_STALE_AFTER_DAYS = 7


@dataclass(frozen=True)
class FileCandidate:
    path: Path
    modified_at: datetime
    state: Optional[dict[str, Any]] = None


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def isoformat_utc(value: Optional[datetime] = None) -> str:
    """Serialise a datetime in stable UTC ISO8601 form."""
    value = value or utc_now()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse an ISO8601 timestamp, returning None for unknown formats."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def age_in_days(value: Any, now: Optional[datetime] = None) -> Optional[float]:
    """Return a non-negative age in days for a timestamp."""
    parsed = value if isinstance(value, datetime) else parse_timestamp(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    current = now or utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    seconds = (current.astimezone(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
    return max(0.0, seconds / 86400)


def is_stale(value: Any, threshold_days: int, now: Optional[datetime] = None) -> bool:
    """Return True when a timestamp is older than the configured threshold."""
    age = age_in_days(value, now=now)
    return age is not None and age > max(0, threshold_days)


def stale_after_days(config: dict[str, Any]) -> int:
    """Read the workflow staleness threshold with a safe default."""
    raw = config.get("workflow", {}).get("stale_after_days", DEFAULT_STALE_AFTER_DAYS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_STALE_AFTER_DAYS
    return max(0, value)


def tool_version() -> str:
    """Return the installed Goldilocks package version when available."""
    try:
        return importlib_metadata.version("goldilocks-curls")
    except importlib_metadata.PackageNotFoundError:
        return "unknown"


def build_file_state(
    source_file: str,
    *,
    sieved_at: Optional[datetime] = None,
    version: Optional[str] = None,
) -> dict[str, Any]:
    """Build a versioned, forward-compatible sieved-file marker."""
    return {
        "namespace": FILE_STATE_NAMESPACE,
        "schema_version": STATE_SCHEMA_VERSION,
        "stage": "sieved",
        "sieved_at": isoformat_utc(sieved_at),
        "tool_version": version or tool_version(),
        "source_file": Path(source_file).name,
    }


def embed_file_state(
    data: dict[str, Any],
    source_file: str,
    *,
    sieved_at: Optional[datetime] = None,
    version: Optional[str] = None,
) -> dict[str, Any]:
    """Return a shallow copy with Goldilocks provenance attached."""
    output = dict(data)
    output[FILE_STATE_KEY] = build_file_state(
        source_file,
        sieved_at=sieved_at,
        version=version,
    )
    return output


def read_file_state(path: Path | str) -> Optional[dict[str, Any]]:
    """Read a top-level Goldilocks marker; unknown future fields are retained."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    state = data.get(FILE_STATE_KEY)
    if not isinstance(state, dict) or not isinstance(state.get("stage"), str):
        return None
    return dict(state)


def without_file_state(data: Any) -> Any:
    """Return JSON-compatible data without the top-level metadata block."""
    if not isinstance(data, dict) or FILE_STATE_KEY not in data:
        return data
    output = dict(data)
    output.pop(FILE_STATE_KEY, None)
    return output


def text_without_file_state(text: str) -> str:
    """Remove file metadata before content scans, falling back to raw text."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(without_file_state(data), ensure_ascii=False)


def atomic_write_text(path: Path | str, text: str) -> Path:
    """Atomically replace a text file using a temporary sibling file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, destination)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    return destination


def atomic_write_json(path: Path | str, data: Any) -> Path:
    """Atomically write indented UTF-8 JSON."""
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return atomic_write_text(path, text)


def _candidate(path: Path) -> FileCandidate:
    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return FileCandidate(path=path, modified_at=modified, state=read_file_state(path))


def _sorted_candidates(paths: Iterable[Path]) -> list[FileCandidate]:
    unique: dict[Path, Path] = {}
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            continue
        try:
            key = path.resolve()
        except OSError:
            key = path.absolute()
        unique[key] = path
    candidates = [_candidate(path) for path in unique.values()]
    return sorted(candidates, key=lambda item: item.modified_at, reverse=True)


def find_fetched_exports(
    exports_dir: Path | str,
    *,
    cwd: Optional[Path] = None,
) -> list[FileCandidate]:
    """Find raw fetched export.json files, newest first."""
    base = Path(cwd) if cwd is not None else Path.cwd()
    configured = Path(exports_dir)
    if not configured.is_absolute():
        configured = base / configured

    paths = [base / "export.json"]
    if configured.is_dir():
        paths.extend(configured.rglob("export.json"))

    return [
        candidate
        for candidate in _sorted_candidates(paths)
        if not candidate.state or candidate.state.get("stage") != "sieved"
    ]


def find_sieved_exports(
    exports_dir: Path | str,
    *,
    cwd: Optional[Path] = None,
) -> list[FileCandidate]:
    """Find marked outputs and compatible legacy anonymised files."""
    base = Path(cwd) if cwd is not None else Path.cwd()
    configured = Path(exports_dir)
    if not configured.is_absolute():
        configured = base / configured

    paths = list(base.glob("*.json"))
    if configured.is_dir():
        paths.extend(configured.rglob("*.json"))

    candidates = []
    for candidate in _sorted_candidates(paths):
        marked = candidate.state and candidate.state.get("stage") == "sieved"
        legacy = "anonymised" in candidate.path.name.lower()
        if marked or legacy:
            candidates.append(candidate)
    return candidates


def read_graph_state(session: Any) -> dict[str, Any]:
    """Read graph metadata and the live pipeline count in one query."""
    record = session.run(
        """
        OPTIONAL MATCH (m:GoldilocksMeta {namespace: $namespace})
        WITH m
        OPTIONAL MATCH (p:Pipeline)
        RETURN
            m.namespace AS namespace,
            m.schema_version AS schema_version,
            m.last_seeded AS last_seeded,
            m.pipeline_count AS recorded_pipeline_count,
            m.source_file AS source_file,
            m.source_sieved_at AS source_sieved_at,
            m.tool_version AS tool_version,
            count(p) AS pipeline_count
        """,
        namespace=GRAPH_STATE_NAMESPACE,
    ).single()

    if record is None:
        return {
            "namespace": GRAPH_STATE_NAMESPACE,
            "schema_version": None,
            "last_seeded": None,
            "recorded_pipeline_count": None,
            "source_file": None,
            "source_sieved_at": None,
            "tool_version": None,
            "pipeline_count": 0,
        }
    return dict(record)


def write_graph_state(
    tx: Any,
    *,
    source_file: str,
    pipeline_count: int,
    last_seeded: Optional[datetime] = None,
    source_sieved_at: Optional[str] = None,
    version: Optional[str] = None,
) -> dict[str, Any]:
    """Upsert the namespaced graph-state node and return its public fields."""
    seeded_at = isoformat_utc(last_seeded)
    record = tx.run(
        """
        MERGE (m:GoldilocksMeta {namespace: $namespace})
        SET m.schema_version = $schema_version,
            m.last_seeded = $last_seeded,
            m.pipeline_count = $pipeline_count,
            m.source_file = $source_file,
            m.source_sieved_at = $source_sieved_at,
            m.tool_version = $tool_version
        RETURN
            m.namespace AS namespace,
            m.schema_version AS schema_version,
            m.last_seeded AS last_seeded,
            m.pipeline_count AS pipeline_count,
            m.source_file AS source_file,
            m.source_sieved_at AS source_sieved_at,
            m.tool_version AS tool_version
        """,
        namespace=GRAPH_STATE_NAMESPACE,
        schema_version=STATE_SCHEMA_VERSION,
        last_seeded=seeded_at,
        pipeline_count=int(pipeline_count),
        source_file=Path(source_file).name,
        source_sieved_at=source_sieved_at,
        tool_version=version or tool_version(),
    ).single()
    return dict(record) if record is not None else {}
