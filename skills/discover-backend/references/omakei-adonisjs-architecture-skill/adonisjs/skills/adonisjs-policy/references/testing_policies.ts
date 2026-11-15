// tests/unit/policies/order_policy.spec.ts
//
// Tests for OrderPolicy authorization logic.
// Tests policies in isolation (no HTTP) and via functional API tests.

import { test } from '@japa/runner'
import User from '#models/user'
import Order from '#models/order'
import OrderPolicy from '#policies/order_policy'
import { Permission } from '#enums/permission'
import { OrderStatus } from '#enums/order_status'
import testUtils from '@adonisjs/core/services/test_utils'

// ─────────────────────────────────────────────────────────────
// Unit tests — test policy methods directly
// ─────────────────────────────────────────────────────────────

test.group('OrderPolicy | viewAny', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('allows user with list permission', async ({ assert }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [Permission.ListOrders],
    })

    const policy = new OrderPolicy()
    assert.isTrue(policy.viewAny(user))
  })

  test('denies user without list permission', async ({ assert }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [],
    })

    const policy = new OrderPolicy()
    assert.isFalse(policy.viewAny(user))
  })
})

test.group('OrderPolicy | view', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('allows owner with view permission', async ({ assert }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [Permission.ViewOrders],
      customerId: 1,
    })
    const order = await Order.create({
      status: OrderStatus.Pending,
      totalInCents: 1000,
      customerId: 1,
    })

    const policy = new OrderPolicy()
    assert.isTrue(policy.view(user, order))
  })

  test('denies non-owner even with permission', async ({ assert }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [Permission.ViewOrders],
      customerId: 1,
    })
    const order = await Order.create({
      status: OrderStatus.Pending,
      totalInCents: 1000,
      customerId: 999,
    })

    const policy = new OrderPolicy()
    assert.isFalse(policy.view(user, order))
  })
})

test.group('OrderPolicy | update', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('allows owner with permission on editable order', async ({ assert }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [Permission.UpdateOrders],
      customerId: 1,
    })
    const order = await Order.create({
      status: OrderStatus.Draft, // editable
      totalInCents: 1000,
      customerId: 1,
    })

    const policy = new OrderPolicy()
    assert.isTrue(policy.update(user, order))
  })

  test('denies update on non-editable order', async ({ assert }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [Permission.UpdateOrders],
      customerId: 1,
    })
    const order = await Order.create({
      status: OrderStatus.Completed, // not editable
      totalInCents: 1000,
      customerId: 1,
    })

    const policy = new OrderPolicy()
    assert.isFalse(policy.update(user, order))
  })
})

test.group('OrderPolicy | cancel (compound)', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('allows cancel on cancellable + updatable order', async ({ assert }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [Permission.UpdateOrders],
      customerId: 1,
    })
    const order = await Order.create({
      status: OrderStatus.Pending, // editable + cancellable
      totalInCents: 1000,
      customerId: 1,
    })

    const policy = new OrderPolicy()
    assert.isTrue(policy.cancel(user, order))
  })

  test('denies cancel on non-cancellable order', async ({ assert }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [Permission.UpdateOrders],
      customerId: 1,
    })
    const order = await Order.create({
      status: OrderStatus.Completed, // not cancellable
      totalInCents: 1000,
      customerId: 1,
    })

    const policy = new OrderPolicy()
    assert.isFalse(policy.cancel(user, order))
  })
})

test.group('OrderPolicy | before (admin bypass)', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('super_admin bypasses all checks', async ({ assert }) => {
    const admin = await User.create({
      email: 'admin@test.com',
      password: 'secret',
      role: 'super_admin',
      permissions: [], // no explicit permissions
      customerId: 999,
    })

    const policy = new OrderPolicy()
    assert.isTrue(policy.before(admin) === true)
  })

  test('regular user falls through to specific method', async ({ assert }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [],
      customerId: 1,
    })

    const policy = new OrderPolicy()
    assert.isUndefined(policy.before(user))
  })
})

// ─────────────────────────────────────────────────────────────
// Functional tests — test authorization via HTTP
// ─────────────────────────────────────────────────────────────

test.group('OrderPolicy | HTTP integration', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('authorized user can view their order', async ({ client }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [Permission.ViewOrders],
      customerId: 1,
    })
    const order = await Order.create({
      status: OrderStatus.Pending,
      totalInCents: 5000,
      customerId: 1,
    })

    const response = await client
      .get(`/api/v1/orders/${order.id}`)
      .loginAs(user)

    response.assertStatus(200)
  })

  test('unauthorized user gets 403', async ({ client }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
      permissions: [Permission.ViewOrders],
      customerId: 1,
    })
    const order = await Order.create({
      status: OrderStatus.Pending,
      totalInCents: 5000,
      customerId: 999, // different customer
    })

    const response = await client
      .get(`/api/v1/orders/${order.id}`)
      .loginAs(user)

    response.assertStatus(403)
  })

  test('super_admin can access any order', async ({ client }) => {
    const admin = await User.create({
      email: 'admin@test.com',
      password: 'secret',
      role: 'super_admin',
      permissions: [],
      customerId: 999,
    })
    const order = await Order.create({
      status: OrderStatus.Pending,
      totalInCents: 5000,
      customerId: 1,
    })

    const response = await client
      .get(`/api/v1/orders/${order.id}`)
      .loginAs(admin)

    response.assertStatus(200)
  })

  test('unauthenticated user gets 401', async ({ client }) => {
    const order = await Order.create({
      status: OrderStatus.Pending,
      totalInCents: 5000,
      customerId: 1,
    })

    const response = await client.get(`/api/v1/orders/${order.id}`)
    response.assertStatus(401)
  })
})
