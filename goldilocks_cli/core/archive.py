# ============================================================
# 🫧 GOLDILOCKS — Safe archive extraction
# ============================================================
# A zip archive names its own members, and those names are not
# trustworthy: "../../.bashrc" and "/etc/cron.d/task" are both
# legal entries.
#
# What CPython already does (verified on 3.12, behaviour dates
# from the CVE-2007-4559 fix): ZipFile.extractall() sanitises
# member names — it strips drive letters, treats absolute paths
# as relative, and drops ".." components. So extractall() does
# NOT escape its destination on supported Python versions.
#
# Why this module exists anyway:
#   1. Building a path by hand — Path(dest) / member — has no
#      such protection, and pathlib makes it worse: an absolute
#      member REPLACES the destination entirely. fetch_and_save()
#      did exactly this before this module existed.
#   2. Sanitising silently is the wrong answer for a tool whose
#      promise is honesty. A member trying to escape means the
#      archive is not what it claims to be; Goldilocks refuses
#      and says so rather than quietly flattening the name.
#   3. Defence in depth against a future refactor reintroducing
#      a hand-built path.
#
# Trade-off worth knowing: this is stricter than extractall().
# A non-conformant archive using backslash separators (Windows
# zip tools sometimes do) is refused here where extractall()
# would have flattened it. For an export that should be a clean
# SnapLogic artefact, refusing loudly is the safer default.
#
# Goldilocks never creates symlinks from archive members: each
# member is read and written as bytes, so a symlink entry
# becomes an ordinary file rather than a link out of the tree.
# ============================================================

from __future__ import annotations

from pathlib import Path, PurePosixPath
from zipfile import ZipFile


class UnsafeArchiveMember(Exception):
    """A zip member would be written outside the destination folder."""

    def __init__(self, member: str) -> None:
        self.member = member
        super().__init__(
            f"unsafe path in archive: {member!r} — refusing to write "
            f"outside the export folder"
        )


def is_suspicious_member(member: str) -> bool:
    """True when a member name cannot be trusted on any platform.

    Checked before resolution so the refusal is explainable:
    backslashes (the zip spec uses "/", so a backslash is a
    Windows traversal vector), absolute paths, "..", and
    drive-letter prefixes are all refused outright.
    """
    if "\\" in member:
        return True

    pure = PurePosixPath(member)
    if pure.is_absolute():
        return True
    if ".." in pure.parts:
        return True

    first = pure.parts[0] if pure.parts else ""
    if len(first) == 2 and first[1] == ":":  # "C:" style prefix
        return True

    return False


def resolve_member(destination: Path, member: str) -> Path:
    """Resolve member under destination, or raise UnsafeArchiveMember.

    Belt and braces: the name is screened first, then the
    resolved path is confirmed to sit inside the destination.
    """
    if is_suspicious_member(member):
        raise UnsafeArchiveMember(member)

    root = Path(destination).resolve()
    target = (root / member).resolve()

    if target != root and root not in target.parents:
        raise UnsafeArchiveMember(member)

    return target


def safe_extract(archive: ZipFile, destination: Path) -> list[Path]:
    """Extract every member into destination, refusing escapes.

    Returns the list of files written. Raises UnsafeArchiveMember
    on the first member that would land outside destination —
    callers should treat that as a failed fetch, not a warning.
    """
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    for member in archive.namelist():
        target = resolve_member(root, member)

        if member.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as source:
            target.write_bytes(source.read())
        written.append(target)

    return written
