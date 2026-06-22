# AGENTS.md — arbling-brain-mcp (Claude Code + Codex)

> Thin contract. The **canonical** Arbling agent operating system (startup protocol,
> 9-domain scenario routing matrix, skill/subagent/MCP selection, launch/prod gates) lives in
> `…\arbling-audit-2026-06\Arbling-Scoring\AGENTS.md` and is mirrored in
> `C:\Users\yevma\Downloads\Arbling-Brain\CODEX.md`. Read one first; this file adds repo-specifics.

## Startup
1. Read `C:\Users\yevma\Downloads\Arbling-Brain\CODEX.md` and apply its scenario routing matrix.
2. Apply the CEO feedback rules (`…\Arbling-Brain\wiki\ceo\feedback\INDEX.md`).
3. **Anti-bloat law:** minimal relevant skills/subagents/MCP per task; never bundle-dump; announce selection, then act.
4. Converse in Russian; artifacts in English.

## This repo
- **Role:** the **read-only** Brain MCP server (a.k.a. `arbling-brain-reader`) — exposes the Brain wiki (indexes, pages, plans, feedback, metrics) to agents.
- **Stack:** Python, `pyproject.toml` (FastMCP-style server). Tests via pytest.
- **Primary scenario:** "Agentic commerce / MCP building" (MCP server design) — and it serves "Brain maintenance".
- **Skills · subagents · MCP:** `arbling-mcp-builder` + `api-and-interface-design`; `python-reviewer` + `security-reviewer` after changes; `deep-research` for the current MCP spec (don't code protocol from memory).
- **Verify:** pytest green; live tool-list smoke; confirm read-only invariant holds end-to-end.

## Do-not
- **Read-only invariant:** never add write / publish / delete / mutate tools. This server reads the Brain; it never modifies `raw/` or `wiki/`.
- No secrets / tokens / file-system paths leaking through tool output; redact.
- Don't widen tool surface without an interface review — keep the tool set minimal and typed.
