# Routing

Route by work type with the table below; the named skill holds the full rules. The `discover-*` gateways point at third-party knowledge files for a technology: read only the files the task needs.

| Work type or situation | Skill |
|---|---|
| Any software task: plan, delegate, review, records (this skill) | `orchestrate` |
| Cause of a bug, failing test, intermittent failure or regression not yet proven | `investigate-first` |
| Small bug fix or behaviour change at the narrowest layer, with regression proof | `surgical-patch` |
| New feature, slice or integration with overbuilding risk | `lean-build` |
| Restructure code while preserving behaviour | `safe-refactor` |
| Writing or changing code, or the owner asks for the "reduced principles" or `/ub-mode` (make it work, make it right, follow practice) | `ub-mode` |
| Designing an API, module boundary or public interface | `api-and-interface-design` |
| Adding or changing backend endpoints or data writes | `backend-api-safety` |
| Planning, scaffolding or restructuring a backend's folder layout (AdonisJS controllers, services, repositories, migrations, OpenAPI docs, tests) | `backend-org-structure` |
| Untrusted input, auth, secrets, data storage, dependencies, privacy | `security-and-hardening` |
| Solution planning, SWC, component documentation | `software-component` |
| Proving acceptance conditions, completion checks; outsider review of a plan, PR or change | `verify-and-stop` |
| Plan a nontrivial change before coding and stop for the owner's go-ahead | `plan` |
| Work with 3 or more steps: turn the plan into a task list file (`tasks.md`) naming the skill for each task | `tasks` |
| Build or fix behaviour test-first (red, green, refactor) | `tdd` |
| Review the current diff with a fresh reviewer and the language checklists | `code-review` |
| Security review of a change (input, auth, secrets, dependencies) | `security-scan` |
| Delivery of a nontrivial task: record project lessons as instincts; show, forget or evolve them | `learn` |
| After a fix lands: the engineering record | `post-mortem` |
| Reporting up to leadership, shaping a message for a channel | `management-talk` |
| Long, looping or stalled work; context setup, degraded output, switching tasks, rules files; session or context ending (handoff document) | `stay-on-track` |
| Mechanical, low-risk, self-contained work | `cheap-delegation` |
| Researching a skill or knowledge that is not here yet (never installs by itself) | `find-skills` |
| Technology-specific frontend work (Vue, Nuxt, Pinia, Vite, Vitest, React, Next.js, accessibility) | `discover-frontend` |
| Technology-specific backend or API work (AdonisJS, NestJS, Nitro, REST, GraphQL, auth) | `discover-backend` |
| Databases: schema, migrations, queries, ORMs, Redis, MongoDB | `discover-database` |
| Caching: HTTP, CDN, Redis, invalidation | `discover-caching` |
| Cloud and infrastructure: AWS, GCP, Cloudflare, Terraform, Kubernetes | `discover-cloud` |
| CI/CD, containers, observability (Docker, Prometheus, OpenTelemetry) | `discover-devops` |
| Debugging tools: devtools, debuggers, profilers, memory, production | `discover-debugging` |
| GitHub pull requests, issues, Actions, repository settings | `discover-collaboration` |
| Test strategy and writing tests: unit, integration, end-to-end, TDD | `discover-testing` |
| Mobile apps: React Native, SwiftUI, Swift concurrency, SwiftData, iOS networking and testing | `discover-mobile` |
| Security topic knowledge: authentication, authorization, OAuth2, input validation, secrets, security headers (hardening and reviewing a change: `security-and-hardening`, `security-scan`) | `discover-security` |
| Distributed systems: consensus, CRDTs, clocks, replication, sharding, event sourcing; system-design interview preparation | `discover-distributed` |
| Web page, app UI or marketing copy that must not look generic or AI-generated: design, build or review | `discover-ui-taste` |
| Design specs and design decisions | The recommended `egm` plugin, if installed (not part of this plugin; the owner types `/egm:egm-<skill>`, the orchestrator can only suggest it); when it is absent, suggest installing it (see `docs/RECOMMENDED.md`) |
