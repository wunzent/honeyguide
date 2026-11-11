@AGENTS.md

## Claude Code specifics
- Read `agents/orchestrators/claude-code.md` before your first delegation in a session.
- This project's dynamic routing (AGENTS.md sections 2-3) applies here: roles are not tied to a vendor or model.
- Spawn native subagents with the Agent tool using the generated definitions in `.claude/agents/` and always pass an
  explicit `model`; record each spawn with `tools/hub.py agent new/update`.
- Delegate to Codex with `tools/hub.py delegate ... --to codex`. Python: `.venv\Scripts\python.exe` (or `py -3.11`).
