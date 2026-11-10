# Phase 1 Verification Log

## Update 2026-11-10 — remove-signing (`docs/PLAN-REMOVE-SIGNING.md` Rev 2)
| Check | Result |
|---|---|
| Slice A (signing/owner console removed, `approvals.py`, `hashing.py`, auto commit) | Codex 636/636 |
| Slice B (settings, rules, requirements, `.gitignore`, app banner, tests) | orchestrator full suite **640/640** (811 s) |
| Leftover references | no `signing`/`cryptography`/`verify_record`/`public_key`/`owner_console` in code; only 2 test lines asserting their absence; lock has no `cryptography`/`cffi`/`pycparser` |
| Runs without keys | `bridge.py status` → `{"ok": true}`; key/signature files left on disk untouched and gitignored |
| v1 | `75f4561`, 19 pending paths, unchanged |
| Review | fresh Claude reviewer **PASS**; 1 medium (`approve-scope` reset task status) + 1 low test gap → fix round (see below); 1 low (this file stale) → fixed here |

AC-3 now reads: *agent output and worker contexts cannot record an approval; approvals are conversational records bound to
plan + policy hash* — unit part PASS (`tests/test_approvals.py`, `tests/test_bridge.py`); **not an identity proof**;
Security Gate **NOT PASS**. Owner key setup below is **no longer required** (superseded).

Commit of the remove-signing change: `22d08c989fe790794f13a325df116a76e3f3443f` (663/663, reviewer PASS).

## LIVE-A — 2026-11-10 14:26–14:28 (owner approval: "อนุมัติ LIVE-A")
Throwaway target repo (session scratchpad, outside every repo), project `live-a`, task `T-1` ("create hello.txt").
Routes set by a test harness (see F1): coder `codex/gpt-6.1-sol/low`, reviewer `claude/sonnet/low`, `--max-budget-usd 0.50`.

| Expected | Result | Evidence |
|---|---|---|
| E1 one template set | prompt.md rendered from `agents/coder.md` / `agents/reviewer.md` for both vendors | runs `R-…c50a`, `R-…31b1` |
| E2 Codex coder run | **PASS** — intent → started (pid, create_time, token) → finished ok, exit 0, ~32 s; `hello.txt` = `hello` only in worktree `…-v2-data\worktrees\live-a\T-1` | events 8–14 |
| E3 Claude reviewer run | **PASS with finding F3** — ok, verdict PASS, 5 turns, **$0.085**; tool calls only Read/Glob/Grep; no Bash/Edit/Write available | events 19–24 |
| E4 trusted test | **PASS** — Python ran pytest, exit 0, 1.1 s | `test-log.txt`, event 15 |
| E5 scope | **PASS** — only `hello.txt` changed; no violation | event 26 |
| E6 cleanup / isolation | **PASS** — 0 hub processes left; v1 `75f4561`/19 unchanged; v2 tracked files unchanged; target `main` unchanged; no remote | before/after check |
| E7 real stream formats | **PASS** — both parsed as ok; no misclassification | outcomes |
| Auto commit | **PASS** — `05edb11` on `hub/T-1` in the worktree, files `[hello.txt]`, message states verification status; no push/merge | event 26 |
Codex usage: 59,599 input tokens (43,392 cached), 152 output. End-to-end ~70 s.

### LIVE-A findings (need an approved fix round)
| ID | Severity | Finding | Fix |
|---|---|---|---|
| F1 | medium | `bridge.py propose-route` is stored (`route_proposal`) but never read by the engine; routes come only from policy defaults, so the orchestrator cannot choose model/effort/budget | engine/model_router consume `route_proposal` per role (validated by router) |
| F2 | medium | `session_id` is redacted by `scrub()` in state/events/meta (`[REDACTED]`), so resume after a quota limit or lost run cannot work in real use | exempt `session_id` fields from scrubbing (keep scrubbing free text) |
| F3 | medium | Claude worker had extra tools available: Cron*, RemoteTrigger, SendMessage, Skill, EnterWorktree, PushNotification and **Claude Docs MCP create/update/delete** (external writes). `--allowedTools` pre-approves but does not restrict | add `--tools Read,Glob,Grep`, `--strict-mcp-config` (no MCP), `--disable-slash-commands`; assert in tests |
| F4 | low | Codex launched through `codex.cmd` → recorded exe is `cmd.exe`; stopping the PID may leave the child `node codex.js` | launch `node …/codex.js` directly or stop the whole process tree (own tree only) |
| F5 | low | `meta.md` lacks argv and prompt-body hash, so E1/E3 evidence must be read from other files | write argv (scrubbed) + prompt sha256 to meta.md |

**Fix round F1–F5 (owner-approved, 2026-11-10):** all five implemented by Codex; focused 175/175, full suite **726/726**
(orchestrator); Claude cross-vendor review **PASS** (static). Status: F1 fixed · F2 fixed · **F3 fixed in code, live
behaviour PENDING VERIFICATION** (needs one real Claude run to confirm `--tools`/`--strict-mcp-config`/
`--disable-slash-commands` actually restrict the init tool list; the run fails closed if not) · F4 fixed (fake process
tree; real `codex.js` layout PENDING) · F5 fixed.
Reviewer low issues (not fixed; need owner approval for a further round): L1 last `session_id` node may be null and drop
a valid earlier one (fails safe, loses resume) · L2 `build()` does not re-validate `resume_session` · L3 `route.rejected`
logged every tick · L4 init check ignores `slash_commands`/`skills`/`agents` fields.

AC status after LIVE-A: AC-1 **PASS (live)**, AC-2 **PASS (live)**; AC-3/6/7/8 unchanged (pending LIVE-B/C/D/E). Security Gate NOT PASS.

The sections below are the original Phase 1 record (signing era) and are kept as history.

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

## Before first real use
1. ~~Owner key setup (init / sign-policy / sign-manifest)~~ — **superseded 2026-11-10**: signing removed; no key setup needed.
2. Data root `ALI\multi-agent-hub-v2-data` — created by the owner 2026-11-10.
