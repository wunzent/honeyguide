---
name: adonisjs-actions
description: Optional single-purpose action classes for AdonisJS v6. Use when a service method grows complex (beyond ~50 lines), needs to be reused across multiple callers, or when the user mentions actions, domain operations, composing workflows, or extracting logic out of services. Actions are optional — start with services, extract to actions when complexity demands it.
---

# AdonisJS Actions

Actions are **optional, single-purpose classes** for complex or reusable domain operations. Start with services — extract to an action when a service method grows complex, involves intricate logic, or is invoked from multiple callers (controllers, jobs, listeners).

**Related guides:**

- [Controllers](../adonisjs-controllers/SKILL.md) - Controllers delegate to services or actions; they contain zero domain logic
- [Exceptions](../adonisjs-exceptions/SKILL.md) - Custom domain exceptions thrown from actions
- [Dependency Injection](https://docs.adonisjs.com/guides/concepts/dependency-injection) - IoC container, `@inject`, constructor injection
- [Lucid Transactions](https://lucid.adonisjs.com/docs/transactions) - `db.transaction()` for atomic database operations
- [Exception Handling](https://docs.adonisjs.com/guides/basics/exception-handling) - Custom exceptions for domain errors
- [Testing](https://docs.adonisjs.com/guides/testing/introduction) - Japa unit tests for actions in isolation

---

## Philosophy

**Controllers, Jobs, and Event Listeners contain ZERO domain logic** — they delegate to services or actions.

Actions are:

- **Single-responsibility classes** — each action does exactly one thing
- **Composable** — actions call other actions to build workflows
- **Stateless by default** — each invocation is independent (though private properties can hold invocation context)
- **Type-safe** — strict TypeScript parameter and return types throughout
- **Transactional** — all database writes are wrapped in a `db.transaction()`

---

## File Naming & Location

AdonisJS v6 uses **snake_case** for all files and directories.

```
# ✅ CORRECT
app/actions/create_order_action.ts
app/actions/cancel_order_action.ts
app/actions/order/create_order_action.ts   # grouped by domain entity

# ❌ INCORRECT — PascalCase filenames
app/Actions/CreateOrderAction.ts
```

### Scaffold

AdonisJS has no built-in `make:action` generator (unlike `make:controller`). Create files manually or add a custom stub.

```bash
# Create manually
touch app/actions/order/create_order_action.ts
```

---

## Naming Conventions

Action **class names** use PascalCase with the `Action` suffix. Files use snake_case.

**Format:** `{Verb}{Entity}Action`

```ts
// ✅ CORRECT
CreateOrderAction          // app/actions/order/create_order_action.ts
UpdateUserProfileAction    // app/actions/user/update_user_profile_action.ts
CancelOrderAction          // app/actions/order/cancel_order_action.ts
CalculateOrderTotalAction  // app/actions/order/calculate_order_total_action.ts
ProcessPaymentAction       // app/actions/payment/process_payment_action.ts
SendWelcomeEmailAction     // app/actions/user/send_welcome_email_action.ts

// ❌ INCORRECT — vague or noun-only names
OrderAction
OrderManager
OrderHelper
```

---

## Basic Structure

Every action is a class with a single public `handle` method. Dependencies are injected via the constructor using `@inject()`.

```ts
// app/actions/order/create_order_action.ts
import { inject } from '@adonisjs/core'
import db from '@adonisjs/lucid/services/db'
import Order from '#models/order'
import User from '#models/user'

export interface CreateOrderPayload {
  customerId: number
  items: Array<{ productId: number; quantity: number; price: number }>
  notes?: string
}

@inject()
export default class CreateOrderAction {
  async handle(user: User, payload: CreateOrderPayload): Promise<Order> {
    return db.transaction(async (trx) => {
      const order = new Order()
      order.userId = user.id
      order.notes = payload.notes ?? null
      order.useTransaction(trx)
      await order.save()

      await order.related('items').createMany(
        payload.items.map((item) => ({
          productId: item.productId,
          quantity: item.quantity,
          price: item.price,
        })),
      )

      await order.load('items')
      return order
    })
  }
}
```

---

## Key Patterns

### 1. Constructor Injection for Action Composition

Inject other actions to build complex workflows:

```ts
// app/actions/order/create_order_action.ts
import { inject } from '@adonisjs/core'
import db from '@adonisjs/lucid/services/db'
import CalculateOrderTotalAction from '#actions/order/calculate_order_total_action'
import NotifyOrderCreatedAction from '#actions/order/notify_order_created_action'
import User from '#models/user'
import Order from '#models/order'
import type { CreateOrderPayload } from '#types/order'

@inject()
export default class CreateOrderAction {
  constructor(
    private calculateTotal: CalculateOrderTotalAction,
    private notifyOrderCreated: NotifyOrderCreatedAction,
  ) {}

  async handle(user: User, payload: CreateOrderPayload): Promise<Order> {
    const order = await db.transaction(async (trx) => {
      const newOrder = await this.createOrder(user, payload, trx)
      const total = await this.calculateTotal.handle(newOrder)
      newOrder.total = total
      await newOrder.save()
      return newOrder
    })

    // Side effects outside the transaction — email won't block a rollback
    await this.notifyOrderCreated.handle(order)

    return order
  }

  private async createOrder(user: User, payload: CreateOrderPayload, trx: any): Promise<Order> {
    const order = new Order()
    order.userId = user.id
    order.notes = payload.notes ?? null
    order.useTransaction(trx)
    await order.save()
    await order.related('items').createMany(payload.items)
    return order
  }
}
```

### 2. Guard Methods for Business Rule Validation

Validate business rules **before** executing the main operation:

```ts
// app/actions/order/cancel_order_action.ts
import { inject } from '@adonisjs/core'
import db from '@adonisjs/lucid/services/db'
import Order from '#models/order'
import OrderException from '#exceptions/order_exception'

@inject()
export default class CancelOrderAction {
  async handle(order: Order): Promise<Order> {
    this.guard(order)

    return db.transaction(async (trx) => {
      order.useTransaction(trx)
      order.status = 'cancelled'
      await order.save()
      return order
    })
  }

  private guard(order: Order): void {
    if (!order.canBeCancelled()) {
      throw OrderException.cannotCancel(order)
    }
  }
}
```

### 3. Private Helper Methods

Break complex operations into focused, named private methods. The `handle` method should read like a high-level recipe:

```ts
async handle(user: User, payload: OnboardUserPayload): Promise<User> {
  return db.transaction(async (trx) => {
    const freshUser = await this.createUser(payload, trx)
    await this.createProfile(freshUser, payload, trx)
    await this.assignDefaultRole(freshUser, trx)
    await this.sendWelcomeEmail(freshUser)
    return freshUser
  })
}
```

### 4. Private Properties for Invocation Context

Store invocation-scoped state in private properties to avoid threading the same argument through every private method:

```ts
@inject()
export default class ProcessOrderAction {
  private order!: Order

  async handle(order: Order): Promise<void> {
    this.order = order
    this.guard()

    await db.transaction(async (trx) => {
      this.order.useTransaction(trx)
      await this.processPayment()
      await this.updateInventory()
      await this.sendNotifications()
    })
  }

  private guard(): void {
    if (this.order.status !== 'pending') {
      throw new OrderException('Order must be pending to be processed', {
        status: 422,
        code: 'E_ORDER_NOT_PENDING',
      })
    }
  }

  private async processPayment(): Promise<void> {
    // uses this.order — no need to pass it around
  }

  private async updateInventory(): Promise<void> {
    // uses this.order
  }

  private async sendNotifications(): Promise<void> {
    // uses this.order
  }
}
```

---

## When to Create an Action

### ✅ Create an action when:

- Implementing **any** domain operation, including simple CRUD (`UpdateUserAction`, `DeletePostAction`)
- Building reusable operations used across controllers, jobs, or event listeners
- Composing multiple steps into a workflow
- Any operation that **reads or writes models or external services**

### ❌ Don't create an action for:

- Pure data retrieval for display — use a dedicated query/repository class
- HTTP-specific concerns — those belong in controllers or middleware
- Formatting or presentation logic — use transformers or serializers

**Critical rule:** Controllers must contain **zero domain logic**. Simple CRUD may live in a service method; extract to an action when it grows complex or needs to be reused across multiple entry points.

---

## Invoking Actions

### Via Constructor Injection in Controllers

```ts
// app/controllers/orders_controller.ts
import { inject } from '@adonisjs/core'
import type { HttpContext } from '@adonisjs/core/http'
import CreateOrderAction from '#actions/order/create_order_action'
import { createOrderValidator } from '#validators/order_validator'

@inject()
export default class OrdersController {
  constructor(private createOrder: CreateOrderAction) {}

  async store({ request, auth, response }: HttpContext) {
    const payload = await request.validateUsing(createOrderValidator)
    const order = await this.createOrder.handle(auth.user!, payload)
    return response.created({ data: order })
  }
}
```

### Via IoC Container (inside other actions or services)

```ts
import app from '@adonisjs/core/services/app'
import ProcessPaymentAction from '#actions/payment/process_payment_action'

const action = await app.container.make(ProcessPaymentAction)
const payment = await action.handle(order, paymentData)
```

### Via Method-Level `@inject()` (advanced)

For actions that themselves need `HttpContext`, use method-level injection:

```ts
import { inject } from '@adonisjs/core'
import type { HttpContext } from '@adonisjs/core/http'
import AuditService from '#services/audit_service'

export default class CreateOrderAction {
  @inject()
  async handle(user: User, payload: CreateOrderPayload, auditService: AuditService): Promise<Order> {
    // auditService automatically receives the current HttpContext
  }
}
```

---

## Database Transactions

**Always wrap all database writes** in a managed transaction. Use `db.transaction()` with a callback — it auto-commits on success and auto-rolls back on any thrown exception.

```ts
import db from '@adonisjs/lucid/services/db'

async handle(payload: CreateUserPayload): Promise<User> {
  return db.transaction(async (trx) => {
    const user = new User()
    user.email = payload.email
    user.useTransaction(trx)
    await user.save()

    // Relationships inherit the transaction from the model instance
    await user.related('profile').create({ fullName: payload.fullName })

    return user
  })
}
```

For actions that **fetch first, then mutate**, pass the transaction to the model query builder:

```ts
return db.transaction(async (trx) => {
  const user = await User.query({ client: trx }).where('email', payload.email).firstOrFail()
  user.status = 'verified'
  await user.save()
  return user
})
```

**Transaction cascades through relationships** — once `useTransaction(trx)` is called on a model instance, all subsequent `related()` calls on that instance implicitly use the same transaction.

---

## Error Handling

Throw **domain exceptions** for business rule violations. Create typed exception classes using `node ace make:exception`.

```bash
node ace make:exception order_exception
# → app/exceptions/order_exception.ts
```

```ts
// app/exceptions/order_exception.ts
import { Exception } from '@adonisjs/core/exceptions'
import type Order from '#models/order'

export default class OrderException extends Exception {
  static cannotCancel(order: Order) {
    return new this(
      `Order #${order.id} cannot be cancelled with status: ${order.status}`,
      { status: 422, code: 'E_ORDER_CANNOT_BE_CANCELLED' }
    )
  }

  static alreadyPaid(order: Order) {
    return new this(
      `Order #${order.id} has already been paid`,
      { status: 409, code: 'E_ORDER_ALREADY_PAID' }
    )
  }
}
```

```ts
// Usage in an action
import OrderException from '#exceptions/order_exception'

private guard(order: Order): void {
  if (!order.canBeCancelled()) {
    throw OrderException.cannotCancel(order)
  }
}
```

Unhandled exceptions bubble up to AdonisJS's global `HttpExceptionHandler`, which converts them to HTTP responses based on the `status` property.

---

## Full Examples

### Simple CRUD Action

```ts
// app/actions/user/update_user_action.ts
import { inject } from '@adonisjs/core'
import User from '#models/user'

export interface UpdateUserPayload {
  name?: string
  email?: string
}

@inject()
export default class UpdateUserAction {
  async handle(user: User, payload: UpdateUserPayload): Promise<User> {
    user.merge(payload)
    await user.save()
    return user
  }
}
```

### Multi-Step Onboarding Workflow

```ts
// app/actions/user/onboard_user_action.ts
import { inject } from '@adonisjs/core'
import db from '@adonisjs/lucid/services/db'
import User from '#models/user'
import CreateUserProfileAction from '#actions/user/create_user_profile_action'
import AssignDefaultRoleAction from '#actions/user/assign_default_role_action'
import SendWelcomeEmailAction from '#actions/user/send_welcome_email_action'

export interface OnboardUserPayload {
  email: string
  password: string
  fullName: string
}

@inject()
export default class OnboardUserAction {
  constructor(
    private createProfile: CreateUserProfileAction,
    private assignRole: AssignDefaultRoleAction,
    private sendWelcomeEmail: SendWelcomeEmailAction,
  ) {}

  async handle(payload: OnboardUserPayload): Promise<User> {
    const user = await db.transaction(async (trx) => {
      const newUser = new User()
      newUser.email = payload.email
      newUser.password = payload.password
      newUser.useTransaction(trx)
      await newUser.save()

      await this.createProfile.handle(newUser, { fullName: payload.fullName }, trx)
      await this.assignRole.handle(newUser, trx)

      return newUser
    })

    // Email is outside the transaction — a mail failure won't roll back the user
    await this.sendWelcomeEmail.handle(user)

    return user
  }
}
```

### External Service Integration

```ts
// app/actions/payment/process_payment_action.ts
import { inject } from '@adonisjs/core'
import db from '@adonisjs/lucid/services/db'
import Order from '#models/order'
import Payment from '#models/payment'
import StripeService from '#services/stripe_service'
import OrderException from '#exceptions/order_exception'

export interface PaymentPayload {
  amount: number
  currency: string
  token: string
}

@inject()
export default class ProcessPaymentAction {
  constructor(private stripe: StripeService) {}

  async handle(order: Order, payload: PaymentPayload): Promise<Payment> {
    this.guard(order)

    // Charge externally first — if it fails the DB is untouched
    const stripeCharge = await this.stripe.charge({
      amount: payload.amount,
      currency: payload.currency,
      token: payload.token,
    })

    return db.transaction(async (trx) => {
      const payment = new Payment()
      payment.orderId = order.id
      payment.amount = payload.amount
      payment.stripeId = stripeCharge.id
      payment.status = 'completed'
      payment.useTransaction(trx)
      await payment.save()

      order.useTransaction(trx)
      order.status = 'paid'
      await order.save()

      return payment
    })
  }

  private guard(order: Order): void {
    if (order.status === 'paid') {
      throw OrderException.alreadyPaid(order)
    }
  }
}
```

---

## Action Organisation

**Group by domain entity** under `app/actions/`:

```
app/actions/
├── order/
│   ├── create_order_action.ts
│   ├── cancel_order_action.ts
│   ├── process_order_action.ts
│   └── calculate_order_total_action.ts
├── user/
│   ├── create_user_action.ts
│   ├── onboard_user_action.ts
│   ├── update_user_profile_action.ts
│   └── delete_user_action.ts
└── payment/
    ├── process_payment_action.ts
    └── refund_payment_action.ts
```

**Not by operation type** — avoid `app/actions/create/`, `app/actions/update/` etc.

---

## Testing Actions

Test actions **in isolation** using Japa. Use `testUtils.db().withGlobalTransaction()` to roll back all writes automatically after each test.

```ts
// tests/unit/actions/order/create_order_action.spec.ts
import { test } from '@japa/runner'
import app from '@adonisjs/core/services/app'
import CreateOrderAction from '#actions/order/create_order_action'
import Order from '#models/order'
import UserFactory from '#database/factories/user_factory'

test.group('CreateOrderAction', (group) => {
  group.each.setup(() => testUtils.db().withGlobalTransaction())

  test('creates an order with items', async ({ assert }) => {
    // Arrange
    const user = await UserFactory.create()
    const payload = {
      customerId: user.id,
      items: [{ productId: 1, quantity: 2, price: 1999 }],
    }

    // Act
    const action = await app.container.make(CreateOrderAction)
    const order = await action.handle(user, payload)

    // Assert
    assert.instanceOf(order, Order)
    assert.equal(order.userId, user.id)
    assert.lengthOf(order.items, 1)
  })

  test('rolls back when item creation fails', async ({ assert }) => {
    const user = await UserFactory.create()
    const payload = {
      customerId: user.id,
      items: [{ productId: 999_999, quantity: 1, price: 100 }], // FK violation
    }

    const action = await app.container.make(CreateOrderAction)
    await assert.rejects(() => action.handle(user, payload))

    const count = await Order.query().where('userId', user.id).count('* as total')
    assert.equal(Number(count[0].$extras.total), 0)
  })
})

test.group('CancelOrderAction', (group) => {
  group.each.setup(() => testUtils.db().withGlobalTransaction())

  test('cancels a pending order', async ({ assert }) => {
    const order = await OrderFactory.merge({ status: 'pending' }).create()

    const action = await app.container.make(CancelOrderAction)
    const cancelled = await action.handle(order)

    assert.equal(cancelled.status, 'cancelled')
  })

  test('throws when order cannot be cancelled', async ({ assert }) => {
    const order = await OrderFactory.merge({ status: 'paid' }).create()

    const action = await app.container.make(CancelOrderAction)
    await assert.rejects(
      () => action.handle(order),
      (err: unknown) => err instanceof OrderException
    )
  })
})
```

---

## Common Mistakes

### ❌ Domain Logic Directly in a Controller

```ts
// BAD — controller doing too much
async store({ request, auth, response }: HttpContext) {
  const data = request.only(['title', 'body'])
  const post = await Post.create({ ...data, userId: auth.user!.id })
  await post.load('tags')
  await NotificationService.notifyFollowers(post)
  return response.created({ data: post })
}
```

### ✅ Delegate to an Action

```ts
// GOOD — controller is a thin HTTP adapter
async store({ request, auth, response }: HttpContext) {
  const payload = await request.validateUsing(createPostValidator)
  const post = await this.createPost.handle(auth.user!, payload)
  return response.created({ data: post })
}
```

---

### ❌ Missing Transaction on Multi-Step Writes

```ts
// BAD — partial writes possible if the second call fails
async handle(payload: CreateUserPayload): Promise<User> {
  const user = await User.create({ email: payload.email })
  await user.related('profile').create({ fullName: payload.fullName }) // could fail
  return user
}
```

### ✅ Wrap in db.transaction()

```ts
// GOOD — atomic: both succeed or neither does
async handle(payload: CreateUserPayload): Promise<User> {
  return db.transaction(async (trx) => {
    const user = new User()
    user.email = payload.email
    user.useTransaction(trx)
    await user.save()
    await user.related('profile').create({ fullName: payload.fullName })
    return user
  })
}
```

---

### ❌ Fat Action with Too Many Responsibilities

```ts
// BAD — one action doing five separate concerns
export default class CreateOrderAction {
  async handle(user: User, payload: any) {
    const order = await this.saveOrder(user, payload)
    await this.sendConfirmationEmail(user, order)
    await this.updateInventory(order)
    await this.notifyWarehouse(order)
    await this.createInvoice(order)
    return order
  }
}
```

### ✅ Compose Focused Actions

```ts
// GOOD — each sub-action has one job; the orchestrator composes them
@inject()
export default class PlaceOrderAction {
  constructor(
    private createOrder: CreateOrderAction,
    private reserveInventory: ReserveInventoryAction,
    private sendConfirmation: SendOrderConfirmationAction,
  ) {}

  async handle(user: User, payload: PlaceOrderPayload): Promise<Order> {
    const order = await this.createOrder.handle(user, payload)
    await this.reserveInventory.handle(order)
    await this.sendConfirmation.handle(order)
    return order
  }
}
```

---

## Summary

**Actions are domain adapters — they translate intent into data changes.**

1. Accept typed, validated inputs (plain payload objects or Lucid model instances)
2. Guard against business rule violations early — throw domain exceptions
3. Wrap all writes in `db.transaction()`
4. Compose with other injected actions rather than growing large
5. Return the resulting model or value — no HTTP concerns

**Every line of domain logic belongs in a service or action — never in a controller.**
