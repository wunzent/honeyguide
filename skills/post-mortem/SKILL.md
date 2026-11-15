---
name: post-mortem
description: "Write the canonical engineering record of a fixed bug after the fix lands: symptom, root cause, mechanism, fix, validation, why it slipped through, follow-ups. For an engineer audience."
---

# Post-mortem

Write this after the fix is merged or applied and validated, not before. It is the lasting record for engineers who meet a similar failure later. Blameless and factual.

## Before writing

- Collect the evidence: the failing report, logs, the fix diff or commit, and the validation output. Do not write from memory.
- Mark anything you did not verify as unverified.

## Sections, in this order

1. **Summary**: two sentences. What broke, and what fixed it.
2. **Symptom**: what was observed, where, since when, and who or what was affected. Include the exact error text or wrong output.
3. **Root cause**: the single underlying defect, stated precisely (file, function, condition, assumption).
4. **Mechanism**: step by step, how the root cause produced the symptom. A reader should be able to predict the symptom from this section alone.
5. **Fix**: what changed and why that addresses the cause rather than the symptom. Link the commit or change.
6. **Validation**: how the fix was proven: the reproduction before and after, tests run and their results, anything not run.
7. **Why it slipped through**: the missing test, review gap, wrong assumption or unclear contract that let it ship. Name the gap, not a person.
8. **Follow-ups**: concrete actions with an owner or a suggested owner (regression test, guard, monitoring, doc change). Mark which are done and which are open.

## Style

- Precise and short: engineers will skim for the section they need. Use code names, paths and commands.
- Facts and evidence over opinion. No blame, no speculation presented as fact.
- Save it where the project keeps such records (for example `docs/post-mortems/`); if there is no place, ask or propose one.
- For a leadership summary of the same event, use `management-talk`.
