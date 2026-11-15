# Implementation Patterns

Detailed code patterns for AdonisJS multi-tenancy. Referenced from the main SKILL.md.

## Table of Contents

1. [Tenant Connection Manager](#tenant-connection-manager)
2. [Tenant Context Service](#tenant-context-service)
3. [HttpContext Extension](#httpcontext-extension)
4. [Tenant Middleware Variants](#tenant-middleware-variants)
5. [Route Configuration](#route-configuration)
6. [Tenanted Models](#tenanted-models)
7. [Central Actions](#central-actions)
8. [Tenanted Actions](#tenanted-actions)
9. [Custom Ace Commands](#custom-ace-commands)
10. [Queue Jobs](#queue-jobs)
11. [Common Patterns](#common-patterns)
12. [Single-Database Tenancy Mixin](#single-database-tenancy-mixin)

---

## Tenant Connection Manager

Dynamically register and manage tenant database connections. Uses AdonisJS ConnectionManager to avoid race conditions.

```typescript
// app/services/tenant_connection_manager.ts
import db from '@adonisjs/lucid/services/db'
import env from '#start/env'
import type { Tenant } from '#models/tenant'

export class TenantConnectionManager {
  /**
   * Register a dynamic connection for the given tenant.
   * ConnectionManager handles deduplication — calling this
   * multiple times for the same tenant is safe.
   */
  static register(tenant: Tenant): string {
    const connectionName = `tenant_${tenant.id}`

    if (!db.manager.has(connectionName)) {
      db.manager.add(connectionName, {
        client: 'pg',
        connection: {
          host: env.get('DB_HOST'),
          port: env.get('DB_PORT'),
          user: env.get('DB_USER'),
          password: env.get('DB_PASSWORD'),
          database: tenant.databaseName,
        },
        pool: {
          min: 0, // Allow idle disconnect
          max: 5,
        },
      })
    }

    db.manager.connect(connectionName)
    return connectionName
  }

  /**
   * Close a tenant connection (e.g. on tenant deletion).
   */
  static async close(tenant: Tenant): Promise<void> {
    const connectionName = `tenant_${tenant.id}`
    if (db.manager.has(connectionName)) {
      await db.manager.close(connectionName)
    }
  }

  /**
   * Check if a tenant connection is active.
   */
  static isConnected(tenant: Tenant): boolean {
    const connectionName = `tenant_${tenant.id}`
    return db.manager.has(connectionName) && db.manager.isConnected(connectionName)
  }
}
```

> **Important:** Set `pool.min: 0` for tenant connections so idle connections are released. Without this, you'll exhaust database connections as tenant count grows.

---

## Tenant Context Service

Request-scoped tenant context using HttpContext.

```typescript
// app/services/tenant_context.ts
import { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'
import type { Tenant } from '#models/tenant'
import { TenantConnectionManager } from '#services/tenant_connection_manager'

export class TenantContext {
  static current(): Tenant | null {
    const ctx = HttpContext.getOrFail()
    return ctx.tenant ?? null
  }

  static currentOrFail(): Tenant {
    const tenant = this.current()
    if (!tenant) {
      throw new Error('No active tenant context')
    }
    return tenant
  }

  static connectionName(): string {
    const tenant = this.currentOrFail()
    return `tenant_${tenant.id}`
  }

  static isActive(): boolean {
    try {
      const ctx = HttpContext.getOrFail()
      return ctx.tenant != null
    } catch {
      return false
    }
  }

  /**
   * Run a callback in a specific tenant's context.
   * Useful for background jobs or cross-tenant operations.
   */
  static async run<T>(tenant: Tenant, callback: () => Promise<T>): Promise<T> {
    TenantConnectionManager.register(tenant)
    return await callback()
  }

  /**
   * Run a callback against the central (landlord) database.
   */
  static async runCentral<T>(callback: () => Promise<T>): Promise<T> {
    return await callback()
  }
}
```

**Usage:**

```typescript
import { TenantContext } from '#services/tenant_context'

const tenant = TenantContext.current()
const tenantId = TenantContext.currentOrFail().id

if (TenantContext.isActive()) {
  // Tenant-specific logic
}

await TenantContext.run(tenant, async () => {
  await Order.create({ ... }, { connection: `tenant_${tenant.id}` })
})
```

---

## HttpContext Extension

```typescript
// types/context.ts
import type { Tenant } from '#models/tenant'

declare module '@adonisjs/core/http' {
  interface HttpContext {
    tenant?: Tenant
    tenantConnection?: string
  }
}
```

---

## Tenant Middleware Variants

### Subdomain-Based

```typescript
// app/middleware/tenant_middleware.ts
import type { HttpContext } from '@adonisjs/core/http'
import type { NextFn } from '@adonisjs/core/types/http'
import { Tenant } from '#models/tenant'
import { TenantConnectionManager } from '#services/tenant_connection_manager'

export default class TenantMiddleware {
  async handle(ctx: HttpContext, next: NextFn) {
    const tenant = await this.resolveTenant(ctx)

    if (!tenant) {
      return ctx.response.notFound({ error: 'Tenant not found' })
    }

    const connectionName = TenantConnectionManager.register(tenant)
    ctx.tenant = tenant
    ctx.tenantConnection = connectionName

    return next()
  }

  private async resolveTenant(ctx: HttpContext): Promise<Tenant | null> {
    const hostname = ctx.request.hostname()
    const subdomain = hostname?.split('.')[0]
    if (subdomain) {
      return Tenant.findBy('subdomain', subdomain)
    }
    return null
  }
}
```

### Header-Based

```typescript
private async resolveTenant(ctx: HttpContext): Promise<Tenant | null> {
  const tenantId = ctx.request.header('X-Tenant-ID')
  if (tenantId) {
    return Tenant.find(tenantId)
  }
  return null
}
```

### Path-Based

```typescript
private async resolveTenant(ctx: HttpContext): Promise<Tenant | null> {
  const tenantSlug = ctx.params.tenant
  if (tenantSlug) {
    return Tenant.findBy('slug', tenantSlug)
  }
  return null
}
```

---

## Route Configuration

```typescript
// start/routes.ts
import router from '@adonisjs/core/services/router'
import { middleware } from '#start/kernel'

// Central Routes (Landlord)
router.group(() => {
  router.get('/tenants', '#controllers/central/tenants_controller.index')
  router.post('/tenants', '#controllers/central/tenants_controller.store')
  router.delete('/tenants/:id', '#controllers/central/tenants_controller.destroy')
}).prefix('/central')

// Tenant Routes
router.group(() => {
  router.get('/orders', '#controllers/tenanted/orders_controller.index')
  router.post('/orders', '#controllers/tenanted/orders_controller.store')
}).use(middleware.tenant())
```

Register middleware:

```typescript
// start/kernel.ts
router.named({
  tenant: () => import('#middleware/tenant_middleware'),
})
```

---

## Tenanted Models

Tenanted models resolve their connection from HttpContext. **Recommended:** pass connection explicitly in queries rather than relying on static resolution.

### Central Model

```typescript
// app/models/tenant.ts
import { DateTime } from 'luxon'
import { BaseModel, column } from '@adonisjs/lucid/orm'

export default class Tenant extends BaseModel {
  static connection = 'central' // Always uses landlord DB

  @column({ isPrimary: true })
  declare id: string

  @column()
  declare name: string

  @column()
  declare subdomain: string

  @column()
  declare databaseName: string

  @column.dateTime({ autoCreate: true })
  declare createdAt: DateTime

  @column.dateTime({ autoCreate: true, autoUpdate: true })
  declare updatedAt: DateTime
}
```

### Tenanted Model (Explicit Connection)

```typescript
// app/models/order.ts
import { DateTime } from 'luxon'
import { BaseModel, column, belongsTo } from '@adonisjs/lucid/orm'
import type { BelongsTo } from '@adonisjs/lucid/types/relations'
import User from '#models/user'

export default class Order extends BaseModel {
  @column({ isPrimary: true })
  declare id: number

  @column()
  declare userId: number

  @column()
  declare status: string

  @column()
  declare total: number

  @belongsTo(() => User)
  declare user: BelongsTo<typeof User>

  @column.dateTime({ autoCreate: true })
  declare createdAt: DateTime
}

// Usage — always pass connection explicitly:
const orders = await Order
  .query({ connection: ctx.tenantConnection })
  .where('status', 'pending')
```

---

## Central Actions

```typescript
// app/actions/central/tenant/create_tenant_action.ts
import { Tenant } from '#models/tenant'
import db from '@adonisjs/lucid/services/db'
import { TenantConnectionManager } from '#services/tenant_connection_manager'

interface CreateTenantData {
  name: string
  subdomain: string
}

export default class CreateTenantAction {
  async execute(data: CreateTenantData): Promise<Tenant> {
    return db.transaction(async (trx) => {
      const existing = await Tenant.query({ client: trx })
        .where('subdomain', data.subdomain)
        .first()

      if (existing) {
        throw new Error(`Subdomain "${data.subdomain}" already exists`)
      }

      const databaseName = `tenant_${data.subdomain}`

      const tenant = await Tenant.create({
        name: data.name,
        subdomain: data.subdomain,
        databaseName,
      }, { client: trx })

      await trx.rawQuery(`CREATE DATABASE "${databaseName}"`)
      TenantConnectionManager.register(tenant)

      return tenant
    })
  }
}
```

---

## Tenanted Actions

```typescript
// app/actions/tenanted/order/create_order_action.ts
import { Order } from '#models/order'
import { TenantContext } from '#services/tenant_context'
import db from '@adonisjs/lucid/services/db'

interface CreateOrderData {
  status: string
  total: number
  items: Array<{ productId: number; quantity: number; price: number }>
}

export default class CreateOrderAction {
  async execute(userId: number, data: CreateOrderData): Promise<Order> {
    const connectionName = TenantContext.connectionName()

    return db.connection(connectionName).transaction(async (trx) => {
      const order = new Order()
      order.userId = userId
      order.status = data.status
      order.total = data.total
      order.useTransaction(trx)
      await order.save()

      for (const item of data.items) {
        await trx.insertQuery().table('order_items').insert({
          order_id: order.id,
          product_id: item.productId,
          quantity: item.quantity,
          price: item.price,
        })
      }

      return order
    })
  }
}
```

---

## Custom Ace Commands

```typescript
// commands/tenant_migrate.ts
import { BaseCommand, flags } from '@adonisjs/core/ace'
import { Tenant } from '#models/tenant'
import { TenantConnectionManager } from '#services/tenant_connection_manager'
import { MigrationRunner } from '@adonisjs/lucid/migration'

export default class TenantMigrate extends BaseCommand {
  static commandName = 'tenant:migrate'
  static description = 'Run migrations for all or a specific tenant'

  @flags.string({ description: 'Run for a specific tenant ID' })
  declare tenant: string

  async run() {
    const tenants = this.tenant
      ? [await Tenant.findOrFail(this.tenant)]
      : await Tenant.all()

    for (const tenant of tenants) {
      this.logger.info(`Migrating: ${tenant.name} (${tenant.databaseName})`)
      const connectionName = TenantConnectionManager.register(tenant)

      const migrator = new MigrationRunner(
        this.app.makePath('database/migrations/tenant'),
        { direction: 'up', connectionName }
      )

      await migrator.run()
      this.logger.success(`Done: ${tenant.name}`)
    }
  }
}
```

---

## Queue Jobs

Jobs must store tenant info and re-establish context when processed.

```typescript
// app/jobs/tenanted/process_order_job.ts
import { Tenant } from '#models/tenant'
import { TenantContext } from '#services/tenant_context'
import ProcessOrderAction from '#actions/tenanted/order/process_order_action'

interface ProcessOrderPayload {
  tenantId: string
  orderId: number
}

export default class ProcessOrderJob {
  static get key() {
    return 'ProcessOrderJob'
  }

  async handle(payload: ProcessOrderPayload) {
    const tenant = await Tenant.findOrFail(payload.tenantId)
    await TenantContext.run(tenant, async () => {
      const action = new ProcessOrderAction()
      await action.execute(payload.orderId)
    })
  }
}
```

**Dispatching:**

```typescript
await ProcessOrderJob.dispatch({
  tenantId: TenantContext.currentOrFail().id,
  orderId: order.id,
})
```

---

## Common Patterns

### Running Code Across All Tenants

```typescript
const tenants = await Tenant.all()
for (const tenant of tenants) {
  await TenantContext.run(tenant, async () => {
    const conn = `tenant_${tenant.id}`
    await db.connection(conn)
      .from('orders')
      .where('status', 'pending')
      .update({ processed: true })
  })
}
```

### Accessing Central Data from Tenant Context

```typescript
// Central models always use the 'central' connection
const allTenants = await Tenant.all() // Always hits landlord DB
```

---

## Single-Database Tenancy Mixin

For simpler cases using a `tenantId` column instead of separate databases:

```typescript
// app/models/mixins/tenant_scoped.ts
import type { NormalizeConstructor } from '@adonisjs/core/types/helpers'
import { BaseModel } from '@adonisjs/lucid/orm'
import { TenantContext } from '#services/tenant_context'

export function TenantScoped<T extends NormalizeConstructor<typeof BaseModel>>(superclass: T) {
  return class extends superclass {
    static boot() {
      if (this.booted) return
      super.boot()

      this.addGlobalScope('tenant', (query) => {
        const tenant = TenantContext.current()
        if (tenant) {
          query.where('tenant_id', tenant.id)
        }
      })

      this.before('create', (instance) => {
        const tenant = TenantContext.current()
        if (tenant && !instance.tenantId) {
          instance.tenantId = tenant.id
        }
      })
    }
  }
}

// Usage:
class Order extends TenantScoped(BaseModel) {
  // queries are automatically scoped to current tenant
}
```
