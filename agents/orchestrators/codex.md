# Codex as Orchestrator

Entry: open Codex (Desktop or `codex`) in this hub folder and give the task. Codex reads `AGENTS.md` natively.
The hub folder must be a trusted project in Codex so the project `.codex/` folder is loaded (it is on this machine).

## Native subagents (Codex)
- Definitions: `.codex/agents/<role>.toml`, generated from `agents/shared|custom` by `python tools/hub.py sync`
  (no model pinned). Codex multi-agent (`features.multi_agent`) is enabled in the owner's config.
- Spawn a native subagent with the role name as the agent type. Codex does not expose a per-spawn model choice in all
  versions: the subagent then uses the session model. When the assignment needs a specific model or effort, use a
  Codex CLI worker instead: `hub.py delegate --to codex` (exact `-m` and effort, verified from the session file).
- Record each native spawn with `hub.py agent new ... --vendor codex --kind native` and update it when it finishes.

## Cross-vendor: Codex -> Claude
- `python tools/hub.py delegate <task> --to claude --role <role> --model sonnet --effort low|medium|high --brief <file> --reason "..." --parent codex-orchestrator [--cwd <repo>] [--write] [--allow-shell]`
- The Claude CLI needs network access and writes its own session files under the user profile. On this Windows machine
  it ran from the default Codex workspace sandbox (acceptance run 2026-11-11); if a sandbox blocks it, run that one
  command with escalated permission (Codex asks the owner). Do not change the owner's global Codex config for it.
- The record shows the actual Claude model from the CLI's init event; Claude does not report effort (`Unverified`).

## Limits to remember
- Read-only roles run Claude with Read/Glob/Grep only; `--write` adds Edit/Write; Bash only with `--allow-shell`.
- Your own quota: if your session is limited, write the checkpoint and tell the owner to continue in Claude Code.
