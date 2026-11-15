// app/queries/order_query.ts
//
// Standalone query object for complex filtering.
// Use when a controller/endpoint has many optional filter params.
// Keeps the controller thin and the query logic testable.

import Order from '#models/order'
import { OrderStatus } from '#enums/order_status'
import type { ModelQueryBuilderContract } from '@adonisjs/lucid/types/model'

type OrderQueryBuilder = ModelQueryBuilderContract<typeof Order, Order>

/**
 * Accepted filter parameters.
 * Typically validated with VineJS before passing here.
 */
export interface OrderFilters {
  status?: OrderStatus
  customerId?: number
  minTotal?: number
  maxTotal?: number
  placedAfter?: string    // ISO date string
  placedBefore?: string   // ISO date string
  search?: string
  hasProduct?: number
  sortBy?: 'placed_at' | 'total_in_cents' | 'created_at'
  sortDir?: 'asc' | 'desc'
  page?: number
  perPage?: number
}

export class OrderQuery {
  private query: OrderQueryBuilder

  constructor(baseQuery?: OrderQueryBuilder) {
    this.query = baseQuery ?? Order.query()
  }

  /**
   * Apply all filters in one call.
   * Skips any filter that is undefined/null.
   */
  apply(filters: OrderFilters): this {
    this.applyStatus(filters.status)
    this.applyCustomer(filters.customerId)
    this.applyTotalRange(filters.minTotal, filters.maxTotal)
    this.applyDateRange(filters.placedAfter, filters.placedBefore)
    this.applySearch(filters.search)
    this.applyProductFilter(filters.hasProduct)
    this.applySort(filters.sortBy, filters.sortDir)
    return this
  }

  // ── Individual filters (can be called standalone) ──────

  applyStatus(status?: OrderStatus): this {
    if (status) {
      this.query.where('status', status)
    }
    return this
  }

  applyCustomer(customerId?: number): this {
    if (customerId) {
      this.query.where('customerId', customerId)
    }
    return this
  }

  applyTotalRange(min?: number, max?: number): this {
    if (min !== undefined) {
      this.query.where('totalInCents', '>=', min)
    }
    if (max !== undefined) {
      this.query.where('totalInCents', '<=', max)
    }
    return this
  }

  applyDateRange(after?: string, before?: string): this {
    if (after) {
      this.query.where('placedAt', '>=', after)
    }
    if (before) {
      this.query.where('placedAt', '<=', before)
    }
    return this
  }

  applySearch(term?: string): this {
    if (!term) return this

    const like = `%${term}%`
    this.query.where((q) => {
      q.whereILike('reference', like)
        .orWhereHas('customer', (cq) => {
          cq.whereILike('name', like).orWhereILike('email', like)
        })
    })
    return this
  }

  applyProductFilter(productId?: number): this {
    if (productId) {
      this.query.whereHas('items', (iq) => {
        iq.where('productId', productId)
      })
    }
    return this
  }

  applySort(sortBy?: string, sortDir?: 'asc' | 'desc'): this {
    this.query.orderBy(sortBy ?? 'placed_at', sortDir ?? 'desc')
    return this
  }

  // ── Preloading ─────────────────────────────────────────

  withRelated(): this {
    this.query.preload('customer').preload('items', (iq) => {
      iq.preload('product')
    })
    return this
  }

  withCustomer(): this {
    this.query.preload('customer')
    return this
  }

  // ── Execution ──────────────────────────────────────────

  async paginate(page = 1, perPage = 20) {
    return this.query.paginate(page, perPage)
  }

  async all() {
    return this.query.exec()
  }

  async first() {
    return this.query.first()
  }

  async count() {
    const result = await this.query.count('* as total')
    return Number(result[0].$extras.total)
  }

  /** Expose the underlying query for further chaining. */
  getQuery(): OrderQueryBuilder {
    return this.query
  }
}

// ─────────────────────────────────────────────────────────────
// Usage in controllers
// ─────────────────────────────────────────────────────────────

// import { OrderQuery } from '#queries/order_query'
//
// export default class OrdersController {
//   async index({ request }: HttpContext) {
//     const filters = request.qs() // ideally validated with VineJS first
//
//     const orders = await new OrderQuery()
//       .apply(filters)
//       .withRelated()
//       .paginate(filters.page, filters.perPage)
//
//     return orders.serialize()
//   }
//
//   // Scoped to current user
//   async myOrders({ request, auth }: HttpContext) {
//     const filters = request.qs()
//     filters.customerId = auth.user!.id
//
//     const orders = await new OrderQuery()
//       .apply(filters)
//       .withRelated()
//       .paginate(filters.page)
//
//     return orders.serialize()
//   }
// }
