---
name: multi-agent-hub
description: Plan and carry out software work in the current project with the active CLI's native agents (Claude Code or Codex), with risk-based independent review and optional portable Hub records.
---
# Multi-Agent Hub

Use the current software project as the task boundary. Read its `AGENTS.md`, `CLAUDE.md` or equivalent and relevant project guidance first. Do not require a Hub project card, dashboard, the other vendor's CLI, a model catalogue, or the optional Python helper for native work.

## Work

Trivial work (a typo, one obvious edit, a status check) stays single-agent: act directly, create no task files, spawn nothing. For larger work, plan the smallest useful set of duties and use the active CLI's native agents where they add value. There is no fixed team size, role list, model, effort, or retry count. Ask the owner when a product decision or scope is unclear.

Native agents: on Claude Code use the `Agent` tool with an explicit `model` and a permission shell, `hub-writer` (may edit) or `hub-readonly` (Read/Grep/Glob only); on Codex use `spawn_agent` with `fork_turns=none`. Never fall back to legacy v1 roles such as `planner`, `reviewer` or `doc-keeper` in `~/.claude/agents`. If the shells are missing, say so (the owner can install them with `tools/install_hub_skill.py --claude`); run read-only work that needs commands through `run.py delegate` without `--write` when the other CLI is verified, otherwise report the limitation. On Codex the same applies: if the `hub-*` shells are missing, say so (owner-run `tools/install_hub_skill.py --codex-agents`), and the permission stays `Unverified` unless observed.

Skills: search the runtime's actual skill catalog (native listing, or `run.py skills`) by task need, read each chosen `SKILL.md` and inspect its requirements before use, and report skills that are missing or unsupported. Do not install third-party skills or dependencies automatically. If `skills/software-component/SKILL.md` exists beside this file, it is the bundled standard for component documentation.

Records are required for nontrivial work, meaning any work that spawns an agent or is rated high risk; trivial work writes none. Before the first spawn write `.multi-agent-hub/<task>/CHECKPOINT.md` (goal, scope, risk rating), then a `briefs/<id>.md` for each agent and an `agents/<id>.md` for each spawn with requested and observed values (`run.py task new`, `run.py agent new` or write the files directly); the final report names the record folder. Skipping them is a defect, not a shortcut. Preserve existing task history when continuing work. Record each agent's duty, skills, vendor, parent and id, requested and observed model/effort, requested permission, observed enforcement, status, and evidence. Keep requested values separate from observed values; use `Unverified` when evidence is unavailable. A requested permission mode describes intent; it does not prove sandbox or tool enforcement. Never write secrets or customer data. Keep records inside the project even when paths contain symlinks. No tool writes Git metadata: if `.multi-agent-hub/` shows as untracked, the final report says so and that it must not be committed (the owner may add it to `.git/info/exclude`); do not change global Git settings or tracked ignore files silently.

Documentation: when a change alters a component's purpose, interface, behaviour, dependencies or operations, the implementer updates that component's documentation in the same task (use `software-component` when available). Internal, behaviour-preserving work changes no documentation. The reviewer checks code-documentation consistency. There is no documentation agent.

Review: rate each change. High risk (money, auth, security, data loss, a public interface, cross-component or non-trivial multi-file logic) requires a fresh independent reviewer before completion: one that neither implemented nor reviewed the change (`fork_turns=none` on Codex, a new `Agent` on Claude Code); never resume a reviewer. Send findings to the implementer, do not fix them yourself, and give the fix a fresh re-review of the fix diff. When a fresh reviewer is impossible, report "not independently reviewed" and why. Lower-risk work needs only your own checks. Run the relevant checks before completing work and report which ran and which did not.

Cross-vendor delegation is optional and only available when its CLI and route are verified. Choose vendor, model, and effort separately for each assignment from what the runtime exposes; native work does not require `models.toml`, and never claim a model, effort, permission mode, or shell unless observable. Read [references/brief.md](references/brief.md) when delegating and make each brief self-contained. Keep work reviewable, preserve unrelated changes, and report checks with exact commands and results. Do not reuse a vendor's session ID with another vendor or reset no-progress history. When a vendor is unavailable, checkpoint current state and hand off from that checkpoint. Resolve `DONE_WITH_CONCERNS`, provide context for `NEEDS_CONTEXT`, and change approach or request an owner decision for `BLOCKED`. A repeated action with the same result is `NO PROGRESS` and needs a different approach.

Running Codex (directly or through the helper) in a new folder makes the Codex CLI add a trust entry to `~/.codex/config.toml`. Compare that file's hash before and after a Codex run and report a change; never edit it.

Skill indexes show discovery only: catalog-only skills are not installed, and another CLI's session-only skills do not establish readiness here. Check real requirements and compatibility. Qwen is optional and never required.

## Optional Hub helper

If Python is available and records/skill indexing would help, run `python <this-skill>/scripts/run.py status` or `python <this-skill>/scripts/run.py skills`. The helper reuses the bundled Hub runtime and writes task records and indexes in the current project. Native work remains available if Python is missing. Portable mode does not support source synchronization or third-party skill installation.
