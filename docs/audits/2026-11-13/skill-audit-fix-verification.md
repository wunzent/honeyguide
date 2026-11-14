<!-- Preserved 2026-11-13 from an untracked report. Redacted: user home paths -> ~, session/agent ids -> placeholders. Evidence report only; Security Gate NOT PASS. -->
# Failed Skill Audit: Fix Verification

Date: 2026-11-13. Branch: `fix/skill-first-audit`. Commit: `1840d89a2bfb7b0a4e6da35527c5dea0ee6ff258` (base `a46f198`).

**Scoped functional verification: PASS in the isolated runtimes below.** Both vendors demonstrably loaded the owned Hub Skill itself. This is not a blanket full-audit, user-global rollout, or security approval. **Security Gate: NOT PASS.**

Source: `~/.codex/worktrees/fix-skill-audit/multi-agent-hub-v2`. Primary evidence: the existing Codex/Claude full-skill-audit reports, copied without alteration into `work/fix-skill-audit/evidence/`.

## Root causes and minimal changes

1. **Session evidence / finalization.** Portable `events()` applied the project-record boundary to Codex-owned rollout metadata outside the project; verification raised before final status updates. A separate constrained reader now resolves the configured session root, checks the selected rollout filename against the child thread, validates `session_meta.payload.id`, rejects malformed object shapes, and uses canonical resume-offset keys. Verification rejection retains its specific failure diagnostic and finalizes an exited worker as failed with its PID cleared. Task-record validation remains unchanged. This is correlation within the configured session root, not cryptographic or OS-ownership attestation.
2. **Native workflow obligations.** The short skill left review and records too discretionary. It now assesses risk, explicitly requests fresh native review where warranted, and requires the checkpoint, that assignment's BRIEF and planned local agent record to exist through a tool check before every high-risk spawn/re-review. Actual returned identity/status updates the planned record afterwards; unknown observed values remain Unverified. It discovers/reads relevant runtime skills rather than a name whitelist. Implementers own affected component docs and reviewers check consistency. Tiny work remains direct.
3. **Claude activation.** The original installer targeted only Codex user skills. Added explicit `--vendor codex|claude|both`, retaining Codex default, exact `--dest`, manifest refusal, backups and rollback. README explains native invocation and existing Owner consent policies; no global policy was changed. Current user packages had already been replaced by a larger parallel build, so these were preserved instead of downgraded.

Only the scoped runtime, installer, skill/reference, generated copies, focused tests, README and design/plan changed. No orchestration framework, fixed business roles, mandatory team size/vendor/model or retry budget was added.

## Final evidence

| Capability | Result | Actual evidence |
|---|---|---|
| Codex loads this branch's Hub | PASS | Final profile explicitly read its project-native `.agents/skills/multi-agent-hub/SKILL.md`; instructions applied and payload hashes remain intact. |
| Claude loads this branch's Hub | PASS | Native `/hub-proof:multi-agent-hub` expansion records the base directory under `claude-final/scenario-a/.hub-proof-plugin/skills/multi-agent-hub` and the exact planned-record instructions. This is a local native test namespace, not generic coding or a new engine. |
| Codex native review and fresh re-review | PASS | Two distinct `spawn_agent` calls: `free_shipping_review`, `free_shipping_recovery_review`, both `fork_turns=none`; no reviewer resume. |
| Claude native review and fresh re-review | PASS | Three distinct new `Agent` calls using the generic `hub-readonly` permission shell, with no resume/fork argument; initial change, boundary fix and conservative shipping review. Duplicate log replay was removed by call ID before counting. |
| Records before each actual spawn | PASS | Timestamped file-observer snapshots show checkpoint plus that assignment's brief and planned agent file before every final-profile call. After spawn, records contain returned ids and completion results. |
| Dynamic compatible skill use | PASS for exercised Codex selection | Codex independently read and applied `surgical-patch` from the active runtime during the internal change; its checkpoint records the path/use. The Hub itself loaded in both vendors. Additional Claude skill composition is NOT VERIFIED; none is inferred from its catalog. |
| Controlled failure diagnosis and recovery | PASS, controlled probe | In disposable projects only, root changed `>=` to `>` after initial review. Existing tests failed; each subject reproduced and corrected the boundary, preserved history, and requested a new independent review. This was an injected test regression, not a model-caused production defect. |
| Code / component docs | PASS | Both updated the original three-field/no-discount contract for the new keyword, four fields and eligibility rules. Independent 50-case oracle passed per vendor on reviewed snapshots and final code. Final unittest counts: Codex 15, Claude 24, both exit 0. |
| Internal-only documentation decision | PASS | Both divmod changes preserve public behavior; component-document SHA-256 remains identical to the reviewed A snapshot. Codex self-verified equivalence; Claude conservatively reviewed the money path. |
| Trivial single-agent work | PASS | Separate final-source typo tasks corrected only README content, produced zero native spawns and no `.multi-agent-hub` directory in both vendors. |
| Actual optional helper / session resume | PASS | Real `marker-observer-1` and `marker-observer-2` both exit 0/status done/PID Unknown, same session, observed `gpt-6-luna / low`. No completed helper record remains running. |
| OS read-only trace | PASS, limited | With correct working directory and normal approval, one Python overwrite returned `PermissionError: [Errno 13] Permission denied: 'protected.txt'`. SHA-256 before/after is `0383D5E279B587F39C66F0EBE639F61CAFA03B49753C6170CFDD47D67B5EDC4F`. This proves the tested CLI mode, not every native child or a general security gate. |
| Invalid evidence / failure lifecycle | PASS in focused fixtures and source review | Installed-wrapper tests cover external-session-root success and rejected header/turn metadata with failure diagnostic, retained output and cleared PID. Relative-root resume passes; linked-root execution skips where OS privilege is unavailable. No real user session was forged. |
| Regression suite | PASS / skips explicit | Final unchanged-code gate: **155 passed, 4 skipped**, 237.16s. All four skips require unavailable symlink capability. Targeted lifecycle/resume gate: **9 passed, 1 skipped**, 13.70s. Skill validation, sync --check and diff --check pass. |
| Independent code review | PASS | First source review found three Important blockers; same native implementer fixed them. A fresh scoped reviewer and a separate fresh whole-patch reviewer returned PASS. They inspected source/artifacts, did not run the root's tests. |
| Vendor independence | PASS for tested tasks | Each child PATH resolved its own CLI and excluded the other; no cross-vendor delegation or Qwen was used. No actual account failure, expiry or quota exhaustion was induced. |
| User-global deployment | BLOCKED / intentionally not performed | Read-only installer validation refuses both current user bundles because their managed file lists differ from this six-file source package. They belong to parallel work and contain extra payload. No overwrite, removal or downgrade was attempted. |
| Global-config invariance | NOT VERIFIED | Claude settings/Git config/user skill manifests matched in final trials. Codex config.toml hash changed in some Codex process intervals; inspected subject commands show no explicit global write. Attribution remains unresolved; no restoration was attempted. |
| Desktop GUI / all plugins / independent Security Gate | NOT VERIFIED | Actual trials were native CLI sessions on Windows, not a GUI or exhaustive skill/security audit. Security Gate remains NOT PASS. |

## Isolation, provenance and permissions

Final projects: `~/Documents/Codex/full-skill-fix-proof-20261113/{codex-final,claude-final}/scenario-a`; tiny profiles and `session-proof` are siblings. No production project was modified. Source CLI versions observed: Codex 0.167.2, Claude Code 2.1.312. No dependency or third-party skill installation occurred.

A same-name user Claude skill took precedence over project copies in early diagnostics. Those results were excluded from this branch's proof. The final local plugin namespace selected the exact six-file owned package via supported `--plugin-dir`; it changes no global plugin setting. Other early attempts with wrong harness profile/resume attribution, denied delegation, or records written after spawn remain in local evidence and are not counted as final PASS. Every final owned payload still validates against its managed hashes.

Owner policy in `~/.claude/CLAUDE.md` says not to spawn unless asked. Tests supplied workflow-level native-delegation consent under this directive, without choosing duties, skills or team size. No policy was weakened. Without that consent, review correctly remains BLOCKED. Low-effort attempts exposed record-order failures; final nontrivial parents used one effort step higher on the same cheap tier. Tiny tasks returned to low effort.

The final native source reviewers cannot access some Git metadata in their lower-permission environment; root's normally approved Git commands verify the actual diff/commit. This environmental restriction was not treated as a Hub defect or fixed through global security changes. One complex OS-preparation command was rejected by active CC Safety Net as unparseable; it was simplified into ordinary commands as the validator instructed. The successful probe used normal approval, the correct directory, and no bypass flag.

## Agent / model evidence

| Assignment | Vendor / kind | Requested model / effort | Observed model / effort | Result |
|---|---|---|---|---|
| audit-gap-integrator | Codex native writer | gpt-6-luna / low | Unverified / Unverified | Done, reviewed corrections applied |
| session-and-skill-reviewer | Codex native, fresh read-only intent | gpt-6.1-sol / medium | Unverified / Unverified | FAIL initially; three Important findings retained |
| evidence-lifecycle-rereviewer | Codex native, fresh read-only intent | gpt-6.1-sol / medium | Unverified / Unverified | Scoped PASS |
| final-scope-reviewer | Codex native, fresh read-only intent | gpt-6.1-sol / medium | Unverified / Unverified | Whole-patch PASS |
| Final Codex parent | Codex CLI | gpt-6-luna / medium | gpt-6-luna / medium, turn_context | Implementation, recovery, review and SWC verified |
| Two Codex reviewers | Codex native | inherited defaults, no override | Unverified / Unverified | Fresh contexts and returned ids verified |
| Final Claude parent | Claude CLI | haiku / medium | claude-haiku-5-5 / Unverified | Implementation, recovery, review and SWC verified |
| Three Claude reviewers | Claude native | shell default, no model override | Unverified / Unverified | Distinct calls, fresh contexts and returned ids recorded |
| Two helper records | Codex CLI, same resumed session | gpt-6-luna / low | gpt-6-luna / low, correlated rollout | done/0; PID cleared |

Requested read-only duties are not proof of per-native-agent OS enforcement. Unknown values stay Unverified. Native record files retain status history, including earlier running text followed by terminal completion; they are readable Markdown, not a newly introduced parser/engine.

## Evidence and remaining decisions

Local ignored evidence is in `work/fix-skill-audit/`: baseline reports; review findings/briefs; integrator report; final-runtime-proof.json; final-independent-checks.json; final-owned-package-checks.json; timestamped record histories; launch/config comparisons; controlled-regression logs; actual helper records/session fixture; os-denial-trace.json and matching before/after marker hashes. Native ids and exact call times are in final-runtime-proof.json. Raw transcripts are local, not committed.

Rulings I made: preserve newer parallel user packages; use exact isolated native bundles and a temporary Claude namespace; do not count generic/misattributed code success as Hub activation; require planned local ids before runtime ids exist; raise cheap-tier effort after observed low-effort record-order failures; respect existing Owner consent policies; preserve failed traces and separate injected failures from real provider events. Costs: user-global rollout remains unperformed and environment invariance is not certified.

Remaining nonblocking review notes: duplicate import in the portable test module; design overview is less precise than the skill's planned-record wording. Neither extends the fix loop. Broader 9arm/plugin compatibility and actual provider account-failure conditions were not rerun in this scoped fix.

No merge, push, deploy, global policy edit or destructive cleanup. Existing worktrees/branches and newer user packages remain. Adopted: none. Undone: none. This fix branch is unmerged. Reconcile the parallel user package's source before applying a default user-level update; the installer deliberately refuses an incompatible manifest. **Security Gate NOT PASS.**
