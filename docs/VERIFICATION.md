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

F1–F5 commit: `f610661df40dbea39baffc5a48d9b29f2de0e7ab` (726/726).
**Fix round L1–L4 (owner-approved, 2026-11-10):** L1 session id never overwritten by empty/invalid · L2 resume id
re-validated in `build()` (invalid → refused + needs-you) · L3 `route.rejected` deduplicated · L4 Claude init check
covers `slash_commands`, `terminal_slash_commands`, `skills`, `plugins` (must be empty), `agents` (allowed only without
Agent/Task), missing key = violation — based on the real Claude Code 2.1.312 init schema from LIVE-A. Full suite
**852/852** (orchestrator); Claude review **PASS**; no real paths/ids in fixtures; v1 unchanged.
Open notes (low, owner decision): N1 a resume whose route vendor/model changed starts fresh with `session.resume_refused`
event (not needs-you); N2 benign `session_id: null` also emits `session.invalid` (noise only).
Live confirmation of F3/L4/F4 → `docs/LIVE-A-RERUN-PROCEDURE.md` (needs separate approval).

## LIVE-A re-run T-2 — 2026-11-10 17:09–17:11 (owner approval: "APPROVED — LIVE-A RE-RUN ONLY…")
No harness: routes via `bridge.py propose-route` (coder codex/gpt-6.1-sol/low; reviewer claude/sonnet/low, budget $0.50).
Plan deviation (narrower): T-2 plan = "create hello.txt" instead of "append world" (target `main` has no hello.txt; allowed_paths = hello.txt).

| Check | Result | Evidence |
|---|---|---|
| R1 Claude lockdown | **FAIL → correctly failed closed.** Real init under `--tools Read,Glob,Grep --strict-mcp-config --disable-slash-commands`: tools = **Glob, Grep, Read only** ✔, mcp_servers 0 ✔, slash_commands 0 ✔, skills 0 ✔, agents 27 (allowed: no Agent/Task) — but **plugins = 16 still loaded** ✘ and `terminal_slash_commands` key **absent** ✘ (unverifiable). Run marked failed, result discarded, `security.tool_violation` {terminal_slash_commands: -1, plugins: 16}, task → needs-you | run `R-20261110101044-67be`, events 24–26 |
| R2 Codex launch | **PASS** — exe `…\nvm\v26.12.1\node.exe`, argv contains `codex.js` | event 10, meta.md |
| R3 routing | **PASS** — coder and reviewer routes = proposals; Claude budget 0.5 in route; no `route.rejected` | events 6–9, 19–20 |
| R4 session ids | **PASS** — verbatim UUIDs stored (`01a1c4ef-…`, `8000bd51-…`) | events 13, 25 |
| R5 meta.md | **PASS** — argv, prompt_sha256, body_sha256, executable, budget; no prompt text, no run_token, no secrets | both runs |
| R6 no unauthorized change | **PASS** — no commit (blocked before commit, as required); `hello.txt` only in worktree `hub/T-2`; target `main` 875b7f3, v1 75f4561/19 and v2 tracked files unchanged; 0 hub processes left | before/after |
Cost: Claude **$0.0305** (3 tool calls: Read, Glob, Read). Codex coder ok in ~32 s; Python tests PASS (0.9 s).

Remaining issue (blocks Claude workers): plugins still load with these flags. Plugins can register hooks that run
commands inside the Claude process regardless of `--tools`, so this is a real gap, not noise. Corrective options (need
owner approval + a live check): (a) add `--bare` (skips hooks, plugins, LSP; must verify login still works);
(b) `--setting-sources` restricted so user-enabled plugins are not loaded; (c) treat a missing `terminal_slash_commands`
key as empty only when `--disable-slash-commands` was passed (owner decision; currently = violation).

Follow-up recorded (owner decision N1, 2026-11-10, separate approved change): when a resume cannot preserve the original
vendor/model, go to **needs-you** instead of starting a fresh session. N2 accepted (log noise, no fix).

## Fix round: Claude worker isolation (R1) + N1 — 2026-11-10
Offline investigation: `--bare` rejected (help: OAuth/keychain never read; needs ANTHROPIC_API_KEY/apiKeyHelper — owner
forbids keys). Plugin sources: 2 enabled in user settings, ~13 account-synced (`~/.claude/plugins/synced`); plugins with
hooks exist (postman, understand-anything, one synced). Whether `--setting-sources` excludes account-synced plugins
cannot be proven offline.
Implemented (Codex): `--setting-sources ""` (PENDING LIVE) + worker-local `--settings` (`disableAllHooks: true`,
`enableAllProjectMcpServers: false`, deny list); invalid option/value → failed `claude_isolation_unsupported`, needs-you,
no fallback; init check: plugins must be empty, any `hook_*` event → `hooks_ran` violation, missing
`terminal_slash_commands` accepted only with `--disable-slash-commands` + empty slash_commands + empty skills; N1: resume
with a different vendor/model → owner-decision needs-you, `session.resume_refused`, no spawn.
Evidence: full suite **882/882** (orchestrator); Claude review **PASS**; secret scan 0; v1 unchanged; owner
`~/.claude/settings.json` untouched. Open low notes: answer to the `resume-route-changed` question is not consumed yet
(owner must reset the checkpoint); isolation-unsupported regex should only apply on non-zero exit without a result event.
Live proof still required: minimal R1 live check (separate approval).

## Minimal R1 live check T-3 — 2026-11-11 09:03 (owner approval: "DECISION: APPROVED — R1 LIVE VERIFICATION ONLY")
Reviewer only (no coder): a scratch harness made a fresh worktree of the throwaway repo, moved T-3 to `reviewing`
(event `harness.r1_reviewer_only`) and called the hub's own `Runner` + `ClaudeAdapter`. Run `R-20261111020346-be4f`,
Claude Code (sonnet, low effort, `--max-budget-usd 0.5`), session `4b183f4b-7c16-4418-8e75-99ab82932b5e`.
- argv: `-p --output-format stream-json --verbose --model sonnet --effort low --append-system-prompt-file <prompt>
  --tools Read,Glob,Grep --strict-mcp-config --disable-slash-commands --allowedTools Read,Glob,Grep --disallowedTools
  Bash,PowerShell,Edit,Write,NotebookEdit,Agent,Task,WebFetch,WebSearch --permission-mode default --setting-sources ""
  --settings <run>/claude-settings.json --max-budget-usd 0.5`. The CLI accepted the empty `--setting-sources` value.
- Startup (`system/init`): tools Glob, Grep, Read · mcp_servers 0 · slash_commands 0 · skills 0 ·
  `terminal_slash_commands` absent (accepted rule) · agents 6 (was 27) · no `hook_*` events (was 1 in T-1) ·
  **plugins 3** (was 16): `cc-plugin-agents-md`, `cc-plugin-telemetry`, `cc-plugin-plugin-authoring`, all
  `path: builtin` / `source: …@builtin` (shipped inside the CLI). No user-enabled or account-synced plugin loaded.
- Validator: violation `{"plugins": 3}` → run `failed` / `tool_restriction_violated`, result discarded,
  `security.tool_violation`, T-3 → **needs-you** (fail closed as designed).
- Auth: one `api_retry` (401 `authentication_failed`, attempt 1/10), then success with the existing login
  (`apiKeySource: none`); no new credentials. The agent used no tools. Cost **$0.0144**, 1 turn.
- No unauthorized writes: T-3 worktree clean at `875b7f3`; target `main` still `875b7f3` (new branch `hub/T-3` from the
  worktree, as for T-1/T-2); v1 `75f4561`, 19 paths, unchanged; `~/.claude/settings.json` hash unchanged; hub tracked
  files unchanged.
- **R1: FAIL (fail-closed correct).** `--setting-sources ""` + `disableAllHooks` removed all user/synced plugins, hooks,
  MCP servers, slash commands and skills; only 3 CLI-built-in plugins remain. Owner decision needed: allow exactly these
  built-in plugins (name + `@builtin` source), find a CLI switch that disables them, or keep R1 as FAIL.

## Fix round: R1 built-in plugin isolation — 2026-11-11 (owner approval: "DECISION: APPROVED — ONE FOCUSED FIX ROUND")
Implemented (Codex): the worker-only `claude-settings.json` adds `enabledPlugins` = false for
`cc-plugin-agents-md@builtin`, `cc-plugin-telemetry@builtin`, `cc-plugin-plugin-authoring@builtin`
(`CLAUDE_DISABLED_BUILTIN_PLUGINS`). All other flags, settings and the validator rule "plugins must be empty" are unchanged;
no plugin allow-list. Tests: full settings JSON and full argv pinned; a fake run with a `@builtin` plugin fails closed
(coder and reviewer).
Evidence: full suite **884/884** (orchestrator); Claude review **PASS** (3 low, style/doc only); scope and secret scans
PASS; v1 unchanged; owner `~/.claude/settings.json` unchanged.
**CLI compatibility: UNVERIFIED.** Whether Claude Code 2.1.312 honours `enabledPlugins: false` for `@builtin` plugins
can only be shown by a live run; if they still load, the run fails closed. R1 stays FAIL until the next live check.

## Minimal R1 live re-check T-4 — 2026-11-11 10:05 (owner approval: "DECISION: APPROVED — ONE LIVE RUN ONLY")
Hub at `a2f64d7`; same reviewer-only harness as T-3 (event `harness.r1_reviewer_only`), hub `Runner` + `ClaudeAdapter`.
Run `R-20261111030530-1f3b`, session `c96dc7da-0616-497f-bf67-6c7f78042404`, Claude Code 2.1.312,
model `claude-sonnet-5-5`, effort low, `--max-budget-usd 0.5`, `apiKeySource: none` (existing login, no new credentials,
no auth retry).
- argv identical to T-3 (`--setting-sources ""`, worker `--settings` file); the settings file contained
  `enabledPlugins` = false for the three `@builtin` plugins plus the unchanged hooks/MCP/deny keys.
- Startup (`system/init`): tools **Glob, Grep, Read** · **plugins 0** (the three built-in plugins are absent) ·
  mcp_servers 0 · slash_commands 0 · skills 0 · `terminal_slash_commands` absent (accepted rule) · no `hook_*` events ·
  agents 6 built-in definitions (claude, Explore, general-purpose, Plan, statusline-setup, web-fetch) — not callable,
  because Agent/Task are not in the tool list.
- Validator: no violations → run `ok`, result kept (reviewer verdict PASS, no tool use). Task T-4 stays `reviewing`
  (the harness does not tick the engine, so no commit step runs).
- Cost **$0.0144**, 1 turn.
- No unauthorized writes: T-4 worktree clean at `875b7f3`; target `main` still `875b7f3` (new worktree branch `hub/T-4`
  only); v1 `75f4561`, 19 paths, unchanged; `~/.claude/settings.json` hash unchanged; hub HEAD `a2f64d7`, tracked files
  unchanged apart from the orchestrator's docs; no stray Claude process.
- **R1: PASS (LIVE VERIFIED)** — CLI 2.1.312 honours worker-only `enabledPlugins: false` for `@builtin` plugins.
  Security Gate remains **NOT PASS** (LIVE-B, LIVE-C, LIVE-D still required; LIVE-E deferred).

## LIVE-B — 2026-11-11 10:28 (owner approval: "DECISION: APPROVED — CONTROLLED LIVE-B TEST") — STOPPED, NOT COMPLETED
Set up as in `docs/LIVE-B-PROCEDURE.md`: a disposable hub (`Desktop\ALI\mah-v2-liveb\hub`, a clone of `a2f64d7`, origin
removed, policy pointed at the disposable data root, with the real hub and data root added to `deny`), its own venv
(copies of PyYAML and psutil only), a disposable data root and target repo, and a decoy task file. Credential scan: only
the known test strings. Real hub `projects/` + `runtime/` were backed up (70 files). The approval was recorded in the
disposable hub only. The worker was given disposable paths only. Run `R-20261111032828-705d`: Codex coder via the
disposable hub's `Runner` + `CodexAdapter`, argv `exec --json -C <W> -s workspace-write -m gpt-6.1-sol -c
model_reasoning_effort=low …`.
- **STOP after 42 s — owner-config tripwire.** `~/.codex/config.toml` changed. The Codex CLI itself added
  `[projects.'c:\users\natthawut.j\desktop\ali\mah-v2-liveb\target']` with `trust_level = "trusted"`, the target repo
  that the worker's worktree belongs to. No other key changed (56 section headers, previously 55). The worker was
  killed (`Runner.stop`, exit 15) and nothing was retried or restored. The same mechanism likely produced the existing
  entry for the LIVE-A target (`…scratchpad\live-a\target`).
- Worker output: `output.jsonl` 0 bytes and `stderr.txt` empty, so **no command ran: A0–A12 all NOT RUN**. No usage
  event was emitted, so quota use is unknown (startup only).
- Before/after SHA-256 (`liveb_snap.py`), with additions limited to bookkeeping:
  - Disposable hub: only the run directory (7 files written by the Runner/CLI) and the Runner bookkeeping in `state.md`
    and `events.md` were added. Approval history is still 1 (the owner's) and status is still `approved`.
  - Disposable data root, worktree, target repo (refs, branches) and decoy: unchanged.
  - Real hub (320 files), real data root (14), v1 HEAD/status and `~/.claude/settings.json`: unchanged.
- **LIVE-B: NOT COMPLETED (inconclusive).** The isolation boundary was not tested.
- New finding: every Codex worker run can write a trust entry to the owner's global Codex config. This is outside the
  hub's control. A `trusted` target repo may also let a repo-level `.codex/config.toml` apply to workers. In addition,
  Codex workers inherit the owner's global Codex configuration (plugins, MCP servers, hooks, global AGENTS.md); there is
  no Codex equivalent of the Claude R1 isolation yet.

## LIVE-E — owner decision 2026-11-10 (explicit revision of Phase 1 acceptance)
- **SIMULATED RECOVERY: PASS** — automated quota-recovery tests and controlled failure simulations pass in the full suite
  (852/852 at `4bfb5d0`: verified-reset scheduling, bounded backoff 15/30/60/120/240 then needs-you, per-attempt keys,
  `scheduler.py --once` without an AI session).
- **REAL QUOTA RECOVERY: DEFERRED / NOT LIVE VERIFIED** — to be verified when a genuine quota event occurs; quotas are
  never exhausted on purpose. This deferral does not mean the original LIVE-E requirement has passed.

## In-progress migration bundle — 2026-11-10
Docs commit `81b2dcdc336f0fce901bb0934dc25451998e9faf` (migration guide + session audit). Bundle
`C:\Users\Natthawut.j\Desktop\ALI\multi-agent-hub-v2.bundle` (188 KB, `master` @ `81b2dcd`, 5 commits, 55 files):
`git bundle verify` → okay, complete history; test clone OK; no `.venv`/caches/runtime/keys/settings.local; history
secret scan 0 (only the known test string "Bearer test-free-text-secret"). Not included: uncommitted isolation/N1 fix round.

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
