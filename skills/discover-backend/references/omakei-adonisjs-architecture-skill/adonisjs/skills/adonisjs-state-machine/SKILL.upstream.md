---
name: adonisjs-state-machines
description: State machine patterns for AdonisJS Lucid models. Use when working with complex state management, state transitions, workflow status, order status, or when user mentions state machines, state transitions, transition validation, transition guards, side effects on state change, finite state machines, FSM, status workflows, or needs to model domain objects with well-defined lifecycle states. Also trigger when user asks how to handle status columns that have rules about which transitions are allowed.
---

# AdonisJS State Machines

Lightweight, zero-dependency state machine pattern for AdonisJS Lucid models. Provides type-safe transitions with guards, side effects, and Lucid integration — without event emitter accumulation or closure leaks.

**Reference implementations:**
- [StateMachine base class →](references/state_machine.ts)
- [OrderStateMachine example →](references/order_state_machine.ts)
- [HasStateMachine mixin →](references/has_state_machine.ts)
- [Testing state machines →](references/testing_state_machines.ts)

## When to Use

**Use state machines when:**
- A model has well-defined lifecycle states (Order: draft → pending → paid → shipped → completed)
- Transitions have rules (can't ship an unpaid order)
- Transitions have side effects (send email when paid, notify warehouse when shipped)
- State-specific behavior exists (only draft orders can be edited)
- You need an audit trail of state changes

**Use simple enums when:**
- Status is informational only (active/inactive)
- No transition rules needed
- No side effects on change
- Any state can move to any other state

---

## Core Concepts

### 1. States — TypeScript enum values

```typescript
// app/enums/order_status.ts
export enum OrderStatus {
  Draft = 'draft',
  Pending = 'pending',
  Paid = 'paid',
  Shipped = 'shipped',
  Completed = 'completed',
  Cancelled = 'cancelled',
}
```

### 2. Transitions — declared statically, not as closures

```typescript
// Transition map: { from → allowed targets[] }
const transitions = {
  [OrderStatus.Draft]:     [OrderStatus.Pending, OrderStatus.Cancelled],
  [OrderStatus.Pending]:   [OrderStatus.Paid, OrderStatus.Cancelled],
  [OrderStatus.Paid]:      [OrderStatus.Shipped, OrderStatus.Cancelled],
  [OrderStatus.Shipped]:   [OrderStatus.Completed],
  [OrderStatus.Completed]: [],           // terminal state
  [OrderStatus.Cancelled]: [],           // terminal state
}
```

### 3. Guards — sync/async checks that must pass before a transition

```typescript
guards: {
  'pending→paid': async (model) => {
    return model.totalInCents > 0 && model.paymentId !== null
  },
}
```

### 4. Side effects — run after a successful transition

```typescript
afterTransition: {
  'pending→paid': async (model) => {
    await mail.send(new OrderPaidEmail(model))
  },
}
```

---

## Quick Start

### Step 1 — Define the enum

```typescript
// app/enums/order_status.ts
export enum OrderStatus {
  Draft = 'draft',
  Pending = 'pending',
  Paid = 'paid',
  Shipped = 'shipped',
  Completed = 'completed',
  Cancelled = 'cancelled',
}
```

### Step 2 — Define the state machine

```typescript
// app/state_machines/order_state_machine.ts
import { StateMachine } from '#lib/state_machine'
import { OrderStatus } from '#enums/order_status'
import type Order from '#models/order'

export class OrderStateMachine extends StateMachine<Order, OrderStatus> {
  // Which column holds the state
  column = 'status' as const

  // All allowed transitions (static — no closures, no memory leak)
  transitions = {
    [OrderStatus.Draft]:     [OrderStatus.Pending, OrderStatus.Cancelled],
    [OrderStatus.Pending]:   [OrderStatus.Paid, OrderStatus.Cancelled],
    [OrderStatus.Paid]:      [OrderStatus.Shipped, OrderStatus.Cancelled],
    [OrderStatus.Shipped]:   [OrderStatus.Completed],
    [OrderStatus.Completed]: [],
    [OrderStatus.Cancelled]: [],
  }

  // Optional: guards that must pass before transition
  guards = {
    'pending→paid': async (order: Order) => {
      if (!order.paymentId) {
        throw new Error('Cannot mark as paid without a payment ID')
      }
    },
    'paid→shipped': async (order: Order) => {
      if (!order.shippingAddress) {
        throw new Error('Shipping address is required')
      }
    },
  }

  // Optional: side effects that run after successful transition + save
  afterTransition = {
    'pending→paid': async (order: Order) => {
      // Send confirmation email, emit event, etc.
    },
    'paid→shipped': async (order: Order) => {
      // Notify warehouse, update tracking, etc.
    },
  }
}
```

### Step 3 — Add the mixin to your model

```typescript
// app/models/order.ts
import { BaseModel, column } from '@adonisjs/lucid/orm'
import { compose } from '@adonisjs/core/helpers'
import { HasStateMachine } from '#lib/has_state_machine'
import { OrderStateMachine } from '#state_machines/order_state_machine'
import { OrderStatus } from '#enums/order_status'

export default class Order extends compose(BaseModel, HasStateMachine) {
  // Register state machines (static — no per-instance allocation)
  static stateMachines = {
    status: OrderStateMachine,
  }

  @column()
  declare status: OrderStatus

  @column()
  declare paymentId: string | null

  @column()
  declare shippingAddress: string | null

  @column()
  declare totalInCents: number
}
```

### Step 4 — Use it

```typescript
const order = await Order.create({
  status: OrderStatus.Draft,
  totalInCents: 5000,
})

// Check if transition is allowed
order.stateMachine('status').canTransitionTo(OrderStatus.Pending) // true
order.stateMachine('status').canTransitionTo(OrderStatus.Shipped) // false

// List allowed targets from current state
order.stateMachine('status').allowedTransitions() // [OrderStatus.Pending, OrderStatus.Cancelled]

// Perform transition (validates → saves → runs side effects)
await order.stateMachine('status').transitionTo(OrderStatus.Pending)

// Current state
order.status // OrderStatus.Pending

// Check current state
order.stateMachine('status').is(OrderStatus.Pending)    // true
order.stateMachine('status').isAny([OrderStatus.Pending, OrderStatus.Paid]) // true
```

---

## Memory Leak Prevention

This implementation is designed to avoid common leak patterns:

| Concern | How it's handled |
|---|---|
| **No event emitter accumulation** | State machines do not register EventEmitter listeners. Side effects are plain async functions stored in static config, not per-instance listeners. |
| **No per-instance closure capture** | The `transitions`, `guards`, and `afterTransition` maps are defined as class properties (shared prototype), not created in constructors. |
| **No model reference retention** | `stateMachine('status')` returns a lightweight proxy that holds a reference to the model only for the duration of the call chain. It does not persist between calls. |
| **Static transition maps** | Transition definitions live on the class, not on instances. They are allocated once at import time. |
| **No WeakMap/Map accumulation** | No global registry of model instances. Each model holds its own state as a plain column value. |

---

## State-specific Behavior

Add helper methods on the model that read the current state:

```typescript
export default class Order extends compose(BaseModel, HasStateMachine) {
  // ...columns...

  get isEditable(): boolean {
    return this.status === OrderStatus.Draft
  }

  get isCancellable(): boolean {
    return this.stateMachine('status').canTransitionTo(OrderStatus.Cancelled)
  }

  get isPaid(): boolean {
    return [OrderStatus.Paid, OrderStatus.Shipped, OrderStatus.Completed]
      .includes(this.status)
  }

  async submit() {
    await this.stateMachine('status').transitionTo(OrderStatus.Pending)
  }

  async markPaid(paymentId: string) {
    this.paymentId = paymentId
    await this.save()
    await this.stateMachine('status').transitionTo(OrderStatus.Paid)
  }
}
```

---

## Transition History (Optional)

If you need an audit trail, create a `state_transitions` table:

```typescript
// database/migrations/xxxx_create_state_transitions_table.ts
export default class extends BaseSchema {
  protected tableName = 'state_transitions'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id')
      table.string('model_type').notNullable()
      table.integer('model_id').unsigned().notNullable()
      table.string('field').notNullable()
      table.string('from').notNullable()
      table.string('to').notNullable()
      table.json('metadata').nullable()
      table.timestamp('created_at', { useTz: true }).defaultTo(this.now())

      table.index(['model_type', 'model_id'])
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
```

Enable logging in the state machine:

```typescript
export class OrderStateMachine extends StateMachine<Order, OrderStatus> {
  logTransitions = true      // enable audit trail
  modelType = 'Order'        // stored in model_type column
  // ...
}
```

---

## Testing State Machines

```typescript
import { test } from '@japa/runner'
import Order from '#models/order'
import { OrderStatus } from '#enums/order_status'
import testUtils from '@adonisjs/core/services/test_utils'

test.group('OrderStateMachine', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('allows draft → pending transition', async ({ assert }) => {
    const order = await Order.create({ status: OrderStatus.Draft, totalInCents: 1000 })
    await order.stateMachine('status').transitionTo(OrderStatus.Pending)

    assert.equal(order.status, OrderStatus.Pending)
  })

  test('prevents draft → shipped transition', async ({ assert }) => {
    const order = await Order.create({ status: OrderStatus.Draft, totalInCents: 1000 })

    await assert.rejects(
      () => order.stateMachine('status').transitionTo(OrderStatus.Shipped),
      'Cannot transition from "draft" to "shipped"'
    )
  })

  test('runs guard before transition', async ({ assert }) => {
    const order = await Order.create({
      status: OrderStatus.Pending,
      totalInCents: 1000,
      paymentId: null,
    })

    await assert.rejects(
      () => order.stateMachine('status').transitionTo(OrderStatus.Paid),
      'Cannot mark as paid without a payment ID'
    )
  })

  test('terminal states have no outgoing transitions', ({ assert }) => {
    const order = new Order()
    order.status = OrderStatus.Completed

    assert.deepEqual(order.stateMachine('status').allowedTransitions(), [])
  })
})
```

---

## Directory Structure

```
app/
├── enums/
│   └── order_status.ts
├── lib/
│   ├── state_machine.ts        # base class
│   └── has_state_machine.ts    # Lucid mixin
├── models/
│   └── order.ts
└── state_machines/
    └── order_state_machine.ts
```

---

## Summary

| Concept | Implementation |
|---|---|
| States | TypeScript enum values |
| Allowed transitions | Static map on state machine class (`{ from → to[] }`) |
| Guards | Async functions keyed by `'from→to'`, throw on failure |
| Side effects | Async functions keyed by `'from→to'`, run after save |
| Model integration | `HasStateMachine` mixin + `stateMachines` static property |
| Memory safety | No EventEmitter, no per-instance closures, static maps |
| Audit trail | Optional `state_transitions` table with `logTransitions = true` |
| Testing | Standard Japa `assert.rejects()` for invalid transitions |

**Use for domain models with lifecycle states. Use simple enums for basic status fields.**
