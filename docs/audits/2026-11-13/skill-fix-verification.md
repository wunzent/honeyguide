<!-- Preserved 2026-11-13 from an untracked report. Redacted: user home paths -> ~, session/agent ids -> placeholders. Evidence report only; Security Gate NOT PASS. -->
# Skill fix verification (2026-11-13)

Change: owner-approved 7-item fix list (`outputs/combined-assessment.md`), worktree `../multi-agent-hub-v2-skillfix`,
branch `hub/skill-fixes/writer-1` from `feat/skill-first-hub` @ `a46f198`, **uncommitted**. Not merged, not pushed.
Security Gate: **NOT PASS**.

## Implementation and review
| Step | Agent | Result |
|---|---|---|
| Items 1-6 + item-7 line | implementer-1 (Claude sonnet, native hub-writer) | DONE; 154 passed / 3 skipped |
| Review | reviewer-2 (Codex) | quota-unavailable (exit 4) - handed to Claude per quota rule |
| Review | reviewer-3 (Claude sonnet hub-readonly, SAME vendor) | PASS, 4 Minor, security PASS |
| Fix round 1 (4 Minor: gitdir hardening, per-file marker, opt-in `--codex-agents`, wording) | implementer-1 | DONE; 156 passed / 4 skipped |
| Re-review | reviewer-4 (Claude sonnet hub-readonly, fresh, SAME vendor) | PASS, all ADDRESSED, 2 residual Minor, security PASS |
| Fix round 2 (records not kept on a nontrivial live run) | implementer-1 | DONE; portable tests 15 passed / 4 skipped; sync clean |
No cross-vendor review of the final code yet (Codex quota at the time).

## Live runtime evidence (disposable `ledger-mini` projects; prompts name no agents, roles, models or skills)
| Scenario | Claude (Codex off PATH) | Codex (Claude off PATH) |
|---|---|---|
| Trivial task (rename a variable) | single agent, no records, no docs; tests OK | single agent, no records, no docs; tests not runnable in its sandbox (reported) |
| High-risk component change (new money component) | rated high risk itself; spawned fresh `hub-readonly` reviewers (`Agent` tool); findings fixed; fresh re-review | rated high risk itself; `spawn_agent` x2, `agent_type: hub-readonly`, `fork_turns: "none"` (session log); finding fixed; fresh re-review |
| Documentation-impacting change | `money.md` updated, `notify.md` created | `money.md` updated, `notify.md` created |
| Change needing no documentation | trivial rename: no doc change | trivial rename: no doc change |
| Records on nontrivial work | after fix round 2: `.multi-agent-hub/notify/` checkpoint, 2 briefs, 2 agent records | `.multi-agent-hub/bank-notifications/` checkpoint, 2 briefs, 2 agent records |
| Unrelated project, user-level install | skill loaded from `~/.claude/skills` with no project setup | skill loaded from updated `~/.codex/skills`; shells from project `.codex/agents` |
| Tests re-run by the audit lead | all OK | all OK |
| Model | `claude-sonnet-5-5` (stream); reviewer model chosen per run (opus or sonnet) | `gpt-6.1-sol` (session log); child values recorded `Unverified` |
Not verified live: enforcement of `hub-readonly` on Codex children (recorded `Unverified`); orchestrator resume after
an interrupted run; Codex shells installed at user level (`--codex-agents` into `~/.codex` was not approved, so
the test used the project's `.codex/agents`).

## Global changes made (owner-approved)
- Codex: `~/.codex/skills/multi-agent-hub` updated by the managed installer; previous version in
  `multi-agent-hub-v2-backups/codex-skill-update-20261113/`.
- Claude: `~/.claude/skills/multi-agent-hub` and `~/.claude/agents/hub-readonly.md`, `hub-writer.md` installed;
  `settings.json` unchanged; listing in `multi-agent-hub-v2-backups/claude-skill-install-20261113/`.
- Codex trust entries: the 3 audit entries and the 1 entry of this verification run were removed exactly (backups
  kept). Not touched: `documents\codex\full-skill-fix-proof-20261113\codex\scenario-a`, added by a separate Codex
  session during this period.
- Still present and not touched: legacy v1 roles in `~/.claude/agents` (planner, reviewer, doc-keeper and old
  `.toml` files); the skill now forbids using them.
