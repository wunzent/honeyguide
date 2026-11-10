# Session Accumulation Audit (read-only) + Phase 2 proposal

Date: 2026-11-10 · Read-only: no v1 change, no session deleted, no process stopped, no AI worker started for the audit.
(One Codex run approved earlier for remove-signing slice A was already in progress and was left running.)

## 1. Findings

### 1.1 Sessions are historical files, not live processes
| Store | Total | Linked to v1 (`ALI\multi-agent-hub`) | Linked to v2 |
|---|---|---|---|
| Codex `~/.codex/sessions/**/*.jsonl` | 746 files, 220.8 MB | **465 files, 136.4 MB** — 476 with originator `codex_exec`, 2 interactive | 12 (one per approved v2 Codex step) |
| Claude `~/.claude/projects/**` | 66 files, 70.4 MB | 6 files, 34.5 MB (Desktop/CLI orchestrator sessions) | 1 (this session) |

v1 Codex sessions per day: 2026-11-05 **128**, 11-06 **233** (≈ 14–47 per hour), 11-09 **104**. Median 269 KB, max 868 KB.
Only 2 of 465 carry a fork/parent marker, so practically **none were resumed**.

Live processes now (Win32_Process): v1 `bin/worker.mjs` and `bin/dashboard.mjs` (both since 11-09 10:10, long-running
by design); **no live v1 `codex exec` worker**; one v2 `codex exec` (approved slice A). Other `claude.exe`/`node.exe`
processes belong to the Claude/Codex Desktop apps, MCP servers and editors, not to hub workers.
**Answer to Q1: historical session files, not running agents.**

### 1.2 Why v1 accumulated them (Q2)
- Each team step is a separate non-interactive `codex exec` call (Code PM brief → coder → tester → PM verdict, per round,
  plus reviewer/fix cards and auto-retries). Every call creates a new Codex session file.
- v1 `team.mjs` "resume" is a **hub checkpoint** (`card.team.waiting`, steps, replay), not a CLI session resume, so a resumed
  team also starts fresh CLI sessions.
- No `--ephemeral` and no cleanup: Codex keeps every session by default; nothing in v1 archives or reuses them.
- Result: 3–5 sessions per round × up to 3 rounds × cards × retries ⇒ hundreds per day under load.

### 1.3 v2 today (Q3, Q4)
| Aspect | v2 Phase 1 behaviour | Evidence |
|---|---|---|
| New session per worker run | **Yes** — every `runner.start` is a fresh `claude -p` / `codex exec` | adapters build argv without session reuse unless `resume_session` |
| Resume | Only after quota limit or lost run, using the recorded `session_id` checkpoint (`claude --resume`, `codex exec resume`) | `engine.py:435-446, 949`; `claude_cli.py:77`; `codex_cli.py:69` |
| Duplicate spawn prevention | Idempotency keys, respawn cap 1, orphan adoption by PID + create time + run token + exe | Phase 1 tests (609/609) |
| Process termination | Runner stops only its own PIDs (identity checked); engine never kills foreign processes | `runner.stop`, `test_v1_isolation.py` |
| Concurrency | ≤ 2 live hub workers, ≤ 1 dynamic | `policy.may_spawn` |
| Session cleanup | None (provider stores are not touched) | by design |
Expected volume: about 3 sessions per round (coder, reviewer, optional tester-analysis) — far fewer than v1 (no PM brief/verdict
LLM steps; tests run by Python), but still one file per run.

### 1.4 Implications (Q5)
| Area | Impact |
|---|---|
| Quota | Fresh sessions re-send the whole prompt + repo context every run (no cache reuse across runs); resume helps only for interrupted runs |
| Storage | v1 ≈ 136 MB in 4 days of Codex history; grows unbounded; lives in the user profile, outside the hub |
| Performance | Desktop "agents/sessions" lists and `codex resume` pickers get slow/noisy with hundreds of `exec` entries |
| Context continuity | Each run starts cold; continuity relies on the hub prompt (plan, prior REPORT, review issues) — which is correct, since task history must not depend on provider sessions |

## 2. Phase 2 proposal — session lifecycle (planning only)

### 2.1 Session registry (hub-owned, Markdown)
`projects/<p>/tasks/<t>/sessions.md` (fenced `hub-sessions` YAML) — one row per provider session:
`{task_id, run_id, role, provider, model, session_id, started_at, ended_at, status: active|completed|lost|resumable|abandoned, resume_count, context_tokens, reason}`.
Written by `runner` under the existing writer lock; events `session.started|ended|resumed|rotated`.

### 2.2 Reuse / resume rules (only when supported and safe)
| Case | Action |
|---|---|
| Quota-interrupted or lost run with a `session_id` | **resume** same session (already in Phase 1) — counts toward the attempt caps |
| Fix round for the same role on the same task (coder round 2/3, review-fix) | **resume** the role's last session if: provider resume verified (LIVE-A/E), same model, plan hash unchanged, session `context_tokens` < policy threshold; else fresh |
| Different role, plan revision, model change, scope change | **fresh** session |
| Reviewer | always **fresh** (independence) |
Resume attempts never bypass `may_spawn`; one active process per `task:role` (duplicate-active guard).

### 2.3 Context exhaustion
- Adapters record `usage` per run (Codex `token_count`, Claude `result.usage`); policy `context_rotate_ratio` (e.g. 0.7).
- Above the threshold, or on a provider "context length" error: checkpoint (`checkpoint.md`: plan hash, done/remaining
  files, last REPORT, open review issues, test log summary) → start a **fresh** session seeded with the checkpoint →
  mark old session `rotated`.

### 2.4 History independent of providers
Task history stays in `spec.md`, `state.md`, `events.md`, `runs/` (prompt, output.jsonl copy, result). Provider session
files are treated as caches: the hub never needs them to reconstruct a task.

### 2.5 Monitoring
Streamlit Agent Tree shows **active** (live PID, identity verified) separately from **completed / resumable / lost**
sessions; counts per task and per day; storage estimate of provider session files (read-only stat, no deletion).

### 2.6 Provider history management — verify, don't assume
- `codex exec --ephemeral` exists in `--help` (not verified): would stop Codex persisting a session, but also disables
  resume → use only for roles that never resume (reviewer, planner one-shots), after a LIVE check.
- Claude `--no-session-persistence` exists in `--help` (not verified): same trade-off.
- `codex archive` / `codex delete` exist; the hub will **not** call them. A Phase 2 `bridge.py sessions report` lists
  hub-created session ids for the owner, who decides any cleanup manually.

### 2.7 Proposed Phase 2 file scope (estimate, not approved)
`sessions.py` (new: registry, rules), `runner.py`/`engine.py` (record, resume decisions, rotation), adapters (usage +
context-error classification, optional `--ephemeral`/`--no-session-persistence` per role), `policy.toml` (`[sessions]`
thresholds, per-role reuse flags), `app.py` (active vs completed view), `bridge.py sessions report`, tests
`tests/test_sessions.py`. Live checks needed: resume of a finished `exec` session (Codex/Claude), ephemeral flags,
usage fields — each as a separately approved LIVE step.

## 3. Owner decisions (for the Phase 2 plan)
| ID | Question | Recommendation |
|---|---|---|
| S-1 | Resume the same role's session across fix rounds (after LIVE verification)? | yes, with context threshold |
| S-2 | Use `--ephemeral` / `--no-session-persistence` for one-shot roles (reviewer)? | yes after LIVE check |
| S-3 | Should the hub ever archive provider sessions? | no — report only, owner cleans up |
