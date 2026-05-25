"""
Core Brain read logic: path resolution, frontmatter parsing, search, git helpers.
No FastMCP imports here — this module is pure functions, easy to unit-test.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Literal

import frontmatter as fm


def get_brain_path() -> Path:
    raw = os.environ.get("ARBLING_BRAIN_PATH", "~/Brain")
    return Path(raw).expanduser().resolve()


def validate_brain(path: Path) -> None:
    missing = []
    if not (path / "CLAUDE.md").exists():
        missing.append("CLAUDE.md")
    if not (path / "wiki").is_dir():
        missing.append("wiki/")
    if missing:
        raise RuntimeError(
            f"ARBLING_BRAIN_PATH={path} does not look like an Arbling Brain "
            f"(missing {', '.join(missing)})"
        )


def _safe_resolve(relative_path: str, brain_path: Path) -> Path:
    """Resolve relative_path against brain_path, rejecting traversal."""
    if ".." in Path(relative_path).parts:
        raise ValueError(f"Path traversal rejected: {relative_path!r}")
    if os.path.isabs(relative_path):
        raise ValueError(f"Absolute paths rejected: {relative_path!r}")
    resolved = (brain_path / relative_path).resolve()
    brain_resolved = brain_path.resolve()
    # Ensure resolved is strictly under brain_resolved
    try:
        resolved.relative_to(brain_resolved)
    except ValueError:
        raise ValueError(f"Path {relative_path!r} escapes Brain root")
    return resolved


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def brain_status(brain_path: Path) -> dict:
    wiki_dir = brain_path / "wiki"
    raw_dir = brain_path / "raw"
    wiki_count = len(list(wiki_dir.glob("**/*.md"))) if wiki_dir.is_dir() else 0
    raw_count = len(list(raw_dir.glob("**/*"))) if raw_dir.is_dir() else 0

    sha = date = message = "unknown"
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H%x1f%ci%x1f%s"],
            cwd=brain_path,
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split("\x1f")
            sha = parts[0] if parts else "unknown"
            date = parts[1] if len(parts) > 1 else "unknown"
            message = parts[2] if len(parts) > 2 else "unknown"
    except Exception:
        pass

    return {
        "path": str(brain_path),
        "wiki_page_count": wiki_count,
        "raw_file_count": raw_count,
        "last_commit_sha": sha,
        "last_commit_date": date,
        "last_commit_message": message,
    }


def read_brain_page(relative_path: str, brain_path: Path) -> str:
    path = _safe_resolve(relative_path, brain_path)
    if not path.exists():
        raise FileNotFoundError(f"Page not found: {relative_path!r}")
    return path.read_text(encoding="utf-8")


def search_brain(
    query: str,
    scope: Literal["wiki", "raw", "all"],
    max_results: int,
    brain_path: Path,
) -> list[dict]:
    if scope == "wiki":
        search_root = brain_path / "wiki"
    elif scope == "raw":
        search_root = brain_path / "raw"
    else:
        search_root = brain_path

    if not search_root.is_dir():
        return []

    matches = _rg_search(query, search_root, brain_path, max_results)
    if matches is None:
        matches = _python_search(query, search_root, brain_path, max_results)
    return matches


def _rg_search(
    query: str, search_root: Path, brain_path: Path, max_results: int
) -> list[dict] | None:
    """Try ripgrep JSON search; return None if rg not available."""
    try:
        result = subprocess.run(
            [
                "rg",
                "--json",
                "--ignore-case",
                "--glob",
                "*.md",
                query,
                str(search_root),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        return None  # rg not installed

    matches: list[dict] = []
    current_context: list[str] = []
    current_file = current_line = None

    for raw_line in result.stdout.splitlines():
        try:
            obj = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "match":
            data = obj["data"]
            file_path = data["path"].get("text", "")
            line_number = data.get("line_number", 0)
            line_text = data["lines"].get("text", "").rstrip("\n")
            try:
                rel = Path(file_path).relative_to(brain_path)
            except ValueError:
                rel = Path(file_path)
            matches.append(
                {
                    "file": str(rel).replace("\\", "/"),
                    "line_number": line_number,
                    "snippet": line_text,
                    "score": 1.0,
                }
            )
            if len(matches) >= max_results:
                break

    return matches


def _python_search(
    query: str, search_root: Path, brain_path: Path, max_results: int
) -> list[dict]:
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    matches: list[dict] = []
    for md_file in sorted(search_root.glob("**/*.md")):
        try:
            lines = md_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines):
            if pattern.search(line):
                try:
                    rel = md_file.relative_to(brain_path)
                except ValueError:
                    rel = md_file
                snippet = line.rstrip()
                if i + 1 < len(lines):
                    snippet += "\n" + lines[i + 1].rstrip()
                matches.append(
                    {
                        "file": str(rel).replace("\\", "/"),
                        "line_number": i + 1,
                        "snippet": snippet,
                        "score": 1.0,
                    }
                )
                if len(matches) >= max_results:
                    return matches
    return matches


def list_pages(folder: str, brain_path: Path) -> list[str]:
    folder_path = _safe_resolve(folder, brain_path)
    if not folder_path.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder!r}")
    pages = sorted(
        str(p.relative_to(brain_path)).replace("\\", "/")
        for p in folder_path.glob("**/*.md")
    )
    return pages


def read_index(folder: str, brain_path: Path) -> str:
    folder_path = _safe_resolve(folder, brain_path)
    for candidate in ("INDEX.md", "README.md"):
        p = folder_path / candidate
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError(
        f"No INDEX.md or README.md found in {folder!r}"
    )


def list_feedback_rules(brain_path: Path) -> list[dict]:
    feedback_dir = brain_path / "wiki" / "ceo" / "feedback"
    if not feedback_dir.is_dir():
        return []
    rules = []
    for md_file in sorted(feedback_dir.glob("*.md")):
        if md_file.name in ("INDEX.md", "README.md"):
            continue
        try:
            post = fm.load(str(md_file))
        except Exception:
            post = None

        summary = ""
        content = post.content if post else md_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                summary = stripped
                break

        try:
            rel = md_file.relative_to(brain_path)
        except ValueError:
            rel = md_file
        rules.append(
            {
                "name": md_file.stem,
                "file": str(rel).replace("\\", "/"),
                "summary": summary,
            }
        )
    return rules


def list_active_plans(brain_path: Path) -> list[dict]:
    plans_dir = brain_path / "wiki" / "plans"
    if not plans_dir.is_dir():
        return []
    active = []
    for md_file in sorted(plans_dir.glob("*.md")):
        if md_file.name in ("INDEX.md", "README.md"):
            continue
        try:
            post = fm.load(str(md_file))
            meta = post.metadata
        except Exception:
            continue
        if str(meta.get("status", "")).lower() != "active":
            continue
        active.append(
            {
                "file": str(md_file.relative_to(brain_path)).replace("\\", "/"),
                "title": meta.get("title", md_file.stem),
                "status": meta.get("status", ""),
                "owner": meta.get("owner", ""),
                "updated": str(meta.get("updated", "")),
            }
        )
    return active


def latest_retrospective(brain_path: Path) -> dict:
    retro_dir = brain_path / "wiki" / "retrospectives"
    if not retro_dir.is_dir():
        raise FileNotFoundError("wiki/retrospectives/ directory not found")

    candidates = [
        f
        for f in sorted(retro_dir.glob("*.md"), reverse=True)
        if f.name not in ("INDEX.md", "README.md")
    ]
    if not candidates:
        raise FileNotFoundError("No retrospective files found")

    md_file = candidates[0]
    try:
        post = fm.load(str(md_file))
        meta = post.metadata
        content = post.content
    except Exception:
        meta = {}
        content = md_file.read_text(encoding="utf-8")

    return {
        "file": str(md_file.relative_to(brain_path)).replace("\\", "/"),
        "title": meta.get("title", md_file.stem),
        "created": str(meta.get("created", "")),
        "content": content,
    }


def refresh_brain(brain_path: Path) -> dict:
    # Capture old SHA before pull
    old_sha = "unknown"
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=brain_path,
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        if r.returncode == 0:
            old_sha = r.stdout.strip()
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=brain_path,
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return {"status": "error", "message": "git not found in PATH"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "git pull timed out after 60s"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    if result.returncode != 0:
        return {
            "status": "error",
            "message": (result.stderr or result.stdout).strip(),
        }

    new_sha = old_sha
    try:
        r2 = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=brain_path,
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        if r2.returncode == 0:
            new_sha = r2.stdout.strip()
    except Exception:
        pass

    # Count files changed between old and new SHA
    files_changed: list[str] = []
    if old_sha != new_sha and old_sha != "unknown":
        try:
            diff = subprocess.run(
                ["git", "diff", "--name-only", old_sha, new_sha],
                cwd=brain_path,
                capture_output=True,
                text=True,
                timeout=10,
                stdin=subprocess.DEVNULL,
            )
            if diff.returncode == 0:
                files_changed = [f for f in diff.stdout.strip().splitlines() if f]
        except Exception:
            pass

    already_current = "Already up to date" in result.stdout or "Already up-to-date" in result.stdout
    return {
        "old_sha": old_sha,
        "new_sha": new_sha,
        "files_changed": files_changed,
        "status": "already_current" if already_current and old_sha == new_sha else "updated",
    }
