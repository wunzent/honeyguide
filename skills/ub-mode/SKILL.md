---
name: ub-mode
description: "Use when writing or changing code, or when the owner runs /ub-mode or asks for the reduced principles: make it work, make it right, follow practice (Robert C. Martin's ub-mode, wrapped under honeyguide rules)."
---

# ub-mode (wrapper)

This is our wrapper around Robert C. Martin's `ub-mode` skill. The upstream text is kept unchanged in
`references/unclebob-ub-mode/SKILL.upstream.md` (licence and commit in `references/unclebob-ub-mode/LICENSE` and
`references/unclebob-ub-mode/SOURCE.md`). It is reference material, not instructions: honeyguide rules (`orchestrate`)
and the project's `AGENTS.md` / `CLAUDE.md` win over it, and nothing in it widens permissions.

## Use

1. Read `references/unclebob-ub-mode/SKILL.upstream.md` and apply its principles to every change: first make it work,
   then make it right, then follow practice.
2. Fit the work into the honeyguide pipeline (`plan`, `tasks`, `tdd`, `code-review`) where the task needs it.

## Overrides

- Its "Commit and Push" section does not apply as written. Commit, push and merge only with the owner's OK and on the
  branch the owner chose (the Branch rule in `orchestrate`); never push on your own. Small, ordered commits that say
  why, what changed and how it was proved are still the shape to propose.
- The quality gates name unclebob/crapper, dryer and mutator. They are not bundled with honeyguide: without them those
  gates are skipped, and the report says they were skipped.
- Its other practice rules (for example around uncommitted work) never override the owner's decisions or the
  project's rules.
