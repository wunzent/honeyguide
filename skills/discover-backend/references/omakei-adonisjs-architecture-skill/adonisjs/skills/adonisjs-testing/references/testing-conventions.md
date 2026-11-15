# Testing Conventions

Guidelines for organizing and structuring tests in AdonisJS projects with Japa.

## File Naming

- Test files end with `.spec.ts`
- Mirror the source structure inside the suite folder
- Group by resource, not by type of test

```
app/
├── models/user.ts
├── services/order_service.ts
└── controllers/posts_controller.ts

tests/
├── unit/
│   ├── services/
│   │   └── order_service.spec.ts
│   └── values/
│       └── money.spec.ts
└── functional/
    ├── posts/
    │   ├── index.spec.ts     ← GET /posts
    │   ├── store.spec.ts     ← POST /posts
    │   ├── show.spec.ts      ← GET /posts/:id
    │   ├── update.spec.ts    ← PUT /posts/:id
    │   └── destroy.spec.ts   ← DELETE /posts/:id
    └── auth/
        ├── login.spec.ts
        └── register.spec.ts
```

## RESTful Test Ordering

For functional tests of a resource, order by HTTP method:

1. `index.spec.ts`   — GET collection
2. `store.spec.ts`   — POST create
3. `show.spec.ts`    — GET single
4. `update.spec.ts`  — PUT/PATCH update
5. `destroy.spec.ts` — DELETE remove

## Group Naming Convention

Use `Resource | Action` format:

```typescript
test.group('Posts | index', () => { /* ... */ })
test.group('Posts | store', () => { /* ... */ })
test.group('Posts | show', () => { /* ... */ })
test.group('Posts | update', () => { /* ... */ })
test.group('Posts | destroy', () => { /* ... */ })
```

## Test Naming

Write test names as behavior descriptions — what it does, not how:

```typescript
// ✅ Good — describes behavior
test('returns paginated list of published posts', async () => {})
test('returns 422 when title is missing', async () => {})
test('returns 403 when user is not the author', async () => {})

// ❌ Bad — describes implementation
test('calls PostService.findAll', async () => {})
test('uses pagination middleware', async () => {})
```

## Test Structure Template

Every test follows Arrange-Act-Assert:

```typescript
test('description of expected behavior', async ({ assert, client }) => {
  // ── Arrange ─────────────────────────────────
  // Set up data, create users/models, prepare input

  // ── Act ─────────────────────────────────────
  // Perform the single operation under test

  // ── Assert ──────────────────────────────────
  // Verify the outcome
})
```

## What to Test per Endpoint

For each endpoint, cover at minimum:

1. **Happy path** — valid input produces correct response
2. **Validation errors** — missing/invalid fields return 422
3. **Authentication** — unauthenticated requests return 401
4. **Authorization** — unauthorized users return 403
5. **Not found** — missing resource returns 404
6. **Edge cases** — empty lists, boundary values, etc.

## Tags

Use tags for selective test execution:

```typescript
test('sends notification email', async () => {})
  .tags(['@slow', '@mail'])

test('computes tax correctly', async () => {})
  .tags(['@fast', '@unit'])
```

Run with: `node ace test --tags="@fast"` or exclude with `--ignore-tags="@slow"`.
