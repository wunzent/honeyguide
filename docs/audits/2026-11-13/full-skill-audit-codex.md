<!-- Preserved 2026-11-13 from an untracked report. Redacted: user home paths -> ~, session/agent ids -> placeholders. Evidence report only; Security Gate NOT PASS. -->
# Full Multi-Agent Hub Skill Audit: Codex

Date: 2026-11-13. Overall result: **FAIL against the full Owner success criterion**. Security Gate: **NOT PASS**. This audit verifies the existing implementation; no Hub fix was made.

## Runtime and tested state

- Hub source: `~/.codex/worktrees/skill-first-hub/multi-agent-hub-v2`.
- Branch: `feat/skill-first-hub`; tested commit: `a46f19812dc20b2aa7f4c58710d471e9794a8767`.
- Installed entrypoint: `~/.codex/skills/multi-agent-hub/SKILL.md`. All six managed payload hashes match the installation manifest. Source and installed skill text were independently compared.
- Disposable projects: `~/Documents/Codex/full-skill-audit-20261113/codex/scenario-a`, `codex/team-task`, and `recovery` under the same audit directory. They are isolated Git projects, not production worktrees.
- Live subject: Codex CLI. Harness requested `gpt-6-luna`, effort `low`; runtime turn_context confirms both. Initial model choice belongs to the harness, not a demonstrated autonomous model-selection decision. Desktop GUI was not exercised.
- Each subject process excluded Claude from its own PATH; Codex still resolved. No Claude or Qwen delegation was observed. No account state was altered.

## Method and autonomous decisions

The subject received `$multi-agent-hub` plus a software requirement and scope. It was not told which duties, team size, models for assignments, skills, documentation changes, or review agents to choose. No project AGENTS.md or fixed agent files were seeded. The fixture README points to an existing component contract, without an instruction to update it.

A: extend quote_order with configurable local free shipping, an explicit discount field, precise validation and preserved iterable/rate semantics. B: resume the same session and replace only internal shipping-block arithmetic with a divmod equivalent. C: a fresh larger task adds a JSONL batch CLI with input validation, line-local errors, streaming order and exit codes. C checks whether a broader task changes the autonomous strategy; it does not force delegation.

Observed decisions: Codex inspected source, tests and docs before editing; selected exact-int threshold validation to reject bool; validated thresholds before consuming empty input; updated the affected component contract on its own; kept B docs untouched because the public contract stayed unchanged; implemented C as a thin stdlib wrapper around existing pricing. It adapted to Git ownership errors using per-command safe.directory, without a global Git setting. It implemented directly in all three trials, ran tests, and reported limitations.

## Original responsibilities versus current evidence

| Capability | Result | Evidence and limits |
|---|---|---|
| Goal understanding, code inspection and bounded strategy | PASS | Actual tool calls read source/tests/docs before edits; implementation and external oracles match requirements. Plans were concise prose, appropriate to the fixtures. |
| Real implementation and focused verification | PASS | A: 10 unit tests and external 50/50 cases. B: 10 tests after resume. C: 14 tests and external 16/16 CLI cases. Root reran tests independently. |
| Avoid unnecessary agents on small work | PASS, limited | A/B were handled directly; no fixed team was forced. This alone does not establish correct delegation decisions for arbitrary complex work. |
| Autonomous native team formation | NOT VERIFIED in these subject trials | Runtime function-call inspection found zero spawn_agent calls in A, B and C. Root's audit observers were real native agents, but were assigned by the audit harness and are not proof of subject team formation. Prior migration native-spawn evidence is historical, not a new audit PASS. |
| Self-contained subject BRIEFs and per-agent permission choices | NOT VERIFIED | No subject subagents were created. Audit observer briefs are separate. Named hub-readonly/hub-writer enforcement was not observed for subject native agents. |
| Fresh independent review before subject delivery | FAIL for the exercised workflow | Subjects delivered changed code without creating a reviewer. Original Hub AGENTS.md section 7 requires independent code review. The portable skill explains how to perform independent review but does not retain that explicit completion obligation. Root later supplied a fresh audit observer; that does not repair subject autonomy. |
| Runtime skill discovery | PASS for catalog visibility; compatibility remains per-skill | Codex runtime exposes 137 catalog names including user and plugin entries; Hub was present and its full instructions loaded. Catalog presence is not proof every dependency works. |
| Autonomous relevant additional skill read/application | FAIL in tested workflow | Zero SKILL.md read calls and no selected additional skill evidence in A/B/C. Hub itself loaded by explicit invocation. Multiple-skill composition was not demonstrated. This is a behavior finding, not proof that skill files cannot be read. |
| Scenario A: affected Software Component Documentation | PASS, limited to implementation ownership | Same implementing subject updated docs/components/quotes.md with keyword-only threshold, four result fields, discount semantics and validation. No separate documentation agent. No subject reviewer checked consistency. Audit observer confirmed consistency. |
| Scenario B: documentation not required | PASS | SHA-256 comparison from A to B shows docs, orders.py and tests unchanged; only shipping.py changed. Preserved public behavior verified. Decision was autonomous, without telling it to avoid docs. |
| New C component documentation | PASS for minimal usage; depth limited | README adds CLI purpose, invocation, input and output ordering/continuation basics. Existing quote contract remains valid. A complete CLI reference/exit-code description was not produced. |
| Native session resume | PASS | B resumes A's same Codex thread; free-shipping changes and tests remain intact. This is native conversation recovery, not file-checkpoint recovery. |
| Subject checkpoints, progress/decision history and agent records | FAIL in exercised workflow | No .multi-agent-hub directory in either Codex project after delivery. Nontrivial C also has no task records. Required requested/observed metadata cannot be audited from subject-produced records. Runtime extraction by the auditor is separate. |
| Optional helper checkpoints and no-progress persistence | PASS for file operations and simulation | Task, brief, checkpoint, two attempt entries retained. Simulated Claude quota returns 4; identical action/outcome after vendor change returns 5 NO PROGRESS. No retry cap or loop was added. |
| Optional helper actual Codex delegation/recovery | FAIL | Worker produces a result, but helper verification exits 1 with record path escapes working directory; its record remains running although the PID was no longer present on root's check. Independent source investigation confirms the cause below. |
| Read-only probe | NOT VERIFIED as independently extracted OS trace in this audit | Actual worker reports one Python overwrite denied with PermissionError; marker remains audit-original. Helper finalization fails. Additional raw runtime extraction was blocked before execution due to the auditor's mistyped working directory; it was not retried. Do not elevate the worker reply alone into a general enforcement certification. Prior migration direct-denial evidence remains historical. |
| Codex-only work | PASS for A/B/C | Other vendor absent from child PATH; live code, docs, tests and resume succeeded without Hub registration, Dashboard or Claude. |
| Claude-only Hub parity | FAIL for installed entrypoint | Separate Claude run's active catalog lacks multi-agent-hub; it explicitly reports plain execution. Successful plain Claude code work is not a Hub skill PASS. See full-skill-audit-claude.md. |
| Actual model/effort and record accuracy | PARTIAL: runtime verified, subject records FAIL | Codex turn_context confirms gpt-6-luna/low and workspace-write. Native child values remain Unverified. Portable helper's record is stale running/Unverified after verification failure. |
| Security Gate | NOT VERIFIED | NOT PASS; this functional audit is not independent security approval. |

## Documentation before/after evidence

Before A, quotes.md described quote_order(items, region="local"), exactly three result fields, and full shipping on every nonempty order. After A, Codex documents the full extended signature, shipping_discount_cents, original undiscounted shipping, local eligibility, None disabling, bool rejection and the total formula. Code and tests changed in the same task. The A snapshot and diff retain both versions. B hashes confirm no documentation or public-interface churn.

The portable skill and compact brief do not explicitly assign affected SWC maintenance to implementers or consistency checks to reviewers. The old v2 instructions inspected here also lack the specific implementer-owned SWC wording. Therefore this is a gap against the newly explicit Owner requirement, not evidence that an identified old v2 clause was removed. Live A/B documentation decisions nevertheless passed. The required independent review obligation is explicit in old/current Hub AGENTS.md and was not exercised by the portable subject.

## Concrete regression and smallest proposed fixes

1. **Portable Codex worker finalization regression, Important.** tools/hub.py:36 confines record_path to project records; events at line 208 applies it to every input; verify at lines 240-245 reads a Codex rollout under the user session directory through events. That legitimate read is rejected before final agent updates at lines 413-415. Keep project-record confinement, add a separate narrowly constrained read path for metadata under the configured Codex session root, and finalize failure status when verification fails. Add a focused fixture with an external session-root rollout; do not remove the confinement guards. No fix implemented.
2. **Portable execution loses completion obligations in practice.** SKILL.md lines 11-19 leaves nontrivial records and review too discretionary; all tested deliveries omit them. Smallest instruction correction: require useful checkpoint/agent/attempt records for nontrivial work, actually read/apply relevant selected skills, and require fresh independent review for code changes where supported; report explicit limitations when unavailable. Preserve direct tiny work and dynamic team decisions. No mandatory role library or fixed team is needed.
3. **Explicit SWC ownership policy missing.** Add one compact implementer-owned affected-component-doc rule and a reviewer consistency check. Avoid docs on internal-only behavior-preserving changes. This strengthens an explicit requirement; it is not a code failure demonstrated by A/B.
4. **Claude entrypoint unavailable in unrelated projects.** Before any installation, Owner should decide whether vendor-neutral skill wording and an opt-in managed native Claude destination are wanted. Current installer defaults to Codex user skills; generated Claude project-local copies in the Hub do not make it available everywhere. Do not claim both-vendor portability or silently install it.

No fixes, dependencies or skills were installed by this audit. No source edits, commit, merge, push, deploy or cleanup occurred. New reports and ignored work records are audit artifacts only.

## Skill inventory and limits

Source-checkout discovery snapshot: 280 location-qualified entries, 185 catalog-only entries excluded from available counts. Separate main-checkout snapshot: 288 location-qualified entries, 202 catalog-only. These are different-root/time discovery snapshots, include cache activation-unverified entries, and are not compatibility counts. Native Codex catalog has 137 names; Claude has 159 skill names. No marketplace-only item was demonstrated as used. No other-vendor-only item was falsely reported as actually activated.

All five 9arm skills exist in both vendor-local directories of the main checkout (10 paths): debug-mantra, scrutinize, post-mortem, management-talk and qwenchance. They do not exist as project copies in the disposable fixtures and are not in those runtime catalogs. Actual trial invocation: none. Their manifest marks text-based support, not live compatibility proof. qwenchance contains a fixed retry cap that must yield to Hub's progress-based policy. qwen-agent remains unsupported due to alias/gateway requirements; neither Qwen nor that skill is needed. Nothing was reinstalled. Graphify had no existing graph here; graph generation/dependency installation was not performed. Claude reported missing pyflakes and did not install it.

## Actual agents and observability

| Agent / identity | Responsibility | Skills | Vendor / kind | Requested model / effort | Actual model / effort | Status |
|---|---|---|---|---|---|---|
| Codex A/B: <session-id> | Quote policy, then internal refactor | Hub loaded; no extra read | Codex CLI subject | gpt-6-luna / low | gpt-6-luna / low, turn_context | Completed; no task records |
| Codex C | Batch CLI implementation | Hub loaded; no extra read | Codex CLI subject | gpt-6-luna / low | gpt-6-luna / low, turn_context | Completed; no task records; ID in runtime-proof JSON |
| /root/historical_capability_auditor | Original/current mapping and helper regression investigation | brief, verify-and-stop assigned | Codex native audit observer | gpt-6-luna / low | Unverified / Unverified | Done; no edits/tests |
| /root/final_audit_reviewer | Fresh code/doc/evidence consistency review | brief, verify-and-stop assigned | Codex native audit observer | gpt-6-luna / medium | Unverified / Unverified | PASS with minor documentation finding; no rerun |
| marker-observer-1 | Recovery fixture read-only marker probe | none | Codex CLI helper worker | gpt-6-luna / low | Unverified / Unverified in helper record | Reply completed; helper exits 1, record remains running |
| simulated-vendor-probe-1 | Simulated unavailable vendor route | none | Claude simulation, no agent launched | haiku / low | Unverified / Unverified | quota-unavailable, simulated |

Both native audit observers were actually spawned with fork_turns=none and self-contained briefs; their requested read-only duty is not independently demonstrated per-agent OS enforcement. They were not spawned by the subjects. Medium effort on the final audit observer follows the multi-file verification scope; no premium model was used. Initial subject model/effort was harness-controlled; autonomous assignment model selection remains NOT VERIFIED.

Fresh observer review found no code blocker in fixture implementations and one minor Claude doc signature issue. It confirmed the helper defect and cautioned against attributing plain Claude work or root-supplied review to the Hub subjects. It read artifacts/source, did not rerun tests, and made no changes.

## Evidence, environment and rulings

All local evidence is under work/full-skill-audit: task-a/b/c.txt, launch.py, *-events.jsonl, *-launch.json, runtime-proof JSON, A diffs/snapshots, A/B observations, independent-test logs, codex-c-oracle.json, recovery-results.json, recovery-marker.json, installed-hash-check.json, ninearm-inventory.json and observer briefs. No full model transcript is committed.

Focused unchanged-source regression was rerun: python -m pytest -q tests/test_portable_skill.py with a disposable basetemp: **7 passed, 3 skipped in 4.80s**. Symlink tests skipped for unavailable OS privilege. The migration's earlier 145-pass full suite is historical matching-commit evidence, not a fresh full-suite run here.

Global-config verification is **NOT VERIFIED**: launcher hash comparisons show Codex config.toml changed during the A/B/C execution intervals. Claude settings.json, Git .gitconfig and the installed skill manifest matched. Subject command/file-change evidence contains no global config write. Attribution is unresolved in a concurrently running host; no value was restored or edited by the auditor. Do not equate an absence of observed write commands with unchanged global state.

One supplemental extraction/checkpoint command was rejected by CC Safety Net because the auditor mistyped the working directory as <user> It never executed and was not retried through another path or tool. Existing artifact-based conclusions remain; independent supplemental OS trace/model extraction is left Unverified.

Rulings I made: small-work direct execution is valid, so zero subject spawns means autonomous formation NOT VERIFIED rather than impossible; root audit reviewers do not count as subject-created reviewers; Claude plain execution is diagnostic only; preserve the live helper defect and stale record rather than silently repair it; do not infer who changed global config or restore it. Costs: full team/parity/global-state claims cannot pass.

Adopted: none. Undone: none. Unadopted branch retained: feat/skill-first-hub. The Owner can review the minimal proposals above before any implementation. Security Gate remains NOT PASS.
