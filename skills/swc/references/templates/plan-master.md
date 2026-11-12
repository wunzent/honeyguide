# {System} — Implementation Plan

**Version**: {X.Y}  **Date**: YYYY-MM-DD  **Owner**: {name}
Service plans: [PLAN_{SERVICE_A}.md](./PLAN_{SERVICE_A}.md) · [PLAN_{SERVICE_B}.md](./PLAN_{SERVICE_B}.md)

Path: `Plan.md` at the docs root. The cross-repo view by phase; detail lives in the service plans. Status here is
copied from the service plans, not tracked twice.

> **API contract rule**
>
> | Role | Duty |
> |---|---|
> | Backend | {publishes the contract first (e.g. OpenAPI) before frontend wiring} |
> | Frontend | {builds against the published contract; mocks until it exists} |

## Architecture Overview

```
[{client}] → [{api}] → [{broker}] → [{worker}] → [{provider}]
                 └──→ [{database}]
```

## Reference Documents

| Type | File | Status |
|---|---|---|
| Requirements | [{SRS / business docs}]({relative}) | ✅ / 📋 |
| Data dictionary | [DATA_DICT.md](./DB/Data%20Dictionary/DATA_DICT.md) | |
| Endpoints | [API-ENDPOINTS.md]({relative}) | |

## Phase {N} — Module {NN}: {Name}

**Backend work**
- [ ] {task} ([PLAN_{SERVICE}.md §{n}]({relative}))

**Frontend work**
- [ ] {task}

**Done when**: {observable acceptance}

## Phase {N+1} — Infrastructure / DevOps
## Phase {N+2} — Testing
