# Plan — Simplify v2: conversational Owner approval (remove signing)

Status: **REV 2 — planning only, awaiting owner approval.** No code changed. Existing keys/signatures untouched.
Owner decisions: "Simplify — remove cryptographic owner signing" and "SIMPLIFY MULTI-AGENT HUB V2 — USABILITY FIRST" (2026-11-10).
Rev 2 replaces Rev 1's separate-terminal approval with **conversational approval** in the existing Desktop chat.

**Honest framing (must appear in ARCHITECTURE):** conversational approval is a *workflow control*. It records what the
owner said in the Desktop conversation. It is **not** proof of owner identity and **not** an isolated security boundary;
the Desktop orchestrator could record an approval the owner never gave. Security status stays **NOT PASS**.

## Target user experience
1. Owner gives instructions in Claude or Codex Desktop.
2. Orchestrator plans, shows the plan, owner says "approve" in chat → orchestrator records it (`bridge.py approve`).
3. Engine runs the team autonomously within that approval: coder → Python tests → reviewer → fix rounds → scoped local
   commit. Quota waits, restarts and resumes continue **without asking again** for the same plan/scope.
4. Only scope changes, plan revisions, policy changes, caps reached, reviewer FAIL ×2, or owner-decision questions stop
   the task; the orchestrator asks in the same conversation and records the answer.
5. No passwords, keys, signatures, or separate terminal.

## Scope boundary (must NOT change)
- v1 untouched; no push/merge/deploy/destructive cleanup; LIVE tests and Goal spikes not run.
- Keys/signature files on disk are **not** deleted or modified (`%USERPROFILE%\.mah-v2-owner\*`, `config/owner.pub*`, `config/policy.toml.sig`); code just stops reading them.
- Kept safeguards: 2-process cap + 1 dynamic slot, path policy P1–P8, scope check after each run, Python-run tests,
  git allow-list (no push/merge/reset/remove), Claude workers read-only (R3), Codex workspace-write sandbox, minimal
  child env, run caps, bounded quota backoff, orphan identity rules, idempotent spawn, independent review.

## 1. Signing dependencies (344 grep hits / 27 files) and what happens to each
| Area | Files | Action |
|---|---|---|
| Crypto core | `signing.py`, `cryptography` in requirements | **remove**; hash helpers (`sha256_text`, `sha256_file`, `canonical`) move to `hashing.py` |
| Owner console | `owner_console.py` (init, passphrase, sign-policy, sign-manifest, signed approve/answer/resume/commit) | **remove the file**; its approval/answer logic moves into `bridge.py` as plain records |
| Policy gate | `policy.py` (`load_policy` sig, `verify_manifest`, `may_spawn` signature check) | `load_policy` plain; manifest check removed; `may_spawn` uses `check_approval` |
| Engine / runner | `engine.py`, `runner.py` (key load, manifest check, signed answer/commit) | remove key/manifest; answers and commit use plain records / commit conditions |
| Bridge / scheduler | `bridge.py`, `scheduler.py` (`load_public_key`) | remove key loading |
| Helpers | `state_writer.py` (`sha256_text` import) | import from `hashing.py` |
| Desktop rules | `.claude/settings.json` (deny `*owner_console*`), `AGENTS.md`, `CLAUDE.md`, `hooks/pending.py` | settings: drop now-pointless owner_console deny, keep `config/**`, `projects/**`, `runtime/**` edit denies; rules describe conversational approval |
| Tests | `test_signing_approval.py`, signed fixtures in `test_path_policy.py`, `test_engine_restart.py`, `test_bridge.py`, `test_v1_isolation.py`, `test_scheduler_quota.py` | rewrite as `test_approvals.py`; unsigned fixtures |
| Docs | ARCHITECTURE §6/§8/§9/§12/§14, PHASE-1-PLAN, VERIFICATION, LIVE-A-PROCEDURE, PHASE-2-BLUEPRINT, agents/*.md (1 line each) | update |

## 2. New approval model
`bridge.py` commands (orchestrator runs them right after the owner's words in chat):
| Command | Records | Effect |
|---|---|---|
| `approve P T --quote "<owner's words>" --desktop claude\|codex` | `approval {kind: approve-plan, plan_hash, policy_hash, quote, desktop, recorded_by: orchestrator, at, nonce}` | task → approved; covers every spawn, round, resume and quota retry **for that plan hash** |
| `answer P T QID --quote "..." [--option LABEL]` | answer record (any question class) | resumes when no blocking question remains |
| `approve-scope P T --add "<globs>" --quote "..."` | scope change record; plan section updated → new plan hash approved in the same step | widens allowed paths only with owner words |
| `pause/resume/cancel P T --quote "..."` | control records | engine obeys |

Engine rules:
- `may_spawn` requires an approval whose `plan_hash` and `policy_hash` match the current spec/policy; plan edit or policy
  edit → `needs-you` ("plan changed, please approve again"). One approval per plan revision — no repeated approvals.
- **Agent text is never an approval.** Approvals come only from bridge records with `recorded_by: orchestrator`; the
  engine ignores approval-looking content in `result.md`, `questions.md` or agent output.
- **Workers cannot record approvals:** `bridge.py` refuses when `HUB_WORKER=1` or cwd is inside the data root
  (deterrence); Claude workers have no shell; Codex workers' sandbox cannot write `projects/` (LIVE-B will prove it).
- Local commit: after Python tests pass + reviewer PASS + scope check clean, the runner commits only the task's changed
  files in the **task worktree branch** (never `git add -A`), message states verification status, SHA → events/WORKLOG.
  Merge into the target branch stays owner-only.
- Every approval/answer appears in `events.md` and the Streamlit timeline with the quote and desktop (audit trail).

Question classes become: `owner-decision` (must be answered by the owner via the orchestrator; never auto-defaulted) and
`clarify` (non-blocking may use its default after a timeout set in policy).

## 3. Threat model after the change
| Threat | After |
|---|---|
| T1 agent text taken as approval | **blocked** (never parsed) |
| T2 worker records an approval | **blocked in practice** (no shell for Claude; Codex sandbox; bridge guard) — Codex part PENDING LIVE-B |
| T4 stale approval reused after plan/policy change | **blocked** (hash binding) |
| T11 orchestrator records an approval the owner did not give | **not prevented** — workflow control only; visible in audit trail; orchestrator rules forbid it |
| T6 tampering with hub code/policy | policy edits invalidate approvals (hash); hub code integrity = git history, not enforced at runtime |
STOP-IF check: no spawned worker gains a way to approve, widen scope or skip `may_spawn`; the only actor that could
record a false approval is the Desktop orchestrator, which is the owner's own conversation partner (accepted, documented).

## 4. Files
| # | Path | Action |
|---|---|---|
| 1 | `signing.py` | delete |
| 2 | `owner_console.py` | delete |
| 3 | `hashing.py` | new |
| 4 | `approvals.py` | new (record build/check, nonce, quote required) |
| 5 | `policy.py`, `engine.py`, `runner.py`, `bridge.py`, `scheduler.py`, `state_writer.py` | modify |
| 6 | `.claude/settings.json`, `AGENTS.md`, `CLAUDE.md`, `hooks/pending.py`, `agents/*.md` | modify |
| 7 | `requirements.txt`, `requirements.lock` | modify (drop `cryptography`; not uninstalled from `.venv`) |
| 8 | `tests/test_signing_approval.py` → `tests/test_approvals.py`; other test files' fixtures | modify |
| 9 | `.gitignore` | modify (ignore leftover `config/owner.pub*`, `config/*.sig`) |
| 10 | `docs/ARCHITECTURE.md` (Rev 3), `docs/PHASE-1-PLAN.md`, `docs/VERIFICATION.md`, `docs/LIVE-A-PROCEDURE.md`, `docs/PHASE-2-BLUEPRINT.md` | modify |

Doc updates elsewhere: LIVE-A drops precondition P2 (keys) and uses `bridge.py approve` in chat; Phase 2 Goal Contract
uses conversational `approve-goal` instead of a signed record; LIVE-B is redefined as "worker cannot write hub state /
cannot run bridge approve", not "cannot read the key".

## 5. Steps (after approval)
1. `check-plan.cjs --snapshot` of this plan.
2. Codex (high): rows 1–5, pytest green. 3. Codex (medium): rows 6–9, pytest green.
4. Orchestrator: docs (row 10); full suite; scope + v1 check; grep proves no `cryptography`/`signing`/`owner_console` imports.
5. Claude reviewer (cross-vendor): T1/T2/T4, no worker write path, commit rules, no repeated-approval prompts.
6. Scoped local commit under the owner's git conditions; SHA in WORKLOG.

## 6. Acceptance
- [ ] Hub runs end-to-end on fakes with no key files and no separate terminal.
- [ ] Spawn refused without approval; one approval covers all rounds/resumes/quota retries of that plan; plan or policy edit → needs-you.
- [ ] Approval-looking agent output ignored; `bridge.py` refuses under `HUB_WORKER=1` / data-root cwd.
- [ ] Scope widening only via `approve-scope` with owner quote.
- [ ] Auto local commit only after tests + reviewer PASS + clean scope; only task files; never push/merge.
- [ ] Audit trail shows every approval/answer with quote; Streamlit shows it.
- [ ] Non-signing coverage of the 609 tests preserved (count reported); full suite green; reviewer PASS.
- [ ] ARCHITECTURE states conversational approval is not an identity proof or isolated security boundary.

## 7. Stop conditions
Any change giving a worker a way to approve, widen scope, write hub state or skip `may_spawn`; reviewer FAIL; test
failure; scope violation; need to touch v1 or the key files on disk.
