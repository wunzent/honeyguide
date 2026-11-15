---
name: adonisjs-query-builders
description: Composable query builder patterns for AdonisJS Lucid. Use when working with database queries, query scopes, reusable query logic, filtering, sorting, pagination, complex where clauses, or when user mentions query builders, query scopes, model scopes, composable queries, query objects, database queries, complex queries, eager loading, preloading, subqueries, raw queries, or asks how to organize Lucid query logic in an AdonisJS project.
---

# AdonisJS Query Builders

Patterns for composable, reusable query logic with Lucid: model scopes, scope extractors, the raw query builder, and a standalone query-object pattern for complex filtering.

**Reference implementations:**
- [Model scopes (recommended) →](references/model-scopes.ts)
- [Standalone query object →](references/query-object.ts)
- [Raw query builder patterns →](references/raw-query-builder.ts)
- [Testing queries →](references/testing-queries.ts)

## Two Approaches

| Approach | When to use |
|---|---|
| **Model scopes** | Default for most queries — keeps logic on the model, chainable, zero overhead |
| **Standalone query objects** | Complex filtering with many optional params (search endpoints, admin tables, report queries) |

---

## 1. Model Scopes (Recommended)

Define reusable query methods directly on the Lucid model using `scope()`:

```typescript
// app/models/order.ts
import { BaseModel, column, scope } from '@adonisjs/lucid/orm'
import { OrderStatus } from '#enums/order_status'
import { DateTime } from 'luxon'
import type { ModelQueryBuilderContract } from '@adonisjs/lucid/types/model'

export default class Order extends BaseModel {
  @column({ isPrimary: true })
  declare id: number

  @column()
  declare status: OrderStatus

  @column()
  declare customerId: number

  @column()
  declare totalInCents: number

  @column.dateTime()
  declare placedAt: DateTime

  // ── Scopes ──────────────────────────────────────────────

  static pending = scope((query) => {
    query.where('status', OrderStatus.Pending)
  })

  static completed = scope((query) => {
    query.where('status', OrderStatus.Completed)
  })

  static cancelled = scope((query) => {
    query.where('status', OrderStatus.Cancelled)
  })

  static forCustomer = scope((query, customerId: number) => {
    query.where('customerId', customerId)
  })

  static totalAbove = scope((query, amountInCents: number) => {
    query.where('totalInCents', '>', amountInCents)
  })

  static placedBetween = scope((query, start: DateTime, end: DateTime) => {
    query.whereBetween('placedAt', [start.toSQL()!, end.toSQL()!])
  })

  static placedAfter = scope((query, date: DateTime) => {
    query.where('placedAt', '>', date.toSQL()!)
  })

  static recent = scope((query) => {
    query.orderBy('placedAt', 'desc')
  })

  static withRelated = scope((query) => {
    query.preload('customer').preload('items', (itemQuery) => {
      itemQuery.preload('product')
    })
  })
}
```

### Chaining scopes

```typescript
const orders = await Order.query()
  .withScopes((scopes) => scopes.pending())
  .withScopes((scopes) => scopes.forCustomer(user.id))
  .withScopes((scopes) => scopes.totalAbove(5000))
  .withScopes((scopes) => scopes.recent())
  .withScopes((scopes) => scopes.withRelated())
  .paginate(page, 20)
```

Or using the shorthand `apply()`:

```typescript
const orders = await Order.query()
  .apply((scopes) => {
    scopes.pending()
    scopes.forCustomer(user.id)
    scopes.totalAbove(5000)
    scopes.recent()
    scopes.withRelated()
  })
  .paginate(page, 20)
```

### Conditional scopes

Apply scopes only when a condition is true using `if`:

```typescript
const orders = await Order.query()
  .apply((scopes) => {
    scopes.recent()
    scopes.withRelated()
  })
  .if(status, (query) => query.where('status', status))
  .if(customerId, (query) => query.apply((s) => s.forCustomer(customerId)))
  .if(minTotal, (query) => query.apply((s) => s.totalAbove(minTotal)))
  .paginate(page, 20)
```

---

## 2. Standalone Query Objects

For complex filtering (search endpoints, admin index pages), extract query logic into a dedicated class:

```typescript
// app/queries/order_query.ts
import Order from '#models/order'
import { OrderStatus } from '#enums/order_status'
import { DateTime } from 'luxon'
import type { ModelQueryBuilderContract } from '@adonisjs/lucid/types/model'

type OrderQuery = ModelQueryBuilderContract<typeof Order, Order>

interface OrderFilters {
  status?: OrderStatus
  customerId?: number
  minTotal?: number
  maxTotal?: number
  placedAfter?: string    // ISO date string
  placedBefore?: string   // ISO date string
  search?: string
  sortBy?: 'placed_at' | 'total_in_cents' | 'created_at'
  sortDir?: 'asc' | 'desc'
}

export class OrderQueryBuilder {
  private query: OrderQuery

  constructor() {
    this.query = Order.query()
  }

  /** Apply all filters from a validated request payload. */
  apply(filters: OrderFilters): this {
    if (filters.status) {
      this.query.where('status', filters.status)
    }

    if (filters.customerId) {
      this.query.where('customerId', filters.customerId)
    }

    if (filters.minTotal !== undefined) {
      this.query.where('totalInCents', '>=', filters.minTotal)
    }

    if (filters.maxTotal !== undefined) {
      this.query.where('totalInCents', '<=', filters.maxTotal)
    }

    if (filters.placedAfter) {
      this.query.where('placedAt', '>=', filters.placedAfter)
    }

    if (filters.placedBefore) {
      this.query.where('placedAt', '<=', filters.placedBefore)
    }

    if (filters.search) {
      const term = `%${filters.search}%`
      this.query.where((q) => {
        q.whereILike('reference', term)
          .orWhereHas('customer', (cq) => {
            cq.whereILike('name', term).orWhereILike('email', term)
          })
      })
    }

    this.query.orderBy(
      filters.sortBy ?? 'placed_at',
      filters.sortDir ?? 'desc'
    )

    return this
  }

  /** Preload common relationships. */
  withRelated(): this {
    this.query.preload('customer').preload('items', (q) => q.preload('product'))
    return this
  }

  /** Execute and paginate. */
  async paginate(page: number, perPage = 20) {
    return this.query.paginate(page, perPage)
  }

  /** Execute and return all results. */
  async all() {
    return this.query.exec()
  }

  /** Get the underlying Lucid query (for further chaining). */
  getQuery(): OrderQuery {
    return this.query
  }
}
```

### Using in a controller

```typescript
// app/controllers/orders_controller.ts
import { OrderQueryBuilder } from '#queries/order_query'

export default class OrdersController {
  async index({ request }: HttpContext) {
    const filters = request.qs()

    const orders = await new OrderQueryBuilder()
      .apply(filters)
      .withRelated()
      .paginate(filters.page ?? 1)

    return orders
  }
}
```

---

## Lucid Query Builder Essentials

### Where clauses

```typescript
// Basic
query.where('status', 'active')
query.where('total', '>', 1000)
query.whereNot('status', 'cancelled')

// Multiple conditions
query.where('status', 'active').where('role', 'admin')

// OR
query.where('role', 'admin').orWhere('role', 'editor')

// Grouped (sub-query)
query.where((q) => {
  q.where('status', 'active').orWhere('role', 'admin')
})

// IN / NOT IN
query.whereIn('status', ['active', 'pending'])
query.whereNotIn('status', ['cancelled', 'archived'])

// NULL
query.whereNull('deletedAt')
query.whereNotNull('verifiedAt')

// BETWEEN
query.whereBetween('createdAt', ['2025-01-01', '2025-12-31'])

// LIKE (case-insensitive)
query.whereILike('name', '%john%')

// JSON columns (PostgreSQL)
query.whereJsonSuperset('metadata', { priority: 'high' })
```

### Relationship queries

```typescript
// Has relationship
query.has('posts')                             // has at least 1 post
query.has('posts', '>=', 5)                    // has 5+ posts

// Where has (filter by related)
query.whereHas('posts', (postQuery) => {
  postQuery.where('status', 'published')
})

// Doesn't have
query.doesntHave('orders')
query.whereDoesntHave('orders', (oq) => {
  oq.where('status', 'cancelled')
})

// Preload (eager load)
query.preload('posts')
query.preload('posts', (pq) => {
  pq.where('status', 'published').orderBy('createdAt', 'desc').limit(5)
})

// Nested preload
query.preload('posts', (pq) => {
  pq.preload('comments', (cq) => {
    cq.preload('author')
  })
})

// Preload counts
query.withCount('posts')
query.withCount('posts', (pq) => pq.where('status', 'published'))
// Access: user.$extras.posts_count
```

### Aggregations

```typescript
// Count
const count = await Order.query().where('status', 'pending').count('* as total')
const total = count[0].$extras.total

// Sum / avg / min / max
const revenue = await Order.query()
  .where('status', 'completed')
  .sum('totalInCents as revenue')

// Group by
const byStatus = await Order.query()
  .select('status')
  .count('* as count')
  .groupBy('status')
```

### Pagination

**Pagination belongs in the repository layer.** Repositories call `.paginate(page, limit)` and return the `ModelPaginatorContract` directly. Services and controllers receive the paginator — they never pass raw `page`/`limit` into a service method.

```typescript
// ✅ In the repository — owns pagination
async list(page: number, limit: number) {
  return Post.query().orderBy('created_at', 'desc').paginate(page, limit)
}

// Simple pagination
const posts = await Post.query().paginate(page, 20)
// posts.total, posts.perPage, posts.currentPage, posts.lastPage

// Serialize for API response
return posts.serialize()

// With base URL for links
return posts.baseUrl('/api/posts').serialize()
```

### Ordering

```typescript
query.orderBy('createdAt', 'desc')
query.orderBy('name', 'asc')

// Multiple orderings
query.orderBy([
  { column: 'isPinned', order: 'desc' },
  { column: 'createdAt', order: 'desc' },
])

// Order by relationship count
query.withCount('comments').orderBy('comments_count', 'desc')
```

### Selecting columns

```typescript
query.select('id', 'title', 'status')
query.select(['id', 'title', 'status'])
```

### Raw expressions

```typescript
import db from '@adonisjs/lucid/services/db'

// Raw where
query.whereRaw('LOWER(email) = ?', [email.toLowerCase()])

// Raw select
query.select(db.raw('COUNT(*) as total'))

// Raw order
query.orderByRaw('FIELD(status, "active", "pending", "archived")')
```

### Subqueries

```typescript
// Where exists
query.whereExists((subquery) => {
  subquery
    .from('orders')
    .whereColumn('orders.user_id', 'users.id')
    .where('orders.status', 'completed')
})

// Subquery in select
query.select('*').select(
  Order.query()
    .whereColumn('orders.user_id', 'users.id')
    .count('* as orders_count')
    .as('ordersCount')
)
```

### Transactions

```typescript
import db from '@adonisjs/lucid/services/db'

const trx = await db.transaction()

try {
  const order = await Order.create({ /* ... */ }, { client: trx })
  await OrderItem.createMany(items, { client: trx })
  await trx.commit()
} catch (error) {
  await trx.rollback()
  throw error
}

// Or use the callback form (auto-commit/rollback)
await db.transaction(async (trx) => {
  await Order.create({ /* ... */ }, { client: trx })
  await OrderItem.createMany(items, { client: trx })
})
```

### Low-level DB query builder

For complex queries that don't map to a model:

```typescript
import db from '@adonisjs/lucid/services/db'

const results = await db
  .from('orders')
  .join('users', 'users.id', 'orders.customer_id')
  .where('orders.status', 'completed')
  .select('users.name', db.raw('SUM(orders.total_in_cents) as revenue'))
  .groupBy('users.id')
  .orderBy('revenue', 'desc')
  .limit(10)
```

---

## Scope Extraction Patterns

### Status scopes

```typescript
static active = scope((query) => query.where('status', 'active'))
static inactive = scope((query) => query.where('status', 'inactive'))
static withStatus = scope((query, status: string) => query.where('status', status))
```

### Date scopes

```typescript
static createdAfter = scope((query, date: DateTime) => {
  query.where('createdAt', '>', date.toSQL()!)
})

static createdToday = scope((query) => {
  query.whereRaw('DATE(created_at) = CURRENT_DATE')
})

static createdBetween = scope((query, start: DateTime, end: DateTime) => {
  query.whereBetween('createdAt', [start.toSQL()!, end.toSQL()!])
})
```

### Owner/user scopes

```typescript
static forUser = scope((query, userId: number) => {
  query.where('userId', userId)
})

static forCurrentUser = scope((query, userId: number) => {
  query.where('userId', userId)
})
```

### Search scopes

```typescript
static search = scope((query, term: string) => {
  const like = `%${term}%`
  query.where((q) => {
    q.whereILike('title', like)
      .orWhereILike('body', like)
  })
})
```

### Relationship preload scopes

```typescript
static withAuthor = scope((query) => query.preload('author'))

static withFullRelations = scope((query) => {
  query
    .preload('author')
    .preload('comments', (cq) => cq.preload('user').limit(10))
    .preload('tags')
})
```

---

## Directory Structure

```
app/
├── models/
│   ├── order.ts         # Scopes defined as static scope() properties
│   └── user.ts
└── queries/             # Standalone query objects (complex filtering only)
    └── order_query.ts
```

---

## Summary

| Pattern | When | How |
|---|---|---|
| Model scopes | Most queries | `scope()` on model, chain with `.apply()` |
| `.if()` conditional | Optional filters | `query.if(condition, callback)` |
| Standalone query object | Complex search/filter endpoints | Class with `.apply(filters)` method |
| Raw DB query builder | Reporting, joins, aggregations | `db.from('table').join().select()` |
| Preload (eager load) | Avoid N+1 | `.preload('relation')` |
| `withCount` | Count without loading | `.withCount('relation')` |

**Default to model scopes. Extract to query objects only for complex filtering endpoints.**
