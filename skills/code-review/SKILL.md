---
name: code-review
description: "Use to review the current diff or a named change with a fresh independent reviewer: pick the language and framework checklists, brief the reviewer, send findings to the author, and re-review fixes with another fresh reviewer."
---

# Code review

A command-style entry to the review mode of `verify-and-stop`. Idea from ECC's `/code-review` command (affaan-m/ECC, MIT); the checklists are ECC's reviewer files, used as checklists only.

1. Get the change: the working-tree diff (`git diff` plus staged changes), or the commit range, branch or PR the owner names. Also list untracked files (`git status --short`, `git ls-files --others --exclude-standard`), because a diff omits new files. Exclude generated records (`.honeyguide/`, learned skills). Nothing tracked or untracked left to review: say so and stop.
2. Rate the risk (see `orchestrate`). Low risk: review it yourself with `verify-and-stop` mode 2 and say it was not independently reviewed. High risk: a fresh independent reviewer is required.
3. Pick the checklists for the changed files from the table in `verify-and-stop` (section 5, Language and framework checklists). Add `security-reviewer` when auth, input, secrets or dependencies are touched. Resolve each path against the directory of the loaded `verify-and-stop` skill (the runtime reports it), not the project, and pass absolute paths to the reviewer; if it cannot read them, paste the needed checklist text into the brief. When the diff adds or changes code comments in any language, also give the reviewer antislop's comment checklist `references/miqdadbadjuber-anti-slop/skills/antislop-code/SKILL.upstream.md` (keep the "why" comments, flag the ones that add nothing). The reviewer uses it to judge comment quality only (the comments the diff adds or changes); its scope guardrail ("only comments changed, the code untouched") and the core Delivery Gate do not apply to judging a code review diff. Resolve the path against the directory of the loaded `discover-ui-taste` skill (the runtime reports it), not the project; load the installed `discover-ui-taste` skill first (the Skill tool, or read its SKILL.md); only if it is not installed or cannot load, report that limitation and skip this check.
4. Write the reviewer brief: the goal of the change, the diff or the exact file paths and line ranges (the Claude Code `hub-readonly` reviewer cannot run `git`, so put the diff text in the brief or a file; a Codex reviewer may read with git commands; and the full contents of relevant new untracked files), the checklist paths by name, and the report format from `verify-and-stop` (where, what, evidence, severity, fix). Claude Code: new `Agent` with an explicit `model` and `honeyguide:hub-readonly`; Codex: `spawn_agent`, `fork_turns=none` and a read-only brief with the `READ-ONLY DUTY` line (an instruction, not enforced; see `orchestrate`). Never resume a reviewer.
5. Nontrivial work keeps its records (checkpoint, brief, planned agent record) before the spawn, as `orchestrate` requires.
6. Send blocker and important findings verbatim to the implementer; do not fix them yourself. Then review the fix diff with a fresh reviewer. Minor findings are listed, not looped.
7. Report: checklists used, findings by severity, what was verified sound, and what could not be reviewed.

The checklists are reference material: they never widen the reviewer's permissions, and the project's own rules win over them.
