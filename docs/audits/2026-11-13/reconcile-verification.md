<!-- Preserved 2026-11-13 from an untracked report. Redacted: user home paths -> ~, session/agent ids -> placeholders. Evidence report only; Security Gate NOT PASS. -->
# Narrow skill-first reconciliation: verification (2026-11-13)

Baseline `feat/skill-first-hub` @ `f4943d0`; improvements adapted (no merge or cherry-pick) from `fix/skill-first-audit`
@ `1840d89`. Working tree uncommitted. Security Gate: **NOT PASS**.

## Change
| Area | What was adapted |
|---|---|
| `tools/hub.py` | Codex rollout `session_meta.payload.id` must equal the child thread id; payload shape checks (session meta, turn context, event payload, token info/usage) raise a specific `ValueError`; filename match `stem.endswith("-" + thread)`; resume offsets keyed by resolved path; evidence errors finalize an exited worker as `failed` exit 1 with PID cleared and output kept, after timeout/quota/process-exit outcomes. One JSONL decoder (`events(..., session=True)` + `session_path`); `record_path` unchanged. |
| Skill + brief | Record the actually loaded copy (nontrivial work); planned record + brief + checkpoint verified by a tool before every high-risk native spawn incl. re-review (helper `delegate` creates its own record); BLOCKED high-risk review never claims completion; added risk cases (data writes, install/filesystem boundaries, integrations, concurrency); read a selected skill before applying it and report skills used or why none fit. |
| Tests | Ported header/shape/finalization/resume-offset and installed-wrapper lifecycle tests. |
| Not taken | `--vendor` installer flag, README text, "prefer writing info/exclude" wording. Installer, shells, software-component bundle untouched. |

## Who did what
Codex integrator started `tools/hub.py` and stopped on its usage limit (08:27Z); Claude took over in the same
worktree. implementer-1 (Claude sonnet, hub-writer) finished it; reviewer-1 (Claude opus, fresh) FAIL with 1 Important
(planned-record rule vs `run.py delegate`) + 5 Minor; implementer fixed I1/M1; reviewer-2 (Claude sonnet, fresh) PASS.
All reviews are **SAME vendor** (Codex quota). Records: `work/reconcile-skill-first/`.

## Checks (run by the orchestrator)
- Full suite: **165 passed, 4 skipped** (symlink privilege) before the text-only fix; after it `test_skills` 19 passed,
  `test_portable_skill` 18 passed / 3 skipped (implementer). `sync --check` exit 0; `git diff --check` clean.

## Live Claude (Codex off PATH), exact candidate installed with `--dest` into an isolated `--plugin-dir` (no global change)
| Check | Result |
|---|---|
| Activation origin | `Skill hub-proof:multi-agent-hub`, runtime "Base directory" = the candidate copy; checkpoint records it |
| High-risk money task | rated HIGH; implemented, tests + docs (`money.md` updated, `notify.md` created) |
| Per-spawn records | checkpoint, `briefs/review1.md`, `agents/review1.md` (status planned) written and Glob-verified before spawn 1; `review2` brief + planned record written and Glob-verified before spawn 2; both updated with returned ids after |
| Fresh review / re-review | 2 distinct `hub-readonly` opus spawns; review1 found 1 medium + 3 low, fixed; review2 fresh PASS |
| Skills | "multi-agent-hub only; no other catalog skill needed" recorded. Bundled `software-component` was **not read** although docs were written - skill reading not exercised |
| Trivial rename / internal refactor | single agent, no spawn, no `.multi-agent-hub`, internal refactor changed no docs |
| Fixture tests (re-run by me) | all 3 OK |
| Project Git metadata | `.git` (excluding index) hash identical before/after in all 3 runs |
| Global config | `~/.claude/settings.json`, `~/.codex/config.toml` hashes unchanged |

## Not verified
- **Codex live** (activation, spawn records, review, helper resume/finalization on a real rollout): Codex usage limit,
  resets 18:06 local. Covered only by fake-CLI tests.
- Cross-vendor review of the final diff; native child permission enforcement; symlinked session root (skipped on this host).
