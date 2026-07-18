# tests/test_archive.py
# ============================================================
# 🫧 GOLDILOCKS — safe archive extraction (finding F1)
# ============================================================
# A zip names its own members and those names are hostile input.
# NOTE (verified 3.12): zipfile.extractall() already sanitises
# member names, so the fetch command was not exploitable via that
# route. The genuine escape was the hand-built path in
# fetch_and_save (Path(dest) / member), where an absolute member
# replaces the destination outright. These tests pin the explicit
# refusal that now covers both.
# ============================================================

import zipfile

import pytest

from goldilocks_cli.core.archive import (
    UnsafeArchiveMember,
    is_suspicious_member,
    resolve_member,
    safe_extract,
)


def make_zip(path, members: dict) -> None:
    """Write a zip whose member NAMES are taken verbatim."""
    with zipfile.ZipFile(path, "w") as z:
        for name, content in members.items():
            z.writestr(name, content)


# ------------------------------------------------------------
# Name screening
# ------------------------------------------------------------

@pytest.mark.parametrize("member", [
    "../evil.txt",
    "../../.bashrc",
    "nested/../../escape.json",
    "/etc/cron.d/task",
    "/absolute.json",
    "..\\windows_evil.txt",       # backslash traversal (Windows vector)
    "folder\\child.json",         # zip spec uses "/", so this is suspect
    "C:/Windows/System32/x.dll",  # drive-letter prefix
])
def test_suspicious_members_are_recognised(member):
    assert is_suspicious_member(member) is True


@pytest.mark.parametrize("member", [
    "export.json",
    "project/export.json",
    "a/b/c/pipeline.json",
    "name with spaces.json",
    "accented-Zoé.json",
])
def test_benign_members_are_allowed(member):
    assert is_suspicious_member(member) is False


# ------------------------------------------------------------
# Resolution
# ------------------------------------------------------------

def test_resolve_member_keeps_benign_paths_inside(tmp_path):
    target = resolve_member(tmp_path, "project/export.json")
    assert target == (tmp_path / "project" / "export.json").resolve()


@pytest.mark.parametrize("member", ["../escape.json", "/etc/passwd", "..\\x"])
def test_resolve_member_refuses_escapes(tmp_path, member):
    with pytest.raises(UnsafeArchiveMember):
        resolve_member(tmp_path, member)


# ------------------------------------------------------------
# Extraction — the behaviour that matters
# ------------------------------------------------------------

def test_traversal_member_is_refused_and_writes_nothing_outside(tmp_path):
    # REGRESSION GUARD (F1): refuse rather than silently flatten.
    outside = tmp_path / "outside.txt"
    dest = tmp_path / "exports"
    dest.mkdir()
    archive = tmp_path / "hostile.zip"
    make_zip(archive, {"../outside.txt": "pwned"})

    with zipfile.ZipFile(archive) as z:
        with pytest.raises(UnsafeArchiveMember):
            safe_extract(z, dest)

    assert not outside.exists()


def test_absolute_member_is_refused(tmp_path):
    dest = tmp_path / "exports"
    archive = tmp_path / "abs.zip"
    make_zip(archive, {"/tmp/goldilocks_should_not_exist.txt": "pwned"})

    with zipfile.ZipFile(archive) as z:
        with pytest.raises(UnsafeArchiveMember):
            safe_extract(z, dest)


def test_benign_archive_extracts_including_nested_folders(tmp_path):
    dest = tmp_path / "exports"
    archive = tmp_path / "clean.zip"
    make_zip(archive, {
        "export.json": '{"entries": []}',
        "project/child.json": '{"name": "child"}',
    })

    with zipfile.ZipFile(archive) as z:
        written = safe_extract(z, dest)

    assert (dest / "export.json").read_text() == '{"entries": []}'
    assert (dest / "project" / "child.json").exists()
    assert len(written) == 2


def test_refusal_happens_before_the_hostile_member_is_written(tmp_path):
    # A mixed archive: the guard must refuse rather than partially
    # extract past the offending member.
    dest = tmp_path / "exports"
    archive = tmp_path / "mixed.zip"
    make_zip(archive, {"good.json": "{}", "../bad.json": "{}"})

    with zipfile.ZipFile(archive) as z:
        with pytest.raises(UnsafeArchiveMember):
            safe_extract(z, dest)

    assert not (tmp_path / "bad.json").exists()


def test_directory_entries_are_created_not_written(tmp_path):
    dest = tmp_path / "exports"
    archive = tmp_path / "dirs.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("folder/", "")
        z.writestr("folder/file.json", "{}")

    with zipfile.ZipFile(archive) as z:
        written = safe_extract(z, dest)

    assert (dest / "folder").is_dir()
    assert (dest / "folder" / "file.json").exists()
    assert len(written) == 1  # the directory entry is not a written file


def test_absolute_member_would_have_replaced_a_handbuilt_path(tmp_path):
    """The escape that was real: pathlib's / operator.

    Path("exports") / "/etc/passwd" is "/etc/passwd" — the
    destination is discarded entirely. This is what
    fetch_and_save did before safe_extract existed.
    """
    dest = tmp_path / "exports"
    naive = dest / "/etc/passwd"
    assert str(naive) == "/etc/passwd"          # the bug, demonstrated
    with pytest.raises(UnsafeArchiveMember):     # the guard, pinned
        resolve_member(dest, "/etc/passwd")
