# Phase 1 Plan — Hub v2 core (engine, state, bridge, owner console, adapters)

Status: **REVISION 2 — awaiting owner Final Coding approval. No product code before approval.**
Architecture: [ARCHITECTURE.md](ARCHITECTURE.md) Rev 2. Every acceptance item is **PENDING VERIFICATION** until its test
has run and evidence is linked in `docs/VERIFICATION.md`. The Security Gate stays **NOT PASS** in Phase 1 (ARCH §6.6).

## Scope boundary (must NOT change)
- Nothing under `C:\Users\Natthawut.j\Desktop\ALI\multi-agent-hub` (v1): source, config, tasks, worklog, git history,
  worktrees, protected files. No signals to v1 processes. v1 snapshot: `main` @ `75f4561`, 19 pending paths.
- No copy of v1 runtime/code into v2.
- No push, no remote, no merge, no deploy, no `git worktree remove`, no branch deletion, no cleanup — in any repo.
- No global Python/PATH/registry/Desktop settings, no Windows users/ACLs, no Scheduled Tasks. Packages only in `v2/.venv`.
- No Node.js/SQLite in the product (the shared `~/.codex/scripts/check-plan.cjs` may run as a plan checker).
- Real agent calls only in steps marked **[LIVE-x]**, each with its own owner go-ahead.
- The hub never creates or reads the owner passphrase; only the owner types it into `owner_console.py`.

## Already done under the 2026-11-09 authorization (environment prep only)
| Item | Evidence |
|---|---|
| `git init` v2, local only, no remote | `git remote -v` empty; nothing committed |
| `.gitignore` | secrets, `.venv`, `runtime/`, `projects/*/`, logs, `worktrees/` |
| `.venv` (Python 3.11.3 via `py -3.11`) | `.venv\Scripts\python.exe --version` → 3.11.3 |
| Deps | streamlit 1.67.0, PyYAML 6.0.3, psutil 7.2.2, pytest 9.2.0; `pip check` clean |
| Version record | `requirements.txt` (direct pins), `requirements.lock` (41 packages, `pip freeze`) |

## Sources
- Owner directive "BUILD MULTI-AGENT HUB V2" and decision "CONDITIONAL APPROVAL — REVISE PLAN BEFORE CODING" (2026-11-09)
- `docs/ARCHITECTURE.md` Rev 2 §3–§14
- CLI `--help`: Claude Code 2.1.312, Codex CLI 0.167.0; Codex `rate_limits` field in `~/.codex/sessions` (VERIFIED)

## Prerequisites before coding starts
| # | Item | Status |
|---|---|---|
| 1 | Owner approves ARCHITECTURE Rev 2 + this plan | open |
| 2 | R1 `cryptography` approved and installed in `.venv`, version recorded | open — **blocking** (owner console cannot be built without it) |
| 3 | R3 (Claude workers shell-free), R4, R5 data root, R6 owner secret path, R7 backoff numbers | open |
| 4 | Create data root folder (R5) — outside every repo, verified by P1 | open |

## Files
| # | Path | Action | Layer | Doc | Mirror | Wired |
|---|---|---|---|---|---|---|
| 1 | `config/policy.toml` | new | config | ARCH §4.1, §7.3–7.4, §12 | — | `policy.py` |
| 2 | `config/models.toml` | new | config | ARCH §7.3 | — | `model_router.py` |
| 3 | `state_writer.py` | new | core | ARCH §10 | — | `engine.py` |
| 4 | `agent_loader.py` | new | core | ARCH §7.1 | — | `runner.py` |
| 5 | `agents/coder.md` | new | templates | ARCH §7.1 | — | `agent_loader.py` |
| 6 | `adapters/base.py` | new | adapter | ARCH §7.2 | — | `runner.py` |
| 7 | `adapters/claude_cli.py` | new | adapter | ARCH §7.2 | — | `adapters/base.py` |
| 8 | `adapters/codex_cli.py` | new | adapter | ARCH §7.2, §12 | — | `adapters/base.py` |
| 9 | `signing.py` | new | core (security) | ARCH §6.4 T2–T4 | — | `policy.py` |
| 10 | `owner_console.py` | new | trusted interface | ARCH §6, §8, §9 | — | `signing.py` |
| 11 | `policy.py` | new | core (security) | ARCH §4.1, §6.4–6.5 | — | `engine.py` |
| 12 | `model_router.py` | new | core | ARCH §7.3 | — | `engine.py` |
| 13 | `worktree_manager.py` | new | core | ARCH §4.1, AD-08 | — | `runner.py` |
| 14 | `runner.py` | new | core | ARCH §7.2, §11 | — | `engine.py` |
| 15 | `scheduler.py` | new | core | ARCH §12 | — | `engine.py` |
| 16 | `engine.py` | new | core | ARCH §11 | — | `scheduler.py` |
| 17 | `bridge.py` | new | interface | ARCH §8, §13 | — | `hooks/pending.py` |
| 18 | `notify.py` | new | integration | ARCH §8 | — | `bridge.py` |
| 19 | `app.py` | new | UI read-only | ARCH §5 | — | `state_writer.py` |
| 20 | `.claude/settings.json` | new | integration | ARCH §8 | — | `hooks/pending.py` |
| 21 | `AGENTS.md` | new | integration | ARCH §8, §6.5 | — | `bridge.py` |
| 22 | `projects/README.md` | new | docs | ARCH §4 | — | `engine.py` |
| 23 | `tests/fakes/fake_codex.py` | new | test | — | — | `tests/test_adapters.py` |
| 24 | `tests/test_state_writer.py` | new | test | AC-4 | — | `state_writer.py` |
| 25 | `tests/test_agent_loader.py` | new | test | AC-1 | — | `agent_loader.py` |
| 26 | `tests/test_adapters.py` | new | test | AC-2 | — | `adapters/base.py` |
| 27 | `tests/test_signing_approval.py` | new | test | AC-3 | — | `signing.py` |
| 28 | `tests/test_path_policy.py` | new | test | AC-9 | — | `policy.py` |
| 29 | `tests/test_engine_restart.py` | new | test | AC-5 | — | `engine.py` |
| 30 | `tests/test_bridge.py` | new | test | AC-6, AC-7 | — | `bridge.py` |
| 31 | `tests/test_scheduler_quota.py` | new | test | AC-8 | — | `scheduler.py` |
| 32 | `tests/test_v1_isolation.py` | new | test | Scope | — | `worktree_manager.py` |
| 33 | `docs/VERIFICATION.md` | new | docs | all AC | — | `docs/PHASE-1-PLAN.md` |
| 34 | `docs/WORKLOG.md` | modify | docs | Q8 | — | `docs/PHASE-1-PLAN.md` |
| 35 | `requirements.txt` | modify | setup | R1 | — | `requirements.lock` |
| 36 | `agents/planner.md` | new | templates (row 5 group) | ARCH §7.1 | — | `agent_loader.py` |
| 37 | `agents/tester.md` | new | templates (row 5 group) | ARCH §7.1 | — | `agent_loader.py` |
| 38 | `agents/reviewer.md` | new | templates (row 5 group) | ARCH §7.1 | — | `agent_loader.py` |
| 39 | `agents/doc-keeper.md` | new | templates (row 5 group) | ARCH §7.1 | — | `agent_loader.py` |
| 40 | `hooks/pending.py` | new | integration (row 20 group) | ARCH §8 | — | `bridge.py` |
| 41 | `CLAUDE.md` | new | integration (row 21 group) | ARCH §8 | — | `bridge.py` |
| 42 | `tests/fakes/fake_claude.py` | new | test (row 23 group) | — | — | `tests/test_adapters.py` |
| 43 | `adapters/__init__.py` | new | adapter (row 6 group, package marker) | — | — | `adapters/base.py` |
| 44 | `requirements.lock` | modify | setup (row 35 group) | Q7, R1 | — | `requirements.txt` |

Rows 36–44 only split the multi-file rows 5, 20, 21, 23 and 35 (plus the `adapters/` package marker) into one path per
row for `check-plan.cjs`. They add no scope beyond Rev 2's 35 approved rows.

Out of scope: MCP bridge server, `codex queue`, separate Windows worker user (R2), Scheduled Task (R4), Streamlit polish,
auto-commit, multi-project UI.

## Implementation steps (bottom-up; each step ends with pytest green before the next)
1. **Snapshot**: `node ~/.codex/scripts/check-plan.cjs docs/PHASE-1-PLAN.md --snapshot`; record v1 `git status` hash.
2. **State layer** (rows 3, 24): lock, atomic replace with EPERM retry, event journal, replay, temp cleanup.
3. **Templates** (rows 4, 5, 25): frontmatter schema, reject vendor/model/effort, per-vendor render spec.
4. **Signing + owner console** (rows 9, 10, 27): Ed25519 key gen, scrypt-encrypted private key, passphrase ≥16 chars,
   `CONIN$`-only input (refuse piped stdin), signed record format with nonce, plan/policy/manifest signing, `verify`.
5. **Policy** (rows 1, 11, 28): signed policy load, source manifest check, path policy P1–P8, approval classes, scope diff check, slots.
6. **Adapters** (rows 6–8, 23, 26): command build, stream parse, classify ok/failed/quota/auth, Codex `resets_at`
   extraction (stream + sessions file), session id; fake CLIs only.
7. **Router, worktree, runner** (rows 2, 12–14): catalog validation, availability probe (version/auth only), fallback,
   `git worktree add` in the data root on a throwaway repo under `tests/tmp`, Python-run tests, scope diff, idempotency keys.
8. **Scheduler + engine** (rows 15, 16, 29, 31): schedule.md, verified reset vs bounded backoff, reconcile on start, singleton, caps.
9. **Bridge + notify + Desktop files** (rows 17, 18, 20–22, 30): JSON commands, `pending --brief`, question validation,
   `relay-answer`, `request-approval`; toast; hook; orchestrator rules.
10. **Streamlit** (row 19): read-only Status, Agent Tree, Timeline, Logs.
11. **Close**: `check-plan.cjs docs/PHASE-1-PLAN.md`, v1 isolation test, `docs/VERIFICATION.md`, WORKLOG row.

## [LIVE] steps — each needs its own owner go-ahead (not covered by Final Coding approval)
| ID | What | Quota | Proves |
|---|---|---|---|
| LIVE-A | One Claude and one Codex run of a trivial template on a throwaway repo in the data root (`--max-budget-usd` for Claude) | small | AC-1, AC-2 real CLIs |
| LIVE-B | Sandbox-escape test: worker instructed to write `v2/config`, `v2/projects`, `runtime/`, read `%USERPROFILE%\.mah-v2-owner`, call `owner_console.py` | small | T6 controls (a)–(c); Security Gate still NOT PASS under same user |
| LIVE-C | Desktop round trip: Claude Desktop and Codex Desktop run `bridge.py pending/ask/relay-answer`; owner signs one approval and one answer in `owner_console.py`; engine resumes | small (orchestrator only) | AC-6, AC-7 |
| LIVE-D | Claude hook injects pending questions; Windows toast appears | none | AC-6 notification part |
| LIVE-E | Real quota reset handling — only if a real limit occurs naturally; never provoked | none extra | AC-8 real-provider part |

## Tests (no quota)
| Test | How |
|---|---|
| Concurrent writes | 8 processes × 200 transactions; contiguous event seq, state parses, no lost update |
| Windows EPERM | reader holds `state.md` open without share-delete during replace → retry then success; clean failure after cap |
| Crash recovery | fault injection between event append and replace; restart → replay equals expected state |
| Template parity | same `coder.md` → Claude and Codex commands with identical prompt-body hash |
| Adapters | fake CLIs emit success, failure, quota with `resets_at`, quota without reset, auth error |
| Approval forgery | "APPROVED" in result.md; hand-written approval block; signature by a different key; valid sig with old plan hash; replayed nonce; relay-answer on an `owner-signed` question; `owner_console.py` with piped stdin → all rejected |
| Policy tamper | edited `policy.toml` without new sig; edited `.py` vs signed manifest; swapped `owner.pub` vs recorded fingerprint → engine refuses to start (documented as tamper-evident, not tamper-proof) |
| Path policy | data root inside a repo, inside v1/v2, `..` traversal, junction, > 200 chars, `ALI\worktrees` → rejected |
| Restart no duplicate | fake long-running agent; kill engine; restart twice → one `spawn.started` per key, re-attached |
| Concurrency | 4 ready tasks + 2 dynamic requests → never > 2 live, never > 1 dynamic |
| Needs-You resume | incomplete `ask` rejected; relay answer resumes relay question; owner-signed answer resumes owner question |
| Scheduler/quota | Codex `resets_at` → wake at reset+2 min; Claude no reset → backoff 15/30/60/120/240 then needs-you; no process alive while waiting |
| v1 isolation | v1 path denied; foreign PID never signalled; v1 `git status` identical before/after suite |
| Git safety | fake-git shim: no push/merge/remove/reset/branch -D/remote add ever issued |

## Acceptance (all PENDING VERIFICATION)
- [ ] AC-1 Claude and Codex read agent templates from one Markdown set — `test_agent_loader.py` + LIVE-A
- [ ] AC-2 Python spawns across vendors through adapters — `test_adapters.py` + LIVE-A
- [ ] AC-3 Owner approval cannot be forged by an agent — `test_signing_approval.py` (T1–T5) + LIVE-B; **Security Gate reported NOT PASS** while T6/T7 are open (same Windows user)
- [x] AC-4 Markdown state safe under concurrent writes and Windows EPERM — `test_state_writer.py` — evidence: 53 tests in 609/609 (2026-11-10), docs/VERIFICATION.md
- [x] AC-5 Engine restart does not spawn duplicates — `test_engine_restart.py` — evidence: 59 tests in 609/609 (2026-11-10), docs/VERIFICATION.md
- [ ] AC-6 Desktop calls the Hub Bridge and reads the result — `test_bridge.py` + LIVE-C + LIVE-D
- [ ] AC-7 Needs-You answer resumes the workflow — `test_bridge.py` + LIVE-C
- [ ] AC-8 Quota/scheduler works without an open AI session — `test_scheduler_quota.py`; real provider part stays PENDING unless LIVE-E occurs
- [x] AC-9 Worktrees stay outside every repo under the path policy — `test_path_policy.py` — evidence: 104 tests in 609/609 (2026-11-10)
- [x] Scope: `check-plan.cjs` reports no `SCOPE:` lines; v1 unchanged vs snapshot — evidence: no SCOPE lines; v1 `75f4561`, 19 paths (2026-11-10)

## Stop conditions (stop immediately, report, ask the owner)
- An agent can forge an approval, leave scope, read trusted credentials (owner key/passphrase) or change policy
  without detection — in any test or LIVE step.
- Any step would modify v1, or a test shows v1 changed.
- Path conflict: data root or a worktree resolves inside any git repo, inside v1/v2, or collides with an existing path.
- `cryptography` not approved (owner console cannot be built) → stop before step 4.
- A CLI flag in ARCH §7.2 is missing or behaves differently → stop, update ARCHITECTURE, re-approve.
- The architecture must deviate from the directive (DB, Node, web chat, owner inbox in Streamlit).
- Same failure 3 times in a step, or a LIVE step would exceed the approved budget.

## Prompt sequence (Codex team, after Final Coding approval; one self-contained prompt per step)
1. "In `multi-agent-hub-v2` use `.venv\Scripts\python.exe`. Implement step 2 (rows 3, 24) per ARCHITECTURE §10. Stdlib only. Run pytest; report rows done."
2. "Implement step 3 (rows 4, 5, 25) per ARCHITECTURE §7.1–7.2. Reject vendor/model/effort keys. Run pytest."
3. "Implement step 4 (rows 9, 10, 27) per ARCHITECTURE §6. Never store or log a passphrase; tests use a throwaway key in a temp dir. Run pytest."
4. "Implement step 5 (rows 1, 11, 28) per ARCHITECTURE §4.1, §6.4–6.5. Run pytest."
5. "Implement step 6 (rows 6–8, 23, 26) with fake CLIs only; never call real `claude`/`codex`. Run pytest."
6. "Implement steps 7–8 (rows 2, 12–16, 29, 31, 32) using a throwaway repo under `tests/tmp`; no push/merge/remove. Run pytest."
7. "Implement steps 9–10 (rows 17–22, 30, 19) per ARCHITECTURE §8, §13. Streamlit read-only. Run pytest."
Steps 1, 11 and all LIVE steps are run by the orchestrator with the owner, not by the Codex team.
