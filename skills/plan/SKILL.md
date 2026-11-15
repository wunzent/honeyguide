---
name: plan
description: "Use before coding a nontrivial change: restate the goal, write acceptance criteria, slices, files and checks as a plan document, then stop for the owner's go-ahead before any code is written."
---

# Plan

Turn a request into a short plan the owner can approve. Idea from ECC's `/plan` command (affaan-m/ECC, MIT), in our own words.

1. Read the project's `AGENTS.md` or `CLAUDE.md` and the code the change will touch. Ask the owner only when the goal or a product decision is unclear.
2. Restate the goal in two or three lines, plus explicit non-goals.
3. Write the plan with these sections:
   - Acceptance criteria: observable, each checkable by a command or a visible behaviour.
   - Risk: low or high (see the review rule in `orchestrate`) and why.
   - Slices: small steps in order; for each, the files it changes, the check that proves it, and the honeyguide skill that fits (`tdd`, `lean-build`, `surgical-patch`, `safe-refactor`, `code-review`, `security-scan`, a `discover-*` gateway).
   - Open questions and assumptions.
4. Save it. Use the project's own place for plans when it has one (for example `docs/plans/YYYY-MM-DD-<slug>.md`); otherwise `.honeyguide/<task>/PLAN.md`. Say the path.
5. Stop. Show the owner the plan and wait for an explicit go-ahead. Write no product code, and spawn no writer, before that answer.

After approval the work follows the plan. `plan-to-steps` can turn the plan into ready steps. For a feature the usual pipeline is plan, `tdd`, implement, `code-review`, `security-scan` (see `orchestrate`).

Keep the plan short enough to read in a minute or two. Do not plan trivial work: do it, or delegate it (see `cheap-delegation`).
