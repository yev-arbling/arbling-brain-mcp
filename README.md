# arbling-brain-reader

A read-only MCP (Model Context Protocol) server that exposes any Arbling-schema
markdown vault — a "Second Brain" — to Claude Code, Cowork, and any other MCP
client. The server has zero Arbling-specific data hardcoded: it reads whatever
path `ARBLING_BRAIN_PATH` points to. The vault data stays in its own private
repository; this package is the generic plumbing.

Any team can adapt this for their own markdown vault as long as it follows the
Arbling Brain schema conventions (`CLAUDE.md` + `wiki/` + per-folder `INDEX.md`
+ YAML frontmatter on every page).

---

## For team members joining an existing vault (5-step onboarding)

```sh
# 1. Make sure you have GitHub access to the private vault repo as a collaborator.
#    (CEO / owner adds you in repo Settings → Collaborators)

# 2. Clone the vault locally — this is the data the MCP will serve.
git clone https://github.com/<owner>/<vault-repo>.git ~/<vault-folder>

# 3. Install the MCP server (public, no auth required).
pip install arbling-brain-reader
# or for ephemeral use (no install):
# uvx arbling-brain-reader

# 4. Add to your Claude Code config — see "Claude Code config" below.

# 5. (Optional but recommended) Set up a background refresh so the local
#    clone stays in sync with what the team commits — see "Keeping fresh" below.
```

---

## Claude Code config

Add to `~/.claude.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "arbling-brain": {
      "command": "uvx",
      "args": ["arbling-brain-reader"],
      "env": {
        "ARBLING_BRAIN_PATH": "/absolute/path/to/Arbling-Brain"
      }
    }
  }
}
```

Or using the CLI:

```sh
claude mcp add arbling-brain -s user \
  -e ARBLING_BRAIN_PATH=/absolute/path/to/Arbling-Brain \
  -- uvx arbling-brain-reader
```

Windows path example:

```json
"ARBLING_BRAIN_PATH": "C:\\Users\\you\\Downloads\\Arbling-Brain"
```

---

## Cowork / desktop app config

In the Anthropic desktop app (Claude for Desktop), open **Settings → MCP Servers**
and add:

```json
{
  "arbling-brain": {
    "command": "uvx",
    "args": ["arbling-brain-reader"],
    "env": {
      "ARBLING_BRAIN_PATH": "/absolute/path/to/Arbling-Brain"
    }
  }
}
```

---

## Tool reference

| Tool | What it does | When to call it |
|------|-------------|-----------------|
| `brain_status()` | Returns path, page count, last git commit SHA + date | First thing in a session — verifies Brain is reachable and shows how stale it is |
| `read_brain_page(relative_path)` | Returns full markdown of any Brain page | When you need the complete content of a specific page |
| `search_brain(query, scope, max_results)` | Full-text search; returns file + line + snippet | When you know what you're looking for but not which page it's in |
| `list_pages(folder)` | Lists all .md files under a folder | To enumerate a domain before deciding which pages to read |
| `read_index(folder)` | Returns INDEX.md or README.md for a folder | Fast domain orientation — read the index, then pick which pages to follow |
| `list_feedback_rules()` | Returns all CEO feedback rules with one-line summaries | Load all behavioral rules at session start |
| `list_active_plans()` | Returns active plans with title/status/owner/updated | See what initiatives are in flight before starting work |
| `latest_retrospective()` | Returns the most recent retrospective | Pick up pending items from the last session |
| `refresh_brain()` | Runs `git pull --ff-only` on the local clone | When you suspect the local clone is stale — say "refresh the brain" or "git pull the brain first" |

---

## Keeping the local clone fresh — 3 options

### Option A: Manual

```sh
cd ~/arbling-brain && git pull
```

Run before important sessions. No setup required.

---

### Option B: In-session refresh

Ask Claude to call the `refresh_brain()` MCP tool. Works from any agent session
without leaving the chat. Say:

> *"refresh the brain"*
> *"git pull the brain first"*
> *"check the latest feedback"*

---

### Option C: Background auto-pull

One-time setup, then forget. Pulls the vault on a schedule.

**macOS (launchd)** — create `~/Library/LaunchAgents/com.arbling.brain-sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.arbling.brain-sync</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/git</string>
    <string>-C</string>
    <string>/Users/<your-username>/arbling-brain</string>
    <string>pull</string>
    <string>--ff-only</string>
  </array>
  <key>StartInterval</key><integer>3600</integer>
  <key>StandardOutPath</key><string>/tmp/arbling-brain-sync.log</string>
  <key>StandardErrorPath</key><string>/tmp/arbling-brain-sync.log</string>
</dict>
</plist>
```

Then load it:

```sh
launchctl load ~/Library/LaunchAgents/com.arbling.brain-sync.plist
```

Pulls every hour. Tail `/tmp/arbling-brain-sync.log` to verify.

---

**Linux (cron)** — add to `crontab -e`:

```
0 * * * * cd ~/arbling-brain && git pull --ff-only >> /tmp/arbling-brain-sync.log 2>&1
```

---

**Windows (Task Scheduler)** — create `C:\Users\<you>\arbling-brain-sync.bat`:

```bat
@echo off
cd /d "C:\Users\<you>\arbling-brain"
git pull --ff-only >> "%TEMP%\arbling-brain-sync.log" 2>&1
```

Then in Task Scheduler: Create Basic Task → Trigger: Daily, Repeat every 1 hour
→ Action: Start a program → `C:\Users\<you>\arbling-brain-sync.bat`.

---

## Privacy

Pages under `wiki/ceo/` may contain investor data, runway figures, and
CEO-private strategic information. The MCP server is **read-only** — it cannot
write or delete any Brain pages. Access to the underlying vault content is
controlled at the GitHub repository level (collaborator list on the private vault
repo), not by this MCP server. Anyone with read access to the vault repo can use
this server to query it.

---

## Development

```sh
git clone https://github.com/yev-arbling/arbling-brain-mcp.git
cd arbling-brain-mcp
pip install -e ".[dev]"
pytest
```

Set `ARBLING_BRAIN_PATH` to point at a real (or fake) Brain before running the
server:

```sh
ARBLING_BRAIN_PATH=/path/to/brain arbling-brain-reader
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
