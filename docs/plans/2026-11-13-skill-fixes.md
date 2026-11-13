# Combined assessment: skill-first migration regressions (2026-11-13)

Inputs: Claude-runtime audit (`outputs/full-skill-audit-claude.md` in this checkout, by Claude) and the Codex-runtime
audit (`~/.codex/worktrees/skill-first-hub/multi-agent-hub-v2/outputs/full-skill-audit-codex.md` plus its
Codex-compiled Claude report). Subject: `feat/skill-first-hub` @ `a46f198`. Security Gate: NOT PASS.

## Where both audits agree (live evidence)
| Area | Both audits found | Root cause |
|---|---|---|
| Code, tests, autonomy on small work | PASS: subjects read code first, adapted (missing `python`, git ownership), stayed single-agent on small tasks | - |
| Docs A / B | PASS behaviourally in every run (docs updated for interface change, untouched for internal change) | Behaviour came from the model and the fixture README, not from the skill: neither `SKILL.md` nor `references/brief.md` nor the `brief` duty notes assigns component docs to the implementer or a consistency check to the reviewer |
| Independent review | FAIL: no subject created a reviewer on its own, even for money-critical code (Claude C2) or a larger CLI task (Codex C) | `SKILL.md` describes how to review but has no completion obligation or risk trigger; hub `AGENTS.md` section 7 ("independent review for code changes") and section 5 ("do not fix reviewed findings yourself; re-review") were not carried over |
| Team formation | NOT VERIFIED / FAIL: zero spawns in all unforced runs; Claude spawned only when review was an acceptance condition | Same as above, plus Codex-only wording (next row) |
| Records | FAIL: no `.multi-agent-hub/` records on nontrivial work (Codex C, Claude C2); created only when asked (Claude C4) | "For tiny work ... create no task files" has no counterpart obligation for nontrivial work |
| Extra skills | FAIL: no subject read or applied any skill besides the hub | No instruction to search the catalog by task need and read the chosen SKILL.md; hub-owned `software-component` is not in the portable bundle; 9arm copies exist only in the hub checkout (correctly not required) |
| Claude parity | FAIL: installer installs only to `~/.codex/skills`; in an unrelated project Claude had no hub skill (Codex audit); with a project-local copy Claude loaded text that says "native Codex" 4 times (Claude audit) | Single Codex-worded `SKILL.md`; installer has no Claude destination |
| Permission agents | Claude used the owner's retired global v1 `~/.claude/agents/reviewer.md` (has Bash) because `hub-readonly`/`hub-writer` exist only inside the hub repo; Codex native child permissions Unverified | Shells are not part of the portable bundle |

## Found by one audit only
- Codex audit: helper Codex-worker finalization defect - `tools/hub.py` record-path confinement (line ~36, applied at
  ~208) rejects the legitimate read of the Codex rollout under the user session root (~240-245); the agent record
  stays `running`. Not exercised by the Claude audit.
- Claude audit: helper does not add `.multi-agent-hub/` to `.git/info/exclude` although `SKILL.md` says it prefers to.
- Claude audit: claude.ai-synced plugin skills are labelled "catalog (not installed)" (conservative mislabel).

## Codex trust entries (finding 7)
Exact scope: `~/.codex/config.toml` gained three `[projects.'...'] trust_level = "trusted"` tables during the audits,
written by the Codex CLI when it ran in a new folder (no hub code writes this file):
1. `...\scratchpad\audit\codex-proj` (Claude audit's Codex run)
2. `...\documents\codex\full-skill-audit-20261113\codex\scenario-a` (Codex audit)
3. `...\documents\codex\full-skill-audit-20261113\codex\team-task` (Codex audit)
Older, not from these audits: `...\Desktop\ALI\docs-trial` and `...\scratchpad\live-a\target`.
Safe cleanup (owner-approved, owner-run or run by me on approval): back up the file, delete only those exact table
headers plus their `trust_level` line (exact-match, fail if a header is not found once), compare the remaining file
with the backup line by line, change nothing else.

## Minimal fix list (one change set, nothing implemented yet)
1. **Docs ownership** (`skills/multi-agent-hub/SKILL.md`, `references/brief.md`, `skills/brief` duty notes): the
   implementer updates the affected component's documentation in the same task when purpose, interface, behaviour,
   dependencies or operations change (use `software-component` when available); no doc change for internal,
   behaviour-preserving work; the reviewer checks code-doc consistency. No documentation agent.
2. **Risk-based review** (`SKILL.md`, `references/brief.md`): the orchestrator rates each change; high risk (money,
   auth, security, data loss, public interface, cross-component or multi-file logic) requires a fresh independent
   reviewer before completion; findings go back to the implementer and the fix gets a fresh re-review; when a fresh
   reviewer is impossible, the report says "not independently reviewed". Trivial work stays single-agent.
3. **Vendor-neutral text** (`SKILL.md`): shared rules say "the active CLI's native agents"; two short vendor lines:
   Claude - `Agent` tool with a hub shell; Codex - `spawn_agent` with `fork_turns=none`. Nontrivial work keeps
   checkpoint/brief/agent records; selected skills are read before use.
4. **Portable permission agents** (`tools/install_hub_skill.py`): bundle `agents/shells/hub-readonly|hub-writer` and an
   opt-in, owner-approved Claude destination (skill + shells, managed with hashes, refuses unmanaged files). Claude
   `hub-readonly` stays Read/Grep/Glob; the skill forbids legacy v1 roles and, if shells are missing, routes read-only
   command work through the headless read-only route or reports the limitation.
5. **Skill selection across projects** (`SKILL.md`, installer): search the runtime catalog by task need, read the chosen
   SKILL.md, report missing ones; bundle hub-owned `software-component` with the managed install. No hardcoded 9arm.
6. **Helper fixes** (`tools/hub.py`): separate, narrowly confined read path for the Codex session root so worker
   verification finalizes (failed status on failure); write `.multi-agent-hub/` to local exclude when writable.
   Focused tests for both.
7. **Trust-entry cleanup** as above, plus one AGENTS/SKILL line: running Codex in a new folder adds a trust entry;
   the orchestrator compares the config hash before/after and reports, never edits.

## Live verification after the fix (both vendors, disposable projects, no named agents/skills in prompts)
Trivial task (no extra agents) - high-risk component change (reviewer appears without being asked, fix re-reviewed) -
docs-impacting change - internal change with no docs - Claude-only (Codex off PATH) - Codex-only (Claude off PATH).
Checks: spawn events in the stream, records content, docs diffs, my own test re-runs, config hashes.
