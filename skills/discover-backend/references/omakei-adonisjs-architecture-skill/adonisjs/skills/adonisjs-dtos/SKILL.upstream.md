---
name: adonisjs-dtos
description: Data Transfer Objects for AdonisJS v6. Plain TypeScript interfaces and classes used to move validated data between the HTTP layer, actions, and services. Use when handling request payloads, structured data transfer, or when the user mentions DTOs, data objects, payload types, or typed interfaces for domain operations.
---

# AdonisJS DTOs

**Never pass loose primitive arguments between layers.** Always wrap related data in a typed DTO.

**Related guides:**

- [Actions](../adonisjs-actions/SKILL.md) - Actions receive DTOs as their primary input
- [Controllers](../adonisjs-controllers/SKILL.md) - Controllers build DTOs from validated request payloads
- [Enums](../adonisjs-enums/SKILL.md) - Enum types used as DTO properties
- [VineJS Validation](https://docs.adonisjs.com/guides/basics/validation) - Validation layer that produces the raw data a DTO is built from

---

## Philosophy

DTOs provide:

- **Type safety** and IDE autocomplete across all layers
- **Clear contracts** between HTTP, domain, and data layers
- **Normalisation** — format and clean data at the boundary, once
- **Composability** — nest DTOs to model complex hierarchies
- **Testability** — actions can be tested in isolation with hand-built DTOs

---

## AdonisJS DTO Approach

Unlike Laravel (which uses Spatie Laravel Data), AdonisJS has no first-party DTO package. The community pattern is **plain TypeScript** — interfaces for read-only payload shapes, and plain classes when construction logic or normalisation is needed.

There is no magic casting. You build the DTO explicitly from validated VineJS output (or from a model/external source), which keeps transformation explicit and traceable.

---

## Two DTO Styles

### Style 1 — Interface (preferred for simple payloads)

Use a plain `interface` when the DTO is purely a structural contract with no construction logic.

```ts
// app/dtos/order/create_order_dto.ts
import { OrderStatus } from '#enums/order_status'
import { PaymentMethod } from '#enums/payment_method'

export interface CreateOrderDto {
  customerEmail: string
  notes: string | null
  status: OrderStatus
  paymentMethod: PaymentMethod
  items: OrderItemDto[]
  shippingAddress: AddressDto
}

export interface OrderItemDto {
  productId: number
  quantity: number
  price: number
}

export interface AddressDto {
  line1: string
  line2: string | null
  city: string
  postcode: string
  countryCode: string
}
```

### Style 2 — Class (use when normalisation or static factories are needed)

Use a `class` when the DTO needs to normalise data on construction (e.g. trim, lowercase) or when you want named static factory methods.

```ts
// app/dtos/order/create_order_dto.ts
import { OrderStatus } from '#enums/order_status'
import { PaymentMethod } from '#enums/payment_method'

export class CreateOrderDto {
  readonly customerEmail: string
  readonly notes: string | null
  readonly status: OrderStatus
  readonly paymentMethod: PaymentMethod
  readonly items: OrderItemDto[]

  constructor(data: {
    customerEmail: string
    notes?: string | null
    status: OrderStatus
    paymentMethod: PaymentMethod
    items: OrderItemDto[]
  }) {
    // Normalise at construction time
    this.customerEmail = data.customerEmail.trim().toLowerCase()
    this.notes = data.notes?.trim() ?? null
    this.status = data.status
    this.paymentMethod = data.paymentMethod
    this.items = data.items
  }
}
```

**Rule of thumb:** Start with an `interface`. Promote to a `class` only when you need normalisation, static factories, or methods.

---

## File Naming & Location

```
app/dtos/
├── order/
│   ├── create_order_dto.ts
│   ├── update_order_dto.ts
│   └── order_item_dto.ts
├── user/
│   ├── create_user_dto.ts
│   └── update_user_profile_dto.ts
└── shared/
    └── address_dto.ts
```

AdonisJS v6 uses **snake_case** for all filenames. Group DTOs by domain entity, mirroring `app/actions/`.

```ts
// ✅ CORRECT
// app/dtos/order/create_order_dto.ts
export interface CreateOrderDto { ... }

// ❌ INCORRECT — PascalCase filename
// app/Dtos/CreateOrderData.ts
```

---

## Naming Conventions

| DTO Type         | Pattern                   | Examples                                         |
|------------------|---------------------------|--------------------------------------------------|
| Action input     | `{Action}{Entity}Dto`     | `CreateOrderDto`, `UpdateUserDto`                |
| Nested / shared  | `{Descriptor}{Entity}Dto` | `OrderItemDto`, `ShippingAddressDto`             |
| Response shape   | `{Entity}Dto`             | `OrderDto`, `UserDto` (used for Inertia/API out) |

---

## Building DTOs from Validated Payloads

VineJS validators produce a typed output object. Build your DTO explicitly from that output in the controller before passing to the action.

```ts
// app/validators/order_validator.ts
import vine from '@vinejs/vine'
import { OrderStatus } from '#enums/order_status'
import { PaymentMethod } from '#enums/payment_method'

export const createOrderValidator = vine.compile(
  vine.object({
    customerEmail: vine.string().email(),
    notes:         vine.string().optional(),
    status:        vine.enum(OrderStatus),
    paymentMethod: vine.enum(PaymentMethod),
    items: vine.array(
      vine.object({
        productId: vine.number().positive(),
        quantity:  vine.number().positive(),
        price:     vine.number().positive(),
      })
    ),
  })
)
```

```ts
// app/controllers/orders_controller.ts
import { inject } from '@adonisjs/core'
import type { HttpContext } from '@adonisjs/core/http'
import { createOrderValidator } from '#validators/order_validator'
import CreateOrderAction from '#actions/order/create_order_action'
import type { CreateOrderDto } from '#dtos/order/create_order_dto'

@inject()
export default class OrdersController {
  constructor(private createOrder: CreateOrderAction) {}

  async store({ request, auth, response }: HttpContext) {
    const payload = await request.validateUsing(createOrderValidator)

    // Build the DTO explicitly from validated data
    const dto: CreateOrderDto = {
      customerEmail: payload.customerEmail,
      notes:         payload.notes ?? null,
      status:        payload.status,
      paymentMethod: payload.paymentMethod,
      items:         payload.items,
    }

    const order = await this.createOrder.handle(auth.user!, dto)
    return response.created({ data: order })
  }
}
```

---

## Static Factory Methods on DTO Classes

For class-based DTOs, add named `from*` static methods to encapsulate construction from different sources. This keeps the controller slim and makes the mapping testable.

**Method naming:** `from{SourceType}` — e.g. `fromRequest`, `fromModel`, `fromWebhook`

```ts
// app/dtos/order/create_order_dto.ts
import type { InferInput } from '@vinejs/vine'
import type { createOrderValidator } from '#validators/order_validator'
import { OrderStatus } from '#enums/order_status'

type ValidatedPayload = InferInput<typeof createOrderValidator>

export class CreateOrderDto {
  readonly customerEmail: string
  readonly notes: string | null
  readonly status: OrderStatus
  readonly items: OrderItemDto[]

  constructor(data: {
    customerEmail: string
    notes?: string | null
    status: OrderStatus
    items: OrderItemDto[]
  }) {
    this.customerEmail = data.customerEmail.trim().toLowerCase()
    this.notes         = data.notes?.trim() ?? null
    this.status        = data.status
    this.items         = data.items
  }

  static fromValidatedPayload(payload: ValidatedPayload): CreateOrderDto {
    return new CreateOrderDto({
      customerEmail: payload.customerEmail,
      notes:         payload.notes,
      status:        payload.status,
      items:         payload.items,
    })
  }
}
```

```ts
// In the controller — single-line construction
const dto = CreateOrderDto.fromValidatedPayload(payload)
const order = await this.createOrder.handle(auth.user!, dto)
```

**When to add static factories:**

- The controller builds the same DTO from multiple routes or sources
- Complex field renaming/mapping is needed (e.g. external webhook payloads)
- You want the mapping tested in isolation, separate from the action

---

## Normalisation in DTO Constructors

Apply data cleaning in the DTO constructor — not in actions, not in validators.

```ts
export class CreateUserDto {
  readonly email: string
  readonly phone: string | null
  readonly postcode: string | null

  constructor(data: {
    email: string
    phone?: string | null
    postcode?: string | null
  }) {
    // Normalise at the boundary — once, in one place
    this.email    = data.email.trim().toLowerCase()
    this.phone    = data.phone ? formatPhone(data.phone) : null
    this.postcode = data.postcode ? data.postcode.trim().toUpperCase() : null
  }
}
```

Keep normalisation helpers in `app/dtos/formatters/`:

```ts
// app/dtos/formatters/format_phone.ts
export function formatPhone(raw: string): string {
  return raw.replace(/\s+/g, '').replace(/^0/, '+44')
}
```

---

## Nested DTOs

Model complex hierarchies by composing DTOs:

```ts
// app/dtos/order/create_order_dto.ts
import type { AddressDto } from '#dtos/shared/address_dto'
import type { OrderItemDto } from '#dtos/order/order_item_dto'

export interface CreateOrderDto {
  customerEmail: string
  notes: string | null
  items: OrderItemDto[]
  shippingAddress: AddressDto
  billingAddress: AddressDto
}
```

```ts
// app/dtos/shared/address_dto.ts
export interface AddressDto {
  line1:       string
  line2:       string | null
  city:        string
  postcode:    string
  countryCode: string
}
```

---

## Response DTOs (Inertia / API serialisation)

When using Inertia.js or returning typed JSON responses, define a separate *response* DTO that represents the serialised shape the frontend receives. This keeps Lucid model internals (`.save()`, `.related()`, etc.) out of the frontend type.

```ts
// app/dtos/order/order_dto.ts
import { OrderStatus } from '#enums/order_status'

export interface OrderDto {
  id: number
  customerEmail: string
  status: OrderStatus
  total: number
  items: OrderItemDto[]
  createdAt: string
}

export interface OrderItemDto {
  id: number
  productId: number
  quantity: number
  price: number
}
```

Services return Lucid models when the default serialisation is acceptable. When the response shape differs significantly (computed fields, hidden internals, nested aggregates), the service may return a plain DTO instead — or the controller builds one from the returned model.

Build the response DTO from the Lucid model in the controller or a dedicated transformer:

> **AdonisJS v7 note:** v7 introduces first-class transformer support. When upgrading, prefer native transformers over hand-rolled transformer functions in `app/dtos/transformers/`.

```ts
// In controller
async show({ params, response }: HttpContext) {
  const order = await Order.query().where('id', params.id).preload('items').firstOrFail()

  const dto: OrderDto = {
    id:            order.id,
    customerEmail: order.customerEmail,
    status:        order.status,
    total:         order.total,
    items:         order.items.map((i) => ({
      id:        i.id,
      productId: i.productId,
      quantity:  i.quantity,
      price:     i.price,
    })),
    createdAt: order.createdAt.toISO()!,
  }

  return response.json({ data: dto })
}
```

For repeated or complex serialisation logic, extract to a dedicated transformer file:

```ts
// app/dtos/transformers/order_transformer.ts
import Order from '#models/order'
import type { OrderDto } from '#dtos/order/order_dto'

export function toOrderDto(order: Order): OrderDto {
  return {
    id:            order.id,
    customerEmail: order.customerEmail,
    status:        order.status,
    total:         order.total,
    items:         order.items.map((i) => ({
      id:        i.id,
      productId: i.productId,
      quantity:  i.quantity,
      price:     i.price,
    })),
    createdAt: order.createdAt.toISO()!,
  }
}
```

---

## Usage in Actions

Actions receive DTOs as their primary input — not raw request data, not loose arguments:

```ts
// app/actions/order/create_order_action.ts
import { inject } from '@adonisjs/core'
import db from '@adonisjs/lucid/services/db'
import User from '#models/user'
import Order from '#models/order'
import type { CreateOrderDto } from '#dtos/order/create_order_dto'

@inject()
export default class CreateOrderAction {
  async handle(user: User, dto: CreateOrderDto): Promise<Order> {
    return db.transaction(async (trx) => {
      const order = new Order()
      order.userId        = user.id
      order.customerEmail = dto.customerEmail
      order.notes         = dto.notes
      order.status        = dto.status
      order.useTransaction(trx)
      await order.save()

      await order.related('items').createMany(dto.items)
      await order.load('items')
      return order
    })
  }
}
```

---

## Testing DTOs

### Test class-based DTOs for normalisation

```ts
// tests/unit/dtos/create_order_dto.spec.ts
import { test } from '@japa/runner'
import { CreateOrderDto } from '#dtos/order/create_order_dto'
import { OrderStatus } from '#enums/order_status'
import { PaymentMethod } from '#enums/payment_method'

test.group('CreateOrderDto', () => {
  test('lowercases and trims customer email', ({ assert }) => {
    const dto = new CreateOrderDto({
      customerEmail: '  TEST@EXAMPLE.COM  ',
      status:        OrderStatus.Pending,
      paymentMethod: PaymentMethod.Stripe,
      items:         [],
    })

    assert.equal(dto.customerEmail, 'test@example.com')
  })

  test('sets notes to null when omitted', ({ assert }) => {
    const dto = new CreateOrderDto({
      customerEmail: 'x@example.com',
      status:        OrderStatus.Pending,
      paymentMethod: PaymentMethod.Stripe,
      items:         [],
    })

    assert.isNull(dto.notes)
  })
})
```

### Test actions using hand-built DTOs

```ts
// tests/unit/actions/order/create_order_action.spec.ts
import { test } from '@japa/runner'
import app from '@adonisjs/core/services/app'
import CreateOrderAction from '#actions/order/create_order_action'
import { OrderStatus } from '#enums/order_status'
import { PaymentMethod } from '#enums/payment_method'
import UserFactory from '#database/factories/user_factory'

test.group('CreateOrderAction', (group) => {
  group.each.setup(() => testUtils.db().withGlobalTransaction())

  test('creates an order from a DTO', async ({ assert }) => {
    const user = await UserFactory.create()

    const dto = {
      customerEmail: 'buyer@example.com',
      notes:         null,
      status:        OrderStatus.Pending,
      paymentMethod: PaymentMethod.Stripe,
      items:         [{ productId: 1, quantity: 2, price: 1999 }],
    }

    const action = await app.container.make(CreateOrderAction)
    const order  = await action.handle(user, dto)

    assert.equal(order.customerEmail, 'buyer@example.com')
    assert.equal(order.status, OrderStatus.Pending)
    assert.lengthOf(order.items, 1)
  })
})
```

---

## Common Mistakes

### ❌ Passing Raw VineJS Payload Directly to an Action

```ts
// BAD — raw payload leaks into the domain layer
async store({ request, auth, response }: HttpContext) {
  const payload = await request.validateUsing(createOrderValidator)
  const order = await this.createOrder.handle(auth.user!, payload) // ← raw validator output
  return response.created({ data: order })
}
```

### ✅ Build a DTO First

```ts
// GOOD — explicit, traceable contract
async store({ request, auth, response }: HttpContext) {
  const payload = await request.validateUsing(createOrderValidator)
  const dto     = CreateOrderDto.fromValidatedPayload(payload)
  const order   = await this.createOrder.handle(auth.user!, dto)
  return response.created({ data: order })
}
```

---

### ❌ Many Loose Parameters on an Action

```ts
// BAD — hard to read, easy to pass arguments in wrong order
async handle(
  user: User,
  email: string,
  notes: string | null,
  status: string,
  items: any[]
): Promise<Order> { ... }
```

### ✅ Single Typed DTO Parameter

```ts
// GOOD — self-documenting, refactor-safe
async handle(user: User, dto: CreateOrderDto): Promise<Order> { ... }
```

---

### ❌ Normalisation Spread Across Multiple Layers

```ts
// BAD — email formatted in the action, not at the boundary
async handle(user: User, dto: CreateOrderDto): Promise<Order> {
  const email = dto.customerEmail.trim().toLowerCase() // should not be here
  ...
}
```

### ✅ Normalise Once, at the DTO Boundary

```ts
// GOOD — constructor normalises; action receives clean data
export class CreateOrderDto {
  readonly customerEmail: string

  constructor(data: { customerEmail: string, ... }) {
    this.customerEmail = data.customerEmail.trim().toLowerCase()
    ...
  }
}
```

---

## Directory Structure

```
app/dtos/
├── order/
│   ├── create_order_dto.ts
│   ├── update_order_dto.ts
│   └── order_item_dto.ts
├── user/
│   ├── create_user_dto.ts
│   └── update_user_profile_dto.ts
├── shared/
│   └── address_dto.ts
├── formatters/
│   ├── format_email.ts
│   ├── format_phone.ts
│   └── format_postcode.ts
└── transformers/
    ├── order_transformer.ts
    └── user_transformer.ts
```

---

## Summary

**DTOs are the typed contract between HTTP and domain.**

1. Define an `interface` (simple) or `class` (normalisation/factories) per action input
2. Build the DTO explicitly from VineJS validated output in the controller
3. Normalise data (trim, lowercase, format) in the DTO constructor — once, at the boundary
4. Pass the DTO to the action — never raw `request.all()` or loose primitives
5. Use response DTOs to serialise Lucid models into clean frontend-facing shapes

**Never pass multiple primitive values between layers — always wrap in a DTO.**
