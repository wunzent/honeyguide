// app/models/order.ts
//
// Full example of a Lucid model with composable query scopes.
// Scopes are static properties defined with scope() — chainable,
// reusable, and zero overhead (no extra classes needed).

import { BaseModel, column, hasMany, belongsTo, scope } from '@adonisjs/lucid/orm'
import type { HasMany, BelongsTo } from '@adonisjs/lucid/types/relations'
import { DateTime } from 'luxon'
import { OrderStatus } from '#enums/order_status'
import User from '#models/user'
import OrderItem from '#models/order_item'

export default class Order extends BaseModel {
  // ── Columns ─────────────────────────────────────────────

  @column({ isPrimary: true })
  declare id: number

  @column()
  declare status: OrderStatus

  @column()
  declare customerId: number

  @column()
  declare totalInCents: number

  @column()
  declare reference: string

  @column()
  declare paymentId: string | null

  @column.dateTime()
  declare placedAt: DateTime

  @column.dateTime({ autoCreate: true })
  declare createdAt: DateTime

  @column.dateTime({ autoCreate: true, autoUpdate: true })
  declare updatedAt: DateTime

  // ── Relationships ───────────────────────────────────────

  @belongsTo(() => User, { foreignKey: 'customerId' })
  declare customer: BelongsTo<typeof User>

  @hasMany(() => OrderItem)
  declare items: HasMany<typeof OrderItem>

  // ── Status scopes ───────────────────────────────────────

  static pending = scope((query) => {
    query.where('status', OrderStatus.Pending)
  })

  static completed = scope((query) => {
    query.where('status', OrderStatus.Completed)
  })

  static cancelled = scope((query) => {
    query.where('status', OrderStatus.Cancelled)
  })

  static paid = scope((query) => {
    query.whereIn('status', [OrderStatus.Paid, OrderStatus.Shipped, OrderStatus.Completed])
  })

  static withStatus = scope((query, status: OrderStatus) => {
    query.where('status', status)
  })

  static notCancelled = scope((query) => {
    query.whereNot('status', OrderStatus.Cancelled)
  })

  // ── Filter scopes ──────────────────────────────────────

  static forCustomer = scope((query, customerId: number) => {
    query.where('customerId', customerId)
  })

  static totalAbove = scope((query, amountInCents: number) => {
    query.where('totalInCents', '>', amountInCents)
  })

  static totalBelow = scope((query, amountInCents: number) => {
    query.where('totalInCents', '<', amountInCents)
  })

  static totalBetween = scope((query, min: number, max: number) => {
    query.whereBetween('totalInCents', [min, max])
  })

  // ── Date scopes ────────────────────────────────────────

  static placedBetween = scope((query, start: DateTime, end: DateTime) => {
    query.whereBetween('placedAt', [start.toSQL()!, end.toSQL()!])
  })

  static placedAfter = scope((query, date: DateTime) => {
    query.where('placedAt', '>', date.toSQL()!)
  })

  static placedToday = scope((query) => {
    query.whereRaw('DATE(placed_at) = CURRENT_DATE')
  })

  static placedThisWeek = scope((query) => {
    const start = DateTime.now().startOf('week')
    const end = DateTime.now().endOf('week')
    query.whereBetween('placedAt', [start.toSQL()!, end.toSQL()!])
  })

  // ── Search scopes ──────────────────────────────────────

  static search = scope((query, term: string) => {
    const like = `%${term}%`
    query.where((q) => {
      q.whereILike('reference', like)
        .orWhereHas('customer', (cq) => {
          cq.whereILike('name', like).orWhereILike('email', like)
        })
    })
  })

  // ── Relationship queries ───────────────────────────────

  static hasItems = scope((query) => {
    query.has('items')
  })

  static hasItemsForProduct = scope((query, productId: number) => {
    query.whereHas('items', (iq) => {
      iq.where('productId', productId)
    })
  })

  // ── Ordering scopes ────────────────────────────────────

  static recent = scope((query) => {
    query.orderBy('placedAt', 'desc')
  })

  static oldest = scope((query) => {
    query.orderBy('placedAt', 'asc')
  })

  static highestValue = scope((query) => {
    query.orderBy('totalInCents', 'desc')
  })

  // ── Preload scopes ─────────────────────────────────────

  static withCustomer = scope((query) => {
    query.preload('customer')
  })

  static withItems = scope((query) => {
    query.preload('items')
  })

  static withRelated = scope((query) => {
    query.preload('customer').preload('items', (iq) => {
      iq.preload('product')
    })
  })
}

// ─────────────────────────────────────────────────────────────
// Usage examples
// ─────────────────────────────────────────────────────────────

// Basic chaining
// const orders = await Order.query()
//   .apply((scopes) => {
//     scopes.pending()
//     scopes.forCustomer(user.id)
//     scopes.recent()
//     scopes.withRelated()
//   })
//   .paginate(1, 20)

// Conditional filters
// const orders = await Order.query()
//   .apply((scopes) => scopes.recent())
//   .if(status, (q) => q.apply((s) => s.withStatus(status)))
//   .if(search, (q) => q.apply((s) => s.search(search)))
//   .if(minTotal, (q) => q.apply((s) => s.totalAbove(minTotal)))
//   .paginate(page, perPage)

// Lazy iteration for batch processing
// await Order.query()
//   .apply((scopes) => scopes.completed())
//   .orderBy('id', 'asc')
//   .pojo()                 // plain objects, less memory
//   .stream(async (order) => {
//     // process each order
//   })
