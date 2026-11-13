<!-- Preserved 2026-11-13 from an untracked report. Redacted: user home paths -> ~, session/agent ids -> placeholders. Evidence report only; Security Gate NOT PASS. -->
# Skill-first branch reconciliation assessment

**Decision requested — approve a narrow reconciliation on top of `f4943d0`.** Retain the Claude branch's installer, permission shells, component-documentation bundle and Owner-only Git exclusion policy. Adapt the Codex session-evidence checks and pre-spawn workflow into that base. Neither tip contains all the verified improvements. Security Gate remains **NOT PASS**.

## Git evidence

Common ancestor `a46f19812dc20b2aa7f4c58710d471e9794a8767`, verified with `git merge-base feat/skill-first-hub fix/skill-first-audit`.

| Tip | History from the ancestor | Diff against ancestor |
|---|---|---|
| Claude `f4943d077dc3dbb6b0c892b682bc08c30c151932` | `ecfa865` restored portable capabilities, `c5cbf0c` removed automatic Git exclusion and repaired marker-write rollback, `f4943d0` merged the writer. Its tree is identical to `c5cbf0c`. | 16 files, +573/−55 |
| Codex `1840d89a2bfb7b0a4e6da35527c5dea0ee6ff258` | One commit directly on the ancestor | 14 files, +272/−36 |

Evidence from the committed objects using `git log --left-right`, `git diff --stat`, and direct comparisons of the two tips' helper, installer, Skill, BRIEF and tests. Generated vendor copies represent the same rules.

## Differences that affect the decision

| Area | Finding and disposition |
|---|---|
| Activation and permissions | Both support native Claude and Codex. Claude's installer includes shell sources and the software-component bundle, opt-in native Claude agents and opt-in Codex agent files, managed upgrades and per-file rollback on marker failure. Codex's six-file package adds vendor destination selection but omits those capabilities and refuses the larger managed package. Keep Claude's installer and flags. Add explicit activation-origin checking from Codex. |
| Team and review | Both keep trivial work single-agent and determine duties from the task. Both require fresh high-risk review, return findings to the implementer and require a new reviewer after fixes. Keep Claude's explicit native shell selection, fresh context and legacy-role avoidance. Add Codex's explicit treatment of blocked high-risk review and its risk cases for installation, filesystem boundaries, writes and concurrency. Permission requested and OS enforcement observed remain separate fields. |
| Records and skill use | Claude requires records for any spawn or high-risk work. Codex explicitly verifies the exact checkpoint, new assignment BRIEF and planned record before **each** high-risk spawn, including re-review, and updates the same record with the returned ID. Preserve both rules. Both select skills dynamically. Keep Claude's requirement and dependency checks, and Codex's evidence of use or reason none fit. |
| Component documentation | Both assign changed documentation to the implementer and consistency checking to the reviewer. Claude also ships the standard and specifies changes to purpose, interface, behaviour, dependencies or operations. Keep that implementation and its no-doc-change rule for internal equivalent edits. |
| Session access and finalization | Both separate private rollout reads from project record writes and can finish ordinary Codex workers. Claude confines the read to the configured session root and matches the filename suffix. Codex also binds the header ID to the child's thread, validates nested payload shapes, uses canonical offsets on resume and keeps evidence errors distinct from route mismatch while preserving output. Carry these behaviours and focused tests. Retain one JSONL decoder with separate path policies. Root confinement and header matching do not attest OS ownership. |
| Git metadata | **No automatic exclude writer in either committed tip's portable task creation.** Only the intermediate Claude commit `ecfa865` called `exclude_records_locally()`. Claude removed it in `c5cbf0c`, prints an Owner hint, and tests a digest of the entire fixture `.git` before/after. Codex retains the ancestor's Skill instruction to prefer adding the exclusion when writable, which can prompt an agent to edit it. Keep Claude's wording, hint, test and generated copies. The shared non-portable third-party skill installer has a separate exclusion path. Portable skill installation and sync are refused. |

## Evidence and limits

**New focused comparison.** Executed each commit's actual `tools/hub.py:verify()` in memory with the same temporary project-record and external session directories. Both accepted a valid rollout. Given a matching filename and a different header ID, Claude returned the supplied model/effort while Codex rejected the mismatch. Given a list for the turn payload, Claude raised `AttributeError` outside its delegation handler's caught exception types; Codex raised a handled, specific `ValueError`. The latter can prevent a completed worker being left running. This probe tested the reader. Installed-wrapper lifecycle coverage and live helper finalization come from the Codex audit.

| Prior evidence examined | What it establishes |
|---|---|
| Claude `outputs/skill-fix-verification.md`, `work/skill-fixes/CHECKPOINT.md` and `agents/reviewer-7.md` in the main checkout | Ledger trials exercised user-level activation in unrelated projects, autonomous fresh native reviews, fixes, new and updated component docs, and trivial direct work. Codex used project-level shells. The earlier Claude run missed records; later runs produced them. The live report predates the final Git-policy fix. The checkpoint and reviewer-7 establish the later static cross-vendor PASS and 156 passed / 3 skipped on the tree merged into the tip. Per-assignment timestamp ordering on that final tree is unverified. |
| Codex `outputs/skill-audit-fix-verification.md`, `work/fix-skill-audit/final-runtime-proof.json` and `final-independent-checks.json` | Branch-specific project activation for Codex and a namespaced local plugin for Claude. The latter disambiguated a shadowing user Skill. Records observed before 2 Codex and 3 Claude native spawns, including fresh review after an injected regression. Shipping oracle 50/50 per vendor, updated docs then stable docs for internal changes, trivial runs without spawns. Codex used an additional selected skill; extra Claude skill composition is unverified. Helper resumed and finalized, and one CLI read-only overwrite was denied. User-level rollout of this branch was blocked by differing package manifests. |
| Test coverage | Claude's 156/3 includes installer upgrade, collision, rollback, shell parity and Git-tree preservation. Codex's 155/4 includes wrong-header and malformed-session failures, installed external-rollout lifecycle and resume offsets. Codex reported four symlink-related skips. Counts describe different suites. No fresh full-suite or vendor run during this assessment. |

Native child OS enforcement across both vendors, final combined behaviour and the independent Security Gate remain unverified. Historical Codex config hash drift has no established cause for every interval. No globals were modified for this assessment.

## Proposed approval scope

1. Start from Claude's tip. Adapt only the evidence-reader/finalization changes and complementary regression cases in the helper and its tests. Keep the Git-tree, installer and rollback tests.
2. Amend the canonical Skill and BRIEF for exact activation evidence, selected-skill use, and a verified planned record before each high-risk spawn. Preserve the broader nontrivial-work rule and regenerate native copies. Leave installer and software-component payload intact.
3. Before adoption, run the combined focused and full suites, verify generated copies, then run each vendor independently against the exact candidate. Observe activation origin, pre-spawn files, fresh re-review, documentation ownership, trivial direct work, helper resume/finalization and unchanged project Git metadata. Obtain fresh independent review.

Assessment only. No source edits, installations, cherry-pick, merge, push or configuration changes.
