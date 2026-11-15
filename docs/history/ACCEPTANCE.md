# MVP acceptance evidence (2026-11-11)

All runs were real CLI runs unless marked SIMULATED. Records: `work/<task>/` (local, git-ignored; `hub.py status <task>`).
Owner `~/.codex/config.toml` hash `259cbae720916dc3` before and after every Codex run (no trust entry written).
Test targets were small throwaway modules inside the hub's `work/` folder (a Codex-trusted project).

| Scenario | Result | Evidence |
|---|---|---|
| A - Claude entry | PASS | Claude Code orchestrated `acc-code`, `acc-research`, `acc-loop`, `acc-handoff`: created tasks/checkpoints, chose roles, named skills in briefs, delegated, recorded every agent |
| B - Codex entry | PASS | `codex exec` given only the owner task (`acc-codex`) followed `AGENTS.md`: created the task, spawned a NATIVE Codex subagent (`agent_role: coder`, depth 1, instructions generated from `agents/shared/coder.md`, actual `gpt-6.1-sol`/low per its session file), delegated review to Claude via `hub.py`, ran pytest (9 passed), reported. It recorded the native model as Unknown; the orchestrator later verified it from the child session file |
| C - Cross-vendor | PASS (both directions) | Claude -> Codex: `acc-code/coder-1` requested and actual `gpt-6.1-sol`/low (session rollout). Codex -> Claude: `acc-codex/reviewer-1` actual `claude-sonnet-5-5`, PASS, run from inside the Codex workspace sandbox. Artifacts: `textutil.py` + tests, `stats.py` + tests, review texts in `<id>.last.md` |
| D - Dynamic team | PASS | `acc-code`: coder (Codex worker) + reviewer (Claude worker) + orchestrator tests. `acc-research`: one researcher (native Claude), no coder/reviewer. `acc-codex` (Codex's own choice): native coder + Claude reviewer. `acc-loop`: coder only after diagnosis |
| E - Checkpoint and quota handoff | PASS (quota SIMULATED) | `acc-handoff`: Codex delegation returned exit 4 `quota-unavailable` (HUB_SIMULATE_QUOTA). The remaining work existed only in `CHECKPOINT.md`; the Claude worker read the checkpoint (Read events in `coder-2.events.jsonl`) and did exactly that work (`longest_word`; checks `bbb`, `NONE`, `NONE`; completed function untouched). Not a live quota failover |
| F - Loop handling | PASS | `acc-loop`: the same failing check run twice -> `hub.py attempt` exit 5 `NO PROGRESS`; the orchestrator recorded the root cause (missing `wc.py`) and changed approach (delegate implementation) instead of re-running; tests then 3 passed. No retry count or time budget involved |
| G - Delivery | PASS | `acc-code`: `slugify` delivered, 5 tests passed (orchestrator run), cross-vendor review PASS, checkpoint "Delivered", agent table in `hub.py status acc-code` |

Unit tests of the tool itself: `tests/test_hub.py` 17/17 (fake CLIs; route refusals, argv, verification, quota, attempts, sync).

## Found during acceptance (fixed or documented)
- The first handoff brief (task `acc-loop`) had a mangled checkpoint path (shell escape), so the worker finished from the brief
  alone. Fixed in `hub.py`: every delegated prompt now carries the absolute checkpoint path, and Claude workers get
  `--add-dir <task folder>`. Re-tested in `acc-handoff` (above).
- Claude Code loads project agents (`.claude/agents`) only at session start: in the session that created them, the
  researcher ran as a general-purpose subagent with the role text in its prompt. New sessions see the roles natively.
- Generated Claude agents and skills must keep frontmatter on line 1 (fixed in `sync` before first use).
- A request to widen the Codex sandbox (network + `~/.claude`) for Scenario B was refused by the Claude Code safety
  check; the run used the default Codex sandbox, and the Claude CLI still worked from it on this Windows machine.
  This is an observation, not a guarantee: in Codex Desktop, approve the escalation if Codex asks.
- Actual effort of Claude workers and native Claude subagents is not exposed by the CLI: recorded as `Unverified`.

## Cost of the acceptance runs
Codex: about 33k (coder-1), 48k (Codex orchestrator) and 38k (its native coder) tokens. Claude workers: USD 0.11-0.22 each
as reported by the CLI. Building `hub.py` (Codex, medium): 257k tokens.

Security Gate: NOT PASS (no security verification was performed in this rebuild).

## Final MVP review (owner decision "FINAL MVP REVIEW AND MIGRATION PREPARATION")
Statuses: **real quota failover NOT VERIFIED**; **simulated quota handoff PASS**; **Security Gate NOT PASS**.

Independent review of `tools/hub.py` (Claude reviewer subagent, sonnet; separate from the Codex author): FAIL with 1 blocker.
- BLOCKER, confirmed by reproduction (8 parallel `agent new` -> `researcher-2` twice, 7 records): unlocked id allocation and
  read-modify-write. Fixed by Codex worker `fix-hub-blockers/coder-1` (actual `gpt-6.1-sol`/medium): exclusive record creation,
  per-task `.lock` around checkpoint/record/attempt updates, temp-file + `os.replace` writes. Re-run of the reproduction:
  8 distinct ids, 8 of 8 checkpoint lines kept. Two data-preservation/scope items fixed with it: `sync` refuses to overwrite
  files without the generated marker; `delegate --write` requires an explicit `--cwd`. `tests/test_hub.py` 27/27.
- Open, not fixed (not blockers; owner rule "fix only confirmed blockers"):
  - no worker timeout (a hung CLI leaves the record `running`; stop it and set the status by hand)
  - quota detection matches `429`/`quota` anywhere in the output (possible false quota handoff on a failing worker)
  - text written into checkpoints/records is not escaped (a line starting `## ` creates a fake section)
  - Claude model match is a substring match, and an `is_error` result with exit 0 counts as done
  - `sync` would prefix non-Markdown skill files (e.g. `.json`, `.js`) with a comment (only `SKILL.md` exists today)
  - attempt fingerprints mask digits but not paths or hex ids
  - a stale `work/<task>/.lock` after a killed process blocks for 30 s (delete it by hand)

## Operational smoke test (task `smoke-quickstart`)
Real task: a Thai quick-start guide, `docs/QUICKSTART-TH.md`. The orchestrator (Claude Code) loaded the `brief` skill (observed:
Skill tool call) to write the brief. `doc-keeper-1`: Codex worker, requested and actual `gpt-6.1-sol`/low (session file), skills
named brief and doc-coauthoring (whether the worker opened doc-coauthoring is not observable). `researcher-1`: native Claude
project role (`.claude/agents/researcher.md`, now loaded natively), checked every command against `hub.py --help`: OK.
Delivered; records in `work/smoke-quickstart/`. Owner Codex config hash unchanged.
