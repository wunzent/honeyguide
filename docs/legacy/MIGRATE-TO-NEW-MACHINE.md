# Move multi-agent-hub-v2 to a new machine

## Current status at bundle time (2026-11-10) — IN PROGRESS
- **Phase 1: PENDING LIVE VERIFICATION. Security Gate: NOT PASS.**
- Committed (in the bundle): `de6eff6` baseline · `22d08c9` remove signing · `f610661` LIVE-A fixes F1–F5 ·
  `4bfb5d0` reviewer fixes L1–L4 · plus the documentation commit that adds this guide and `docs/SESSION-AUDIT.md`.
- **Not in the bundle (work in progress, uncommitted on the old machine):** the Claude worker isolation + N1 fix round
  (`adapters/claude_cli.py`, `engine.py`, `runner.py`, tests) and the latest `docs/VERIFICATION.md` notes (LIVE-A re-run
  T-2 results, LIVE-E deferral). Finish and commit them on the old machine and make a new bundle, or redo them on the new one.
- Verified so far: LIVE-A (real Codex + Claude) PASS; LIVE-A re-run T-2: R2–R6 PASS, R1 FAIL (plugins still load in the
  Claude worker; failed closed as designed) → isolation fix round in progress.
- Still required for Phase 1: minimal R1 live check, LIVE-B, LIVE-C, LIVE-D (each needs owner approval).
  LIVE-E: SIMULATED RECOVERY only (unit tests); REAL QUOTA RECOVERY: DEFERRED / NOT LIVE VERIFIED (owner decision).
- Future planning (not written yet): Phase 3–5 blueprints. Existing: `docs/PHASE-2-BLUEPRINT.md`, `docs/SESSION-AUDIT.md` §2.
- Bundle file: `C:\Users\Natthawut.j\Desktop\ALI\multi-agent-hub-v2.bundle` (branch `master`).

Owner plan: switch machines by Friday 2026-11-13 (or earlier). v2 has **no git remote** (push is owner-only), so the
code moves as a **git bundle** file. Nothing here touches v1.

## What moves and what does not
| Item | Moves? | How |
|---|---|---|
| Source + full git history (`master`) | yes | `git bundle` file |
| Docs (ARCHITECTURE, plans, VERIFICATION, WORKLOG, SESSION-AUDIT …) | yes | committed docs are in the bundle; commit or copy any uncommitted ones first |
| `.venv` | no | recreate from `requirements.lock` |
| `projects/`, `runtime/` (task state, LIVE-A evidence) | optional | copy the folder if you want the history; not needed to run |
| Data root `ALI\multi-agent-hub-v2-data` (worktrees) | no | recreated empty; LIVE-A worktree is throwaway |
| Old key files (`config/owner.pub*`, `config/policy.toml.sig`, `%USERPROFILE%\.mah-v2-owner`) | no | not used any more |
| Claude / Codex logins | no | log in again on the new machine |
| Provider session history (`~/.codex/sessions`, `~/.claude/projects`) | no | not needed by the hub |

## On the old machine (before Friday)
```bash
cd C:\Users\Natthawut.j\Desktop\ALI\multi-agent-hub-v2
```
```bash
git status --short
```
(commit pending docs first via the orchestrator, then:)
```bash
git bundle create ..\multi-agent-hub-v2.bundle --all
```
```bash
git bundle verify ..\multi-agent-hub-v2.bundle
```
Copy `C:\Users\Natthawut.j\Desktop\ALI\multi-agent-hub-v2.bundle` (and optionally `projects\`) to the new machine
(USB / OneDrive / network share).

## On the new machine
1. Install Git, Python 3.11 (`py -3.11` must work), Claude Code CLI and Codex CLI; log in to both
   (`claude auth status`, `codex login status`).
2. Clone and set up:
```bash
git clone -b master multi-agent-hub-v2.bundle C:\Users\<you>\Desktop\ALI\multi-agent-hub-v2
```
(The clone's `origin` points at the bundle file; there is still no real remote — push stays owner-only.)
```bash
cd C:\Users\<you>\Desktop\ALI\multi-agent-hub-v2
```
```bash
py -3.11 -m venv .venv
```
```bash
.venv\Scripts\python.exe -m pip install -r requirements.lock
```
3. Check `config/policy.toml` `[paths]`: `data_root` and `deny` contain `C:\Users\Natthawut.j\...`. If the user name or
   folder differs, ask the orchestrator to update them (a policy edit invalidates old approvals — expected).
4. Create the data root folder, then verify:
```bash
.venv\Scripts\python.exe -m pytest -q tests
```
```bash
.venv\Scripts\python.exe bridge.py status
```
5. Open the folder in Claude Desktop (Code) or Codex Desktop and continue from `docs/VERIFICATION.md`.

## Not portable / check after the move
- Windows paths in `config/policy.toml` and in any copied `projects/*/project.md`.
- `.claude/settings.json` hook path uses `.venv\Scripts\python.exe` (relative) — works after step 2.
