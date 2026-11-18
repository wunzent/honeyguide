---
name: backend-org-structure
description: "Use when planning, scaffolding or restructuring an AdonisJS backend: the owner's target folder layout (controllers, services, repositories, migrations, OpenAPI docs, tests), its layer rules and where each part is described in the Backend SWC."
---

# Backend org structure

The owner's target layout for backend projects. Use it when designing a new backend or planning a restructure.
Existing repositories may not follow it yet: do not move files in an existing repository unless the owner asks for that restructure.

```
backend/
├── app/
│   ├── controllers/              # HTTP controllers
│   ├── services/                 # Business logic layer
│   ├── repositories/             # Data access layer
│   ├── models/                   # models (extends XxxSchema)
│   ├── validators/               # validators
│   ├── middleware/
│   │   ├── auth_middleware.ts    # JWT verify → AuthenticatedContext
│   │   └── rbac_middleware.ts    # Role check
│   └── utils/
│       ├── pii_encrypt.ts        # PII encrypt/decrypt helpers
│       └── keycloak_client.ts    # Keycloak SSO
├── config/                       # App config
├── database/
│   ├── migrations/               # Knex migrations
│   ├── seeders/
│   └── schema.ts                 # Auto-generated column declarations
├── api-docs/                     # OpenAPI spec (YAML modular)
│   ├── openapi.yaml
│   ├── paths/
│   └── components/
├── tests/
│   ├── unit/                     # Unit tests (timeout: 2s)
│   ├── functional/               # Functional/API tests (timeout: 30s)
│   └── bootstrap.ts
├── docs/                         # documentation
└── ....js                        # CLI entrypoint
```

## Layer rules

- Controllers only handle HTTP: validate input with a validator, call a service, shape the response.
- Services hold business logic and call repositories; they never read `ctx`.
- Repositories are the only layer that queries the database.
- Models extend the generated `XxxSchema` from `database/schema.ts`; do not hand-write column declarations there.
- Auth: `auth_middleware` verifies the JWT and builds `AuthenticatedContext`; `rbac_middleware` checks roles.
- PII goes through `utils/pii_encrypt.ts`; SSO through `utils/keycloak_client.ts`.
- Every endpoint has an OpenAPI path file under `api-docs/paths/`, with shared schemas in `api-docs/components/`.
- Unit tests (2s timeout) go in `tests/unit/`, API tests (30s timeout) in `tests/functional/`.

## With SWC

When the project keeps Software Component documents, load `software-component` and write the Backend SWC with
`references/backend-standard.md`; this table says which code each part describes. SWC files go where
`software-component` says (default `docs/swc/BE`, inside this layout's `docs/`).

| SWC part | Code it describes |
|---|---|
| 3. Access Control | `auth_middleware` (JWT, `AuthenticatedContext`) and the roles `rbac_middleware` checks |
| 4. Request Specification | the validator in `app/validators/` and the request schema in `api-docs/paths/` |
| 5. Response Specification | the response schemas in `api-docs/paths/` and `api-docs/components/` |
| 6. Business Rules | the service in `app/services/` |
| 7. Data and Side Effects | repositories, models and migrations; PII fields name `pii_encrypt`, SSO calls name `keycloak_client` |
| 9. API Flow Chart | participants `Controller`, `Service`, `Repository` use the real class names |
| `UT-nn-mm` / `IT-nn-mm` | `tests/unit/` (mock, 2s) / `tests/functional/` (real DB, 30s) |
| `API-ENDPOINTS.md` columns | OpenAPI: path file in `api-docs/paths/`; Test: `tests/functional/`; Dev API: controller, service and repository done |
| table or column change | migration in `database/migrations/`, regenerated `database/schema.ts`, then table-schema, data dictionary and ER |
