---
name: adonisjs-services
description: Service layer for external API integration using the manager/driver pattern in AdonisJS. Use when working with external APIs, third-party services, payment gateways, email providers, SMS, file storage, or when user mentions services, service layer, external API, manager pattern, driver pattern, driver swapping, null driver, API integration, or wrapping third-party SDKs in an AdonisJS project. Also trigger when user asks how to abstract external dependencies for testability or swap implementations at runtime.
---

# AdonisJS Services

External service integrations use a **manager/driver pattern** — a thin abstraction that wraps third-party APIs behind a contract, supports multiple drivers, and provides a null driver for fast, deterministic tests.

**Reference implementations:**
- [ServiceManager base class →](references/service_manager.ts)
- [PaymentService full example →](references/payment_service.ts)
- [Null driver →](references/null_payment_driver.ts)
- [Service provider →](references/payment_provider.ts)
- [Testing services →](references/testing_services.ts)

## When to Use

**Use the service layer when:**
- Integrating external APIs (Stripe, SendGrid, Twilio, S3, etc.)
- Multiple drivers serve the same contract (email via SMTP or SES, payment via Stripe or PayPal)
- You need to swap implementations at runtime (multi-tenant, per-environment)
- You want a null driver for testing without HTTP calls
- Business logic should not depend on a specific vendor

**Do NOT use for:**
- Internal domain logic (use services/actions directly)
- Simple database queries (use Lucid models)
- Validation (use VineJS validators)

---

## Architecture Overview

```
app/
└── services/
    └── payment/
        ├── payment_manager.ts           # Manager — resolves the active driver
        ├── contracts/
        │   └── payment_driver.ts        # Interface all drivers implement
        ├── drivers/
        │   ├── stripe_driver.ts         # Stripe implementation
        │   ├── paypal_driver.ts         # PayPal implementation
        │   └── null_driver.ts           # Deterministic fake for testing
        └── exceptions/
            └── payment_exception.ts     # Domain-specific errors
config/
└── payment.ts                           # Driver selection & credentials
providers/
└── payment_provider.ts                  # Registers manager in IoC container
```

---

## Step-by-Step

### 1. Define the driver contract

```typescript
// app/services/payment/contracts/payment_driver.ts

export interface PaymentIntentResult {
  id: string
  amount: number
  currency: string
  status: 'succeeded' | 'pending' | 'failed'
}

export interface PaymentDriver {
  createPaymentIntent(amount: number, currency: string): Promise<PaymentIntentResult>
  refundPayment(paymentIntentId: string, amount?: number): Promise<boolean>
  retrievePaymentIntent(paymentIntentId: string): Promise<PaymentIntentResult>
}
```

### 2. Create the config

```typescript
// config/payment.ts
import env from '#start/env'
import { defineConfig } from '@adonisjs/core/config'

const paymentConfig = defineConfig({
  default: env.get('PAYMENT_DRIVER', 'stripe'),

  drivers: {
    stripe: {
      apiKey: env.get('STRIPE_API_KEY', ''),
      webhookSecret: env.get('STRIPE_WEBHOOK_SECRET', ''),
    },
    paypal: {
      clientId: env.get('PAYPAL_CLIENT_ID', ''),
      clientSecret: env.get('PAYPAL_CLIENT_SECRET', ''),
    },
  },
})

export default paymentConfig
```

### 3. Implement drivers

```typescript
// app/services/payment/drivers/stripe_driver.ts

import type { PaymentDriver, PaymentIntentResult } from '../contracts/payment_driver.js'
import { PaymentException } from '../exceptions/payment_exception.js'

export class StripeDriver implements PaymentDriver {
  /** HTTP client instance — created once, reused across requests. */
  private baseUrl = 'https://api.stripe.com'

  constructor(
    private readonly apiKey: string,
    private readonly webhookSecret: string
  ) {}

  async createPaymentIntent(amount: number, currency: string): Promise<PaymentIntentResult> {
    const response = await fetch(`${this.baseUrl}/v1/payment_intents`, {
      method: 'POST',
      headers: this.headers(),
      body: new URLSearchParams({
        amount: String(amount),
        currency,
      }),
    })

    if (!response.ok) {
      throw PaymentException.failedRequest(await response.text())
    }

    const data = await response.json()
    return {
      id: data.id,
      amount: data.amount,
      currency: data.currency,
      status: data.status === 'succeeded' ? 'succeeded' : 'pending',
    }
  }

  async refundPayment(paymentIntentId: string, _amount?: number): Promise<boolean> {
    const response = await fetch(`${this.baseUrl}/v1/refunds`, {
      method: 'POST',
      headers: this.headers(),
      body: new URLSearchParams({ payment_intent: paymentIntentId }),
    })
    return response.ok
  }

  async retrievePaymentIntent(paymentIntentId: string): Promise<PaymentIntentResult> {
    const response = await fetch(
      `${this.baseUrl}/v1/payment_intents/${paymentIntentId}`,
      { headers: this.headers() }
    )

    if (!response.ok) {
      throw PaymentException.failedRequest(await response.text())
    }

    const data = await response.json()
    return { id: data.id, amount: data.amount, currency: data.currency, status: data.status }
  }

  private headers(): Record<string, string> {
    return {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    }
  }
}
```

### 4. Create the null driver

```typescript
// app/services/payment/drivers/null_driver.ts

import { randomUUID } from 'node:crypto'
import type { PaymentDriver, PaymentIntentResult } from '../contracts/payment_driver.js'

export class NullPaymentDriver implements PaymentDriver {
  async createPaymentIntent(amount: number, currency: string): Promise<PaymentIntentResult> {
    return {
      id: `pi_test_${randomUUID().slice(0, 8)}`,
      amount,
      currency,
      status: 'succeeded',
    }
  }

  async refundPayment(_paymentIntentId: string, _amount?: number): Promise<boolean> {
    return true
  }

  async retrievePaymentIntent(paymentIntentId: string): Promise<PaymentIntentResult> {
    return {
      id: paymentIntentId,
      amount: 0,
      currency: 'usd',
      status: 'succeeded',
    }
  }
}
```

### 5. Create the manager

```typescript
// app/services/payment/payment_manager.ts

import type { PaymentDriver } from './contracts/payment_driver.js'
import { StripeDriver } from './drivers/stripe_driver.js'
import { NullPaymentDriver } from './drivers/null_driver.js'
import type { ApplicationService } from '@adonisjs/core/types'

export class PaymentManager {
  /** Cache of instantiated drivers — bounded by config (typically 2-3 entries). */
  private drivers = new Map<string, PaymentDriver>()
  private defaultDriver: string

  constructor(private app: ApplicationService) {
    this.defaultDriver = this.app.config.get<string>('payment.default', 'stripe')
  }

  /** Get the driver instance (creates once, reuses thereafter). */
  use(name?: string): PaymentDriver {
    const driverName = name ?? this.defaultDriver
    let driver = this.drivers.get(driverName)

    if (!driver) {
      driver = this.createDriver(driverName)
      this.drivers.set(driverName, driver)
    }

    return driver
  }

  private createDriver(name: string): PaymentDriver {
    switch (name) {
      case 'stripe': {
        const config = this.app.config.get<any>('payment.drivers.stripe')
        return new StripeDriver(config.apiKey, config.webhookSecret)
      }
      case 'null':
        return new NullPaymentDriver()
      default:
        throw new Error(`Unknown payment driver: ${name}`)
    }
  }

  /** Clear cached drivers (useful in tests). */
  flush(): void {
    this.drivers.clear()
  }
}
```

### 6. Register via service provider

```typescript
// providers/payment_provider.ts

import type { ApplicationService } from '@adonisjs/core/types'
import { PaymentManager } from '#services/payment/payment_manager'

export default class PaymentProvider {
  constructor(protected app: ApplicationService) {}

  register() {
    this.app.container.singleton(PaymentManager, () => {
      return new PaymentManager(this.app)
    })
  }

  async shutdown() {
    // Flush driver cache on shutdown to prevent stale references
    const manager = await this.app.container.make(PaymentManager)
    manager.flush()
  }
}
```

Register in `adonisrc.ts`:

```typescript
providers: [
  // ...
  () => import('#providers/payment_provider'),
]
```

### 7. Use in controllers / actions

```typescript
// app/controllers/orders_controller.ts
import { inject } from '@adonisjs/core'
import { PaymentManager } from '#services/payment/payment_manager'

export default class OrdersController {
  @inject()
  async pay({ request, response }: HttpContext, payment: PaymentManager) {
    const { amount, currency } = request.only(['amount', 'currency'])

    const result = await payment.use().createPaymentIntent(amount, currency)

    return response.ok({ data: result })
  }
}
```

Or resolve manually:

```typescript
import app from '@adonisjs/core/services/app'
import { PaymentManager } from '#services/payment/payment_manager'

const payment = await app.container.make(PaymentManager)
const result = await payment.use('stripe').createPaymentIntent(5000, 'usd')
```

---

## Memory Leak Prevention

| Concern | How it's handled |
|---|---|
| **Driver cache is bounded** | `drivers` Map has at most N entries where N = number of configured drivers (typically 2–3). Not per-request. |
| **No EventEmitter usage** | Drivers are plain objects with async methods. No listener accumulation. |
| **Singleton via IoC** | `PaymentManager` is registered as a singleton — one instance for the app lifetime, not per-request. |
| **Shutdown cleanup** | Provider's `shutdown()` calls `manager.flush()` to clear driver references on app stop. |
| **No static connector cache** | Unlike the Laravel example's `static $connector`, drivers are per-manager-instance, tied to the singleton lifecycle. |
| **No closure capture** | Driver constructors take plain config values, not closures or app references. |
| **fetch() is stateless** | Native `fetch()` does not hold persistent connections by default. Each call is independent. |

---

## Testing

### Use null driver (recommended)

Set in `.env.test`:
```env
PAYMENT_DRIVER=null
```

Tests automatically get the null driver — no mocking needed:

```typescript
test('processes payment', async ({ client }) => {
  // NullPaymentDriver returns deterministic 'succeeded' responses
  const response = await client
    .post('/api/orders/1/pay')
    .loginAs(user)
    .json({ amount: 5000, currency: 'usd' })

  response.assertStatus(200)
  response.assertBodyContains({ data: { status: 'succeeded' } })
})
```

### Swap via IoC container (for specific behavior)

```typescript
import app from '@adonisjs/core/services/app'
import { PaymentManager } from '#services/payment/payment_manager'

test('handles payment failure', async ({ client, cleanup }) => {
  app.container.swap(PaymentManager, () => {
    return {
      use: () => ({
        createPaymentIntent: async () => {
          throw new Error('Card declined')
        },
        refundPayment: async () => false,
        retrievePaymentIntent: async () => { throw new Error('Not found') },
      }),
      flush: () => {},
    }
  })

  cleanup(() => app.container.restore(PaymentManager))

  const response = await client
    .post('/api/orders/1/pay')
    .loginAs(user)
    .json({ amount: 5000, currency: 'usd' })

  response.assertStatus(500)
})
```

### Custom fake driver for specific scenarios

```typescript
// tests/fakes/failing_payment_driver.ts
import type { PaymentDriver, PaymentIntentResult } from '#services/payment/contracts/payment_driver'

export class FailingPaymentDriver implements PaymentDriver {
  async createPaymentIntent(): Promise<PaymentIntentResult> {
    throw new Error('Card declined')
  }
  async refundPayment(): Promise<boolean> {
    return false
  }
  async retrievePaymentIntent(): Promise<PaymentIntentResult> {
    throw new Error('Payment not found')
  }
}
```

---

## Adding a New Driver

1. Create `app/services/payment/drivers/paypal_driver.ts` implementing `PaymentDriver`
2. Add config in `config/payment.ts` under `drivers.paypal`
3. Add a `case 'paypal'` in `PaymentManager.createDriver()`
4. Done — switch via `PAYMENT_DRIVER=paypal` or call `payment.use('paypal')`

---

## When to Create a Service vs. Use Directly

| Scenario | Approach |
|---|---|
| One-off API call, no swapping needed | Call `fetch()` directly in your action/service |
| Multiple callers, same API | Create a service class (no manager needed) |
| Multiple drivers for same contract | Full manager/driver pattern |
| Need null driver for fast tests | Full manager/driver pattern |
| Wrapping a complex SDK | Service class + IoC binding |

---

## Summary

| Component | Purpose |
|---|---|
| **Driver contract** | Interface defining the API surface |
| **Concrete drivers** | Vendor-specific implementations (Stripe, PayPal) |
| **Null driver** | Deterministic fake for testing — no HTTP, no mocking |
| **Manager** | Resolves and caches the active driver by name |
| **Service provider** | Registers the manager as a singleton in the IoC container |
| **Config** | Selects the default driver + stores credentials per driver |

**Use for external API integrations. Use null drivers over mocks wherever possible.**
