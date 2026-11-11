# LIVE-A Re-run Procedure — confirm Claude tool lockdown (F3/L4) and Codex launch (F4)

Status: **PROPOSED — needs separate owner approval.** Small quota use. Security Gate stays **NOT PASS**.

## Purpose
Prove with the **real** CLIs what unit tests (fake CLIs) cannot:
1. F3/L4: with `--tools Read,Glob,Grep --strict-mcp-config --disable-slash-commands`, the Claude worker's real
   `system/init` event lists only Read/Glob/Grep, no live MCP servers, and empty `slash_commands`, `skills`, `plugins`
   (`terminal_slash_commands` empty); if not, the hub must **fail closed** (run failed, result discarded, needs-you).
2. F4: Codex is launched as `node …/codex.js` (not `cmd.exe`), and the recorded exe/process tree is correct.
3. F1: the orchestrator's `propose-route` (with `--budget-usd 0.50` for Claude) is honoured — no test harness needed.
4. F2/L1: real `session_id` values are stored verbatim (not `[REDACTED]`).
5. F5: `meta.md` contains sanitized argv + `prompt_sha256` + `body_sha256`, no prompt text or secrets.

## Preconditions
| # | Check |
|---|---|
| P1 | L1–L4 fix round committed; `git status` clean for tracked code |
| P2 | Same throwaway target repo (session scratchpad, outside every repo) or a fresh one; project `live-a`, new task `T-2` |
| P3 | Both CLIs logged in (`claude auth status`, `codex login status`) — no quota |
| P4 | v1 `git status` snapshot taken (read-only) |

## Steps
| # | Action | Quota |
|---|---|---|
| 1 | `bridge.py new-task live-a T-2`, `set-plan` ("append line `world` to hello.txt"), `request-approval` | none |
| 2 | Orchestrator records the owner's approval words: `bridge.py approve live-a T-2 --quote "<owner words>" --desktop claude` | none |
| 3 | `bridge.py propose-route live-a T-2 --role coder --vendor codex --model gpt-6.1-sol --effort low` and `--role reviewer --vendor claude --model sonnet --effort low --budget-usd 0.50` | none |
| 4 | `engine.py --once` loop until a terminal state (max 20 min); no harness writes to state | small |
| 5 | Inspect run folders, events, `meta.md`, Claude init event; v1/v2 status after | none |

## Expected results
| ID | PASS if |
|---|---|
| R1 | Claude init `tools` = exactly Read, Glob, Grep; `mcp_servers` empty or all failed/disabled; `slash_commands`, `terminal_slash_commands`, `skills`, `plugins` empty; `agents` may be non-empty (Agent/Task absent) |
| R1-alt | If the real CLI still exposes extra items: the run is **failed** with `tool_restriction_violated`, no verdict accepted, task needs-you → reported as finding (lockdown not enforceable with these flags) — this is a correct fail-closed outcome but means Claude workers cannot be used until resolved |
| R2 | Codex `meta.md` exe = node, argv includes `codex.js`; no lingering processes after the run |
| R3 | Routes in events match the proposals (incl. Claude budget 0.50); no `route.rejected` |
| R4 | `session_id` stored verbatim in state/meta for both runs |
| R5 | `meta.md` has argv, `prompt_sha256`, `body_sha256`; no prompt text, tokens or run_token |
| R6 | Tests PASS → review PASS → auto commit on `hub/T-2` in the throwaway worktree only; v1 and v2 tracked files unchanged; no push |

## Stop conditions
Any write outside the task worktree; v1/v2 change; a Claude run that shows shell/write/MCP-write tools **and is not
failed closed**; CLI flag rejected; auth/quota error (record, no retry loop); Claude spend reaching $0.50.

## Evidence reported
Init-event field counts (tools/mcp/slash/skills/plugins/agents), meta.md excerpts, events excerpt, cost/tokens, before/after status.
