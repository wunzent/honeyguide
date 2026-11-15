---
name: adonisjs-models
description: Lucid ORM model patterns and database layer. Use when working with models, database entities, Lucid ORM, or when user mentions models, lucid, relationships, column types, hooks, database entities, AdonisJS models.
---

# AdonisJS Models

Models represent database tables and domain entities using AdonisJS's Lucid ORM.

**Related guides:**

- [Query Builders](../adonisjs-query-builder/SKILL.md) - Composable query scopes and query objects
- [State Machines](../adonisjs-state-machine/SKILL.md) - Complex model lifecycle and state transitions
- [Validation](../adonisjs-validation/SKILL.md) - VineJS input validation before passing data to models
- [Exceptions](../adonisjs-exceptions/SKILL.md) - Domain exceptions for business rule violations
- Services / Actions - Business logic belongs here, not in models

## Philosophy

Models should:

- Define **columns and their types** via decorators
- Define **relationships** between models
- Define **computed properties** (accessors)
- Contain **simple helper methods** (status checks, etc.)
- Use **hooks** for lifecycle side effects
- **NOT contain business logic** (that belongs in Services/Actions)

---

## Basic Model Structure

```typescript
import { DateTime } from 'luxon'
import { BaseModel, column, belongsTo, hasMany } from '@adonisjs/lucid/orm'
import type { BelongsTo, HasMany } from '@adonisjs/lucid/types/relations'
import User from '#models/user'
import OrderItem from '#models/order_item'
import { OrderStatus } from '#enums/order_status'

export default class Order extends BaseModel {
  @column({ isPrimary: true })
  declare id: number

  @column()
  declare userId: number

  @column()
  declare status: OrderStatus

  @column()
  declare total: number

  @column.dateTime({ autoCreate: true })
  declare createdAt: DateTime

  @column.dateTime({ autoCreate: true, autoUpdate: true })
  declare updatedAt: DateTime

  // Relationships
  @belongsTo(() => User)
  declare user: BelongsTo<typeof User>

  @hasMany(() => OrderItem)
  declare items: HasMany<typeof OrderItem>
}
```

---

## Column Decorators

**Define columns for type safety and serialisation:**

```typescript
@column({ isPrimary: true })
declare id: number

@column()
declare name: string

@column()
declare total: number

@column()
declare isPaid: boolean

@column()
declare status: OrderStatus  // Enum

@column({
  prepare: (value: object) => JSON.stringify(value),
  consume: (value: string) => JSON.parse(value),
})
declare metadata: OrderMetadata  // JSON

@column.dateTime({ autoCreate: true })
declare createdAt: DateTime

@column.dateTime({ autoCreate: true, autoUpdate: true })
declare updatedAt: DateTime

@column.date()
declare dueDate: DateTime

@column.dateTime()
declare completedAt: DateTime | null
```

**Column options:**

- `isPrimary: true` — marks as primary key
- `serializeAs: null` — excludes from serialisation (e.g. passwords)
- `serializeAs: 'snake_case_name'` — custom serialised key name
- `prepare(value)` — transform before writing to DB
- `consume(value)` — transform after reading from DB

---

## Relationships

### BelongsTo

```typescript
@column()
declare userId: number

@belongsTo(() => User)
declare user: BelongsTo<typeof User>

// With custom foreign key
@belongsTo(() => Customer, { foreignKey: 'customerId' })
declare customer: BelongsTo<typeof Customer>
```

### HasMany

```typescript
@hasMany(() => Order)
declare orders: HasMany<typeof Order>

@hasMany(() => OrderItem)
declare items: HasMany<typeof OrderItem>
```

### HasOne

```typescript
@hasOne(() => UserProfile)
declare profile: HasOne<typeof UserProfile>
```

### BelongsToMany (Many-to-Many)

```typescript
@manyToMany(() => Role, {
  pivotTable: 'user_roles',
  pivotTimestamps: true,
  pivotColumns: ['assigned_at'],
})
declare roles: ManyToMany<typeof Role>
```

### HasManyThrough

```typescript
@hasManyThrough([() => Deployment, () => Environment])
declare deployments: HasManyThrough<typeof Deployment>
```

---

## Computed Properties (Accessors)

```typescript
import { computed } from '@adonisjs/lucid/orm'

export default class User extends BaseModel {
  @column()
  declare firstName: string

  @column()
  declare lastName: string

  @computed()
  get fullName(): string {
    return `${this.firstName} ${this.lastName}`
  }
}

// Usage
const user = await User.find(1)
user.fullName // "John Doe"
```

> **Note:** Computed properties are included in serialisation by default. Use `serializeAs: null` on `@column` to hide sensitive columns.

---

## Model Hooks

**For model lifecycle side effects:**

```typescript
import { BaseModel, column, beforeCreate, afterCreate, beforeSave, afterSave } from '@adonisjs/lucid/orm'
import { cuid } from '@adonisjs/core/helpers'

export default class Order extends BaseModel {
  @column({ isPrimary: true })
  declare id: number

  @column()
  declare uuid: string

  @beforeCreate()
  static assignUuid(order: Order) {
    order.uuid = cuid()
  }

  @afterCreate()
  static async dispatchCreatedEvent(order: Order) {
    // Dispatch event, queue job, etc.
  }

  @beforeSave()
  static async hashPassword(user: User) {
    if (user.$dirty.password) {
      user.password = await hash.make(user.password)
    }
  }

  @afterSave()
  static async syncCache(order: Order) {
    // Update cache, etc.
  }

  @beforeDelete()
  static async cleanupRelated(order: Order) {
    // Cleanup before hard delete
  }
}
```

**Available hooks:**

- `@beforeCreate()` / `@afterCreate()`
- `@beforeSave()` / `@afterSave()` — runs on both create and update
- `@beforeUpdate()` / `@afterUpdate()`
- `@beforeDelete()` / `@afterDelete()`
- `@beforeFind()` / `@afterFind()`
- `@beforeFetch()` / `@afterFetch()`
- `@beforePaginate()` / `@afterPaginate()`

---

## Helper Methods

**Simple status/predicate methods are acceptable on models:**

```typescript
export default class Order extends BaseModel {
  @column()
  declare status: OrderStatus

  isPending(): boolean {
    return this.status === OrderStatus.Pending
  }

  isCompleted(): boolean {
    return this.status === OrderStatus.Completed
  }

  canBeCancelled(): boolean {
    return this.isPending() || this.status === OrderStatus.Processing
  }
}
```

**But NOT business logic:**

```typescript
// ❌ Bad – business logic in model
export default class Order extends BaseModel {
  async cancel() {
    await db.transaction(async (trx) => {
      this.status = OrderStatus.Cancelled
      await this.useTransaction(trx).save()
      await this.refundPayment()
      await this.notifyCustomer()
    })
  }
}

// ✅ Good – business logic in a service/action
export default class CancelOrderService {
  async handle(order: Order) {
    return await db.transaction(async (trx) => {
      order.status = OrderStatus.Cancelled
      await order.useTransaction(trx).save()
      await new RefundPaymentService().handle(order, trx)
      await new NotifyCustomerService().handle(order)
      return order
    })
  }
}
```

---

## Scopes

**For reusable query constraints:**

```typescript
import { scope } from '@adonisjs/lucid/orm'

export default class Order extends BaseModel {
  static pending = scope((query) => {
    query.where('status', OrderStatus.Pending)
  })

  static forUser = scope((query, userId: number) => {
    query.where('user_id', userId)
  })

  static recent = scope((query, days = 30) => {
    query.where('created_at', '>=', DateTime.now().minus({ days }).toSQL())
  })
}

// Usage
const orders = await Order.query()
  .apply((scopes) => scopes.pending())
  .apply((scopes) => scopes.forUser(userId))
```

---

## Soft Deletes

```typescript
import { SoftDeletes } from '@adonisjs/lucid/orm'
import { compose } from '@adonisjs/core/helpers'

export default class Order extends compose(BaseModel, SoftDeletes) {
  @column.dateTime()
  declare deletedAt: DateTime | null
}
```

**Usage:**

```typescript
await order.delete()         // Soft delete (sets deletedAt)
await order.forceDelete()    // Permanent delete
await order.restore()        // Restore soft deleted record

// Querying
await Order.withTrashed().exec()
await Order.onlyTrashed().exec()
await Order.query().withTrashed()
```

---

## Model Concerns (Mixins/Traits)

**Extract reusable behaviour using mixins:**

```typescript
// app/models/concerns/has_uuid.ts
import { column, beforeCreate } from '@adonisjs/lucid/orm'
import { cuid } from '@adonisjs/core/helpers'

// Mixin factory
export function HasUuid<T extends { new(...args: any[]): {} }>(Base: T) {
  class HasUuidMixin extends (Base as any) {
    @column()
    declare uuid: string

    @beforeCreate()
    static assignUuid(model: any) {
      model.uuid = cuid()
    }
  }
  return HasUuidMixin
}
```

**Use in models:**

```typescript
import { compose } from '@adonisjs/core/helpers'
import { HasUuid } from '#models/concerns/has_uuid'

export default class Order extends compose(BaseModel, HasUuid) {
  // uuid column and beforeCreate hook are inherited
}
```

---

## Custom Table Name & Primary Key

```typescript
export default class OrderItem extends BaseModel {
  // Override table name (default: snake_case plural of class name)
  static table = 'order_line_items'

  // Override primary key (default: 'id')
  static primaryKey = 'uuid'

  @column({ isPrimary: true })
  declare uuid: string
}
```

---

## Serialisation

**Control what gets exposed:**

```typescript
export default class User extends BaseModel {
  @column()
  declare name: string

  @column({ serializeAs: null })  // Hidden from serialisation
  declare password: string

  @column({ serializeAs: 'email_address' })  // Renamed in output
  declare email: string

  // Custom serialise method
  serialize() {
    return {
      ...super.serialize(),
      fullName: this.fullName,
    }
  }
}
```

---

## Query Examples

```typescript
// Basic fetch
const order = await Order.find(1)
const order = await Order.findOrFail(1)
const order = await Order.findBy('uuid', uuid)

// With relationships
const order = await Order.query()
  .where('id', id)
  .preload('user')
  .preload('items', (query) => {
    query.orderBy('created_at', 'asc')
  })
  .firstOrFail()

// Eager loading after fetch
await order.load('user')

// Create / update
const order = await Order.create({ userId: 1, total: 1000 })
await order.merge({ status: OrderStatus.Completed }).save()

// First or create
const order = await Order.firstOrCreate(
  { userId: 1, status: OrderStatus.Pending },
  { total: 500 }
)
```

---

## Model Organisation

```
app/
└── models/
    ├── order.ts
    ├── user.ts
    ├── order_item.ts
    └── concerns/
        ├── has_uuid.ts
        ├── belongs_to_tenant.ts
        └── searchable.ts
```

---

## Testing Models

```typescript
import { test } from '@japa/runner'
import Order from '#models/order'
import User from '#models/user'
import { OrderStatus } from '#enums/order_status'
import { OrderFactory } from '#database/factories/order_factory'

test.group('Order Model', (group) => {
  group.each.setup(async () => {
    await resetTables()  // or use RefreshDatabase
  })
})

test('can create an order with attributes', async ({ assert }) => {
  const user = await UserFactory.create()
  const order = await Order.create({
    userId: user.id,
    status: OrderStatus.Pending,
    total: 1000,
  })

  assert.equal(order.userId, user.id)
  assert.equal(order.total, 1000)
})

test('casts status to enum', async ({ assert }) => {
  const order = await OrderFactory
    .merge({ status: OrderStatus.Pending })
    .create()

  assert.instanceOf(order.status, String)
  assert.equal(order.status, OrderStatus.Pending)
})

test('has user relationship', async ({ assert }) => {
  const order = await OrderFactory.with('user').create()
  await order.load('user')

  assert.instanceOf(order.user, User)
})

test('isPending returns true when status is pending', async ({ assert }) => {
  const order = await OrderFactory
    .merge({ status: OrderStatus.Pending })
    .create()

  assert.isTrue(order.isPending())
})
```

---

## Summary

**Models should:**

- Define columns using `@column` decorators with correct types
- Define relationships using `@belongsTo`, `@hasMany`, `@hasOne`, `@manyToMany`, etc.
- Use `@computed()` for derived/accessor properties
- Use hooks (`@beforeCreate`, `@beforeSave`, etc.) for lifecycle side effects
- Have simple helper/predicate methods (e.g. `isPending()`)
- Use scopes for reusable query constraints
- Use mixins/`compose()` for shared behaviour

**Models should NOT:**

- Contain business logic (use Services or Actions)
- Make HTTP calls or interact with external services
- Have complex multi-step methods (use Services)
- Handle validation (use AdonisJS Validators)
