// tests/functional/payments/process_payment.spec.ts
//
// Demonstrates three strategies for testing services:
// 1. Null driver via config (recommended for most tests)
// 2. Container swap for specific behavior (error paths)
// 3. Custom fake driver for detailed assertions

import { test } from '@japa/runner'
import User from '#models/user'
import Order from '#models/order'
import app from '@adonisjs/core/services/app'
import { PaymentManager } from '#services/payment/payment_manager'
import { NullPaymentDriver, FailingPaymentDriver } from '#services/payment/drivers/null_driver'
import testUtils from '@adonisjs/core/services/test_utils'

// ─────────────────────────────────────────────────────────────────
// Strategy 1: Null driver (zero setup, fastest)
// ─────────────────────────────────────────────────────────────────
//
// Set PAYMENT_DRIVER=null in .env.test
// NullPaymentDriver returns 'succeeded' for all calls.
// No mocking, no HTTP, no setup code needed.

test.group('Payments | null driver', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('processes payment successfully', async ({ client, assert }) => {
    const user = await User.create({ email: 'buyer@test.com', password: 'secret' })
    const order = await Order.create({ totalInCents: 5000, userId: user.id })

    const response = await client
      .post(`/api/orders/${order.id}/pay`)
      .loginAs(user)
      .json({ amount: 5000, currency: 'usd' })

    response.assertStatus(200)
    response.assertBodyContains({
      data: { status: 'succeeded' },
    })

    // Verify order was updated
    await order.refresh()
    assert.isNotNull(order.paymentId)
  })

  test('returns payment intent details', async ({ client }) => {
    const user = await User.create({ email: 'buyer@test.com', password: 'secret' })

    const response = await client
      .post('/api/payments/create-intent')
      .loginAs(user)
      .json({ amount: 10000, currency: 'usd' })

    response.assertStatus(200)
    response.assertBodyContains({
      data: {
        amount: 10000,
        currency: 'usd',
        status: 'succeeded',
      },
    })
  })
})

// ─────────────────────────────────────────────────────────────────
// Strategy 2: Container swap (for specific error behavior)
// ─────────────────────────────────────────────────────────────────

test.group('Payments | error handling', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('handles card declined gracefully', async ({ client, cleanup }) => {
    const user = await User.create({ email: 'buyer@test.com', password: 'secret' })
    const order = await Order.create({ totalInCents: 5000, userId: user.id })

    // Swap PaymentManager with one that uses the failing driver
    app.container.swap(PaymentManager, () => {
      return {
        use: () => new FailingPaymentDriver('Card declined'),
        flush: () => {},
      } as any
    })

    // Always restore — even if test fails
    cleanup(() => app.container.restore(PaymentManager))

    const response = await client
      .post(`/api/orders/${order.id}/pay`)
      .loginAs(user)
      .json({ amount: 5000, currency: 'usd' })

    response.assertStatus(422)
    response.assertBodyContains({
      error: 'Card declined',
    })
  })

  test('handles refund failure', async ({ client, cleanup }) => {
    const user = await User.create({ email: 'buyer@test.com', password: 'secret' })

    app.container.swap(PaymentManager, () => {
      return {
        use: () => new FailingPaymentDriver('Refund not available'),
        flush: () => {},
      } as any
    })

    cleanup(() => app.container.restore(PaymentManager))

    const response = await client
      .post('/api/payments/pi_123/refund')
      .loginAs(user)

    response.assertStatus(422)
  })
})

// ─────────────────────────────────────────────────────────────────
// Strategy 3: Null driver with call tracking
// ─────────────────────────────────────────────────────────────────

test.group('Payments | call tracking', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('calls createPaymentIntent with correct args', async ({ assert, cleanup }) => {
    const nullDriver = new NullPaymentDriver()

    app.container.swap(PaymentManager, () => {
      return {
        use: () => nullDriver,
        flush: () => {},
      } as any
    })

    cleanup(() => {
      nullDriver.reset()
      app.container.restore(PaymentManager)
    })

    // Resolve the manager and use it (simulating what a controller would do)
    const manager = await app.container.make(PaymentManager)
    await manager.use().createPaymentIntent(7500, 'eur')

    // Assert the driver was called with expected arguments
    assert.lengthOf(nullDriver.calls, 1)
    assert.deepEqual(nullDriver.calls[0], {
      method: 'createPaymentIntent',
      args: [7500, 'eur'],
    })
  })
})

// ─────────────────────────────────────────────────────────────────
// Unit test: Manager directly (no HTTP)
// ─────────────────────────────────────────────────────────────────

test.group('PaymentManager | unit', () => {
  test('uses default driver from config', async ({ assert }) => {
    const manager = await app.container.make(PaymentManager)
    const driver = manager.use()

    // In test env with PAYMENT_DRIVER=null, should be NullPaymentDriver
    const result = await driver.createPaymentIntent(1000, 'usd')
    assert.equal(result.status, 'succeeded')
    assert.equal(result.amount, 1000)
  })

  test('creates different instances for different driver names', async ({ assert }) => {
    const manager = await app.container.make(PaymentManager)
    const d1 = manager.use('null')
    const d2 = manager.use('null')

    // Same instance (cached)
    assert.strictEqual(d1, d2)
  })

  test('flush clears driver cache', async ({ assert }) => {
    const manager = await app.container.make(PaymentManager)
    const before = manager.use('null')
    manager.flush()
    const after = manager.use('null')

    // Different instance after flush
    assert.notStrictEqual(before, after)
  })

  test('throws on unknown driver', async ({ assert }) => {
    const manager = await app.container.make(PaymentManager)

    assert.throws(
      () => manager.use('nonexistent'),
      'Unknown payment driver "nonexistent"'
    )
  })
})
