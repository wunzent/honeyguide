# Skill-first migration plan

| Row | Files | Task / acceptance |
|---|---|---|
| 1 | tools/hub.py, tools/hub_skills.py | Add narrow optional records/catalog/destination seams; legacy defaults and launch fix preserved. No unrelated historical fixes. |
| 2 | skills/multi-agent-hub/SKILL.md, references/brief.md, scripts/run.py | Native-first portable instructions and optional reused helper wrapper; no fixed roles/vendors/models/team counts, no registration or source path dependency. |
| 3 | tools/install_hub_skill.py | Deterministic self-contained owned-skill install/update; native user path, optional --dest; source hashes/provenance; preserve old managed version; refuse unsafe/unmanaged/modified destinations; no dependencies/globals. |
| 4 | tests/test_portable_skill.py | Focused meaningful compatibility, portable project-boundary and install/update/no-progress tests using stdlib/local fixtures. No mocked E2E claims. |
| 5 | README.md (or docs skill-first guide) | Minimal install/update and $multi-agent-hub usage; legacy repository mode optional, old surfaces retained. |
| 6 | work/skill-first-hub/ evidence + docs migration report | Install own skill, fresh actual invocation in separate temporary project with Claude unavailable; native-agent proof when exposed, real work/checks/records; independent review and focused/full tests. |

Conflict ruling: rows 1-4 share root/catalog interfaces; one implementer owns them sequentially. Root orchestrator owns design/plan and later actual E2E harness/report. No concurrent source writers. No new dependency, global CLI/Git configuration, merge, push or cleanup.
