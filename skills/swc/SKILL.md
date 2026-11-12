---
name: swc
description: Write or update SWC documents (solution overview, Frontend page SWC, Backend API/flow SWC, diagrams, AC/test cases, manual notes, decisions, traceability). Use for any solution planning or SWC documentation task.
---

# SWC

A template standard: it holds no project's real specs. Read only the reference section you need.

## Where documents go

- Project SWC: the folder the project card names (`projects/<name>.md`, "SWC docs"); none named: `docs/swc/FE` and
  `docs/swc/BE` in the target repo. Ask the owner before creating a new SWC location.
- Shared files for one project (solution-overview, shared, traceability) go in FE unless the project already places them elsewhere.
- Never copy a real project's specs, names or paths (including paths from other machines) into this skill or the hub;
  examples here stay placeholders. In a project's own docs, link files by relative path, never by an absolute path.

## Document set

The full set (plans, workflows, contracts, DB dictionary and ER, per-endpoint and single-file HTTP services,
worker services, web SWC and testing, releases) with paths, templates and the "update together" table:
`references/document-set.md`. Create only what the work touches.

- Work log rows: `worklog/YYYY-MM-DD.md` next to the project's SWC folders (see `references/swc-central.md` section 11).

## References

| Need | File |
|---|---|
| Routing, delivery order, planning-only rules | `references/rules.md`, `references/guide.md` |
| Frontend page/module SWC (Mermaid v8.8.0) | `references/frontend-standard.md` |
| Backend endpoint SWC (sections 1-11, flow chart) | `references/backend-standard.md` |
| Header, Evidence, IDs, AC, UT/IT, manual notes, DEC/Change Log, Work Log, checklist | `references/swc-central.md` |
| New module skeleton | `references/templates/solution-overview.md`, `references/templates/traceability.md` |
| Which document, where, what changes together | `references/document-set.md` |
| Backend trackers | `references/templates/api-endpoints.md`, `references/templates/user-matrix.md` |
| Frontend tracking and test results | `references/templates/swc-overview.md`, `references/templates/testing-overview.md`, `references/templates/page-testing.md` |
| Component / feature spec (no URL) | `references/frontend-standard.md` section 8 |
| Worker, small HTTP service, message contract | `references/templates/service-spec.md`, `service-flowchart.md`, `program-spec.md`, `message-contract.md` |
| Database | `references/templates/data-dictionary.md`, `er-diagram.md`, `table-schema.md` |
| Release and deploy | `references/templates/release/*.md` |
| Plans and business process | `references/templates/plan-master.md`, `plan-service.md`, `workflow.md` |
| Optional: business FR/UC, UI design system, agent instructions | `references/templates/business-module.md`, `ui-design-system.md`, `agent-instructions.md` |
| Work log row | `references/templates/worklog.md` |

Long Thai lines: find headings first (`rg -n --max-columns 160 "^#" <file>`), then read only those ranges.

## Routing

- page / component / composable / UI flow → frontend standard
- endpoint / auth / validation / data / side effect / external service → backend standard
- full-stack or cross-system → both, linked by the same REQ/AC and API contract

## Workflow (meaningful features)

1. Capture the request as REQ and AC.
2. Discover the current system from source, tests and contracts; examples in the standards are placeholders.
3. Write and review the shared solution document and API contract.
4. Split into FE and BE handoff; write each SWC with its standard.
5. Write AC from REQ, then UT/IT test cases from AC in each page/endpoint spec.
6. Write Manual Notes (FE) or Usage Notes (BE) when user-facing or called by others; else `not needed` with a reason.
7. Update Change Log, add a DEC when direction changes, update `traceability.md`.
8. Map implementation, tests and evidence back to REQ/AC; keep both SWCs and diagrams in sync.
9. Add a Work Log row with real start/end time (or `?` + `Source = Estimate`).

Planning-only work may stop after the solution/spec/diagram stage if assumptions, open questions and unverified areas are explicit.

## Hard rules

- Headers: every document has `Last Updated` (or Version + Date); SWC specs add `Status`, `Evidence`
  (Current / Proposed / POC / Verified), `REQ Refs`, `Owner` when the project tracks REQ/AC (see `references/document-set.md`).
- Never claim `Verified` without a real run; keep mock tests separate from real DB/provider tests.
- Manuals only from Current or Verified sections, never Proposed/POC.
- Direction change: new DEC, mark REQs Changed/Dropped, follow traceability to AC/tests/manuals, keep old DEC as Superseded. Never delete history.
- Evidence conflicts → record the conflict or an Open Question; do not invent behavior.
- Owner decisions in the current task win over older SWC text; note the difference in the doc.
- Diagram syntax follows the destination renderer (FE: Mermaid v8.8.0).
