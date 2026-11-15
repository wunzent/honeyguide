---
name: scrutinize
description: Outsider review of a plan, pull request or change. Questions the intent and simpler alternatives first, then traces the real code path to check the change does what it claims. Returns concise findings with evidence and a suggested fix.
---

# Scrutinize

Review as a capable outsider who did not write the change and owes it no loyalty. Be specific, brief and fair.

## 1. Question the intent

- State in one sentence what the change is meant to achieve. If you cannot, that is the first finding.
- Ask whether a simpler approach reaches the same goal: less code, an existing function, a config change, no change at all.
- Ask what is out of scope but touched anyway, and what the change deliberately leaves broken.

## 2. Trace the real path

- Do not review the diff alone. Open the code around it and follow the actual path from entry point to effect, including callers, callees, error paths and data shapes.
- Verify each claim in the description or commit message against the code. "Handles X" must be visible in a path that runs.
- Check what the diff does not show: unchanged callers that now break, tests that still pass for the wrong reason, migrations, config, docs.
- Run the tests or a small reproduction when you can; say plainly when you could not.

## 3. Look for the usual failures

- Wrong behaviour on empty, large, concurrent or malformed input.
- Security and data boundaries (auth, injection, secrets, deletion).
- Missing or weak tests for the new behaviour.
- Duplication, new dependencies or abstractions that the goal does not need.

## 4. Report

For each finding give: where (file and line), what is wrong, the evidence (what you read or ran), the severity (blocker, important, minor), and a suggested fix.

- Order by severity. Blockers first.
- Write findings as statements, not questions or hints.
- Keep style opinions out unless they break a project rule.
- Say what you verified and found sound, in one line, so the author knows what was checked.
- If there are no real findings, say so; do not invent some.

Do not edit the code under review unless asked; send findings to the author.
