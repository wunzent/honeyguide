# Multi-Tenancy Testing

Testing patterns for multi-tenant AdonisJS applications using Japa test runner.

**Related guides:**

- [Multi-tenancy](../SKILL.md) - Core multi-tenancy patterns

## Test Directory Structure

```
tests/
├── helpers/
│   ├── tenant_helper.ts         # Tenant creation/cleanup utilities
│   └── test_tenant_context.ts   # Test-specific tenant context
├── functional/
│   ├── central/                 # Tests against landlord DB
│   │   └── tenant_management.spec.ts
│   └── tenanted/                # Tests within a tenant context
│       ├── orders.spec.ts
│       └── customers.spec.ts
├── unit/
│   ├── central/
│   │   └── create_tenant_action.spec.ts
│   └── tenanted/
│       └── create_order_action.spec.ts
└── bootstrap.ts
```

## Test Tenant Helper

Provides tenant creation, database setup, and cleanup for tests.

```typescript
// tests/helpers/tenant_helper.ts
import { Tenant } from '#models/tenant'
import { TenantConnectionManager } from '#services/tenant_connection_manager'
import db from '@adonisjs/lucid/services/db'
import { MigrationRunner } from '@adonisjs/lucid/migration'
import app from '@adonisjs/core/services/app'

export class TestTenantHelper {
  private static createdTenants: Tenant[] = []

  /**
   * Create a test tenant with its own database.
   */
  static async createTenant(
    overrides: Partial<{ name: string; subdomain: string }> = {}
  ): Promise<Tenant> {
    const suffix = Math.random().toString(36).substring(7)
    const subdomain = overrides.subdomain ?? `test-${suffix}`
    const databaseName = `test_tenant_${suffix}`

    // Create the database
    await db.rawQuery(`CREATE DATABASE "${databaseName}"`)

    // Create the tenant record in the central DB
    const tenant = await Tenant.create({
      name: overrides.name ?? `Test Tenant ${suffix}`,
      subdomain,
      databaseName,
    })

    // Register the connection
    TenantConnectionManager.register(tenant)

    // Run tenant migrations
    const connectionName = `tenant_${tenant.id}`
    const migrator = new MigrationRunner(
      app.makePath('database/migrations/tenant'),
      { direction: 'up', connectionName }
    )
    await migrator.run()

    this.createdTenants.push(tenant)
    return tenant
  }

  /**
   * Clean up all test tenants created during this test run.
   */
  static async cleanup(): Promise<void> {
    for (const tenant of this.createdTenants) {
      await TenantConnectionManager.close(tenant)
      await db.rawQuery(`DROP DATABASE IF EXISTS "${tenant.databaseName}"`)
      await tenant.delete()
    }
    this.createdTenants = []
  }
}
```

## Testing Central Actions

Central tests operate on the landlord database with no tenant context.

```typescript
// tests/functional/central/tenant_management.spec.ts
import { test } from '@japa/runner'
import { Tenant } from '#models/tenant'
import CreateTenantAction from '#actions/central/tenant/create_tenant_action'

test.group('Tenant Management', (group) => {
  group.each.setup(async () => {
    // Each test starts with a clean state
    await Tenant.query().delete()
  })

  test('creates a new tenant', async ({ assert }) => {
    const action = new CreateTenantAction()

    const tenant = await action.execute({
      name: 'Acme Corp',
      subdomain: 'acme',
    })

    assert.instanceOf(tenant, Tenant)
    assert.equal(tenant.name, 'Acme Corp')
    assert.equal(tenant.subdomain, 'acme')
  })

  test('rejects duplicate subdomains', async ({ assert }) => {
    const action = new CreateTenantAction()

    await action.execute({ name: 'First', subdomain: 'acme' })

    await assert.rejects(
      () => action.execute({ name: 'Second', subdomain: 'acme' }),
      /already exists/
    )
  })
})
```

## Testing Tenanted Actions

Tenanted tests create a temporary tenant database and run within that context.

```typescript
// tests/functional/tenanted/orders.spec.ts
import { test } from '@japa/runner'
import { TestTenantHelper } from '#tests/helpers/tenant_helper'
import { TenantContext } from '#services/tenant_context'
import { Order } from '#models/order'

test.group('Tenanted Orders', (group) => {
  let tenant: Awaited<ReturnType<typeof TestTenantHelper.createTenant>>

  group.setup(async () => {
    tenant = await TestTenantHelper.createTenant()
  })

  group.teardown(async () => {
    await TestTenantHelper.cleanup()
  })

  test('creates an order in tenant context', async ({ assert }) => {
    await TenantContext.run(tenant, async () => {
      const connectionName = `tenant_${tenant.id}`

      const order = await Order.create({
        userId: 1,
        status: 'pending',
        total: 100,
      }, { connection: connectionName })

      assert.instanceOf(order, Order)
      assert.equal(order.status, 'pending')

      // Verify it exists in the tenant DB
      const found = await Order.query({ connection: connectionName })
        .where('id', order.id)
        .firstOrFail()

      assert.equal(found.id, order.id)
    })
  })
})
```

## HTTP Test with Tenant Context

Test tenant-scoped HTTP endpoints by setting the appropriate header or subdomain.

```typescript
// tests/functional/tenanted/orders_api.spec.ts
import { test } from '@japa/runner'
import { TestTenantHelper } from '#tests/helpers/tenant_helper'

test.group('Orders API', (group) => {
  let tenant: Awaited<ReturnType<typeof TestTenantHelper.createTenant>>

  group.setup(async () => {
    tenant = await TestTenantHelper.createTenant({ subdomain: 'testco' })
  })

  group.teardown(async () => {
    await TestTenantHelper.cleanup()
  })

  // Header-based identification
  test('lists orders for tenant', async ({ client, assert }) => {
    const response = await client
      .get('/orders')
      .header('X-Tenant-ID', tenant.id)

    response.assertStatus(200)
    assert.isArray(response.body())
  })

  // Subdomain-based identification (using Host header)
  test('lists orders via subdomain', async ({ client, assert }) => {
    const response = await client
      .get('/orders')
      .header('Host', `${tenant.subdomain}.myapp.test`)

    response.assertStatus(200)
  })

  test('returns 404 for unknown tenant', async ({ client }) => {
    const response = await client
      .get('/orders')
      .header('X-Tenant-ID', 'nonexistent')

    response.assertStatus(404)
  })
})
```

## Japa Test Plugin (Optional)

Create a Japa plugin to automatically manage tenant lifecycle in tests.

```typescript
// tests/helpers/tenant_plugin.ts
import type { PluginFn } from '@japa/runner/types'
import { TestTenantHelper } from '#tests/helpers/tenant_helper'

export function tenantPlugin(): PluginFn {
  return function (config, runner, { TestContext }) {
    // Make tenant helper available on test context
    TestContext.macro('createTenant', async function (overrides = {}) {
      return TestTenantHelper.createTenant(overrides)
    })

    // Auto-cleanup after each test suite
    runner.onSuite((suite) => {
      suite.teardown(async () => {
        await TestTenantHelper.cleanup()
      })
    })
  }
}
```

Register in your test configuration:

```typescript
// tests/bootstrap.ts
import { configure } from '@japa/runner'
import { tenantPlugin } from '#tests/helpers/tenant_plugin'

configure({
  plugins: [tenantPlugin()],
})
```

## Testing Queued Jobs with Tenant Context

```typescript
// tests/unit/tenanted/process_order_job.spec.ts
import { test } from '@japa/runner'
import { TestTenantHelper } from '#tests/helpers/tenant_helper'
import ProcessOrderJob from '#jobs/tenanted/process_order_job'

test.group('ProcessOrderJob', (group) => {
  let tenant: Awaited<ReturnType<typeof TestTenantHelper.createTenant>>

  group.setup(async () => {
    tenant = await TestTenantHelper.createTenant()
  })

  group.teardown(async () => {
    await TestTenantHelper.cleanup()
  })

  test('processes order in correct tenant context', async ({ assert }) => {
    // Create test data in tenant DB
    const connectionName = `tenant_${tenant.id}`
    const [order] = await db.connection(connectionName)
      .table('orders')
      .insert({ user_id: 1, status: 'pending', total: 50 })
      .returning('id')

    // Execute job directly (without queue)
    const job = new ProcessOrderJob()
    await job.handle({ tenantId: tenant.id, orderId: order.id })

    // Verify in tenant DB
    const updated = await db.connection(connectionName)
      .from('orders')
      .where('id', order.id)
      .first()

    assert.equal(updated.status, 'processed')
  })
})
```

## Key Testing Principles

1. **Isolate tenant databases per test group** — create and destroy databases in setup/teardown
2. **Always pass connection explicitly** — don't rely on global state in tests
3. **Test both contexts separately** — central tests should never leak into tenant and vice versa
4. **Use transactions where possible** — for central DB tests, wrap in transactions for speed
5. **Clean up aggressively** — drop test databases in teardown to avoid accumulation
6. **Test tenant resolution** — verify middleware correctly identifies (or rejects) tenants
