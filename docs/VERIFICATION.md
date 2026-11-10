# Phase 1 Verification Log

Date: 2026-11-10 · Plan: `docs/PHASE-1-PLAN.md` Rev 2 · Coder: Codex CLI 0.167.0 (`gpt-6.1-sol`, direct exec, workspace-write sandbox in v2)
Reviewer: Claude `reviewer` (cross-vendor) · **Security Gate: NOT PASS** (same Windows user; ARCHITECTURE §6.3, §6.6)

## Evidence summary
| Check | Result | Evidence |
|---|---|---|
| Full unit/contract suite | **609 passed / 609**, 610 s | `.venv\Scripts\python.exe -m pytest -q tests` run by orchestrator after fix round 2 |
| Flakiness | 504/504 ×3 after fix round 1 (2 Codex + 1 orchestrator); 571/571 after review fix 1; 609/609 after review fix 2 | run logs in orchestrator scratchpad |
| Scope | `check-plan.cjs` 43/44 rows OK before this file, **no `SCOPE:` lines** | baseline `docs/PHASE-1-PLAN.baseline.json` |
| v1 isolation | v1 `main` @ `75f4561`, 19 pending paths, identical to 2026-11-09 snapshot | `git -C ..\multi-agent-hub status --porcelain` (read-only) |
| Real agent CLIs | **not called** by any test (fakes only); LIVE-A…E not run | `tests/fakes/` |
| Independent review | Round 1 FAIL (1 high, 4 medium, 4 low) → fixed; re-review FAIL (2 medium, 2 low new) → fixed; re-review **PASS** | reviewer reports in session |

Tests per file: adapters 112 · agent_loader 53 · bridge 70 · engine_restart 59 · path_policy 104 · scheduler_quota 9 ·
signing_approval 87 · state_writer 53 · v1_isolation 62.

## Acceptance status
| AC | Unit/contract part | Live part | Status |
|---|---|---|---|
| AC-1 one template set for both vendors | PASS (`test_agent_loader.py`, template parity in `test_adapters.py`) | LIVE-A | **PENDING VERIFICATION** |
| AC-2 cross-vendor spawn via adapters | PASS with fake CLIs (`test_adapters.py`, `test_engine_restart.py`) | LIVE-A | **PENDING VERIFICATION** |
| AC-3 approval cannot be forged | PASS for T1–T5, T9 (`test_signing_approval.py`, `test_bridge.py`, `test_path_policy.py`) | LIVE-B | **NOT PASS (Security Gate)** — T6/T7 open under same user |
| AC-4 concurrent writes + Windows EPERM | PASS (`test_state_writer.py`: 8×200 txns, real sharing violation, crash replay) | none | **PASS** |
| AC-5 restart never duplicates spawns | PASS (`test_engine_restart.py`: double restart, intent respawn cap, orphan adoption by token) | none | **PASS** |
| AC-6 Desktop calls bridge and reads result | PASS for CLI contract (`test_bridge.py`, hook exit 0) | LIVE-C, LIVE-D | **PENDING VERIFICATION** |
| AC-7 Needs-You answer resumes | PASS (relay + owner-signed loops, forged answer rejected) | LIVE-C | **PENDING VERIFICATION** |
| AC-8 quota/scheduler without AI session | PASS (`test_scheduler_quota.py`: verified reset, bounded backoff 15/30/60/120/240, `--once`) | LIVE-E (only if a real limit occurs) | **PENDING VERIFICATION** (real provider fields) |
| AC-9 worktrees outside every repo | PASS (`test_path_policy.py` P1–P8, junction, length) | none | **PASS** |

## Known residual items (accepted, low)
- `runner.py` `finished_at` stamped at poll time → active-time overcount ≤ one tick (safe direction).
- Orphan adoption without `pid.json` relies on run token + vendor cmdline (no exe/create-time check).
- Allowlisted ignored `.pyc`/`__pycache__` could be loaded by the unsandboxed Python test run; marginal vs. existing ability to write tests. Option: run tests with `-B` / `PYTHONDONTWRITEBYTECODE=1`.
- Python-run tests execute coder-authored code with the owner's Windows privileges (ARCH §6.4 T6).
- `HUB_WORKER`/cwd guard in `bridge.py` is deterrence only.

## Before first real use (owner actions, not done)
1. `owner_console.py init` in your own terminal (creates `%USERPROFILE%\.mah-v2-owner\owner.key.enc` + `config/owner.pub`).
2. `owner_console.py sign-policy` and `sign-manifest` — until then `bridge.py` and `engine.py` refuse to run ("could not load owner public key"), by design.
3. Create the data root `ALI\multi-agent-hub-v2-data` (path policy re-checks it).
