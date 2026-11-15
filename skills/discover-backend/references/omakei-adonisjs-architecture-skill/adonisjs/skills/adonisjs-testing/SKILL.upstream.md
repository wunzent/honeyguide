---
name: adonisjs-testing
description: Comprehensive testing patterns with Japa for AdonisJS. Use when working with tests, testing patterns, or when user mentions testing, tests, Japa, assertions, mocking, factories, unit tests, functional tests, API tests, browser tests, test suites, expect, assert, database testing, HTTP testing in an AdonisJS project. Also trigger when user asks how to test controllers, services, actions, models, validators, middleware, or any AdonisJS feature.
---

# AdonisJS Testing with Japa

Testing patterns with Japa: Arrange-Act-Assert, assertion APIs, API client, database testing, mocking, factories, and browser testing.

**Reference implementations:**
- [Testing conventions →](references/testing-conventions.md)
- [API test example →](references/api-test-example.ts)
- [Unit test example →](references/unit-test-example.ts)
- [Database test helpers →](references/database-helpers.ts)

## Philosophy

Testing should be:
- **Isolated** — Test one thing at a time
- **Reliable** — Consistent results, no flaky tests
- **Maintainable** — Easy to update when code changes
- **Fast** — Quick feedback loop
- **Realistic** — Use factories and real HTTP calls, not hardcoded values

## Test Suites

AdonisJS organizes tests into suites. A typical project has:

| Suite | Purpose | Server booted? | Directory |
|---|---|---|---|
| `unit` | Test functions/classes in isolation | No | `tests/unit/` |
| `functional` | Test HTTP endpoints end-to-end | Yes | `tests/functional/` |
| `browser` | Test in a real browser (Playwright) | Yes | `tests/browser/` |

```
tests/
├── bootstrap.ts          # Japa plugins, lifecycle hooks
├── unit/
│   ├── services/
│   │   └── order_service.spec.ts
│   └── values/
│       └── money.spec.ts
└── functional/
    ├── posts/
    │   ├── store.spec.ts
    │   ├── index.spec.ts
    │   └── update.spec.ts
    └── auth/
        └── login.spec.ts
```

Create test files with:

```bash
node ace make:test users/store --suite=functional
node ace make:test services/order_service --suite=unit
```

Run tests with:

```bash
node ace test                    # all suites
node ace test --suite=unit       # unit only
node ace test --suite=functional # functional only
node ace test --files="posts"    # filter by filename
node ace test --tags="@slow"     # filter by tag
```

---

## The Arrange-Act-Assert Pattern

Every test follows **Arrange → Act → Assert**:

```typescript
import { test } from '@japa/runner'
import User from '#models/user'
import OrderService from '#services/order_service'

test('creates an order for a user', async ({ assert }) => {
  // Arrange — set up the world
  const user = await User.create({
    email: 'john@example.com',
    password: 'secret123',
  })

  // Act — perform the single operation
  const order = await OrderService.create(user, {
    items: [{ productId: 1, quantity: 2 }],
  })

  // Assert — verify outcomes
  assert.instanceOf(order, Order)
  assert.equal(order.userId, user.id)
  assert.lengthOf(order.items, 1)
})
```

---

## Assertion APIs

Japa offers two assertion styles. Use whichever fits your preference — **do not mix them within a single project**.

### Style 1: `assert` (Chai-style)

Available via `{ assert }` from test context. Reads like sentences.

```typescript
test('example', async ({ assert }) => {
  // Equality
  assert.equal(actual, expected)           // == (loose)
  assert.strictEqual(actual, expected)     // === (strict)
  assert.deepEqual(obj1, obj2)            // deep comparison
  assert.notDeepEqual(obj1, obj2)

  // Truthiness
  assert.isTrue(value)
  assert.isFalse(value)
  assert.isNull(value)
  assert.isNotNull(value)
  assert.exists(value)                     // not null/undefined
  assert.notExists(value)

  // Type checking
  assert.typeOf(value, 'string')
  assert.instanceOf(value, MyClass)

  // Collections
  assert.lengthOf(array, 3)
  assert.empty(array)                      // [] or ''
  assert.isNotEmpty(array)
  assert.include([1, 2, 3], 2)            // array contains
  assert.include('hello world', 'hello')   // string contains
  assert.include({ a: 1, b: 2 }, { a: 1 })// object subset
  assert.containsSubset(obj, subset)       // deep subset match (great for API responses)

  // Numbers
  assert.isAbove(5, 3)
  assert.isBelow(3, 5)
  assert.isAtLeast(5, 5)
  assert.isAtMost(5, 5)
  assert.closeTo(0.1 + 0.2, 0.3, 0.001)

  // Objects
  assert.properties(obj, ['id', 'name'])   // has all keys
  assert.notAnyProperties(obj, ['secret']) // has none of the keys
  assert.property(obj, 'name')             // has specific key
  assert.propertyVal(obj, 'name', 'John')  // key === value

  // Exceptions
  assert.throws(() => dangerousCall(), Error)
  assert.throws(() => dangerousCall(), 'specific message')
  await assert.rejects(asyncFn, CustomError)
  await assert.rejects(asyncFn, 'error message')

  // One of (list membership)
  assert.oneOf('foo', ['foo', 'bar', 'baz'])
})
```

### Style 2: `expect` (Jest-style)

Available via `{ expect }` from test context. Chain matchers fluently.

```typescript
test('example', async ({ expect }) => {
  // Equality
  expect(value).toBe(expected)             // === strict
  expect(obj).toEqual(expected)            // deep equality
  expect(obj).toStrictEqual(expected)      // deep + type equality

  // Truthiness
  expect(value).toBeTruthy()
  expect(value).toBeFalsy()
  expect(value).toBeNull()
  expect(value).toBeDefined()
  expect(value).toBeUndefined()

  // Numbers
  expect(value).toBeGreaterThan(3)
  expect(value).toBeGreaterThanOrEqual(3)
  expect(value).toBeLessThan(5)
  expect(value).toBeCloseTo(0.3, 5)

  // Strings
  expect(str).toMatch(/regex/)
  expect(str).toContain('substring')

  // Arrays / iterables
  expect(array).toHaveLength(3)
  expect(array).toContain(item)
  expect(array).toContainEqual({ id: 1 })  // deep match

  // Objects
  expect(obj).toHaveProperty('name')
  expect(obj).toHaveProperty('name', 'John')
  expect(obj).toMatchObject({ name: 'John' }) // subset match

  // Exceptions
  expect(() => dangerousCall()).toThrow()
  expect(() => dangerousCall()).toThrow(Error)
  expect(() => dangerousCall()).toThrow('message')
  await expect(asyncFn()).rejects.toThrow(CustomError)

  // Negation
  expect(value).not.toBe(other)
  expect(array).not.toContain(item)

  // Snapshots
  expect(value).toMatchSnapshot()
})
```

---

## Functional Tests (API / HTTP)

Functional tests make real HTTP requests against your running AdonisJS server using Japa's API client.

### Basic API Test

```typescript
import { test } from '@japa/runner'
import User from '#models/user'
import testUtils from '@adonisjs/core/services/test_utils'

test.group('Posts store', (group) => {
  group.each.setup(() => testUtils.db().withGlobalTransaction())

  test('can create a post', async ({ client }) => {
    // Arrange
    const user = await User.create({
      email: 'john@example.com',
      password: 'secret',
    })

    // Act
    const response = await client
      .post('/api/posts')
      .loginAs(user)
      .json({
        title: 'Hello World',
        body: 'My first post',
      })

    // Assert
    response.assertStatus(201)
    response.assertBodyContains({
      data: { title: 'Hello World' },
    })
  })

  test('validates required fields', async ({ client }) => {
    const user = await User.create({
      email: 'john@example.com',
      password: 'secret',
    })

    const response = await client
      .post('/api/posts')
      .loginAs(user)
      .json({})

    response.assertStatus(422)
    response.assertBodyContains({
      errors: [{ rule: 'required', field: 'title' }],
    })
  })
})
```

### Using Route Names (type-safe)

```typescript
const response = await client.visit('posts.store')  // uses route name lookup
const response = await client.visit('posts.show', { params: { id: 1 } })
```

### Request Helpers

```typescript
// Authentication
await client.post('/api/posts').loginAs(user)
await client.get('/api/posts').basicAuth('email', 'password')

// Headers
await client.get('/api/posts').header('X-Custom', 'value')
await client.get('/api/posts').accept('application/json')

// Query string
await client.get('/api/posts').qs({ page: 1, limit: 10 })

// Form data
await client.post('/api/upload').field('name', 'avatar').file('photo', filePath)

// CSRF (for web/session apps)
await client.post('/posts').withCsrfToken().form({ title: 'Hello' })

// Session data
await client.get('/dashboard').withSession({ cartId: '123' })
await client.get('/dashboard').withFlashMessages({ success: 'Done!' })
```

### Response Assertions

```typescript
response.assertStatus(200)
response.assertStatus(201)
response.assertStatus(422)
response.assertStatus(302)

response.assertBody(exactObject)
response.assertBodyContains(subset)       // partial match — very useful
response.assertBodyNotContains(subset)

response.assertHeader('content-type', 'application/json')
response.assertRedirectsTo('/login')

// Session / flash assertions (web apps)
response.assertSession('key', 'value')
response.assertSessionMissing('key')
response.assertFlashMessage('success', 'Post created')

// Read response data for further assertions
const body = response.body()
const sessions = response.session()
const flash = response.flashMessages()
```

---

## Unit Tests

Unit tests run without booting the HTTP server. Test services, actions, value objects, and helpers in isolation.

```typescript
import { test } from '@japa/runner'
import { Money } from '#values/money'

test.group('Money value object', () => {
  test('creates from dollars', ({ assert }) => {
    const money = Money.fromDollars(29.99)

    assert.equal(money.amount, 2999)
    assert.equal(money.currency, 'USD')
  })

  test('adds two money values', ({ assert }) => {
    const a = Money.fromDollars(10)
    const b = Money.fromDollars(5.50)
    const total = a.add(b)

    assert.equal(total.amount, 1550)
    assert.equal(total.formatted(), '15.50')
  })

  test('throws on currency mismatch', ({ assert }) => {
    const usd = Money.fromDollars(10)
    const eur = Money.fromCents(500, 'EUR')

    assert.throws(
      () => usd.add(eur),
      'Currency mismatch'
    )
  })

  test('throws on negative amount', ({ assert }) => {
    assert.throws(
      () => Money.fromCents(-100),
      'Amount cannot be negative'
    )
  })
})
```

### Testing Services / Actions

```typescript
import { test } from '@japa/runner'
import User from '#models/user'
import OrderService from '#services/order_service'
import testUtils from '@adonisjs/core/services/test_utils'

test.group('OrderService', (group) => {
  group.each.setup(() => testUtils.db().withGlobalTransaction())

  test('creates order with correct total', async ({ assert }) => {
    const user = await User.create({ email: 'test@test.com', password: 'secret' })

    const order = await OrderService.create(user, {
      items: [
        { productId: 1, quantity: 2, priceInCents: 1000 },
        { productId: 2, quantity: 1, priceInCents: 500 },
      ],
    })

    assert.equal(order.totalInCents, 2500)
    assert.lengthOf(await order.related('items').query(), 3)
  })
})
```

---

## Database Testing

### Clean State Between Tests

```typescript
import testUtils from '@adonisjs/core/services/test_utils'

test.group('My feature', (group) => {
  // ✅ Recommended — wrap each test in a transaction and roll back (fast, no I/O)
  group.each.setup(() => testUtils.db().withGlobalTransaction())

  // Use truncate() only when your test contains concurrent queries or explicit transactions
  // group.each.setup(() => testUtils.db().truncate())
})
```

`withGlobalTransaction()` wraps each test in a transaction and rolls back after — this is the **recommended default**. It is faster than truncation and leaves no data behind. Avoid it only when the test itself uses explicit transactions or concurrent queries (both would conflict with the outer transaction).

`truncate()` truncates all tables after each test — use it when `withGlobalTransaction()` causes issues (e.g. nested transactions, `FOR UPDATE` locks).

### Database Assertions

```typescript
import User from '#models/user'

test('creates a user in the database', async ({ assert, client }) => {
  await client.post('/api/users').json({ email: 'john@example.com', password: 'secret' })

  // Query the database directly to verify
  const user = await User.findBy('email', 'john@example.com')
  assert.isNotNull(user)
  assert.equal(user!.email, 'john@example.com')

  // Or count rows
  const count = await User.query().count('* as total')
  assert.equal(count[0].$extras.total, 1)
})
```

---

## Mocking

### Only Mock What You Own

Never mock third-party libraries directly. Instead, create service abstractions and swap them in tests.

### Container-based Mocking

AdonisJS IoC container makes mocking easy — bind a fake implementation:

```typescript
import { test } from '@japa/runner'
import app from '@adonisjs/core/services/app'
import PaymentService from '#services/payment_service'

test.group('Order processing', (group) => {
  test('processes payment through service', async ({ assert, client }) => {
    // Swap PaymentService with a fake
    app.container.swap(PaymentService, () => {
      return {
        charge: async (_amount: number) => ({
          id: 'fake_charge_123',
          status: 'succeeded',
        }),
      }
    })

    const response = await client
      .post('/api/orders/1/pay')
      .loginAs(user)
      .json({ amount: 5000 })

    response.assertStatus(200)
    response.assertBodyContains({ paymentStatus: 'succeeded' })
  })

  // Restore after each test
  group.each.teardown(() => {
    app.container.restore(PaymentService)
  })
})
```

### Faking Mail / Events / Queues

AdonisJS provides first-class fakes for common services:

```typescript
import mail from '@adonisjs/mail/services/main'
import emitter from '@adonisjs/core/services/emitter'

test.group('User registration', () => {
  test('sends welcome email', async ({ assert, client, cleanup }) => {
    const { mails } = mail.fake()
    cleanup(() => mail.restore())

    await client.post('/api/register').json({
      email: 'john@example.com',
      password: 'secret123',
    })

    mails.assertSent('WelcomeEmail', (message) => {
      return message.to[0].address === 'john@example.com'
    })
  })

  test('emits user:registered event', async ({ assert, cleanup }) => {
    const events = emitter.fake()
    cleanup(() => emitter.restore())

    await client.post('/api/register').json({
      email: 'john@example.com',
      password: 'secret123',
    })

    events.assertEmitted('user:registered')
  })
})
```

---

## Lifecycle Hooks

```typescript
test.group('My group', (group) => {
  // Runs once before all tests in the group
  group.setup(async () => { /* seed database */ })

  // Runs once after all tests in the group
  group.teardown(async () => { /* cleanup */ })

  // Runs before each test
  group.each.setup(async () => { /* reset state */ })

  // Runs after each test
  group.each.teardown(async () => { /* cleanup per test */ })
})
```

---

## Grouping & Organizing Tests

```typescript
import { test } from '@japa/runner'

test.group('Posts | store', () => {
  test('creates a post with valid data', async ({ client }) => { /* ... */ })
  test('returns 422 for missing title', async ({ client }) => { /* ... */ })
  test('returns 401 when not authenticated', async ({ client }) => { /* ... */ })
})

test.group('Posts | update', () => {
  test('updates a post', async ({ client }) => { /* ... */ })
  test('returns 403 when not the author', async ({ client }) => { /* ... */ })
})
```

### Tags

```typescript
test('slow integration test', async () => { /* ... */ })
  .tags(['@slow', '@integration'])

// Run only tagged tests:  node ace test --tags="@slow"
// Exclude tagged tests:   node ace test --ignore-tags="@slow"
```

### Skipping & Pinning

```typescript
test.skip('not implemented yet', async () => { /* ... */ })
test.pin('only run this one for debugging', async () => { /* ... */ })
```

---

## Datasets (Parameterized Tests)

Run the same test with multiple inputs:

```typescript
test('validates email format')
  .with([
    { email: 'not-an-email', valid: false },
    { email: 'user@example.com', valid: true },
    { email: '@missing.com', valid: false },
    { email: 'user@.com', valid: false },
  ])
  .run(async ({ assert }, { email, valid }) => {
    const result = isValidEmail(email)
    assert.equal(result, valid)
  })
```

---

## Testing Exceptions

```typescript
// Synchronous exceptions
test('throws on invalid input', ({ assert }) => {
  assert.throws(
    () => OrderService.validate(null),
    'Input cannot be null'
  )
})

// Async exceptions
test('rejects unauthorized access', async ({ assert }) => {
  await assert.rejects(
    () => OrderService.getSecret(guestUser),
    'Unauthorized'
  )
})

// HTTP-level error responses
test('returns 404 for missing resource', async ({ client }) => {
  const response = await client.get('/api/posts/99999')
  response.assertStatus(404)
})

// With expect style
test('throws specific error type', ({ expect }) => {
  expect(() => Money.fromCents(-1)).toThrow('Amount cannot be negative')
})
```

---

## Snapshot Testing

Capture output once, then assert it doesn't change:

```typescript
test('serializes user correctly', async ({ assert }) => {
  const user = await User.create({ email: 'test@test.com', password: 'secret' })
  assert.snapshot(user.serialize()).match()
})
```

---

## Tips & Best Practices

**Do:**
- One assertion concept per test (it's okay to use multiple `assert` calls to verify one outcome)
- Use `group.each.setup(() => testUtils.db().withGlobalTransaction())` for database cleanup (fall back to `truncate()` only when the test uses explicit transactions or concurrent queries)
- Use `client.visit('route.name')` for type-safe route references
- Use `.loginAs(user)` instead of manually setting auth headers
- Use `cleanup()` to restore fakes within the test itself
- Name test files with `.spec.ts` suffix

**Don't:**
- Mix `assert` and `expect` styles in the same project
- Mock third-party SDKs directly — wrap them in a service
- Test implementation details — test behavior and outcomes
- Forget to clean up database state between tests
- Use `group.setup` for per-test cleanup (use `group.each.setup` instead)

---

## .env.test

Create a `.env.test` file for test-specific configuration:

```env
NODE_ENV=test
SESSION_DRIVER=memory
DB_CONNECTION=sqlite
DB_DATABASE=:memory:
DRIVE_DISK=fake
MAIL_MAILER=fake
```

---

## Summary

| What to test | Suite | Key tools |
|---|---|---|
| Value objects, helpers, utils | `unit` | `assert` / `expect` |
| Services, actions with DB | `unit` | `assert`, `testUtils.db()` |
| HTTP endpoints (JSON APIs) | `functional` | `client`, `response.assertStatus()`, `response.assertBodyContains()` |
| Auth flows | `functional` | `client.loginAs()`, `response.assertRedirectsTo()` |
| Validation rules | `functional` | `response.assertStatus(422)`, `response.assertBodyContains({ errors })` |
| Mail / events / queues | `functional` | `mail.fake()`, `emitter.fake()` |
| Full browser interactions | `browser` | Playwright via `@japa/browser-client` |
