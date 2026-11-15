---
name: debug-mantra
description: "Four-step debugging discipline to apply before proposing any fix for a bug, failing test or unexpected behaviour: reproduce, trace, falsify, cross-check. Use whenever the cause is not yet proven."
---

# Debug mantra

Do not propose or write a fix until all four steps are done. A fix without a proven cause is a guess.

## 1. Reproduce reliably

- Get a command, test or input that fails every time. Write down the exact command and the exact failure.
- If it fails only sometimes, find what varies (data, timing, order, environment) and pin it until it fails on demand.
- If you cannot reproduce it, say so and list what you would need; do not fix what you cannot see fail.

## 2. Trace the actual failing path

- Follow the real execution from the entry point to the failure, reading the code that runs, not the code you expect to run.
- Check real values at each hop (logs, a debugger, a temporary print, a focused test), not assumed ones.
- Note where the observed behaviour first differs from the intended behaviour.

## 3. Try to falsify the leading hypothesis

- State one hypothesis in a sentence: "X happens because Y."
- Design a check that would prove it wrong, run it, and read the result honestly. A hypothesis that survives a real attempt to break it is worth keeping.
- If the check contradicts it, drop it fully. Do not bend the evidence to keep the idea.

## 4. Cross-check every clue

- List every clue: error text, logs, stack frames, recent commits and diffs, config changes, what works and what does not.
- The cause must explain all of them. A clue left unexplained means the cause is wrong or incomplete; go back to step 2 or 3.
- Check why it worked before: what changed, and since when.

## Then fix and prove

- Fix at the cause, not at the symptom. Keep the change as small as the cause allows.
- Run the step 1 reproduction again and show it now passes, then run the surrounding tests.
- Add a regression check when the project has a fitting place for it.
- Report the cause in one or two sentences with the evidence that proves it. Use `post-mortem` to record it after the fix lands.

## Stop signals

- Two attempts with no new information: stop and use `stay-on-track`.
- Do not add retries, sleeps, broad try/catch or defensive checks to hide a failure you have not explained.
