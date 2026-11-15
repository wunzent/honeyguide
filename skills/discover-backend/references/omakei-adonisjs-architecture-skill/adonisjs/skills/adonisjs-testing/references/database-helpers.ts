// tests/helpers/database.ts
//
// Common patterns for database testing in AdonisJS with Japa.
// This file documents patterns — copy the ones you need into your tests.

import { test } from '@japa/runner'
import testUtils from '@adonisjs/core/services/test_utils'
import app from '@adonisjs/core/services/app'
import User from '#models/user'
import Post from '#models/post'

// ── Pattern 1: Truncate tables (recommended) ─────────────────
//
// Runs migrations, then truncates all tables after each test.
// Safest option — each test starts with a completely clean database.

test.group('With truncation', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('example', async ({ assert }) => {
    const user = await User.create({ email: 'a@b.com', password: 'secret' })
    assert.exists(user.id)
  })
})

// ── Pattern 2: Global transaction (faster) ───────────────────
//
// Wraps each test in a DB transaction and rolls back after.
// Faster than truncation but can cause issues with:
// - Tests that explicitly use transactions
// - Tests that run concurrent queries
// - Tests that rely on auto-increment IDs resetting

test.group('With global transaction', (group) => {
  group.each.setup(() => testUtils.db().withGlobalTransaction())

  test('example', async ({ assert }) => {
    const user = await User.create({ email: 'a@b.com', password: 'secret' })
    assert.exists(user.id)
    // User is automatically rolled back after this test
  })
})

// ── Pattern 3: Seed data once, truncate per test ─────────────
//
// Use group.setup() (runs once) for data shared across all tests,
// and group.each.setup() for per-test cleanup of mutable data.

test.group('With seeded reference data', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  // Seed lookup/reference data once before all tests
  group.setup(async () => {
    // Ensure categories exist (these are read-only in tests)
    // await Category.createMany([...])
  })

  test('example using reference data', async ({ assert }) => {
    // Reference data is available here
  })
})

// ── Pattern 4: Factory helper functions ──────────────────────
//
// Create reusable helper functions for common test data setups.

async function createUserWithPosts(count = 3) {
  const user = await User.create({
    email: `user-${Date.now()}@test.com`,
    password: 'secret',
  })

  const posts = []
  for (let i = 0; i < count; i++) {
    posts.push(
      await Post.create({
        userId: user.id,
        title: `Post ${i + 1}`,
        body: `Body of post ${i + 1}`,
      })
    )
  }

  return { user, posts }
}

test.group('Using factory helpers', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('user has posts', async ({ assert }) => {
    const { user, posts } = await createUserWithPosts(5)

    assert.equal(user.email.includes('@test.com'), true)
    assert.lengthOf(posts, 5)
  })
})

// ── Pattern 5: Container swap for services ───────────────────
//
// Replace real services with fakes during tests.

test.group('With service fakes', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  group.each.teardown(() => {
    // Restore any swapped bindings
    app.container.restoreAll()
  })

  test('uses fake payment service', async ({ assert, client }) => {
    // Import your service
    const PaymentService = (await import('#services/payment_service')).default

    // Swap it with a fake
    app.container.swap(PaymentService, () => ({
      charge: async () => ({ id: 'fake_123', status: 'succeeded' }),
      refund: async () => ({ id: 'fake_456', status: 'refunded' }),
    }))

    // Now any code that resolves PaymentService from the container
    // will get the fake implementation
  })
})

// ── Pattern 6: Testing with mail/event fakes ─────────────────

import mail from '@adonisjs/mail/services/main'
import emitter from '@adonisjs/core/services/emitter'

test.group('With mail fake', () => {
  test('sends welcome email on registration', async ({ client, cleanup }) => {
    // Start faking
    const { mails } = mail.fake()

    // Restore when test ends (even if it fails)
    cleanup(() => mail.restore())

    // Act
    await client.post('/api/register').json({
      email: 'new@user.com',
      password: 'secret123',
    })

    // Assert mail was sent
    mails.assertSent('WelcomeEmail', (message) => {
      return message.to[0].address === 'new@user.com'
    })

    // Assert mail was NOT sent
    mails.assertNotSent('AdminNotification')

    // Assert exact count
    mails.assertSentCount(1)
  })
})

test.group('With event fake', () => {
  test('emits order:created event', async ({ cleanup }) => {
    const events = emitter.fake()
    cleanup(() => emitter.restore())

    // ... perform action that should emit event

    events.assertEmitted('order:created')
    events.assertNotEmitted('order:cancelled')
  })
})
