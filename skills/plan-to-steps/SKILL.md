---
name: plan-to-steps
description: "Use to turn a plan document into ordered, ready steps, each naming the honeyguide skill to run and carrying the step's scope; a step whose scope cannot be carried is marked BLOCKED with the reason."
---

# Plan to steps

Read a plan and emit one ready step per item, so each can be handed to the right skill or agent. Idea from ECC's `plan-orchestrate` skill (affaan-m/ECC, MIT), in our own words. It writes steps; it does not run them.

1. Read the plan the owner names, or the one `plan` wrote (`docs/plans/...` or `.honeyguide/<task>/PLAN.md`). No plan: use `plan` first.
2. For each item emit, in plan order:

       Step <n>: <item in one line>
       Skill: <one name from the table>
       Scope: <files or directories it may change, and what it must not touch>
       Check: <command or observable result that proves the step>
       Depends on: <step numbers, or none>
       Status: READY | BLOCKED (<reason>)

3. Pick the skill from this table:

| Item is | Skill |
|---|---|
| A plan or design still to write | `plan` |
| New behaviour, test-first | `tdd` |
| A new feature or slice | `lean-build` |
| A small bug fix or behaviour change | `surgical-patch` |
| Restructuring with the same behaviour | `safe-refactor` |
| Review of a finished change | `code-review` |
| Security review of a change | `security-scan` |
| Technology-specific knowledge (frontend, backend, database, caching, cloud, devops, debugging, collaboration, testing) | the matching `discover-*` gateway, for example `discover-database` |

4. Carry the scope: each step names its own files, its own check and what it leaves alone, copied from the plan. When the plan does not give that (no files, no check, an owner decision pending, a dependency not done), mark the step BLOCKED with the reason; do not invent scope.
5. End with the list of BLOCKED steps and the question that would unblock each. Wait for the owner's go-ahead before running any step.

Steps that touch the same file are ordered, never parallel. Independent read-only steps (reviews) may run in parallel. Running the steps follows `orchestrate`: records, fresh reviewers for high-risk work, owner approval for commit and push.
