# Fix failed skill audit plan

| Row | Files | Work and checks |
|---|---|---|
| 1 | tools/hub.py, tests/test_hub.py, tests/test_portable_skill.py | Narrow correlated session evidence reader plus failed finalization. Regression: installed portable wrapper verifies external-root Codex evidence and records done; forged/mismatched header/outside-root evidence rejected and failed/PID cleared; resume offsets preserved; record path escapes remain rejected. Adjust old fake session fixtures to include real-shaped session_meta where necessary. No global-session scans in unit tests. |
| 2 | skills/multi-agent-hub/SKILL.md, references/brief.md | Compact risk-based workflow from design; actual skill use, records-before-spawn for high risk, autonomous fresh review/re-review, component-doc ownership and vendor-neutral native activation. No hardcoded skill list, role library or model. |
| 3 | tools/install_hub_skill.py, tests/test_portable_skill.py | Explicit owned native Claude/both destinations with Codex default/--dest preserved. Isolated HOME tests, repeat updates/refusals/rollback still pass. |
| 4 | README.md, docs/specs/2026-11-13-skill-first-hub-design.md | Implementer updates current component/install/workflow docs with minimal corrected semantics and commands, including Claude invocation. |
| 5 | root-owned work/evidence, generated native copies, verification report | Root runs tests, sync/check, skill validation, managed vendor installs, live independent Codex and Claude scenarios with evidence of Hub activation, relevant skill read/application, records-before-spawn, fresh review, SWC A/B and OS trace; independent code review and scoped re-review after fixes. Commit only verified final work, no merge/push. |

One native writer owns rows 1-4 to avoid interface conflicts. No other source writers. Root owns initial plan/spec and live evidence. Source reviewer is fresh/read-only. Existing audit history is preserved. A fixed process-hang timeout is not a retry budget; no orchestration retry count is introduced.
