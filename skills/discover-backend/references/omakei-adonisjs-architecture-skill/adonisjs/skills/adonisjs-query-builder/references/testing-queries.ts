// tests/unit/queries/order_query.spec.ts
//
// Tests for model scopes and standalone query objects.

import { test } from '@japa/runner'
import Order from '#models/order'
import User from '#models/user'
import { OrderStatus } from '#enums/order_status'
import { OrderQuery } from '#queries/order_query'
import { DateTime } from 'luxon'
import testUtils from '@adonisjs/core/services/test_utils'

test.group('Order scopes', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('pending scope filters by pending status', async ({ assert }) => {
    await Order.createMany([
      { status: OrderStatus.Pending, totalInCents: 1000, customerId: 1 },
      { status: OrderStatus.Completed, totalInCents: 2000, customerId: 1 },
      { status: OrderStatus.Pending, totalInCents: 3000, customerId: 1 },
    ])

    const orders = await Order.query()
      .apply((scopes) => scopes.pending())

    assert.lengthOf(orders, 2)
    orders.forEach((o) => assert.equal(o.status, OrderStatus.Pending))
  })

  test('forCustomer filters by customer id', async ({ assert }) => {
    const user1 = await User.create({ email: 'a@test.com', password: 'secret' })
    const user2 = await User.create({ email: 'b@test.com', password: 'secret' })

    await Order.createMany([
      { status: OrderStatus.Pending, totalInCents: 1000, customerId: user1.id },
      { status: OrderStatus.Pending, totalInCents: 2000, customerId: user2.id },
      { status: OrderStatus.Pending, totalInCents: 3000, customerId: user1.id },
    ])

    const orders = await Order.query()
      .apply((scopes) => scopes.forCustomer(user1.id))

    assert.lengthOf(orders, 2)
    orders.forEach((o) => assert.equal(o.customerId, user1.id))
  })

  test('totalAbove filters by minimum amount', async ({ assert }) => {
    await Order.createMany([
      { status: OrderStatus.Pending, totalInCents: 500, customerId: 1 },
      { status: OrderStatus.Pending, totalInCents: 5000, customerId: 1 },
      { status: OrderStatus.Pending, totalInCents: 15000, customerId: 1 },
    ])

    const orders = await Order.query()
      .apply((scopes) => scopes.totalAbove(1000))

    assert.lengthOf(orders, 2)
    orders.forEach((o) => assert.isAbove(o.totalInCents, 1000))
  })

  test('scopes can be chained together', async ({ assert }) => {
    const user = await User.create({ email: 'a@test.com', password: 'secret' })

    await Order.createMany([
      { status: OrderStatus.Pending, totalInCents: 500, customerId: user.id },
      { status: OrderStatus.Pending, totalInCents: 5000, customerId: user.id },
      { status: OrderStatus.Completed, totalInCents: 5000, customerId: user.id },
    ])

    const orders = await Order.query()
      .apply((scopes) => {
        scopes.pending()
        scopes.forCustomer(user.id)
        scopes.totalAbove(1000)
      })

    assert.lengthOf(orders, 1)
    assert.equal(orders[0].totalInCents, 5000)
  })

  test('recent scope orders by placed_at desc', async ({ assert }) => {
    await Order.createMany([
      { status: OrderStatus.Pending, totalInCents: 1000, customerId: 1, placedAt: DateTime.now().minus({ days: 3 }) },
      { status: OrderStatus.Pending, totalInCents: 2000, customerId: 1, placedAt: DateTime.now().minus({ days: 1 }) },
      { status: OrderStatus.Pending, totalInCents: 3000, customerId: 1, placedAt: DateTime.now().minus({ days: 2 }) },
    ])

    const orders = await Order.query()
      .apply((scopes) => scopes.recent())

    assert.equal(orders[0].totalInCents, 2000) // most recent first
  })
})

test.group('OrderQuery (standalone)', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('applies status filter', async ({ assert }) => {
    await Order.createMany([
      { status: OrderStatus.Pending, totalInCents: 1000, customerId: 1 },
      { status: OrderStatus.Completed, totalInCents: 2000, customerId: 1 },
    ])

    const result = await new OrderQuery()
      .apply({ status: OrderStatus.Pending })
      .all()

    assert.lengthOf(result, 1)
    assert.equal(result[0].status, OrderStatus.Pending)
  })

  test('applies total range filter', async ({ assert }) => {
    await Order.createMany([
      { status: OrderStatus.Pending, totalInCents: 500, customerId: 1 },
      { status: OrderStatus.Pending, totalInCents: 5000, customerId: 1 },
      { status: OrderStatus.Pending, totalInCents: 15000, customerId: 1 },
    ])

    const result = await new OrderQuery()
      .apply({ minTotal: 1000, maxTotal: 10000 })
      .all()

    assert.lengthOf(result, 1)
    assert.equal(result[0].totalInCents, 5000)
  })

  test('applies multiple filters simultaneously', async ({ assert }) => {
    const user = await User.create({ email: 'a@test.com', password: 'secret' })

    await Order.createMany([
      { status: OrderStatus.Pending, totalInCents: 5000, customerId: user.id },
      { status: OrderStatus.Completed, totalInCents: 5000, customerId: user.id },
      { status: OrderStatus.Pending, totalInCents: 500, customerId: user.id },
    ])

    const result = await new OrderQuery()
      .apply({
        status: OrderStatus.Pending,
        customerId: user.id,
        minTotal: 1000,
      })
      .all()

    assert.lengthOf(result, 1)
  })

  test('paginate returns pagination meta', async ({ assert }) => {
    await Order.createMany(
      Array.from({ length: 25 }, (_, i) => ({
        status: OrderStatus.Pending,
        totalInCents: (i + 1) * 100,
        customerId: 1,
      }))
    )

    const page = await new OrderQuery()
      .apply({})
      .paginate(1, 10)

    assert.equal(page.perPage, 10)
    assert.equal(page.total, 25)
    assert.equal(page.lastPage, 3)
    assert.lengthOf(page.all(), 10)
  })

  test('count returns total matching rows', async ({ assert }) => {
    await Order.createMany([
      { status: OrderStatus.Pending, totalInCents: 1000, customerId: 1 },
      { status: OrderStatus.Pending, totalInCents: 2000, customerId: 1 },
      { status: OrderStatus.Completed, totalInCents: 3000, customerId: 1 },
    ])

    const count = await new OrderQuery()
      .apply({ status: OrderStatus.Pending })
      .count()

    assert.equal(count, 2)
  })

  test('search filters by reference and customer name', async ({ assert }) => {
    const user = await User.create({ email: 'john@test.com', password: 'secret', name: 'John Doe' })

    await Order.createMany([
      { status: OrderStatus.Pending, totalInCents: 1000, customerId: user.id, reference: 'ORD-001' },
      { status: OrderStatus.Pending, totalInCents: 2000, customerId: user.id, reference: 'ORD-002' },
    ])

    const byRef = await new OrderQuery().apply({ search: 'ORD-001' }).all()
    assert.lengthOf(byRef, 1)

    const byName = await new OrderQuery().apply({ search: 'john' }).all()
    assert.lengthOf(byName, 2) // both orders belong to John
  })
})
