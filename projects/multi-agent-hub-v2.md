# multi-agent-hub-v2
Path: C:\Users\Natthawut.j\Desktop\ALI\multi-agent-hub-v2    Default branch: main (no remote)
Summary: the hub itself - orchestrator instructions, dynamic duties, permission shells, skill discovery and `tools/hub.py`.
Lets Claude Code or Codex orchestrate a team of native and cross-vendor agents with readable records, vendor-neutral
checkpoints and cross-vendor delegation. Used by the owner only, on Windows.

## Stack
Python 3.11 standard library only (`tools/hub.py`); pytest for tests; Markdown/TOML agent definitions.

## Layout
`AGENTS.md`, `CLAUDE.md`, `LEARNED.md` (instructions) - `agents/shells|orchestrators` (shells and guides) -
`skills/` (hub skills, edit these) - `.claude/`, `.codex/`, `.agents/` (GENERATED from sync; .hub-local stays local) - `tools/hub.py` -
`tests/test_hub.py` - `projects/` (project cards) - `docs/` - `work/` (local task records, git-ignored).

## Commands
- Python: `.venv\Scripts\python.exe` (`python` is the Microsoft Store stub)
- Test: `.venv\Scripts\python.exe -m pytest -q tests`
- Generated files: `.venv\Scripts\python.exe tools/hub.py sync` then `... sync --check` (must be clean)
- Skill discovery: `... tools/hub.py skills` -> `work/skills-index.md`
- Approved local install: `... tools/hub.py skills install` (git required; `skills/external.toml`)

## Conventions
Use the task's owner-approved branch/worktree; commit only when asked; stage explicit files, never `git add -A`; `.claude/settings.local.json` is
the owner's and stays untracked. Edit sources, never generated files. English in files.

## Route here
Changes to orchestration rules, roles, skills, delegation, checkpoints, agent records, cross-vendor routing.

## Not here
`../multi-agent-hub` (v1, read-only reference); product code of other repositories.

## Decisions
- 2026-11-11: minimal native rebuild; no retry budget, dashboard, signing or custom engine.
- 2026-11-12: EGM and improve installed globally by owner decision; superpowers ideas adopted without installing.
- 2026-11-12: assignment duties replace fixed role files; two shells per vendor, dynamic discovery and approved local
  third-party copies with .hub-local/exclude; no global changes or unclear-licence files in commits.
