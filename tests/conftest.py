"""Shared fixtures: creates a minimal fake Brain in tmp_path."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

FEEDBACK_CONTENT = """\
---
name: no-foo
type: feedback
created: 2026-05-23
updated: 2026-05-23
tags: [ceo, communication]
---

# No foo — avoid foo patterns

Skip foo. Lead with bar.

**Why:** It wastes time.

**How to apply:**
- Do not foo
"""

PLAN_CONTENT = """\
---
title: Test Plan
type: plan
status: active
created: 2026-05-23
updated: 2026-05-23
owner: Yevgeniy
---

# Test Plan

Some plan content.
"""

RETRO_CONTENT = """\
---
title: Test Retro
type: retrospective
created: 2026-05-23
updated: 2026-05-23
---

# Test Retro

Session went well.
"""

WIKI_INDEX = """\
---
title: Master Index
type: index
created: 2026-05-23
updated: 2026-05-23
---

# Arbling Wiki — Master Index

Meta-router.
"""

CLAUDE_MD = """\
# Arbling Second Brain — Schema

## Company Context
Test company context.
"""


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.email=test@test.com", "-c", "user.name=Test", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def fake_brain(tmp_path: Path) -> Path:
    """A minimal git-initialised fake Brain."""
    brain = tmp_path / "brain"
    brain.mkdir()

    (brain / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")
    (brain / "wiki").mkdir()
    (brain / "wiki" / "index.md").write_text(WIKI_INDEX, encoding="utf-8")

    feedback = brain / "wiki" / "ceo" / "feedback"
    feedback.mkdir(parents=True)
    (feedback / "no-foo.md").write_text(FEEDBACK_CONTENT, encoding="utf-8")

    plans = brain / "wiki" / "plans"
    plans.mkdir(parents=True)
    (plans / "2026-05-23-test.md").write_text(PLAN_CONTENT, encoding="utf-8")

    retros = brain / "wiki" / "retrospectives"
    retros.mkdir(parents=True)
    (retros / "2026-05-23-test.md").write_text(RETRO_CONTENT, encoding="utf-8")

    # Initialise as a real git repo so brain_status and refresh_brain work
    _git(["-c", "init.defaultBranch=main", "init"], brain)
    _git(["add", "."], brain)
    _git(["commit", "-m", "initial brain"], brain)

    return brain
