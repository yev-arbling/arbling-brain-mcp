"""FastMCP server — registers all 9 Brain read tools."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

from .brain import (
    brain_status as _brain_status,
    get_brain_path,
    list_active_plans as _list_active_plans,
    list_feedback_rules as _list_feedback_rules,
    list_pages as _list_pages,
    latest_retrospective as _latest_retrospective,
    read_brain_page as _read_brain_page,
    read_index as _read_index,
    refresh_brain as _refresh_brain,
    search_brain as _search_brain,
    validate_brain,
)

mcp = FastMCP("arbling-brain-reader")

# Resolved at import time so the server fails fast if the path is wrong.
_BRAIN_PATH: Path = get_brain_path()
validate_brain(_BRAIN_PATH)


@mcp.tool()
def brain_status() -> dict:
    """
    Return health and freshness info for the mounted Brain vault.

    Returns: {path, wiki_page_count, raw_file_count, last_commit_sha,
              last_commit_date, last_commit_message}

    Call this first to verify the Brain is reachable and to check how
    stale the local clone is (last_commit_date).
    """
    return _brain_status(_BRAIN_PATH)


@mcp.tool()
def read_brain_page(relative_path: str) -> str:
    """
    Return the full markdown content of a Brain page.

    Args:
        relative_path: Path relative to the Brain root, e.g.
            "wiki/product/ai-readiness-scoring.md" or
            "wiki/ceo/feedback/no-fluff-direct-actionable.md"

    Note: pages under wiki/ceo/ may contain private investor, runway, or
    strategic data. Surface these to end-users only when explicitly relevant
    to their question.

    Raises FileNotFoundError if the page does not exist.
    Rejects any path containing ".." or starting with "/" (security).
    """
    return _read_brain_page(relative_path, _BRAIN_PATH)


@mcp.tool()
def search_brain(
    query: str,
    scope: Literal["wiki", "raw", "all"] = "wiki",
    max_results: int = 10,
) -> list[dict]:
    """
    Full-text search across Brain pages. Returns top N matches.

    Args:
        query: Case-insensitive search string (plain text, not regex).
        scope: "wiki" (default) | "raw" | "all".
               Use "wiki" unless you specifically need raw source material.
               "raw" is high-volume and low-signal-per-token.
        max_results: Max results to return (default 10, max sensible ~50).

    Returns: list of {file, line_number, snippet, score}

    Uses ripgrep if available, falls back to Python re walk.
    """
    return _search_brain(query, scope, max_results, _BRAIN_PATH)


@mcp.tool()
def list_pages(folder: str = "wiki") -> list[str]:
    """
    List all .md files under a given Brain folder.

    Args:
        folder: Relative path from Brain root.
                Examples: "wiki", "wiki/plans", "wiki/ceo/feedback"

    Returns: sorted list of relative file paths (e.g. "wiki/plans/2026-05-23-foo.md")

    Use this to enumerate a domain before deciding which pages to read.
    """
    return _list_pages(folder, _BRAIN_PATH)


@mcp.tool()
def read_index(folder: str = "wiki") -> str:
    """
    Return the INDEX.md (or README.md) for a Brain folder.

    Args:
        folder: Relative path from Brain root. Examples: "wiki", "wiki/plans",
                "wiki/ceo/feedback"

    Returns: full markdown content of INDEX.md or README.md.

    This is the fastest way to orient inside a domain — read the index,
    then decide which specific pages to follow up on.
    """
    return _read_index(folder, _BRAIN_PATH)


@mcp.tool()
def list_feedback_rules() -> list[dict]:
    """
    Return all CEO behavioral rules from wiki/ceo/feedback/.

    Returns: list of {name, file, summary} — one entry per rule file.
    "summary" is the first substantive line (the one-line rule statement).

    Call this at session start to load all behavioral rules without reading
    each file individually. Then call read_brain_page() on specific rules
    you need in full detail.
    """
    return _list_feedback_rules(_BRAIN_PATH)


@mcp.tool()
def list_active_plans() -> list[dict]:
    """
    Return all active multi-step plans from wiki/plans/.

    Returns: list of {file, title, status, owner, updated} for each plan
    where frontmatter status == "active".

    Use this to see what initiatives are in flight before starting a session,
    so you can align your work with existing plans rather than duplicating them.
    """
    return _list_active_plans(_BRAIN_PATH)


@mcp.tool()
def latest_retrospective() -> dict:
    """
    Return the most recent retrospective from wiki/retrospectives/.

    Returns: {file, title, created, content}

    Files are sorted by filename (which uses YYYY-MM-DD prefix), so the
    most-recent date always wins. Use this to pick up pending items and
    lessons from the last session.
    """
    return _latest_retrospective(_BRAIN_PATH)


@mcp.tool()
def refresh_brain() -> dict:
    """
    Pull the latest Brain content from the GitHub remote.

    Returns: {old_sha, new_sha, files_changed, status}
    status is "updated", "already_current", or "error".
    On error, an additional "message" key explains what went wrong.

    Use when you suspect the local clone is stale — e.g., the user says
    "check the latest feedback" or "what did we decide about X yesterday".
    This runs 'git pull --ff-only': fast-forward only, never merges.
    If the local branch has diverged, the pull aborts with an error message
    (status: error) rather than creating a merge commit.

    This is the ONLY tool that modifies local filesystem state, and only by
    syncing the clone from the remote. It does NOT push or edit Brain pages.
    """
    return _refresh_brain(_BRAIN_PATH)
