# Multi-Agent Hub (minimal native, Claude Code + Codex)

## Portable Codex skill
Install the owned native-first skill with `python tools/install_hub_skill.py` for Codex, `--vendor claude` for Claude Code, or `--vendor both` for both native user locations. `--dest <skill-directory>` remains available for a chosen path and cannot be combined with non-default vendor selection. Invoke `$multi-agent-hub` in Codex or `/multi-agent-hub` in Claude Code. Re-run the same command to update managed copies; prior versions are retained outside scanned skill directories. It needs no Hub project card or dashboard. The optional helper writes `.multi-agent-hub` task data in the current project and reuses the existing Hub runtime. Native work remains available without Python. Installation does not configure the CLI or install third-party skills.

A small shared workspace in which **Claude Code or Codex** acts as the orchestrator, builds a team with duties defined
per assignment and two generic permission shells, delegates within and across vendors, and keeps readable records and checkpoints.
There is no engine, scheduler, dashboard or approval ceremony: planning, skills and subagents are the CLIs' own.

Native spawning also follows the active runtime and Owner policies. If an Owner policy requires explicit consent, the user can authorize task-level delegation by asking the orchestrator to use Hub and delegate when its risk assessment calls for review; no fixed business roles or team are needed. Otherwise, required review remains BLOCKED. The installer refuses unmanaged, modified, or differently shaped managed packages. Do not blindly overwrite a larger or newer package installed by another worktree; use an isolated destination and preserve that package.

## Start a task
**From Claude Code:** open this folder in Claude Code (Desktop Code tab or `claude`) and describe the task.
**From Codex:** open this folder in Codex (Desktop or `codex`) and describe the task.
Example: "Task: add input validation to `<repo>/src/x.ts`; working directory `<repo>`; tests must pass."
The orchestrator follows `AGENTS.md`: it creates `work/<task>/CHECKPOINT.md`, picks duties, models and efforts,
delegates, records every agent and reports the result.

**Legacy repository mode (optional):** open this Hub repository and use the commands below to manage Hub-rooted records and maintenance surfaces.

To continue a task in the other vendor (quota, preference): "Continue task `<slug>` from `work/<slug>/CHECKPOINT.md`."

## What you can inspect
| What | Where |
|---|---|
| Agents of a task (duty, skills, vendor, requested/actual model and effort, status) | `python tools/hub.py status <task>` or `work/<task>/agents/*.md` |
| Task state, remaining work, failures tried | `work/<task>/CHECKPOINT.md` |
| Worker output | `work/<task>/agents/<id>.last.md` |
| Permission shells and duty notes | `agents/INVENTORY.md`, `agents/shells/`, `skills/brief/SKILL.md` |
| Discovered skills | `python tools/hub.py skills` -> local `work/skills-index.md` |
| Approved third-party sources | `skills/external.toml`; `skills/EXTERNAL.md` |
| Orchestrator rules | `AGENTS.md` (both), `CLAUDE.md`, `agents/orchestrators/` |
| Models allowed for routing | `models.toml` |

## Maintenance
- Edit shells in `agents/shells/*.md` or hub-owned skills in `skills/`, then `python tools/hub.py sync`
  (regenerates `.claude/agents`, `.codex/agents`, `.claude/skills`, `.agents/skills`; `--check` shows drift).
- Python: `.venv\Scripts\python.exe` (stdlib only; `pytest` for `tests/test_hub.py`). Create with
  `py -3.11 -m venv .venv` and `.venv\Scripts\pip install -r requirements.txt` on a new machine.
- Discover all project/user/plugin skills with `python tools/hub.py skills`; it prints counts and the index path.
  Read selected SKILL.md files, check requirements and native availability. After owner approval, `... skills install`
  clones pinned sources to ignored `.hub/vendor/` and copies supported skills into `.claude/skills` and `.agents/skills`.
  Local copies have `.hub-local` and git info/exclude entries; `sync --check` lists them as `LOCAL SKILL`, not drift.
  A linked worktree's outside-scope info/exclude is reported for the orchestrator to handle. Globals are untouched;
  unclear-licence copies never belong in commits. See `skills/EXTERNAL.md`.
- Plugin catalogs are shown as not installed and excluded from available counts; plugin cache activation is unverified.
  Read-only duties needing commands use Codex hub-readonly or `hub.py delegate`; Claude native hub-readonly has no Bash.
- Either vendor works alone with native/same-vendor CLI workers; with both, cross-vendor delegation and quota handoff work.
- `models.toml` is the routing catalog; use only verified models and record actual values when observable.

## Limits (honest)
- Prompt rules are not enforcement: file limits come from the CLI sandbox (Codex `-s read-only|workspace-write`) and
  tool permissions (Claude `--allowedTools`). Claude Code has no OS sandbox.
- Codex -> Claude delegation needs network and writes under the user profile. In the acceptance run it worked from the
  default Codex workspace sandbox on this Windows machine; other setups may block it - then approve the escalation Codex asks for.
- Native subagent model/effort is not always reported back; records say `Unverified` instead of guessing.
- Quota detection is text-based (usage-limit messages and exit codes); the handoff itself is the orchestrator's job.
- Acceptance evidence: `docs/ACCEPTANCE.md`; research reuse: `docs/SKILLS-REUSE.md`.
- History: `docs/WORKLOG.md`, `docs/REBUILD-INVENTORY.md`. The previous version (engine, docs, evidence) is only in git
  history before `1f1d677` and in the backup `ALI/multi-agent-hub-v2-backups/20261111-173509/`.
