# Claude Code as Orchestrator

Entry: open Claude Code (Desktop Code tab or `claude`) in this hub folder and give the task. `CLAUDE.md` loads `AGENTS.md`.

## Native subagents (Claude)
- Definitions: `.claude/agents/<role>.md`, generated from `agents/shared|custom` by `python tools/hub.py sync`
  (no model pinned: you choose per spawn).
- Spawn with the Agent tool: `subagent_type` = role name, `model` = `sonnet` (default) or `opus` (premium, needs a reason).
  `haiku` is unverified: do not use it. Effort cannot be set per native spawn; it is recorded as `Unverified`.
- Before the spawn: `hub.py agent new ... --vendor claude --kind native`; after: `hub.py agent update ... --status done|failed --result "..."`.
  The actual model of a native subagent is not reported back reliably; leave `Actual model` as `Unverified` unless you
  read it from the subagent transcript.
- Parallel spawns only for independent read-only work or disjoint files.
- Agent tool subagents start without your conversation; the prompt is the brief path plus one line of context.
  Fix rounds: resume the same subagent with SendMessage (its id from the spawn result) and the findings verbatim.
  Cross-vendor workers cannot be resumed: re-delegate with the brief, the report file and the findings.

## Cross-vendor: Claude -> Codex
- `python tools/hub.py delegate <task> --to codex --role <role> --model gpt-6.1-sol --effort low|medium|high --brief <file> --reason "..." --parent claude-orchestrator [--cwd <repo>] [--write]`
- The worker runs `codex exec` with the exact model/effort (`-s read-only`, or `workspace-write` with `--write`), and the
  record shows the actual model/effort from the Codex session file.
- Long runs: start the command in the background and continue other work; you are notified when it ends.

## Limits to remember
- Claude Code permissions are not an OS sandbox. For Claude CLI workers, hub.py restricts tools (read-only roles get
  Read/Glob/Grep; `--write` adds Edit/Write; Bash only with `--allow-shell`).
- Your own quota: if your session is limited, write the checkpoint and tell the owner to continue in Codex
  ("continue task <slug> from work/<slug>/CHECKPOINT.md").
