"""Unit tests for brain.py helpers — no FastMCP, no async."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from arbling_brain_reader.brain import (
    _safe_resolve,
    brain_status,
    latest_retrospective,
    list_active_plans,
    list_feedback_rules,
    list_pages,
    read_brain_page,
    read_index,
    refresh_brain,
    search_brain,
    validate_brain,
)


# ---------------------------------------------------------------------------
# validate_brain
# ---------------------------------------------------------------------------


def test_validate_brain_ok(fake_brain: Path):
    validate_brain(fake_brain)  # must not raise


def test_validate_brain_missing_claude_md(tmp_path: Path):
    (tmp_path / "wiki").mkdir()
    with pytest.raises(RuntimeError, match="CLAUDE.md"):
        validate_brain(tmp_path)


def test_validate_brain_missing_wiki(tmp_path: Path):
    (tmp_path / "CLAUDE.md").write_text("x")
    with pytest.raises(RuntimeError, match="wiki"):
        validate_brain(tmp_path)


# ---------------------------------------------------------------------------
# _safe_resolve — path traversal
# ---------------------------------------------------------------------------


def test_safe_resolve_ok(fake_brain: Path):
    p = _safe_resolve("wiki/index.md", fake_brain)
    assert p == (fake_brain / "wiki" / "index.md").resolve()


def test_safe_resolve_dotdot(fake_brain: Path):
    with pytest.raises(ValueError, match="traversal"):
        _safe_resolve("../../etc/passwd", fake_brain)


def test_safe_resolve_absolute(fake_brain: Path):
    with pytest.raises(ValueError, match="Absolute"):
        _safe_resolve("/etc/passwd", fake_brain)


# ---------------------------------------------------------------------------
# brain_status
# ---------------------------------------------------------------------------


def test_brain_status_counts(fake_brain: Path):
    status = brain_status(fake_brain)
    assert status["path"] == str(fake_brain)
    # fake brain has: wiki/index.md, wiki/ceo/feedback/no-foo.md,
    #                 wiki/plans/2026-05-23-test.md, wiki/retrospectives/2026-05-23-test.md
    assert status["wiki_page_count"] == 4
    assert status["raw_file_count"] == 0


def test_brain_status_sha(fake_brain: Path):
    status = brain_status(fake_brain)
    assert len(status["last_commit_sha"]) == 40
    assert status["last_commit_message"] == "initial brain"


# ---------------------------------------------------------------------------
# read_brain_page
# ---------------------------------------------------------------------------


def test_read_brain_page_ok(fake_brain: Path):
    content = read_brain_page("wiki/index.md", fake_brain)
    assert "Master Index" in content


def test_read_brain_page_not_found(fake_brain: Path):
    with pytest.raises(FileNotFoundError):
        read_brain_page("wiki/nonexistent.md", fake_brain)


def test_read_brain_page_traversal(fake_brain: Path):
    with pytest.raises(ValueError, match="traversal"):
        read_brain_page("../../../etc/passwd", fake_brain)


# ---------------------------------------------------------------------------
# search_brain
# ---------------------------------------------------------------------------


def test_search_brain_finds_match(fake_brain: Path):
    results = search_brain("avoid foo patterns", "wiki", 10, fake_brain)
    assert len(results) >= 1
    assert any("no-foo.md" in r["file"] for r in results)


def test_search_brain_no_match(fake_brain: Path):
    results = search_brain("ZZZQQQXXX_NOMATCH", "wiki", 10, fake_brain)
    assert results == []


def test_search_brain_max_results(fake_brain: Path):
    # "the" should appear in multiple files; cap at 2
    results = search_brain("e", "wiki", 2, fake_brain)
    assert len(results) <= 2


def test_search_brain_missing_scope_dir(fake_brain: Path):
    # "raw" dir doesn't exist in fake brain — should return [] not raise
    results = search_brain("anything", "raw", 10, fake_brain)
    assert results == []


# ---------------------------------------------------------------------------
# list_pages
# ---------------------------------------------------------------------------


def test_list_pages_wiki(fake_brain: Path):
    pages = list_pages("wiki", fake_brain)
    assert "wiki/index.md" in pages
    assert "wiki/plans/2026-05-23-test.md" in pages


def test_list_pages_subfolder(fake_brain: Path):
    pages = list_pages("wiki/plans", fake_brain)
    assert all("wiki/plans/" in p for p in pages)


def test_list_pages_not_found(fake_brain: Path):
    with pytest.raises(FileNotFoundError):
        list_pages("wiki/nonexistent", fake_brain)


# ---------------------------------------------------------------------------
# read_index
# ---------------------------------------------------------------------------


def test_read_index_ok(fake_brain: Path):
    content = read_index("wiki", fake_brain)
    assert "Master Index" in content


def test_read_index_not_found(fake_brain: Path):
    (fake_brain / "wiki" / "empty_folder").mkdir()
    with pytest.raises(FileNotFoundError, match="INDEX.md"):
        read_index("wiki/empty_folder", fake_brain)


# ---------------------------------------------------------------------------
# list_feedback_rules
# ---------------------------------------------------------------------------


def test_list_feedback_rules(fake_brain: Path):
    rules = list_feedback_rules(fake_brain)
    assert len(rules) == 1
    rule = rules[0]
    assert rule["name"] == "no-foo"
    assert "wiki/ceo/feedback/no-foo.md" in rule["file"]
    assert rule["summary"]  # non-empty one-liner


# ---------------------------------------------------------------------------
# list_active_plans
# ---------------------------------------------------------------------------


def test_list_active_plans(fake_brain: Path):
    plans = list_active_plans(fake_brain)
    assert len(plans) == 1
    plan = plans[0]
    assert plan["status"] == "active"
    assert plan["title"] == "Test Plan"
    assert plan["owner"] == "Yevgeniy"


# ---------------------------------------------------------------------------
# latest_retrospective
# ---------------------------------------------------------------------------


def test_latest_retrospective(fake_brain: Path):
    retro = latest_retrospective(fake_brain)
    assert retro["title"] == "Test Retro"
    assert "Session went well" in retro["content"]
    assert retro["file"].startswith("wiki/retrospectives/")


def test_latest_retrospective_no_dir(tmp_path: Path):
    (tmp_path / "CLAUDE.md").write_text("x")
    (tmp_path / "wiki").mkdir()
    with pytest.raises(FileNotFoundError):
        latest_retrospective(tmp_path)


# ---------------------------------------------------------------------------
# refresh_brain
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=T", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def test_refresh_brain_already_current(fake_brain: Path):
    result = refresh_brain(fake_brain)
    # No remote set — pull fails gracefully
    assert result["status"] in ("error", "already_current")


def test_refresh_brain_picks_up_upstream_commit(tmp_path: Path):
    """Create a bare remote, clone it, add a commit upstream, refresh."""
    remote = tmp_path / "remote.git"
    remote.mkdir()
    _git(["-c", "init.defaultBranch=main", "init", "--bare", str(remote)], tmp_path)

    # Clone the bare remote
    local = tmp_path / "local"
    _git(["clone", str(remote), str(local)], tmp_path)

    # Create a valid Brain layout in local
    (local / "CLAUDE.md").write_text("# Brain\n", encoding="utf-8")
    (local / "wiki").mkdir()
    (local / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
    _git(["add", "."], local)
    _git(["commit", "-m", "brain init"], local)
    _git(["push", "origin", "main"], local)

    # Capture SHA before upstream change
    old_sha_r = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=local,
        capture_output=True,
        text=True,
    )
    old_sha = old_sha_r.stdout.strip()

    # Add a commit directly to remote (simulating a team-member push)
    # We use a second clone for this
    contributor = tmp_path / "contributor"
    _git(["clone", str(remote), str(contributor)], tmp_path)
    (contributor / "wiki" / "new-page.md").write_text("# New\n", encoding="utf-8")
    _git(["add", "."], contributor)
    _git(["commit", "-m", "add new page"], contributor)
    _git(["push", "origin", "main"], contributor)

    # Now refresh local clone
    validate_brain(local)
    result = refresh_brain(local)

    assert result["status"] == "updated"
    assert result["old_sha"] == old_sha
    assert result["new_sha"] != old_sha
    assert "wiki/new-page.md" in result["files_changed"]


def test_refresh_brain_not_a_git_repo(tmp_path: Path):
    """refresh_brain should return status:error, not raise, on non-git dir."""
    (tmp_path / "CLAUDE.md").write_text("x")
    (tmp_path / "wiki").mkdir()
    result = refresh_brain(tmp_path)
    assert result["status"] == "error"
    assert "message" in result
