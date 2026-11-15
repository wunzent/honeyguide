---
name: tasks
description: "Use for work with 3 or more steps: turn the plan into a trackable task list file (tasks.md) with ordered IDs, phases, dependencies, parallel markers and the honeyguide skill for each task; a task whose scope cannot be carried is written as BLOCKED."
---

# Tasks

Read a plan and write one trackable task list, so each task can be handed to the right skill or agent and ticked off when verified. The task-list idea comes from github/spec-kit (MIT) and the skill-per-step routing from ECC's `plan-orchestrate` (affaan-m/ECC, MIT); the text here is our own. It writes the list; it does not run it.

Use it only for work with 3 or more steps. Smaller work needs no task list, and trivial work goes straight to cheap delegation (see `orchestrate`).

## Steps

1. Read the plan the owner names, or the one `plan` wrote (`docs/plans/...` or `.honeyguide/<task>/PLAN.md`), an egm plan or a spec. No plan: use `plan` first.
2. Write `.honeyguide/<task>/tasks.md`, or put it next to the project's own plan document when the project keeps plans in the repo. Header: source plan path, date, one-line goal.
3. Group the tasks in phases, in this order: Setup, Build, Review. Build holds one task per slice of behaviour. Review always holds a `code-review` task and, when auth, input, secrets, data or dependencies are touched, a `security-scan` task.
4. Write one line per task:

       - [ ] T001 [P] <short description> (after: T00x, ...) -> skill: <honeyguide skill> guide: <skill> files: <paths>

   - IDs run T001, T002, ... in execution order.
   - `(after: ...)` lists the tasks it depends on; leave it out when there is none.
   - `skill:` names an existing honeyguide skill; `guide:` is optional, Build tasks only, and names existing skills (or a `discover-*` gateway), comma separated; `files:` lists every path the task may touch, tests and source alike, and nothing else.
   - Every task keeps its full line (description, dependencies, skill, files) while its prerequisites are pending.
5. Pick the skill. Every Build task that changes code or tests routes `skill: tdd`: it owns the whole test-first cycle (red, green, refactor) for one slice, so its `files:` lists both the test files and the source files. Do not split tests and implementation into separate tasks. A Build task may add `guide:` naming the skill that sets its size and scope discipline; `skill:` stays `tdd`. Only a Setup task that changes no behaviour (config, scaffolding, dependencies) routes to `lean-build`.

| Item is | Skill or guide |
|---|---|
| A plan or design still to write | `plan` |
| Build task, one slice of code and tests (always the skill) | `tdd` |
| Setup task that changes no behaviour: config, scaffolding, dependencies | `lean-build` |
| Guide for a Build task adding new behaviour | `lean-build` |
| Guide for a narrow bug fix or behaviour change | `surgical-patch` |
| Guide for restructuring with the same behaviour | `safe-refactor` |
| Review of a finished change (Review phase) | `code-review` |
| Security review of a change (Review phase) | `security-scan` |
| Technology-specific knowledge (frontend, backend, database, caching, cloud, devops, debugging, collaboration, testing), as a guide | the matching `discover-*` gateway, for example `discover-database` |

6. Ready and parallel. A task is ready when every task in its `after:` is ticked `[x]`. `[P]` means the task may run alongside other `[P]` tasks of the same phase once it is ready, and only when their `files:` are disjoint; two tasks that share a file never both carry `[P]`. After each verified tick, re-check which tasks are now ready and which `[P]` tasks may start together.
7. `BLOCKED` is only for a task whose scope cannot be carried: unclear files, no check, or an owner decision pending. Write it as `- [ ] T00x BLOCKED: <reason>`, do not dispatch it and do not invent scope. A task that merely waits for prerequisites is not blocked; it keeps its full line. End with the BLOCKED tasks and the question that would unblock each, and wait for the owner's go-ahead before running any task.

A task is ticked `[x]` only after the orchestrator verified its result. Running the tasks follows `orchestrate`: records, fresh reviewers for high-risk work, owner approval for commit and push.

## Example

A valid `tasks.md`, snapshot taken after T001 was verified:

```tasks.md
# Tasks: add rate limiting to login
Source plan: .honeyguide/rate-limit/PLAN.md | Date: 2026-11-16 | Goal: limit login attempts per IP

## Setup
- [x] T001 Add rate-limit config keys -> skill: lean-build files: config/limits.ts

## Build
- [ ] T002 [P] Limiter module with its unit tests (after: T001) -> skill: tdd guide: lean-build files: src/limiter.ts, tests/limiter.test.ts
- [ ] T003 [P] Login 429 response with its integration test (after: T001) -> skill: tdd guide: surgical-patch files: src/routes/login.ts, tests/login.test.ts
- [ ] T004 BLOCKED: lockout duration for repeat offenders is an owner decision

## Review
- [ ] T005 Review the diff (after: T002, T003) -> skill: code-review files: src/limiter.ts, src/routes/login.ts
- [ ] T006 Security review of the auth path (after: T002, T003) -> skill: security-scan files: src/routes/login.ts
```
