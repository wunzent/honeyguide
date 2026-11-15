---
name: cheap-delegation
description: "Use when work is mechanical, low-risk and self-contained (bulk edits, doc fixes, log reading, per-file changes): hand it to the cheapest native model to save quota. Defines what fits, what does not, how to write the brief, and how to verify the result."
---

# Cheap delegation

Use the cheapest native model the active CLI exposes for work that is mechanical and cheap to check. Claude Code: `Agent` with `model: haiku` and the `multi-agent-hub:hub-writer` or `multi-agent-hub:hub-readonly` shell. Codex: `spawn_agent` with the cheapest available model (for example `gpt-6-luna`) and `fork_turns=none`.

## What fits

- Trivial work: a typo, one obvious edit, a status check. The orchestrator delegates it instead of doing it itself.
- Bulk renames, formatting, boilerplate, find-replace.
- Search and summarise; reading or condensing logs and files.
- Scaffolding tests, docstrings and comments.
- Running builds, linters or tests and reporting pass or fail.

## What does not fit

- Architecture or design.
- Debugging that needs judgement.
- Security-sensitive edits.
- Anything that needs this conversation's context.
- Work where a wrong cheap edit is costly to catch.

When in doubt, keep the work.

## The brief

- Fully self-contained: absolute paths, explicit inputs, expected outputs and acceptance criteria. No reference to earlier turns.
- Small enough for a small model. Split large jobs into independent per-file or per-directory pieces and run independent pieces in parallel.
- State what the agent must not touch, and ask for a short report of what it changed and what it ran.

## Afterwards

- Always verify the result yourself against the acceptance criteria before reporting it. Cheap-model claims are unverified until checked (re-run the check, read the diff).
- If the result is wrong, fix the brief and delegate again; do not resend the same brief unchanged. Do the work yourself only for non-trivial work, or for trivial work after the cheap agent failed it twice (say so).

## Records

A cheap delegation of low-risk work does not by itself make the task nontrivial: write no records for it unless the task already has a `.multi-agent-hub/<task>/` folder, then add an agent record there. Trivial work never writes records, even when such a folder exists.
