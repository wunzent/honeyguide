---
name: adonisjs-queue
description: Background jobs and queue processing for async tasks. Use when working with queued jobs, background processing, job retries, scheduled jobs, or when user mentions jobs, queues, workers, async processing, background tasks, AdonisJS queue.
---

# AdonisJS Queue

Background jobs are thin delegation layers to services/actions. Keep domain logic in services, not jobs.

**Related guides:**

- [Actions](../adonisjs-actions/SKILL.md) - Business logic belongs here, not in jobs
- [Events](../adonisjs-events/SKILL.md) - Use events + listeners to trigger job dispatching
- Scheduler — Recurring jobs via cron or intervals

---

## Core Concept

Jobs should:

- **Accept a typed payload** as their input contract
- **Delegate to a service/action** for the actual work
- **Handle failure** via the `failed()` method (notifications, logging, cleanup)
- **NOT contain business logic** — that belongs in services

---

## Installation

```bash
node ace add @adonisjs/queue
```

This registers the queue provider, creates `config/queue.ts`, and scaffolds `start/scheduler.ts`.

> **Note:** `@adonisjs/queue` is currently experimental. Pin your version in `package.json`.

---

## Configuration

```typescript
// config/queue.ts
import env from '#start/env'
import { defineConfig, drivers } from '@adonisjs/queue'

export default defineConfig({
  default: env.get('QUEUE_DRIVER', 'redis'),

  adapters: {
    redis: drivers.redis({
      connectionName: 'main',       // from config/redis.ts
    }),
    database: drivers.database({
      connectionName: 'primary',    // from config/database.ts
    }),
    sync: drivers.sync(),           // executes immediately — for dev/testing
  },

  worker: {
    concurrency: 5,
    idleDelay: '2s',
  },

  // Global retry defaults (overridable per queue or per job)
  retry: {
    maxRetries: 3,
  },

  // Per-queue retry overrides
  queues: {
    emails: {
      retry: { maxRetries: 5 },
    },
    payments: {
      retry: { maxRetries: 1 },
    },
  },

  locations: ['./app/jobs/**/*.{ts,js}'],
})
```

**Adapters:**

- `drivers.redis()` — recommended for production; requires `@adonisjs/redis`
- `drivers.database()` — uses Lucid (PostgreSQL, MySQL, SQLite); avoids extra infrastructure
- `drivers.sync()` — runs jobs immediately in-process; use in `development` / `test` environments

Use `QUEUE_DRIVER` env var to switch adapters per environment.

---

## Basic Job Structure

```typescript
// app/jobs/process_order_job.ts
import { Job } from '@adonisjs/queue'
import type { JobOptions } from '@adonisjs/queue/types'
import { inject } from '@adonisjs/core'
import ProcessOrderService from '#services/process_order_service'
import Order from '#models/order'
import logger from '@adonisjs/core/services/logger'

interface ProcessOrderPayload {
  orderId: number
}

@inject()
export default class ProcessOrderJob extends Job<ProcessOrderPayload> {
  static options: JobOptions = {
    queue: 'default',
    maxRetries: 3,
    priority: 5,
  }

  constructor(private processOrderService: ProcessOrderService) {
    super()
  }

  async execute() {
    const order = await Order.findOrFail(this.payload.orderId)
    await this.processOrderService.handle(order)
  }

  async failed(error: Error) {
    // Called after all retries are exhausted
    logger.error(`ProcessOrderJob permanently failed for order ${this.payload.orderId}: ${error.message}`)
    // Notify team, trigger refund, etc.
  }
}
```

**Job methods:**

- `execute()` — required; any thrown error triggers the retry mechanism
- `failed(error)` — optional; runs after all retries are exhausted; use for cleanup/notifications

---

## Job Options

```typescript
static options: JobOptions = {
  queue: 'payments',      // Named queue (default: 'default')
  maxRetries: 5,          // Max retry attempts (default: 3)
  priority: 1,            // 1–10, lower = processed first (default: 5)
  timeout: '2m',          // Max execution time ('30s', '5m', or ms number)
  failOnTimeout: true,    // Mark failed on timeout vs retry (default: true)
  retry: {
    strategy: 'exponential',
    delay: 5000,          // Base delay in ms
  },
  removeOnComplete: true, // Clean up completed job records
}
```

---

## Dispatching Jobs

```typescript
import ProcessOrderJob from '#jobs/process_order_job'

// Basic dispatch
await ProcessOrderJob.dispatch({ orderId: 123 })

// Dispatch to a specific queue
await ProcessOrderJob.dispatch({ orderId: 123 }, { queue: 'payments' })

// Delayed dispatch
await ProcessOrderJob.dispatch({ orderId: 123 }, { delay: '10m' })

// With custom retry for this dispatch only
await ProcessOrderJob.dispatch({ orderId: 123 }, {
  maxRetries: 1,
  retry: { strategy: 'fixed', delay: 30_000 },
})
```

---

## Retry & Backoff Strategies

**Configure globally in `config/queue.ts`:**

```typescript
retry: {
  maxRetries: 3,
  strategy: 'exponential',
  delay: 5000,    // 5s → 20s → 40s...
}
```

**Override per job:**

```typescript
static options: JobOptions = {
  maxRetries: 5,
  retry: {
    strategy: 'exponential',  // 'exponential' | 'linear' | 'fixed'
    delay: 2000,
  },
}
```

**Override per dispatch:**

```typescript
await SendInvoiceJob.dispatch({ invoiceId: 42 }, {
  maxRetries: 3,
  retry: { strategy: 'fixed', delay: 60_000 },
})
```

**Backoff strategies:**

- `exponential` — delay doubles each attempt (5s → 20s → 40s...)
- `linear` — delay increases by a fixed amount each attempt
- `fixed` — same delay between every attempt

---

## Failure Handling

```typescript
export default class ChargeSubscriptionJob extends Job<{ subscriptionId: number }> {
  static options: JobOptions = {
    queue: 'payments',
    maxRetries: 3,
    retry: { strategy: 'exponential', delay: 60_000 },
  }

  constructor(
    private chargeSubscriptionService: ChargeSubscriptionService,
    private notifyPaymentFailedService: NotifyPaymentFailedService,
  ) {
    super()
  }

  async execute() {
    const subscription = await Subscription.findOrFail(this.payload.subscriptionId)
    await this.chargeSubscriptionService.handle(subscription)
  }

  async failed(error: Error) {
    const subscription = await Subscription.find(this.payload.subscriptionId)

    if (subscription) {
      await this.notifyPaymentFailedService.handle(subscription, error)
    }

    logger.error({
      job: 'ChargeSubscriptionJob',
      subscriptionId: this.payload.subscriptionId,
      error: error.message,
    })
  }
}
```

---

## Named Queues

Separate jobs by priority or concern using named queues:

```typescript
// High-priority payments queue
export default class ProcessPaymentJob extends Job<PaymentPayload> {
  static options: JobOptions = { queue: 'payments', priority: 1 }
  // ...
}

// Lower-priority email queue
export default class SendWelcomeEmailJob extends Job<EmailPayload> {
  static options: JobOptions = { queue: 'emails', priority: 5 }
  // ...
}
```

**Start workers for specific queues:**

```bash
node ace queue:work
node ace queue:work --queue=payments
node ace queue:work --queue=payments,emails
```

---

## Event Listeners Dispatching Jobs

Use AdonisJS Emitter + class-based listeners to dispatch jobs in response to domain events — the AdonisJS equivalent of Laravel event listeners triggering queued jobs.

**1. Define the event:**

```typescript
// app/events/order_placed.ts
import Order from '#models/order'

export default class OrderPlaced {
  constructor(public order: Order) {}
}
```

**2. Create the listener:**

```typescript
// app/listeners/send_order_confirmation_listener.ts
import OrderPlaced from '#events/order_placed'
import SendOrderConfirmationJob from '#jobs/send_order_confirmation_job'

export default class SendOrderConfirmationListener {
  async handle(event: OrderPlaced) {
    await SendOrderConfirmationJob.dispatch({ orderId: event.order.id })
  }
}
```

**3. Register in `start/events.ts`:**

```typescript
import emitter from '@adonisjs/core/services/emitter'
import OrderPlaced from '#events/order_placed'

emitter.on(OrderPlaced, [
  () => import('#listeners/send_order_confirmation_listener'),
])
```

**4. Dispatch the event from a controller or service:**

```typescript
import emitter from '@adonisjs/core/services/emitter'
import OrderPlaced from '#events/order_placed'

const order = await Order.create(data)
await emitter.emit(OrderPlaced, new OrderPlaced(order))
```

> Lazy-load listeners (`() => import(...)`) to keep boot time fast.

---

## Scheduled / Recurring Jobs

Define recurring jobs in `start/scheduler.ts`:

```typescript
// start/scheduler.ts
import scheduler from '@adonisjs/queue/services/scheduler'
import SendDailyDigestJob from '#jobs/send_daily_digest_job'
import CleanStaleSessionsJob from '#jobs/clean_stale_sessions_job'
import SyncInventoryJob from '#jobs/sync_inventory_job'

// Cron expression
scheduler.schedule(SendDailyDigestJob, '0 8 * * *')     // 8am every day

// Human-readable interval
scheduler.schedule(CleanStaleSessionsJob, { every: '1h' })

// With date boundaries and run limit
scheduler.schedule(SyncInventoryJob, { every: '15m' })
  .from(new Date('2025-01-01'))
  .to(new Date('2025-12-31'))
  .times(1000)
```

---

## Dependency Injection in Jobs

Jobs are resolved through the IoC container — type-hint services in the constructor:

```typescript
import { inject } from '@adonisjs/core'
import type { Logger } from '@adonisjs/core/logger'
import ResizeImageService from '#services/resize_image_service'

@inject()
export default class ResizeUploadedImageJob extends Job<{ fileId: string }> {
  constructor(
    private resizeImageService: ResizeImageService,
    private logger: Logger,
  ) {
    super()
  }

  async execute() {
    this.logger.info(`Resizing file ${this.payload.fileId}`)
    await this.resizeImageService.handle(this.payload.fileId)
  }
}
```

> **Note:** You cannot inject `HttpContext` into jobs — the HTTP request will be gone by the time the worker runs.

---

## Good vs Bad Patterns

```typescript
// ❌ Bad — business logic inside the job
export default class ProcessOrderJob extends Job<{ orderId: number }> {
  async execute() {
    const order = await Order.findOrFail(this.payload.orderId)
    order.status = 'processing'
    await order.save()
    await stripe.charges.create({ amount: order.total, currency: 'usd' })
    await mail.send(new OrderConfirmationMail(order))
  }
}

// ✅ Good — job delegates to a service
@inject()
export default class ProcessOrderJob extends Job<{ orderId: number }> {
  constructor(private processOrderService: ProcessOrderService) {
    super()
  }

  async execute() {
    const order = await Order.findOrFail(this.payload.orderId)
    await this.processOrderService.handle(order)
  }
}
```

---

## Running Workers

```bash
# All queues
node ace queue:work

# Specific queue
node ace queue:work --queue=payments

# Multiple queues
node ace queue:work --queue=payments,emails,default
```

In production, use PM2 or Supervisor to keep workers alive and restart on crash.

---

## Testing

**Fake the queue to assert dispatches without executing jobs:**

```typescript
import { test } from '@japa/runner'
import ProcessOrderJob from '#jobs/process_order_job'

test.group('OrdersController', (group) => {
  test('dispatches ProcessOrderJob after creating an order', async ({ client, assert }) => {
    // Use the sync adapter in test env (QUEUE_DRIVER=sync in .env.test)
    // or fake the queue service to capture dispatches

    const response = await client.post('/orders').json({ /* valid payload */ })
    response.assertStatus(201)

    // Assert the job was dispatched with the correct payload
    // (exact API depends on your testing setup — see QueueFake if available)
  })
})
```

**Use the `sync` adapter for integration tests** — jobs run immediately without a worker:

```bash
# .env.test
QUEUE_DRIVER=sync
```

With `sync`, `execute()` runs inline during the test so you can assert side effects directly.

---

## Job Organisation

```
app/
└── jobs/
    ├── process_order_job.ts
    ├── send_welcome_email_job.ts
    ├── charge_subscription_job.ts
    ├── resize_uploaded_image_job.ts
    └── send_daily_digest_job.ts

start/
├── events.ts      # Event → listener bindings (lazy-loaded)
└── scheduler.ts   # Recurring job schedules

app/
└── listeners/
    ├── send_order_confirmation_listener.ts
    └── provision_stripe_customer_listener.ts
```

---

## Summary

**Jobs should:**

- Have a typed payload interface
- Call a service/action in `execute()`
- Handle permanent failure in `failed()` (notify, log, clean up)
- Use `static options` to configure queue, retries, priority, and timeout
- Use `@inject()` + constructor DI for service dependencies
- Be dispatched from controllers, services, or event listeners

**Jobs should NOT:**

- Contain business logic (use Services)
- Access `HttpContext` (unavailable in workers)
- Make data-flow decisions (the service's responsibility)
- Use the `sync` adapter in production
