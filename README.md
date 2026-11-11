# Multi-Agent Hub (minimal native, Claude Code + Codex)

A small shared workspace in which **Claude Code or Codex** acts as the orchestrator, builds a task-specific team from a
shared agent library, delegates within and across vendors, and keeps readable records and checkpoints.
There is no engine, scheduler, dashboard or approval ceremony: planning, skills and subagents are the CLIs' own.

## Start a task
**From Claude Code:** open this folder in Claude Code (Desktop Code tab or `claude`) and describe the task.
**From Codex:** open this folder in Codex (Desktop or `codex`) and describe the task.
Example: "Task: add input validation to `<repo>/src/x.ts`; working directory `<repo>`; tests must pass."
The orchestrator follows `AGENTS.md`: it creates `work/<task>/CHECKPOINT.md`, picks roles, models and efforts,
delegates, records every agent and reports the result.

To continue a task in the other vendor (quota, preference): "Continue task `<slug>` from `work/<slug>/CHECKPOINT.md`."

## What you can inspect
| What | Where |
|---|---|
| Agents of a task (role, vendor, requested/actual model and effort, status) | `python tools/hub.py status <task>` or `work/<task>/agents/*.md` |
| Task state, remaining work, failures tried | `work/<task>/CHECKPOINT.md` |
| Worker output | `work/<task>/agents/<id>.last.md` |
| Reusable roles | `agents/INVENTORY.md`, `agents/shared/`, `agents/custom/` |
| Orchestrator rules | `AGENTS.md` (both), `CLAUDE.md`, `agents/orchestrators/` |
| Models allowed for routing | `models.toml` |

## Maintenance
- Edit roles in `agents/shared|custom/*.md` or skills in `skills/`, then `python tools/hub.py sync`
  (regenerates `.claude/agents`, `.codex/agents`, `.claude/skills`, `.agents/skills`; `--check` shows drift).
- Python: `.venv\Scripts\python.exe` (stdlib only; `pytest` for `tests/test_hub.py`). Create with
  `py -3.11 -m venv .venv` and `.venv\Scripts\pip install -r requirements.txt` on a new machine.
- `gpt-6-luna` and `haiku` are listed as unverified in `models.toml`; move one to `verified` only after a live check.

## Limits (honest)
- Prompt rules are not enforcement: file limits come from the CLI sandbox (Codex `-s read-only|workspace-write`) and
  tool permissions (Claude `--allowedTools`). Claude Code has no OS sandbox.
- Codex -> Claude delegation needs network and writes under the user profile, which the Codex workspace sandbox blocks:
  approve that command's escalation when Codex asks.
- Native subagent model/effort is not always reported back; records say `Unverified` instead of guessing.
- Quota detection is text-based (usage-limit messages and exit codes); the handoff itself is the orchestrator's job.
- History: `docs/legacy/` (old engine docs and evidence), `docs/WORKLOG.md`, `docs/REBUILD-INVENTORY.md`.
