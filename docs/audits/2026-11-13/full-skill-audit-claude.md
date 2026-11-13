<!-- Preserved 2026-11-13 from an untracked report. Redacted: user home paths -> ~, session/agent ids -> placeholders. Evidence report only; Security Gate NOT PASS. -->
# Full audit of the `multi-agent-hub` Skill - Claude runtime

Date: 2026-11-13. Auditor: Claude Code (claude-opus-5-5) as audit lead; test orchestrators were fresh headless
Claude Code runs (`claude -p`, sonnet). Security Gate: **NOT PASS** (not independently verified by this audit).

Evidence labels: **LIVE** = observed in a real run in this audit; **HELPER-LIVE** = the optional helper run for real;
**INSPECT** = read from files/config only; **NOT VERIFIED** = no evidence either way.

## 1. Runtime, paths, commit
| Item | Value |
|---|---|
| Skill under test | `skills/multi-agent-hub/` on branch `feat/skill-first-hub` @ `a46f198` (worktree `~/.codex/worktrees/skill-first-hub/multi-agent-hub-v2`) |
| Installed copies | Codex: `~/.codex/skills/multi-agent-hub` (managed bundle). Claude: none at user level; for the tests the branch's own installer put a copy in each disposable project's `.claude/skills/multi-agent-hub` |
| Hub `main` | `2563bfb` (not changed by this audit) |
| Test projects | disposable git repos `ledger-mini` (Python, `ledger/money.py`, `docs/components/money.md`, unittest) under the session scratchpad |
| Orchestrator runs | 4 Claude (sonnet) + 1 Codex (gpt-6.1-sol medium), same task wording style, no agents/roles/models/skills named |
| Evidence copies | `work/full-skill-audit/` (stream logs `*.jsonl`, diffs, records, run scripts) |

## 2. Requirements versus current capability (summary)
| # | Capability | Verdict | Evidence |
|---|---|---|---|
| 1 | Autonomous analysis, planning, decisions | **PASS** | LIVE: every run read code, tests, docs and README before editing; chose scope; found `python` missing and switched to `py -3` / the Python 3.11 path; stated limitations |
| 2 | Dynamic agent and team formation | **FAIL** | LIVE: no run formed a team or reviewer on its own, including a task marked "handles money, correctness matters" (run C2). An agent was spawned only when review was an acceptance condition (run C4). See section 12 |
| 3 | Native spawning and delegation | Claude **PASS**; Codex **NOT VERIFIED** | LIVE (C4): `Agent` tool, `subagent_type: reviewer`, brief file written first, fresh agent, not resumed. Codex run spawned nothing; `fork_turns=none` not observed |
| 4 | Dynamic skill discovery and selection | **PARTIAL** | LIVE: `multi-agent-hub` loaded by every run. HELPER-LIVE index accurate (catalog skills marked "catalog (not installed)", Codex-only `multi-agent-hub` shown as codex). No run selected or combined any other skill; `software-component` and the 9arm skills are not accessible outside the hub checkout |
| 5 | Real implementation and problem solving | **PASS** | LIVE: working code in all runs; my re-run of each project's tests: OK |
| 6 | Testing, verification, independent review | **PARTIAL** | LIVE: Claude runs tested; Codex could not run tests in its sandbox and said so. Review only when demanded; the review's Important fix was applied by the orchestrator itself with no re-review (it said so) |
| 7 | Software Component Documentation | **PASS (behaviour) / regression in instructions** | LIVE A/A-new/B scenarios correct (section 8), but every run cited the test project's README rule, not the skill: the skill and duty notes no longer carry the documentation duty |
| 8 | Checkpoints, recovery, no-progress | Helper **PASS**; orchestrator-level **NOT VERIFIED** | HELPER-LIVE: NO PROGRESS exit 5 on a repeated action/outcome, history kept across resume, `task new` on an existing slug refused. No interrupted orchestrator run was resumed |
| 9 | Agent/vendor/model/effort/progress records | **PASS when created; not created by default** | LIVE (C4): record has duty, vendor, id, requested vs observed model (`Unverified`), permission requested vs enforcement (`Unverified (Bash available)`), status, evidence. Runs C1-C3 and Codex wrote no records (allowed by the skill for small work) |
| 10 | Claude-only / Codex-only operation | Claude-only **PASS**; Codex-only **PARTIAL** | LIVE: C2-C4 ran with every `codex` removed from PATH (`codex hidden`); Codex run with `claude` removed (`claude hidden`) completed without Claude but with no native agents and no test run |

## 3. Orchestrator decisions observed (LIVE)
| Run | Task (owner words only) | Decisions it made |
|---|---|---|
| C1 Claude | currency prefix + simplify `_strip_groups` | Worked alone ("small enough to do directly"); updated docs citing README; adapted to missing `python`; codex was still on PATH via `AppData/Roaming/npm` but was never called |
| C2 Claude | new `ledger/notify.py` (money, correctness matters) + prefix support | Worked alone; strict case-sensitive design for money; created `docs/components/notify.md`, updated `money.md`; found the 3.11 interpreter path itself; no reviewer ("the only review was my own") |
| C3 Claude | internal-only simplification | Worked alone; changed only `ledger/money.py`; no docs, no records (said so) |
| C4 Claude | same change "needs an independent review by someone who did not write it" | Created `.multi-agent-hub/review-money/` (checkpoint, brief, agent record), spawned a fresh read-only reviewer, fixed the Important finding, added tests and doc lines, stated that the fix was not independently re-reviewed |
| X1 Codex | same as C1 | Worked alone; updated docs citing README; used per-command `git -c safe.directory` (no global change); could not find Python in its sandbox and reported tests unverified |

## 4. Agents actually spawned
| Run | Agent | Duty | Mechanism | Fresh | Evidence |
|---|---|---|---|---|---|
| C4 | reviewer-1 (`<agent-id>`) | independent read-only review of the money change | Claude `Agent` tool, `subagent_type: reviewer` | yes (new agent, not resumed) | `claude-review.jsonl` spawn event and `[sub]` tool calls; `claude-new-records/review-money/agents/reviewer-1.md` |
No other run spawned an agent. The `reviewer` type used is the owner's user-global v1 fixed role (`~/.claude/agents/reviewer.md`, "Only when explicitly requested ..."), because the hub's `hub-readonly` shell exists only inside the hub repo. Its Bash access means read-only was not enforced; the record says so.

## 5. Skills discovered, selected and used
- Discovery (HELPER-LIVE, foreign project): 240 entries (claude 68, codex 172), 202 "catalog (not installed)". Not
  found outside the hub checkout: `software-component`, `debug-mantra`, `scrutinize`, `post-mortem`,
  `management-talk`, `qwenchance` (they are project-local to the hub repo) - correctly not reported as available.
  `multi-agent-hub` shown for codex only (true: no user-level Claude copy). `qwen-agent` not required and not used.
- Still mislabelled (known Minor): skills of claude.ai-synced plugins are shown as "catalog (not installed)" although
  the Claude session loads them (e.g. `design-skills:accessibility-audit` is in this audit lead's own skill list).
- Selected and used: only `multi-agent-hub` (LIVE, `Skill` tool call first in every Claude run; `$multi-agent-hub` in
  Codex). No run read or applied another skill; combining skills was not observed.
- The 9arm skills were verified as installed and loadable only inside the hub checkout (earlier session, `sync --check`
  LOCAL SKILL); not exercised by these test runs.

## 6. Code changes and test evidence (my re-runs: `py -3.11 -m unittest discover -s tests`)
| Run | Files | Re-run |
|---|---|---|
| C1 | `ledger/money.py`, `tests/test_money.py`, `docs/components/money.md` | OK |
| C2 | + `ledger/notify.py`, `tests/test_notify.py`, `docs/components/notify.md` | OK |
| C3 | `ledger/money.py` only | OK |
| C4 | `ledger/money.py` grouping fix, 3 tests, both docs | OK (13 tests per run log) |
| X1 | `ledger/money.py`, `tests/test_money.py`, `docs/components/money.md` | OK (Codex itself could not run them) |
Diagnosis/correction: C4's reviewer found by probing that `parse_amount("1,2,3")` returned 12300 (reachable from
notifications); the orchestrator fixed it and probed the fix. Diffs: `work/full-skill-audit/*.diff`.

## 7. Software Component Documentation (before -> after)
| Scenario | Expected | Observed | Verdict |
|---|---|---|---|
| A: documented behaviour changed (prefix support) | update `money.md` formats + change log | C1, C2, X1 added the format line and a Change Log row | PASS |
| A-new: new component | minimum useful doc | C2 created `notify.md` (purpose, formats, dependencies, change log) | PASS |
| B: internal-only change | no doc change | C3 changed no doc | PASS |
| Mixed (C1/X1) | doc for A only | both also mentioned the internal refactor in the Change Log row (harmless noise) | PASS with note |
| Reviewer checks code vs docs | consistency checked | C4 reviewer found a doc/behaviour mismatch (inner spaces) and the doc was corrected | PASS |
Decision source: every run cited the test project's README ("must match the code"). The skill text and
`skills/brief` duty notes no longer contain the documentation duty that `agents/shared/coder.md` had before the
dynamic-roles change (`f3776d2`: "Edit specification documents only when the brief names them (then follow the
software-component skill)"). In a project without such a README line this behaviour is NOT VERIFIED.

## 8. Checkpoint and recovery (HELPER-LIVE, `~/.codex/skills/multi-agent-hub/scripts/run.py`)
- `task new probe` wrote `.multi-agent-hub/probe/CHECKPOINT.md` with the objective; `checkpoint` added a Ruling line.
- `attempt` same action+outcome twice -> exit 5 `NO PROGRESS`; a changed action -> exit 0; after a resume attempt the
  history (3 lines) was kept and the repeat was still detected (exit 5). No retry count or time budget exists.
- `task new` on an existing slug -> `ERROR: task already exists` (original requirements not overwritten).
- Gap: the helper did not add `.multi-agent-hub/` to `.git/info/exclude` (the folder showed as untracked); C4's
  orchestrator added it itself.
- Orchestrator-level resume after an interrupted run: NOT VERIFIED.

## 9. Vendor independence
- Claude-only (LIVE): C2-C4 with `codex` absent from PATH (both `nvm4w` and `AppData/Roaming/npm` removed) completed;
  no Codex call. C1's hiding failed (second codex copy) but no Codex call happened.
- Codex-only (LIVE, supplementary): X1 with `claude` absent completed without Claude; no native agents; tests not run
  in its sandbox. The Codex-runtime audit proper is `outputs/full-skill-audit-codex.md` (run by Codex; a Codex
  session was running a parallel audit, seen as `documents\codex\full-skill-audit-20261113` in the Codex config).
- Global config: X1 added a trust entry for its test folder to `~/.codex/config.toml` (Codex behaviour on a new
  project). My attempt to remove it was denied by the permission classifier; it is still there. Backup of the
  pre-run file: scratchpad `audit/codex-config.before.toml`.

## 10. Model and effort verification
- Claude stream `init` and every assistant event: `claude-sonnet-5-5` (LIVE, matches the requested `--model sonnet`).
  Sub-agent events in C4 also show `claude-sonnet-5-5`, but the orchestrator recorded the reviewer's model as
  `Unverified` (conservative; it did not read the stream). Effort is not exposed by Claude headless: Unverified.
- Codex: requested gpt-6.1-sol / medium via flags; the JSON stream does not name the model; `Unverified` here.

## 11. Regressions or missing original features
1. **Documentation duty lost from instructions** (Important): skill and duty notes do not tell the implementer to
   update component docs or the reviewer to check code-doc consistency; behaviour relied on the project's README.
2. **No default independent review for code changes** (Important): hub `AGENTS.md` section 7 required it; the skill
   makes review conditional ("For independent review, use ..."), so even money-critical code was self-reviewed (C2).
   The rule "do not fix reviewed findings yourself; re-review the fix" (hub section 5) is also absent (C4).
3. **Claude copy is Codex-worded** (Important for Claude-only): the installed `SKILL.md` says "native Codex tools and
   agents" four times; Claude runs never considered native agents unless forced.
4. **No portable permission shells**: outside the hub repo there is no `hub-readonly`/`hub-writer`; C4 fell back to the
   owner's user-global v1 fixed roles (`~/.claude/agents/reviewer.md`, `planner.md`, `doc-keeper.md`), which the
   dynamic-roles decision retired, and whose read-only is not enforced (Bash).
5. **Hub-owned skills not portable**: `software-component` and the approved 9arm skills are unreachable in other
   projects; portable mode disables third-party install.
6. Minor: helper does not write the local exclude; synced plugins labelled catalog; Codex sandbox cannot see the Python
   launcher, so Codex cannot run Python tests in that sandbox.

## 12. Recommended minimal fixes (not implemented)
1. `skills/multi-agent-hub/SKILL.md`: vendor-neutral wording ("the active CLI's native agents"), and one paragraph:
   "When a change alters a component's documented purpose, interface, behaviour, dependencies or operations, the
   implementer updates that component's documentation in the same task (follow `software-component` when available);
   internal-only changes need none; the reviewer checks code-doc consistency."
2. Same file: "Code changes other than tiny ones get a fresh independent review before completion; review findings go
   back to the implementer and the fix gets a scoped re-review."
3. Bundle the two permission shells with the skill (or name the CLI's built-in read-only agent type) so it never falls
   back to retired user-global roles; ask the owner whether to remove the v1 `~/.claude/agents` roles (global change).
4. Add `software-component` (hub-owned) to the portable bundle; document how approved third-party skills reach other
   projects.
5. Helper: write `.multi-agent-hub/` to `.git/info/exclude` when writable, as the skill says.

## 13. What was not verified
Codex native agent spawning and `fork_turns=none`; orchestrator-level resume after interruption; model/effort for
Codex; behaviour in a project without a documentation rule in its README; security properties (Security Gate NOT PASS).
