---
name: backend-api-safety
description: Checklist for any backend API change (any framework): authorization, tenant scoping, validation, secrets, idempotency, logging, error codes, contract stability. Use when adding or changing endpoints or data writes.
---

# Backend API safety checklist

Run through this before writing and again before finishing. Report only the items that apply.

1. Who may call it? Auth and role checks are present and match sibling endpoints.
2. Scope: every query is limited to the caller's tenant/company/user. No ids trusted from the request when the server can derive them.
3. Input: validated (type, length, format, allowed values) at the boundary; unknown fields are not silently stored.
4. Writes: one transaction for multi-step changes; retries or double-submits do not create duplicates (idempotency key or unique constraint).
5. Secrets: API keys, tokens, passwords, full secure URLs are never logged, returned, or stored unencrypted. Use `***` in any message.
6. Errors: stable code + safe message; right status (400 validation, 401/403 auth, 404 missing, 409 conflict, 422 business rule).
7. Contract: path, method, request and response shape match the spec/PLAN.md. A change to any of them needs approval first.
8. Lists: pagination or a hard limit; no unbounded query.
9. External calls: timeout, error mapping, no real provider calls in tests.
10. Tests: success, validation failure, permission denied, out-of-scope data, external failure.
