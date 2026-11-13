<!-- Preserved 2026-11-13 from an untracked report. Redacted: user home paths -> ~, session/agent ids -> placeholders. Evidence report only; Security Gate NOT PASS. -->
# Full Multi-Agent Hub Skill Audit: Claude

Date: 2026-11-13. Overall result: **FAIL for portable Hub skill entrypoint; plain Claude implementation works**. Security Gate: **NOT PASS**.

This report was compiled by the Codex audit orchestrator from actual separate Claude CLI runs, not authored by a Claude Hub orchestrator. Do not confuse that provenance with Claude skill activation.

## State and live test

Hub source: ~/.codex/worktrees/skill-first-hub/multi-agent-hub-v2, branch feat/skill-first-hub, tested commit a46f19812dc20b2aa7f4c58710d471e9794a8767. Disposable project: ~/Documents/Codex/full-skill-audit-20261113/claude/scenario-a. Session: <session-id>.

Harness requested haiku/low. System init and assistant messages identify claude-haiku-5-5. Actual effort: **Unverified**; requested low is not runtime proof. Child PATH excluded Codex, while Claude and the existing Python interpreter resolved. Normal native Agent/Skill tools were allowed, not assigned duties. No install, global setting edit or bypass-permissions mode was requested. No account failure or expiry was induced.

Prompt A invoked /multi-agent-hub and supplied the same quote-policy task as Codex, without naming teams, roles, extra skills or documentation requirements. The active catalog lists 159 skills and 197 slash commands, but no multi-agent-hub. Claude explicitly reported: the command is not installed in this session and it implemented inline instead. A plausible code result must therefore NOT be recorded as successful Hub skill execution.

## Capability results

| Capability | Result | Evidence |
|---|---|---|
| Hub entrypoint discovered and loaded in unrelated project | FAIL | Missing from active native catalog; no Skill tool call or Hub body read; subject expressly says unavailable. Generated .claude skill exists only in Hub checkout, not this project/user destination. |
| Autonomous plain code understanding and implementation | PASS, diagnostic only | Reads code/tests/docs, validates thresholds before item iteration, preserves shipping and iterable behavior. Harness did not tell it to update docs. |
| Actual code correctness and tests | PASS | A: 16 unit tests and root's 50/50 external cases. B after native resume: 16 unit tests. No package installation. |
| Scenario A component docs ownership | PASS, diagnostic only | Same implementing Claude updates quotes.md with threshold, four fields, eligibility and totals. No separate doc agent. |
| Scenario B docs unnecessary | PASS, diagnostic only | Equivalent divmod refactor; docs/orders/tests hashes unchanged from A. Subject autonomously avoided extra documentation. |
| Native agent creation and fresh reviewer independence | NOT VERIFIED | Zero Agent/Task calls. No subject-created independent review. Root's fresh Codex observer does not establish Claude-native review. |
| Dynamic skill selection/application and multi-skill combination | FAIL for exercised skill workflow | No Skill tool calls or additional SKILL.md reads; Hub was unavailable, so plain work does not establish skill composition. |
| Useful Hub task records and BRIEFs | FAIL for exercised workflow | No .multi-agent-hub records; no spawned-agent briefs. |
| Native session resume and preserved work | PASS, diagnostic only | B resumes the same Claude session and preserves the free-shipping feature/tests. No Hub file-checkpoint recovery demonstrated. |
| Claude-only execution without Codex | PASS for plain work; Hub parity FAIL | Isolated PATH and actual implementation/test results; no Codex calls. Do not extend to a skill that was not loaded. |
| Actual model/effort records | PARTIAL | Model verified from init/messages; effort Unverified; no subject Hub record. |
| Read-only/writer boundary for Claude native agents | NOT VERIFIED | No subject native child was created. File tools changed the disposable fixture; no OS filesystem enforcement conclusion. |
| Real quota/auth/expiry events | NOT VERIFIED | No real account event induced or observed. |
| Global-config invariance | NOT VERIFIED overall | Claude intervals include host Codex config hash change during A; no Claude global-write tool call evidenced. Git/Claude settings and installed Codex skill manifest hashes matched. Attribution unresolved. |
| Security Gate | NOT VERIFIED | NOT PASS. |

## Documentation and review

Before A, docs described three result fields and no discount policy. After A, the implementing subject documented the new keyword, validation, discount and total, and local-only eligibility. Root preserved both via git diff and snapshot. B changed only shipping.py and left docs untouched. Root's fresh observer found the component contract consistent with implementation, with one minor issue: the displayed quote_order(items, region="local") signature omits the new keyword that the following paragraph describes. Smallest correction is to include *, free_shipping_threshold_cents=10000 in that displayed signature. No fix was made.

The observer is audit-supplied and from Codex, not an autonomous Claude review. Its review cannot satisfy the missing Claude native review proof. The task remains valid as single-agent implementation; absence of extra agents does not prove Claude cannot spawn them.

## Skills and missing items

Native catalog visibility is runtime evidence of session access, not a blanket dependency/compatibility PASS. Claude tried pyflakes, reported it missing, and did not install it. Five 9arm skills remain project-local to the main Hub checkout for both vendors, not in this disposable project's catalog. None was invoked in these trials. qwen-agent is unsupported and Qwen is unnecessary. Catalog-only entries were not falsely reported as activated.

## Minimal proposed changes, not implemented

1. Owner-approved vendor-neutral skill wording and optional managed native Claude installation, if both-vendor portability is intended. Do not silently copy skills or remove Codex support.
2. Preserve nontrivial records, actual relevant skill use and required independent review as completion obligations while keeping team formation dynamic and tiny direct work valid.
3. Explicitly assign affected-component documentation to the implementer and consistency checking to the reviewer. A/B passed behaviorally; current portable text does not state that policy explicitly.
4. Correct the minor fixture documentation signature only if the fixture is adopted; it is disposable and no production code was changed.

See full-skill-audit-codex.md for the separately reproduced portable Codex helper finalization defect; this Claude task did not use that helper, so it is not evidence of a Claude worker defect.

## Evidence and decisions

Local evidence: work/full-skill-audit/claude-a/b.events.jsonl, launch JSON, claude-runtime-proof.json, A diff/snapshot, A/B observation JSON, root independent-test logs and observer briefs. Full transcript data remains local/ignored. Root used fresh native audit observers with fork_turns=none, requested gpt-6-luna low/medium; actual observer model/effort Unverified. They made no edits or test reruns.

Rulings: unavailable Hub entrypoint is a failure rather than an assumed activation; plain Claude work and native session resume are diagnostic only; no agents are forced merely to create a PASS; no installation or Hub correction is permitted in this audit. No fixes, commits, merges, pushes, deployments, global setting edits or cleanup were performed by the auditor. Global hash drift is explicitly unresolved. Branch feat/skill-first-hub remains unmerged. Adopted/Undone: none. Security Gate NOT PASS.
