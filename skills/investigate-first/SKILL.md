---
name: investigate-first
description: "Use when the cause of a bug, failing test, intermittent behaviour or performance regression is not yet proven, before proposing or writing any fix. Reproduce, trace, falsify, cross-check, with evidence-ranked hypotheses."
---

# Investigate first

Gather evidence before changing product code. Do not propose or write a fix until the four steps are done. A fix without a proven cause is a guess. Separate the observed symptom from the inferred cause.

## 1. Reproduce reliably

- Get a command, test or input that fails every time. Write down the exact command and the exact failure.
- If it fails only sometimes, find what varies (data, timing, order, environment) and pin it until it fails on demand.
- If you cannot reproduce it, say so and list what you would need; do not fix what you cannot see fail.

## 2. Trace the actual failing path

- Follow the real execution from the entry point to the failure, reading the code that runs, not the code you expect to run.
- Trace inputs, state transitions, ownership boundaries and failure output. Check real values at each hop (logs, a debugger, a temporary print, a focused test), not assumed ones.
- Note where the observed behaviour first differs from the intended behaviour.

## 3. Rank hypotheses and try to falsify the leading one

- Rank hypotheses by the evidence for them and by how cheaply they can be falsified; test the cheap, likely ones first.
- State the leading hypothesis in a sentence: "X happens because Y."
- Design a check that would prove it wrong, run it, and read the result honestly. A hypothesis that survives a real attempt to break it is worth keeping.
- If the check contradicts it, drop it fully. Do not bend the evidence to keep the idea.

## 4. Cross-check every clue

- List every clue: error text, logs, stack frames, recent commits and diffs, config changes, what works and what does not.
- The cause must explain all of them. A clue left unexplained means the cause is wrong or incomplete; go back to step 2 or 3.
- Check why it worked before: what changed, and since when.
- Do not edit until one credible mechanism explains the evidence. Stop exploring when the evidence is enough to name the cause or the exact blocker.

## Then report, fix and prove

- Report the cause in one or two sentences with the evidence that proves it. Make no fix unless the task authorizes implementation.
- When fixing: fix at the cause, not at the symptom, and keep the change as small as the cause allows.
- Run the step 1 reproduction again and show it now passes, then run the surrounding tests. Add a regression check when the project has a fitting place for it.
- Use `post-mortem` to record the cause after the fix lands.

## Stop signals

- Two attempts with no new information: stop and use `stay-on-track`.
- Do not add retries, sleeps, broad try/catch or defensive checks to hide a failure you have not explained.
