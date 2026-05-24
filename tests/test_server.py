"""
Smoke tests for the FastMCP server — import the tool functions and call them
directly (bypassing MCP transport) by monkey-patching BRAIN_PATH.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest


def _load_server(brain_path: Path):
    """(Re-)import server with ARBLING_BRAIN_PATH set to brain_path."""
    os.environ["ARBLING_BRAIN_PATH"] = str(brain_path)
    import arbling_brain_reader.server as srv_mod

    importlib.reload(srv_mod)
    return srv_mod


def test_server_rejects_bad_brain(tmp_path: Path, fake_brain: Path):
    """Reloading server with an invalid Brain path raises RuntimeError."""
    bad = tmp_path / "notabrain"
    bad.mkdir()
    # Load with a valid brain first so the module is in sys.modules
    srv_mod = _load_server(fake_brain)
    # Now point at a bad path and reload — must raise, not silently fail
    os.environ["ARBLING_BRAIN_PATH"] = str(bad)
    with pytest.raises(RuntimeError, match="does not look like"):
        importlib.reload(srv_mod)


def test_server_brain_status_tool(fake_brain: Path):
    srv = _load_server(fake_brain)
    result = srv.brain_status()
    assert "wiki_page_count" in result
    assert result["wiki_page_count"] >= 1


def test_server_list_pages_tool(fake_brain: Path):
    srv = _load_server(fake_brain)
    pages = srv.list_pages("wiki")
    assert isinstance(pages, list)
    assert len(pages) >= 1


def test_server_list_feedback_rules_tool(fake_brain: Path):
    srv = _load_server(fake_brain)
    rules = srv.list_feedback_rules()
    assert len(rules) == 1
    assert rules[0]["name"] == "no-foo"


def test_server_list_active_plans_tool(fake_brain: Path):
    srv = _load_server(fake_brain)
    plans = srv.list_active_plans()
    assert len(plans) == 1


def test_server_read_brain_page_traversal(fake_brain: Path):
    srv = _load_server(fake_brain)
    with pytest.raises(ValueError):
        srv.read_brain_page("../../../etc/passwd")


def test_server_search_brain_tool(fake_brain: Path):
    srv = _load_server(fake_brain)
    results = srv.search_brain("avoid foo patterns")
    assert isinstance(results, list)
    assert len(results) >= 1
