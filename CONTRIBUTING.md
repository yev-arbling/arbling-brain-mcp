# Contributing to arbling-brain-reader

## Development setup

```sh
git clone https://github.com/yev-arbling/arbling-brain-mcp.git
cd arbling-brain-mcp
pip install -e ".[dev]"
```

Run tests:

```sh
pytest
```

Set `ARBLING_BRAIN_PATH` to a real Brain before running the server locally:

```sh
# macOS/Linux
ARBLING_BRAIN_PATH=~/arbling-brain arbling-brain-reader

# Windows PowerShell
$env:ARBLING_BRAIN_PATH = "C:\Users\you\arbling-brain"; arbling-brain-reader
```

## Releasing a new version (Yevgeniy or Kairat)

Releases are fully automated via GitHub Actions + PyPI Trusted Publishing.
No tokens, no secrets — just a git tag.

### One-time PyPI setup (already done for v0.1.0)

1. Go to https://pypi.org/manage/project/arbling-brain-reader/settings/publishing/
2. Click **Add a new publisher**
3. Fill in:
   - Owner: `yev-arbling`
   - Repository: `arbling-brain-mcp`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
4. Save. That's it — no token needed from this point on.

### Releasing a patch/minor/major

```sh
# 1. Bump the version in pyproject.toml
#    [project]
#    version = "0.1.1"   ← change this

# 2. Commit the bump
git add pyproject.toml
git commit -m "chore: bump version to 0.1.1"

# 3. Tag and push — Actions picks this up automatically
git tag v0.1.1
git push origin main --tags
```

GitHub Actions will:
1. Build `arbling_brain_reader-0.1.1.tar.gz` and the `.whl`
2. Publish both to PyPI via OIDC (no credentials needed in the workflow)
3. The new version appears at https://pypi.org/project/arbling-brain-reader/

### Watching the release

Go to https://github.com/yev-arbling/arbling-brain-mcp/actions and open the
**Release to PyPI** run. If it fails, fix the issue and re-tag:

```sh
git tag -d v0.1.1               # delete local tag
git push origin :refs/tags/v0.1.1   # delete remote tag
# fix the issue, re-commit if needed
git tag v0.1.1
git push origin main --tags
```

## Adding a new tool

1. Implement the pure function in `src/arbling_brain_reader/brain.py`.
2. Register it in `src/arbling_brain_reader/server.py` with `@mcp.tool()`.
3. Add happy-path + error-path tests in `tests/test_brain.py` and a server
   smoke test in `tests/test_server.py`.
4. Update the tool table in `README.md`.
5. Never add a tool that writes, deletes, or edits Brain pages — read-only
   is a hard constraint. The single exception (`refresh_brain`) only runs
   `git pull --ff-only` to sync the local clone, never modifying wiki/ content.

## Hard constraints

- **Read-only**: no Write, Edit, or Delete tools that touch Brain pages.
- **No telemetry**: no outbound network calls from `brain.py` or `server.py`.
- **No secrets in code**: credentials live in env vars, never committed.
- **Path safety**: every tool that accepts a path must call `_safe_resolve()`.
