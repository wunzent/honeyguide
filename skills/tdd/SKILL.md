---
name: tdd
description: "Use to build or fix behaviour test-first: write a failing test, make it pass with the smallest change, then refactor with the tests green. Points to ub-mode, surgical-patch and lean-build for how to size the work."
---

# Test-driven development

Red, green, refactor, one behaviour at a time. Idea from ECC's `tdd-workflow` skill (affaan-m/ECC, MIT), in our own words.

1. Find the project's test setup (framework, command, where tests live) and use it. Add no new test framework or dependency.
2. Pick one small behaviour from the acceptance criteria. Write one test for it in the existing style.
3. Red: run the test and see it fail for the expected reason (missing behaviour, not a typo or a broken import). Show the failure. A test that never failed proves nothing.
4. Green: write the smallest change that makes it pass. Do not add behaviour the tests do not ask for.
5. Run the focused test, then the surrounding suite.
6. Refactor with the tests green: remove duplication, improve names. Re-run after each step. Stop refactoring when the code is clear; do not widen scope.
7. Repeat for the next behaviour. Stop when the acceptance criteria pass.

Bug fix: the failing test reproduces the bug first, at the narrowest layer; that is the regression proof (see `surgical-patch`). If the cause is not yet proven, use `investigate-first` before writing the fix.

Sizing and discipline: `ub-mode` for make it work, make it right, follow practice; `surgical-patch` for a small fix; `lean-build` for a new feature or slice with overbuilding risk. For strategy (unit versus integration versus end-to-end, coverage, mocks) read `discover-testing`.

Report the test command, the red result, the green result and anything left untested. Do not claim a check passed that did not run.
