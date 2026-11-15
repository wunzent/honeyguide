---
name: adonisjs-enums
description: TypeScript string enums with labels and business logic for AdonisJS v6. Use when working with enums, status values, fixed sets of options, or when the user mentions enums, status enums, enum cases, or finite value sets. Also use when typing Lucid model columns or validating enum fields with VineJS.
---

# AdonisJS Enums

Enums provide type-safe, finite sets of values across the entire stack — models, validators, actions, and controllers.

**Related guides:**

- [DTOs](../adonisjs-dtos/SKILL.md) - DTO properties typed as enums
- [Actions](../adonisjs-actions/SKILL.md) - Business logic that references enums
- [Lucid Models](https://lucid.adonisjs.com/docs/models) - Typing model columns with enums
- [VineJS Enum](https://vinejs.dev/docs/types/enum) - Validating enum values in request payloads

---

## Always Use String Enums

**Always use string enums** — not numeric enums, not `const` enums, not plain union types.

String values are human-readable in the database, in logs, and over the wire. Numeric enums are opaque; `const` enums have ESM/isolation issues.

```ts
// ✅ CORRECT — string enum
export enum OrderStatus {
  Pending    = 'pending',
  Processing = 'processing',
  Completed  = 'completed',
  Cancelled  = 'cancelled',
}

// ❌ INCORRECT — numeric enum (opaque values in DB)
export enum OrderStatus {
  Pending,     // 0
  Processing,  // 1
  Completed,   // 2
}

// ❌ INCORRECT — const enum (breaks with ESM/isolated modules)
export const enum OrderStatus {
  Pending = 'pending',
}

// ❌ AVOID for shared enums — union types lack runtime values
type OrderStatus = 'pending' | 'processing' | 'completed'
```

---

## File Naming & Location

AdonisJS v6 uses **snake_case** for all files.

```
app/enums/
├── order_status.ts
├── payment_method.ts
├── user_role.ts
└── queue.ts
```

```ts
// ✅ CORRECT
// app/enums/order_status.ts
export enum OrderStatus { ... }

// ❌ INCORRECT — PascalCase filename
// app/Enums/OrderStatus.ts
```

---

## Basic Enum

```ts
// app/enums/order_status.ts
export enum OrderStatus {
  Pending    = 'pending',
  Processing = 'processing',
  Completed  = 'completed',
  Cancelled  = 'cancelled',
}
```

---

## Enum with Labels

Add a `label()` method for human-readable display text (UI selects, notifications, etc.):

```ts
// app/enums/order_status.ts
export enum OrderStatus {
  Pending    = 'pending',
  Processing = 'processing',
  Completed  = 'completed',
  Cancelled  = 'cancelled',
}

export const OrderStatusLabel: Record<OrderStatus, string> = {
  [OrderStatus.Pending]:    'Pending',
  [OrderStatus.Processing]: 'Processing',
  [OrderStatus.Completed]:  'Completed',
  [OrderStatus.Cancelled]:  'Cancelled',
}

// Helper — get label for a given value
export function getOrderStatusLabel(status: OrderStatus): string {
  return OrderStatusLabel[status]
}

// Helper — get all values as dropdown options
export function orderStatusOptions(): Array<{ value: string; label: string }> {
  return Object.values(OrderStatus).map((value) => ({
    value,
    label: OrderStatusLabel[value],
  }))
}
```

**Usage:**

```ts
getOrderStatusLabel(OrderStatus.Completed)  // 'Completed'
orderStatusOptions()
// [{ value: 'pending', label: 'Pending' }, ...]
```

---

## Enum with Business Logic

Enums can carry domain behaviour directly — keeps switch statements out of your actions:

```ts
// app/enums/payment_method.ts
export enum PaymentMethod {
  Stripe       = 'stripe',
  PayPal       = 'paypal',
  BankTransfer = 'bank_transfer',
}

export const PaymentMethodLabel: Record<PaymentMethod, string> = {
  [PaymentMethod.Stripe]:       'Credit / Debit Card',
  [PaymentMethod.PayPal]:       'PayPal',
  [PaymentMethod.BankTransfer]: 'Bank Transfer',
}

/**
 * Returns the processing fee in minor currency units (e.g. cents).
 */
export function processingFee(method: PaymentMethod, amount: number): number {
  switch (method) {
    case PaymentMethod.Stripe:
      return Math.round(amount * 0.029 + 30)
    case PaymentMethod.PayPal:
      return Math.round(amount * 0.034 + 30)
    case PaymentMethod.BankTransfer:
      return 0
  }
}

export function supportsRefunds(method: PaymentMethod): boolean {
  return method === PaymentMethod.Stripe || method === PaymentMethod.PayPal
}
```

For richer OO behaviour on a per-value basis, a small class with static factories or a plain `Map<Enum, Config>` are both clean alternatives to open-ended switch statements.

---

## Enum with Colour / Icon Metadata

For UI-heavy applications, pair metadata records alongside the enum:

```ts
// app/enums/order_status.ts
export enum OrderStatus {
  Pending    = 'pending',
  Processing = 'processing',
  Completed  = 'completed',
  Cancelled  = 'cancelled',
}

export const OrderStatusColor: Record<OrderStatus, string> = {
  [OrderStatus.Pending]:    'yellow',
  [OrderStatus.Processing]: 'blue',
  [OrderStatus.Completed]:  'green',
  [OrderStatus.Cancelled]:  'red',
}

export const OrderStatusIcon: Record<OrderStatus, string> = {
  [OrderStatus.Pending]:    'clock',
  [OrderStatus.Processing]: 'refresh',
  [OrderStatus.Completed]:  'check-circle',
  [OrderStatus.Cancelled]:  'x-circle',
}
```

---

## Usage in Lucid Models

Type the column property with the enum. Lucid stores and reads the raw string value — no special cast is needed for string enums.

```ts
// app/models/order.ts
import { BaseModel, column } from '@adonisjs/lucid/orm'
import { OrderStatus } from '#enums/order_status'

export default class Order extends BaseModel {
  @column({ isPrimary: true })
  declare id: number

  @column()
  declare status: OrderStatus

  @column()
  declare paymentMethod: PaymentMethod
}
```

**For enum columns in migrations**, use `Object.values()` to derive the allowed list at the database level:

```ts
// database/migrations/TIMESTAMP_create_orders_table.ts
import { BaseSchema } from '@adonisjs/lucid/schema'
import { OrderStatus } from '#enums/order_status'

export default class extends BaseSchema {
  protected tableName = 'orders'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id')
      table.enum('status', Object.values(OrderStatus)).notNullable().defaultTo(OrderStatus.Pending)
      table.timestamps(true)
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
```

---

## Usage in VineJS Validators

Pass the TypeScript enum directly to `vine.enum()`:

```ts
// app/validators/order_validator.ts
import vine from '@vinejs/vine'
import { OrderStatus } from '#enums/order_status'
import { PaymentMethod } from '#enums/payment_method'

export const createOrderValidator = vine.compile(
  vine.object({
    status:        vine.enum(OrderStatus),
    paymentMethod: vine.enum(PaymentMethod),
    notes:         vine.string().optional(),
  })
)

export const updateOrderValidator = vine.compile(
  vine.object({
    status: vine.enum(OrderStatus).optional(),
  })
)
```

VineJS infers the output type as the enum itself, so `payload.status` is typed as `OrderStatus` — no manual cast needed.

---

## Usage in DTOs

```ts
// app/dtos/create_order_dto.ts
import { OrderStatus } from '#enums/order_status'
import { PaymentMethod } from '#enums/payment_method'

export interface CreateOrderDto {
  customerEmail: string
  status: OrderStatus
  paymentMethod: PaymentMethod
  notes?: string
}
```

---

## Usage in Actions

```ts
// app/actions/order/cancel_order_action.ts
import Order from '#models/order'
import { OrderStatus } from '#enums/order_status'
import OrderException from '#exceptions/order_exception'

export default class CancelOrderAction {
  async handle(order: Order): Promise<Order> {
    if (order.status !== OrderStatus.Pending && order.status !== OrderStatus.Processing) {
      throw OrderException.cannotCancel(order)
    }

    order.status = OrderStatus.Cancelled
    await order.save()
    return order
  }
}
```

---

## Common Patterns

### Comparing Enum Values

```ts
// Direct equality
if (order.status === OrderStatus.Completed) { ... }

// Membership check
const cancellable = [OrderStatus.Pending, OrderStatus.Processing]
if (cancellable.includes(order.status)) { ... }
```

### Match / Switch with Exhaustiveness

```ts
function statusMessage(status: OrderStatus): string {
  switch (status) {
    case OrderStatus.Pending:    return 'Your order is being prepared.'
    case OrderStatus.Processing: return 'Your order is on its way.'
    case OrderStatus.Completed:  return 'Your order has arrived.'
    case OrderStatus.Cancelled:  return 'Your order was cancelled.'
    default:
      // TypeScript exhaustiveness check
      status satisfies never
      return ''
  }
}
```

### Queue Enum

A common pattern — centralise queue names to avoid magic strings throughout jobs:

```ts
// app/enums/queue.ts
export enum Queue {
  Default       = 'default',
  Emails        = 'emails',
  Notifications = 'notifications',
  Processing    = 'processing',
}
```

```ts
// Usage in a job dispatch
import { Queue } from '#enums/queue'
await someQueue.dispatch(job, { queue: Queue.Emails })
```

---

## Directory Structure

```
app/enums/
├── order_status.ts
├── payment_method.ts
├── payment_provider.ts
├── user_role.ts
└── queue.ts
```

Group all enums flat under `app/enums/`. Sub-folders are only needed once the count becomes unwieldy.

---

## Testing Enums

Enum logic (label helpers, fee calculations) is easy to test in isolation:

```ts
// tests/unit/enums/order_status.spec.ts
import { test } from '@japa/runner'
import { OrderStatus, getOrderStatusLabel, orderStatusOptions } from '#enums/order_status'

test.group('OrderStatus', () => {
  test('returns the correct label', ({ assert }) => {
    assert.equal(getOrderStatusLabel(OrderStatus.Completed), 'Completed')
    assert.equal(getOrderStatusLabel(OrderStatus.Cancelled), 'Cancelled')
  })

  test('returns dropdown options for all values', ({ assert }) => {
    const options = orderStatusOptions()
    assert.lengthOf(options, Object.values(OrderStatus).length)
    assert.deepInclude(options, { value: 'pending', label: 'Pending' })
  })
})
```

---

## When to Use Enums vs Plain Union Types

**Use string enums when:**

- The value persists to the database
- The value is validated in request payloads
- The value is compared in business logic across multiple files
- You need label, colour, or icon metadata alongside the value

**Use a plain union type when:**

- The set of values is local to a single function or type
- No runtime iteration is needed
- You're describing a pure TypeScript contract with no DB or validation surface

```ts
// Fine as a union — never hits the DB or a validator
type SortDirection = 'asc' | 'desc'
```

---

## Summary

**String enums provide:**

- Type safety and IDE autocomplete across the full stack
- Readable values in the database and logs
- A single source of truth for label, colour, and icon metadata
- Direct compatibility with `vine.enum()` and Lucid column types
- Exhaustiveness checking in switch statements

**Always use string-backed enums** — never numeric enums, never `const` enums for shared code.
