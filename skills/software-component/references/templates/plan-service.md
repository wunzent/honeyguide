# PLAN — {service}

**Repo**: `{repo}`
**Dev**: {name}
**Version**: {X.Y}  **Date**: YYYY-MM-DD (ISO dates only)
**Master plan**: [Plan.md]({relative}) · siblings: [PLAN_{OTHER}.md]({relative})
**References**: [{business / workflow doc}]({relative})

> **v{X.Y} change**: {what changed in this plan version}

Path: `PLAN_{SERVICE}.md` (upper-case, one spelling for every plan). Keep plan, status and as-built apart: tasks and
checkboxes here; what was built goes in the specs; release state goes in Deployments/.

## 1. Responsibility

{what this service owns; what it does not do and who does}

## 2. Tech Stack

| Part | Technology | Note |
|---|---|---|

## 3. Coding Rules

- {rules enforced on every change}

## 4. Folder Structure

```
{repo}/
└── {...}
```

## 5. Phases

### Phase {N} — {name}

**Endpoints / jobs**: {list with links to specs}
**Business rules**: {...}
**Adapters / integrations**: {...}

- [ ] {task}

## 6. Environment Variables

| Variable | Default | Description |
|---|---|---|

## 7. Status Transitions

| From | To | Trigger |
|---|---|---|

## 8. Checklist

- [ ] {item} (link to spec / test when done)

## 9. Priorities

| Priority | Item | Why |
|---|---|---|
| 🔴 | {...} | {...} |
| 🟠 | {...} | {...} |

## 10. Known Gaps / Timeline

| Item | Status | Target |
|---|---|---|

## 11. Design Decisions

| DEC | Decision | Why | Date |
|---|---|---|---|

---

### Variant: feature plan (one feature across repos)

Header: **Feature**, **Status** (Draft / Approved / Done), **Last Updated**, **Refs**. Sections: Scope, Current state,
Decisions (locked), Phases (BE-0..n, FE, QA; each done phase gets ✅ + date + test count), Impact / Risk per repo,
Open questions, Recommended order.
