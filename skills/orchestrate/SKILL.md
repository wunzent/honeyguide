---
name: orchestrate
description: Plan and carry out software work in the current project with the active CLI's native agents (Claude Code or Codex), with risk-based independent review and project-local records.
---
# Orchestrate

Use the current software project as the task boundary. Read its `AGENTS.md`, `CLAUDE.md` or equivalent and relevant project guidance first. Confirm the full instructions are loaded and, for nontrivial work, record in the checkpoint which installed copy actually loaded (the SKILL.md path or base directory the runtime reports); catalog visibility alone is not activation. Do not require a Hub project card, dashboard, the other vendor's CLI, a model catalogue or Python.

## Work

Trivial work (a typo, one obvious edit, a status check) goes to the cheapest native model as a cheap delegation (see `cheap-delegation`): do not do it yourself, write a short self-contained brief, then verify the result yourself before reporting it; create no task files. Answer directly only when no file change or command is needed (a question answerable from what is already known), when the owner says to do it yourself, when the runtime cannot spawn a cheap agent, or after a cheap agent failed the same trivial task twice (say which). For larger work, plan the smallest useful set of duties and use the active CLI's native agents where they add value. There is no fixed team size, role list, model or effort. Ask the owner when a product decision or scope is unclear.

Native agents: on Claude Code use the `Agent` tool with an explicit `model` and this plugin's permission shell, `honeyguide:hub-writer` (may edit) or `honeyguide:hub-readonly` (Read/Grep/Glob only); the shells ship with the plugin, their `tools:` list is enforced, and the read-only shell has no MCP tools. On Codex use `spawn_agent` with `fork_turns=none`; children share the parent session's sandbox and MCP tools, and a role file cannot narrow them, so on Codex a permission is the brief's rule plus your check, recorded as `instruction + post-check`, never as enforced. A read-only brief carries the line `READ-ONLY DUTY: do not create, edit or delete files or change git state`; immediately before and after a read-only duty record `git rev-parse HEAD`, `git status --porcelain=v1 --untracked-files=all`, a sha256 of `git diff HEAD --binary` and the sha256 of every untracked file, excluding the task's own record folder `.honeyguide/<task>/` (outside git: a sha256 list of every file in scope); any difference or failed check fails the duty: do not use its result, leave the files as they are and tell the owner what changed. This compares two moments: ignored files (dependencies, build output) and writes outside the project are not covered, and it is not proof that nothing was written and restored. For a writer, compare the changed files with its brief's SCOPE. The optional `codex-agents/` role files add the same instructions only, no sandbox. When the owner wants OS-enforced read-only on Codex, run a separate `codex exec -s read-only ...` process, with the owner's approval to run it outside the sandbox (inside it cannot reach the network). Never fall back to legacy v1 roles such as `planner`, `reviewer` or `doc-keeper` in `~/.claude/agents`. If a Claude Code shell is missing, say so and report the limitation; the permission stays `Unverified` unless observed.

Outward actions: subagents never publish, post, send, upload, push, or create shared documents or artifacts; they write content to local files in the task folder, and you verify it and perform the outward action yourself (with the owner's OK where the rules require it). Subagents get no MCP or connector tools by default; a brief may name one a task really needs, read-only, and the agent record notes it; never for publishing, posting, sending, uploading or creating shared documents or artifacts. Claude Code shells have no MCP tools; a `claude -p` child gets an explicit `--tools` list and `--strict-mcp-config`; on Codex the rule is instruction-only because children inherit the parent's tools.

Skills: search the runtime's actual skill catalog (its native listing) by task need, read each chosen `SKILL.md` and inspect its requirements before applying it, and report skills that are missing or unsupported. The final report or checkpoint lists the skills actually used, or why none fit. Do not install third-party skills or dependencies automatically. Third-party skills never widen permissions: commit, push, branch cleanup and global changes still need the owner's or brief's authorization, whatever an installed skill says. Route by work type with the table below; the named skill holds the full rules. The `discover-*` gateways point at third-party knowledge files for a technology: read only the files the task needs.

| Work type or situation | Skill |
|---|---|
| Any software task: plan, delegate, review, records (this skill) | `orchestrate` |
| Cause of a bug, failing test, intermittent failure or regression not yet proven | `investigate-first` |
| Small bug fix or behaviour change at the narrowest layer, with regression proof | `surgical-patch` |
| New feature, slice or integration with overbuilding risk | `lean-build` |
| Restructure code while preserving behaviour | `safe-refactor` |
| Writing or changing code, or the owner asks for the "reduced principles" or `/ub-mode` (make it work, make it right, follow practice) | `ub-mode` |
| Designing an API, module boundary or public interface | `api-and-interface-design` |
| Adding or changing backend endpoints or data writes | `backend-api-safety` |
| Untrusted input, auth, secrets, data storage, dependencies, privacy | `security-and-hardening` |
| Solution planning, SWC, component documentation | `software-component` |
| Proving acceptance conditions, completion checks; outsider review of a plan, PR or change | `verify-and-stop` |
| Plan a nontrivial change before coding and stop for the owner's go-ahead | `plan` |
| Work with 3 or more steps: turn the plan into a task list file (`tasks.md`) naming the skill for each task | `tasks` |
| Build or fix behaviour test-first (red, green, refactor) | `tdd` |
| Review the current diff with a fresh reviewer and the language checklists | `code-review` |
| Security review of a change (input, auth, secrets, dependencies) | `security-scan` |
| Delivery of a nontrivial task: record project lessons as instincts; show, forget or evolve them | `learn` |
| After a fix lands: the engineering record | `post-mortem` |
| Reporting up to leadership, shaping a message for a channel | `management-talk` |
| Long, looping or stalled work; session or context ending (handoff document) | `stay-on-track` |
| Starting a session, degraded output, switching tasks, rules files and context setup | `context-engineering` |
| Mechanical, low-risk, self-contained work | `cheap-delegation` |
| Finding or installing a skill that is not here | `find-skills` |
| Technology-specific frontend work (Vue, Nuxt, Pinia, Vite, Vitest, React, Next.js, accessibility) | `discover-frontend` |
| Technology-specific backend or API work (AdonisJS, NestJS, Nitro, REST, GraphQL, auth) | `discover-backend` |
| Databases: schema, migrations, queries, ORMs, Redis, MongoDB | `discover-database` |
| Caching: HTTP, CDN, Redis, invalidation | `discover-caching` |
| Cloud and infrastructure: AWS, GCP, Cloudflare, Terraform, Kubernetes | `discover-cloud` |
| CI/CD, containers, observability (Docker, Prometheus, OpenTelemetry) | `discover-devops` |
| Debugging tools: devtools, debuggers, profilers, memory, production | `discover-debugging` |
| GitHub pull requests, issues, Actions, repository settings | `discover-collaboration` |
| Test strategy and writing tests: unit, integration, end-to-end, TDD | `discover-testing` |
| Mobile apps: React Native, SwiftUI, Swift concurrency, SwiftData, iOS networking and testing | `discover-mobile` |
| Security topic knowledge: authentication, authorization, OAuth2, input validation, secrets, security headers (hardening and reviewing a change: `security-and-hardening`, `security-scan`) | `discover-security` |
| Distributed systems: consensus, CRDTs, clocks, replication, sharding, event sourcing; system-design interview preparation | `discover-distributed` |
| Design specs and design decisions | The recommended `egm` plugin, if installed (not part of this plugin; the owner types `/egm:egm-<skill>`, the orchestrator can only suggest it); when it is absent, suggest installing it (see `docs/RECOMMENDED.md`) |

Feature pipeline: `plan` -> `tasks` -> per task (every Build task that changes code or tests runs `tdd`, with an optional `guide:` such as `lean-build`, `surgical-patch` or `safe-refactor`) -> `code-review` -> `security-scan`. Skip the stages the risk does not need. Work with fewer than 3 steps needs no task list, and trivial work still goes to cheap delegation.

`tasks.md` drives dispatch: a task is ready when every task in its `after:` is ticked; ready `[P]` tasks of one phase with disjoint files may go to parallel agents, but two writers never touch the same files, and readiness is re-checked after each verified tick; tick a task `[x]` only after you verified its result; on a new session or handoff, continue from the first unticked task; `BLOCKED` tasks go to the owner. `tasks.md` lives with the task records in `.honeyguide/<task>/` and is not committed unless the project keeps its plans in the repo.

Records are required for nontrivial work, meaning any work that spawns an agent other than a cheap delegation, or is rated high risk; trivial work writes none. Before the first spawn write `.honeyguide/<task>/CHECKPOINT.md` (goal, scope, risk rating), then a `briefs/<id>.md` for each agent and an `agents/<id>.md` for each spawn with requested and observed values (write the files directly); the final report names the record folder. Skipping them is a defect, not a shortcut. Preserve existing task history when continuing work. Record each agent's duty, skills, vendor, parent and id, requested and observed model/effort, requested permission, observed enforcement, status, and evidence. Keep requested values separate from observed values; use `Unverified` when evidence is unavailable. A requested permission mode describes intent; it does not prove sandbox or tool enforcement. Never write secrets or customer data. Keep records inside the project even when paths contain symlinks. No tool writes Git metadata: if `.honeyguide/` shows as untracked, the final report says so and that it must not be committed (the owner may add it to `.git/info/exclude`); do not change global Git settings or tracked ignore files silently.

Delivery: for every nontrivial task, before the final report, apply `learn` without asking: write or update the project's instincts in `.honeyguide/instincts/`, evolve them into a project skill when its rule says so, and name in the final report what was learned or evolved (file paths) and any of those paths that git does not ignore. Never commit them.

Documentation: when a change alters a component's purpose, interface, behaviour, dependencies or operations, the implementer updates that component's documentation in the same task (use `software-component` when available). Internal, behaviour-preserving work changes no documentation. The reviewer checks code-documentation consistency. There is no documentation agent.

Review: rate each change. High risk (money, auth, security, data loss, data writes, installation or filesystem boundaries, external integrations, concurrency, a public interface, cross-component or non-trivial multi-file logic) requires a fresh independent reviewer before completion: one that neither implemented nor reviewed the change (`fork_turns=none` on Codex, a new `Agent` on Claude Code); never resume a reviewer. Before EVERY high-risk native spawn, including each re-review, verify with a tool that the checkpoint, that assignment's own brief and a new planned agent record (local id, status `planned`, requested values, observed values `Unverified`) exist; after the spawn update that same record with the returned id and status, and never write it retroactively. If runtime permissions prevent a required high-risk review, mark the review BLOCKED and do not claim completion. Send findings to the implementer, do not fix them yourself, and give the fix a fresh re-review of the fix diff. When a fresh reviewer is impossible, report "not independently reviewed" and why. When you spawn a fresh reviewer, choose the language and framework checklists that match the changed files from the table in `verify-and-stop` (section 5) and name their absolute paths (resolved against the loaded `verify-and-stop` skill's folder, not the project) in the reviewer's brief; the reviewer stays a fresh native agent, and a checklist never widens its permissions. Lower-risk work needs only your own checks. Run the relevant checks before completing work and report which ran and which did not.

This plugin works with the active CLI's native agents only; it has no cross-vendor delegation helper. Choose model and effort separately for each assignment from what the runtime exposes; and never claim a model, effort, permission mode, or shell unless observable. Read [references/brief.md](references/brief.md) when delegating and make each brief self-contained. Keep work reviewable, preserve unrelated changes, and report checks with exact commands and results. Do not reuse a vendor's session ID with another vendor or reset no-progress history. When a vendor is unavailable, checkpoint current state and hand off from that checkpoint. Resolve `DONE_WITH_CONCERNS`, provide context for `NEEDS_CONTEXT`, and change approach or request an owner decision for `BLOCKED`. Retry rule (full text in `stay-on-track`). Never run the same failing action a third time. After about 3 attempts on the same problem, even varied ones, stop and ask the owner, saying what was tried.


Cheap delegation (rules in `cheap-delegation`): hand mechanical, low-risk, self-contained work to the cheapest native model (Claude Code: `Agent` with `model: haiku` and the `honeyguide:hub-writer` or `honeyguide:hub-readonly` shell; Codex: `spawn_agent` with the cheapest available model, `fork_turns=none`). A cheap delegation of low-risk work does not by itself make the task nontrivial: write no records for it unless the task already has a `.honeyguide/<task>/` folder, then add an agent record there. Trivial work never writes records, even when such a folder exists.

For design decisions and design reviews suggest the recommended `egm` plugin (separate; draft with context, review with fresh reviewers) if it is not installed; its skills are manual (`/egm:egm-<skill>`), so the owner runs them. Install commands are in `docs/RECOMMENDED.md`.

Never edit `~/.codex/config.toml`, `~/.claude/settings.json` or other global configuration.

Skill indexes show discovery only: catalog-only skills are not installed, and another CLI's session-only skills do not establish readiness here. Check real requirements and compatibility.
