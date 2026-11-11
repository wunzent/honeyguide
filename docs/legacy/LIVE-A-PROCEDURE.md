# LIVE-A Procedure — first real Claude + Codex runs

Status: **PROPOSED — needs separate owner approval.** Proves the live parts of AC-1 and AC-2 only.
Security Gate stays **NOT PASS**. LIVE-B…E are not covered by this approval.

## Preconditions (all must hold; any missing → do not start)
| # | Item | Who | Check |
|---|---|---|---|
| P1 | Phase 1 baseline commit exists, `git status` clean for tracked files | orchestrator | `git log -1`, `git status` |
| P2 | Signing removed (ARCHITECTURE Rev 3); no key setup needed | — | `bridge.py status` returns `ok: true` with no key files present |
| P3 | Data root `C:\Users\Natthawut.j\Desktop\ALI\multi-agent-hub-v2-data` exists | owner or orchestrator after approval | path policy: not inside any repo / v1 / v2 (checked read-only 2026-11-10: all false, folder not yet created) |
| P4 | Throwaway target repo `…-v2-data\live-a\target` (git init, one commit with `README.md`, `test_hello.py`) registered as project `live-a` in `projects/live-a/project.md` | orchestrator after approval | `policy.check_target_repo` passes |
| P5 | Task `live-a/T-1` spec with a one-line plan "create `hello.txt` containing `hello`", approved by the owner in chat | orchestrator runs `bridge.py approve live-a T-1 --quote "<owner words>" --desktop claude` | `bridge.py show live-a T-1` shows the approval with quote and matching plan hash |
| P6 | Both CLIs logged in (`claude auth status`, `codex login status`) | orchestrator | no quota used |

## Steps
| # | Action | Route (proposed) | Quota |
|---|---|---|---|
| 1 | Availability probe through the adapters (`--version`, auth status) | — | none |
| 2 | Engine `--once` dispatches **coder** on Codex | `codex / gpt-6.1-sol / low`, sandbox `workspace-write`, `-C <worktree>` | small |
| 3 | Python runner runs `python -m pytest -q` in the worktree (trusted test) | — | none |
| 4 | Engine dispatches **reviewer** on Claude | `claude / sonnet / low`, tools Read/Glob/Grep only, `--max-budget-usd 0.50` | small |
| 5 | If tests + review PASS and scope clean: auto local commit in the task worktree branch `hub/T-1` (throwaway repo). Stop; engine not left running; no push/merge. | — | — |

## Expected results (PASS criteria)
- E1 Both runs render their prompt from the same `agents/*.md` set; prompt-body sha256 recorded in each run's `meta.md` matches `agent_loader` output (AC-1).
- E2 Codex run: `spawn.intent` → `spawn.started` (pid + create_time) → `run.finished status=ok`; `hello.txt` exists only in the worktree under the data root (AC-2).
- E3 Claude run: `run.finished status=ok`, verdict line present; argv in `meta.md` shows no Bash/Edit/Write tools (R3).
- E4 Trusted test exit code 0 recorded in `test-log.txt`; no agent claim is used as the test result.
- E5 Scope check: only `hello.txt` changed; no `scope.violation`.
- E6 No process left running after step 5; v1 `git status` unchanged; v2 tracked files unchanged.
- E7 Real stream formats parsed without `failed` misclassification; any mismatch with the fakes is recorded as a finding (fakes updated in a later approved fix, not during LIVE-A).

## Stop conditions (stop immediately, report)
- Any write outside the task worktree, or any change in v2 tracked files / v1.
- A CLI flag rejected or behaving differently from ARCHITECTURE §7.2.
- Claude run shows a shell or write tool available.
- Auth or quota error (no retry loop during LIVE-A; record and stop).
- Claude spend reaches the budget cap.

## Evidence to report
Run folders `projects/live-a/tasks/T-1/runs/*` (prompt.md, output.jsonl excerpt, meta.md, result.md, test-log.txt),
`events.md` excerpt, v1/v2 status before/after, token/cost usage per run.
