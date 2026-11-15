// tests/unit/state_machines/order_state_machine.spec.ts
//
// Comprehensive test suite for the OrderStateMachine.
// Demonstrates: transition validation, guards, terminal states, datasets.

import { test } from '@japa/runner'
import Order from '#models/order'
import { OrderStatus } from '#enums/order_status'
import testUtils from '@adonisjs/core/services/test_utils'

test.group('OrderStateMachine | allowed transitions', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('draft can transition to pending or cancelled', ({ assert }) => {
    const order = new Order()
    order.status = OrderStatus.Draft

    assert.deepEqual(order.stateMachine('status').allowedTransitions(), [
      OrderStatus.Pending,
      OrderStatus.Cancelled,
    ])
  })

  test('pending can transition to paid or cancelled', ({ assert }) => {
    const order = new Order()
    order.status = OrderStatus.Pending

    assert.deepEqual(order.stateMachine('status').allowedTransitions(), [
      OrderStatus.Paid,
      OrderStatus.Cancelled,
    ])
  })

  test('shipped can only transition to completed', ({ assert }) => {
    const order = new Order()
    order.status = OrderStatus.Shipped

    assert.deepEqual(order.stateMachine('status').allowedTransitions(), [
      OrderStatus.Completed,
    ])
  })

  test('terminal states have no outgoing transitions')
    .with([OrderStatus.Completed, OrderStatus.Cancelled])
    .run(({ assert }, status) => {
      const order = new Order()
      order.status = status

      assert.deepEqual(order.stateMachine('status').allowedTransitions(), [])
      assert.isFalse(order.stateMachine('status').canTransitionTo(OrderStatus.Draft))
    })
})

test.group('OrderStateMachine | transition execution', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('transitions draft → pending', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Draft,
      totalInCents: 5000,
    })

    await order.stateMachine('status').transitionTo(OrderStatus.Pending)

    assert.equal(order.status, OrderStatus.Pending)

    // Verify persisted to database
    await order.refresh()
    assert.equal(order.status, OrderStatus.Pending)
  })

  test('transitions through full lifecycle', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Draft,
      totalInCents: 5000,
    })

    // Draft → Pending
    await order.stateMachine('status').transitionTo(OrderStatus.Pending)
    assert.equal(order.status, OrderStatus.Pending)

    // Pending → Paid (need paymentId for guard)
    order.paymentId = 'pay_123'
    await order.save()
    await order.stateMachine('status').transitionTo(OrderStatus.Paid)
    assert.equal(order.status, OrderStatus.Paid)

    // Paid → Shipped (need shippingAddress for guard)
    order.shippingAddress = '123 Main St'
    await order.save()
    await order.stateMachine('status').transitionTo(OrderStatus.Shipped)
    assert.equal(order.status, OrderStatus.Shipped)

    // Shipped → Completed
    await order.stateMachine('status').transitionTo(OrderStatus.Completed)
    assert.equal(order.status, OrderStatus.Completed)
  })
})

test.group('OrderStateMachine | invalid transitions', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('prevents draft → shipped (skipping states)', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Draft,
      totalInCents: 5000,
    })

    await assert.rejects(
      () => order.stateMachine('status').transitionTo(OrderStatus.Shipped),
      'Cannot transition from "draft" to "shipped"'
    )

    // State should not have changed
    assert.equal(order.status, OrderStatus.Draft)
  })

  test('prevents transition from terminal state', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Completed,
      totalInCents: 5000,
    })

    await assert.rejects(
      () => order.stateMachine('status').transitionTo(OrderStatus.Draft),
      'Cannot transition from "completed" to "draft"'
    )
  })

  test('prevents self-transition', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Draft,
      totalInCents: 5000,
    })

    await assert.rejects(
      () => order.stateMachine('status').transitionTo(OrderStatus.Draft),
      'Cannot transition from "draft" to "draft"'
    )
  })
})

test.group('OrderStateMachine | guards', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('guard blocks pending → paid without payment ID', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Pending,
      totalInCents: 5000,
      paymentId: null,
    })

    await assert.rejects(
      () => order.stateMachine('status').transitionTo(OrderStatus.Paid),
      'Cannot mark as paid without a payment ID'
    )

    // State unchanged
    assert.equal(order.status, OrderStatus.Pending)
  })

  test('guard allows pending → paid with payment ID', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Pending,
      totalInCents: 5000,
      paymentId: 'pay_abc',
    })

    await order.stateMachine('status').transitionTo(OrderStatus.Paid)
    assert.equal(order.status, OrderStatus.Paid)
  })

  test('guard blocks paid → shipped without shipping address', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Paid,
      totalInCents: 5000,
      paymentId: 'pay_abc',
      shippingAddress: null,
    })

    await assert.rejects(
      () => order.stateMachine('status').transitionTo(OrderStatus.Shipped),
      'Shipping address is required'
    )
  })

  test('guard blocks draft → pending with zero total', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Draft,
      totalInCents: 0,
    })

    await assert.rejects(
      () => order.stateMachine('status').transitionTo(OrderStatus.Pending),
      'Order total must be greater than zero'
    )
  })
})

test.group('OrderStateMachine | state helpers', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('.is() checks current state', ({ assert }) => {
    const order = new Order()
    order.status = OrderStatus.Draft

    assert.isTrue(order.stateMachine('status').is(OrderStatus.Draft))
    assert.isFalse(order.stateMachine('status').is(OrderStatus.Pending))
  })

  test('.isAny() checks against multiple states', ({ assert }) => {
    const order = new Order()
    order.status = OrderStatus.Paid

    assert.isTrue(
      order.stateMachine('status').isAny([OrderStatus.Paid, OrderStatus.Shipped])
    )
    assert.isFalse(
      order.stateMachine('status').isAny([OrderStatus.Draft, OrderStatus.Pending])
    )
  })

  test('model convenience methods work', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Draft,
      totalInCents: 5000,
    })

    assert.isTrue(order.isEditable)
    assert.isTrue(order.isCancellable)

    await order.submit()
    assert.isFalse(order.isEditable)
    assert.isTrue(order.isCancellable)
  })
})

test.group('OrderStateMachine | memory safety', () => {
  test('stateMachine() returns a new proxy each call (no accumulation)', ({
    assert,
  }) => {
    const order = new Order()
    order.status = OrderStatus.Draft

    const proxy1 = order.stateMachine('status')
    const proxy2 = order.stateMachine('status')

    // Different proxy objects (no cached/accumulated references)
    assert.notStrictEqual(proxy1, proxy2)

    // But both work identically
    assert.deepEqual(proxy1.allowedTransitions(), proxy2.allowedTransitions())
  })
})
