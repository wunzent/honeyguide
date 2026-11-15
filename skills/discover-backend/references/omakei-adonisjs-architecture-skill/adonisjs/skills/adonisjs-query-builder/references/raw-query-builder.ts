// references/raw-query-builder.ts
//
// Patterns for the low-level Knex-based query builder in Lucid.
// Use for complex joins, reporting queries, aggregations, and
// anything that doesn't map cleanly to a single Lucid model.

import db from '@adonisjs/lucid/services/db'

// ─────────────────────────────────────────────────────────────
// Joins
// ─────────────────────────────────────────────────────────────

// Inner join
async function topCustomersByRevenue() {
  return db
    .from('orders')
    .join('users', 'users.id', 'orders.customer_id')
    .where('orders.status', 'completed')
    .select('users.id', 'users.name', 'users.email')
    .select(db.raw('SUM(orders.total_in_cents) as revenue'))
    .select(db.raw('COUNT(orders.id) as order_count'))
    .groupBy('users.id')
    .orderBy('revenue', 'desc')
    .limit(10)
}

// Left join
async function usersWithOptionalProfile() {
  return db
    .from('users')
    .leftJoin('profiles', 'profiles.user_id', 'users.id')
    .select('users.*', 'profiles.bio', 'profiles.avatar_url')
}

// ─────────────────────────────────────────────────────────────
// Aggregations
// ─────────────────────────────────────────────────────────────

async function orderStats() {
  return db
    .from('orders')
    .select(db.raw(`
      COUNT(*) as total_orders,
      SUM(total_in_cents) as total_revenue,
      AVG(total_in_cents) as avg_order_value,
      MIN(total_in_cents) as min_order,
      MAX(total_in_cents) as max_order
    `))
    .where('status', 'completed')
    .first()
}

// Group by with having
async function revenueByMonth() {
  return db
    .from('orders')
    .select(db.raw("DATE_TRUNC('month', placed_at) as month"))
    .select(db.raw('SUM(total_in_cents) as revenue'))
    .select(db.raw('COUNT(*) as order_count'))
    .where('status', 'completed')
    .groupByRaw("DATE_TRUNC('month', placed_at)")
    .havingRaw('SUM(total_in_cents) > ?', [100000])
    .orderBy('month', 'desc')
}

// ─────────────────────────────────────────────────────────────
// Subqueries
// ─────────────────────────────────────────────────────────────

async function usersWithRecentOrders() {
  return db
    .from('users')
    .whereExists((subquery) => {
      subquery
        .from('orders')
        .whereColumn('orders.customer_id', 'users.id')
        .where('orders.placed_at', '>', db.raw("NOW() - INTERVAL '30 days'"))
    })
}

// Subquery as a column
async function usersWithOrderCounts() {
  return db
    .from('users')
    .select('users.*')
    .select(
      db.from('orders')
        .whereColumn('orders.customer_id', 'users.id')
        .count('* as orders_count')
        .as('ordersCount')
    )
}

// ─────────────────────────────────────────────────────────────
// Insert / Update / Delete
// ─────────────────────────────────────────────────────────────

// Bulk insert
async function bulkInsertTags(tags: Array<{ name: string }>) {
  return db.table('tags').multiInsert(tags)
}

// Update with conditions
async function archiveOldOrders() {
  return db
    .from('orders')
    .where('status', 'completed')
    .where('placed_at', '<', db.raw("NOW() - INTERVAL '1 year'"))
    .update({ status: 'archived' })
}

// Delete
async function purgeExpiredTokens() {
  return db
    .from('tokens')
    .where('expires_at', '<', db.raw('NOW()'))
    .delete()
}

// ─────────────────────────────────────────────────────────────
// Upsert (insert or update on conflict)
// ─────────────────────────────────────────────────────────────

async function upsertMetric(date: string, pageViews: number) {
  // PostgreSQL-specific: ON CONFLICT ... DO UPDATE
  await db.rawQuery(
    `INSERT INTO daily_metrics (date, page_views)
     VALUES (?, ?)
     ON CONFLICT (date)
     DO UPDATE SET page_views = daily_metrics.page_views + EXCLUDED.page_views`,
    [date, pageViews]
  )
}

// ─────────────────────────────────────────────────────────────
// Transactions with the raw builder
// ─────────────────────────────────────────────────────────────

async function transferFunds(fromId: number, toId: number, amount: number) {
  await db.transaction(async (trx) => {
    await trx
      .from('accounts')
      .where('id', fromId)
      .decrement('balance', amount)

    await trx
      .from('accounts')
      .where('id', toId)
      .increment('balance', amount)

    await trx.table('transfers').insert({
      from_account_id: fromId,
      to_account_id: toId,
      amount,
      transferred_at: new Date(),
    })
  })
}

// ─────────────────────────────────────────────────────────────
// Streaming large result sets (memory efficient)
// ─────────────────────────────────────────────────────────────

async function exportAllOrders() {
  const stream = db
    .from('orders')
    .where('status', 'completed')
    .orderBy('id', 'asc')
    .stream()

  for await (const row of stream) {
    // Process each row without loading everything into memory
    console.log(row.id, row.total_in_cents)
  }
}

export {
  topCustomersByRevenue,
  usersWithOptionalProfile,
  orderStats,
  revenueByMonth,
  usersWithRecentOrders,
  usersWithOrderCounts,
  bulkInsertTags,
  archiveOldOrders,
  purgeExpiredTokens,
  upsertMetric,
  transferFunds,
  exportAllOrders,
}
