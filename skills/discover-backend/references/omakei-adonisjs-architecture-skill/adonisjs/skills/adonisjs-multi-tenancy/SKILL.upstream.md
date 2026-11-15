---
name: adonisjs-multi-tenancy
description: Multi-tenant application architecture patterns for AdonisJS. Use when working with multi-tenant systems, tenant isolation, tenant scoping, database-per-tenant, schema-per-tenant, or single-database tenancy in AdonisJS. Trigger whenever the user mentions multi-tenancy, tenants, tenant middleware, tenant context, SaaS architecture, tenant databases, tenant migrations, or tenant-aware models in an AdonisJS project — even if they don't explicitly say "multi-tenant."
---

# AdonisJS Multi-Tenancy

Multi-tenancy separates application logic into **central** (landlord) and **tenanted** (tenant-specific) contexts. AdonisJS supports this via Lucid's ConnectionManager, HttpContext, and Async Local Storage.

**Reference guides:**

- [implementation-patterns.md](references/implementation-patterns.md) — Full code for every component below
- [tenancy-testing.md](references/tenancy-testing.md) — Testing multi-tenant features

## Philosophy

- **Clear separation** between central and tenant contexts
- **Database isolation** via ConnectionManager (database-per-tenant or schema-per-tenant)
- **Request-scoped tenancy** through middleware + HttpContext
- **No shared-memory race conditions** — connections added via `db.manager.add()`, never by mutating config
- **Queue integration** with tenant context preservation

## When to Use

**Database-per-tenant:** SaaS with strict data isolation, compliance requirements, varying data volume per tenant.

**Single-database with tenant scoping:** Simpler apps, shared schema, easier ops. Just add a `tenantId` column and scope queries.

**Schema-per-tenant (PostgreSQL):** Middle ground — isolation without separate DB servers.

This skill focuses on **database-per-tenant** as it needs the most architectural guidance.

## Directory Structure

```
app/
├── actions/
│   ├── central/              # Landlord actions
│   │   └── tenant/
│   │       └── create_tenant_action.ts
│   └── tenanted/             # Tenant-scoped actions
│       └── order/
│           └── create_order_action.ts
├── middleware/
│   └── tenant_middleware.ts   # Resolves + initialises tenant
├── models/                    # All models here (not in subdirs)
│   ├── tenant.ts              # Central model
│   └── order.ts               # Tenanted model
├── services/
│   ├── tenant_context.ts
│   └── tenant_connection_manager.ts
config/
│   └── database.ts            # Central connection only
database/
├── migrations/
│   ├── central/               # Landlord migrations
│   └── tenant/                # Per-tenant migrations
commands/
│   └── tenant_migrate.ts      # Custom ace command
```

## Database Configuration

Register only the **central** (landlord) connection in config. Tenant connections are added dynamically at runtime via ConnectionManager.

```typescript
// config/database.ts
import env from '#start/env'
import { defineConfig } from '@adonisjs/lucid'

const databaseConfig = defineConfig({
  connection: 'central',
  connections: {
    central: {
      client: 'pg',
      connection: {
        host: env.get('DB_HOST'),
        port: env.get('DB_PORT'),
        user: env.get('DB_USER'),
        password: env.get('DB_PASSWORD'),
        database: env.get('DB_DATABASE'),
      },
      migrations: {
        paths: ['database/migrations/central'],
      },
    },
  },
})

export default databaseConfig
```

## Core Components (Summary)

Full implementations are in **[implementation-patterns.md](references/implementation-patterns.md)**.

### TenantConnectionManager

Registers dynamic database connections per tenant using `db.manager.add()`. Key rules:

- **Never mutate `config/database.ts`** at runtime — causes race conditions
- Set `pool.min: 0` on tenant connections to release idle connections
- ConnectionManager deduplicates — safe to call `register()` multiple times

```typescript
// app/services/tenant_connection_manager.ts
export class TenantConnectionManager {
  static register(tenant: Tenant): string {
    const connectionName = `tenant_${tenant.id}`
    if (!db.manager.has(connectionName)) {
      db.manager.add(connectionName, {
        client: 'pg',
        connection: { ...baseConfig, database: tenant.databaseName },
        pool: { min: 0, max: 5 },
      })
    }
    db.manager.connect(connectionName)
    return connectionName
  }

  static async close(tenant: Tenant): Promise<void> { /* ... */ }
}
```

### TenantContext

Accesses the current tenant from HttpContext. Provides `run()` for executing code in a specific tenant's scope (useful for jobs and cross-tenant operations).

```typescript
// app/services/tenant_context.ts
export class TenantContext {
  static current(): Tenant | null        // From HttpContext
  static currentOrFail(): Tenant         // Throws if no tenant
  static connectionName(): string        // `tenant_${id}`
  static isActive(): boolean

  // Run callback in a tenant's context
  static async run<T>(tenant: Tenant, cb: () => Promise<T>): Promise<T>
}
```

### HttpContext Extension

```typescript
// types/context.ts
declare module '@adonisjs/core/http' {
  interface HttpContext {
    tenant?: Tenant
    tenantConnection?: string
  }
}
```

### Tenant Middleware

Resolves tenant from request (subdomain, header, or path), registers the connection, and attaches to HttpContext. Supports three identification strategies:

- **Subdomain:** `acme.myapp.com` → lookup by subdomain
- **Header:** `X-Tenant-ID` header → lookup by ID
- **Path:** `/tenant/:slug/...` → lookup by slug

```typescript
// app/middleware/tenant_middleware.ts
export default class TenantMiddleware {
  async handle(ctx: HttpContext, next: NextFn) {
    const tenant = await this.resolveTenant(ctx)
    if (!tenant) return ctx.response.notFound({ error: 'Tenant not found' })

    ctx.tenant = tenant
    ctx.tenantConnection = TenantConnectionManager.register(tenant)
    return next()
  }
}
```

Register in kernel:

```typescript
// start/kernel.ts
router.named({
  tenant: () => import('#middleware/tenant_middleware'),
})
```

## Routes

```typescript
// start/routes.ts
// Central (landlord)
router.group(() => {
  router.resource('/tenants', '#controllers/central/tenants_controller')
}).prefix('/central')

// Tenant-scoped
router.group(() => {
  router.resource('/orders', '#controllers/tenanted/orders_controller')
}).use(middleware.tenant())
```

## Models

All models live in `app/models/`. Central vs tenanted is distinguished by connection, not subdirectory.

- **Central models** use `static connection = 'central'`
- **Tenanted models** pass connection explicitly in queries: `Order.query({ connection: ctx.tenantConnection })`

```typescript
// Central model
export default class Tenant extends BaseModel {
  static connection = 'central'
  // ...
}

// Tenanted model — pass connection in queries
const orders = await Order
  .query({ connection: ctx.tenantConnection })
  .where('status', 'pending')
```

## Actions Pattern

**Central actions** manage tenants and cross-tenant operations (e.g., `CreateTenantAction`).

**Tenanted actions** operate within a tenant's database using `TenantContext.connectionName()`.

Both use transactions scoped to the correct connection. See [implementation-patterns.md](references/implementation-patterns.md) for full examples.

## Tenant Migrations (Ace Command)

Custom ace command to run tenant-specific migrations for all or a single tenant:

```bash
# All tenants
node ace tenant:migrate

# Specific tenant
node ace tenant:migrate --tenant=acme-corp-id
```

See [implementation-patterns.md](references/implementation-patterns.md#custom-ace-commands) for the full command implementation.

## Queue Jobs

Jobs must store `tenantId` and re-establish context when processed:

```typescript
// Dispatching
await ProcessOrderJob.dispatch({
  tenantId: TenantContext.currentOrFail().id,
  orderId: order.id,
})

// Handling
async handle(payload: ProcessOrderPayload) {
  const tenant = await Tenant.findOrFail(payload.tenantId)
  await TenantContext.run(tenant, async () => {
    // runs in tenant's DB context
  })
}
```

## Single-Database Alternative

For simpler tenancy, use a mixin that auto-scopes queries by `tenantId` column. See [implementation-patterns.md](references/implementation-patterns.md#single-database-tenancy-mixin) for the `TenantScoped` mixin.

## Testing

**[→ Complete testing guide: references/tenancy-testing.md](references/tenancy-testing.md)**

Key points:

- Create/destroy tenant databases in test setup/teardown
- Always pass connection explicitly in test queries
- Separate test directories for central vs tenanted tests
- Use `TestTenantHelper` for tenant lifecycle management
- Test tenant middleware resolution (valid, invalid, missing)

## Best Practices Summary

1. **Never mutate config at runtime** — use `db.manager.add()` instead
2. **Set `pool.min: 0`** on tenant connections to release idle connections
3. **Pass connection explicitly** in all queries — don't rely on global state
4. **Separate directories** for central and tenanted actions/controllers
5. **Keep models in `app/models/`** — distinguish by connection, not location
6. **Preserve tenant context in jobs** by storing `tenantId` in payload
7. **Test both contexts** — central and tenant tests should be fully isolated
