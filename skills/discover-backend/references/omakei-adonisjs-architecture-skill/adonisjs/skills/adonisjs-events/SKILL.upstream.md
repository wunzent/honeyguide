---
name: adonisjs-events
description: Event-driven architecture with AdonisJS Emitter. Use when working with events, listeners, emitter, event classes, decoupling side effects, or when user mentions events, emit, listen, emitter, event listeners, AdonisJS events.
---

# AdonisJS Events

Events decouple side effects from core application logic. When you emit an event, all registered listeners execute asynchronously without blocking the caller.

**Related guides:**

- [Jobs](../adonisjs-jobs/SKILL.md) - Dispatch jobs from listeners for heavy background work
- [Actions](../adonisjs-actions/SKILL.md) - Listeners delegate to actions/services, not hold logic
- Dependency Injection — Listener classes support full constructor injection

---

## Philosophy

- **Events are data containers** — they hold what happened, nothing more
- **Listeners are thin** — delegate to services for any real work
- **All registrations live in `start/events.ts`** — one authoritative place
- **Always lazy-load listener imports** — avoids boot-time overhead and circular deps
- **Always handle errors** — unhandled listener errors crash the process
- **Always clean up dynamic listeners** — inline `on()` calls outside `start/events.ts` leak memory

---

## Two Approaches

AdonisJS supports **class-based events** (preferred) and **string-based events**.

| | Class-based | String-based |
|---|---|---|
| Type safety | Built-in (class is the type) | Requires module augmentation |
| Discoverability | Auto-discovered via barrel | Must be manually declared |
| Refactoring | Rename class → IDE handles it | String renames are fragile |
| Recommended | ✅ Yes | Only for framework/package events |

---

## Class-Based Events (Preferred)

### 1. Create the event class

```bash
node ace make:event UserRegistered
```

```typescript
// app/events/user_registered.ts
import { BaseEvent } from '@adonisjs/core/events'
import User from '#models/user'

export default class UserRegistered extends BaseEvent {
  constructor(public user: User) {
    super()
  }
}
```

Events are **pure data containers**. No methods, no logic — just a typed constructor that
documents what the event carries.

### 2. Create a listener class

```bash
node ace make:listener SendVerificationEmail
```

```typescript
// app/listeners/send_verification_email.ts
import { inject } from '@adonisjs/core'
import { events } from '#generated/events'
import MailService from '#services/mail_service'

@inject()
export default class SendVerificationEmail {
  constructor(private mailService: MailService) {}

  async handle(event: events.UserRegistered) {
    await this.mailService.sendVerification(event.user)
  }
}
```

### 3. Register in `start/events.ts`

```typescript
// start/events.ts
import emitter from '@adonisjs/core/services/emitter'
import { events } from '#generated/events'
import { listeners } from '#generated/listeners'

// Single listener
emitter.on(events.UserRegistered, listeners.SendVerificationEmail)

// Multiple listeners for the same event — all run in parallel
emitter.listen(events.UserRegistered, [
  listeners.SendVerificationEmail,
  listeners.RegisterWithStripe,
  listeners.LogSignup,
])
```

### 4. Dispatch the event

```typescript
// app/controllers/users_controller.ts
import { events } from '#generated/events'

export default class UsersController {
  async store({ request }: HttpContext) {
    const user = await User.create(request.only(['email', 'password']))

    // Class-based events use the static dispatch() method
    events.UserRegistered.dispatch(user)

    return user
  }
}
```

---

## String-Based Events

Use these only for framework/package events, or when integrating third-party code that emits string events. For your own domain events, prefer class-based.

### Define types

```typescript
// types/events.ts
import User from '#models/user'
import Order from '#models/order'

declare module '@adonisjs/core/types' {
  interface EventsList {
    'user:registered': User
    'order:placed': { order: Order; userId: number }
  }
}
```

### Register and emit

```typescript
// start/events.ts
import emitter from '@adonisjs/core/services/emitter'

emitter.on('user:registered', (user) => {
  // user is typed as User
})
```

```typescript
// Anywhere in your app
import emitter from '@adonisjs/core/services/emitter'

emitter.emit('user:registered', user)
```

---

## Listener Registration Methods

### `emitter.on` — persistent listener

Fires every time the event is emitted. Registered in `start/events.ts`.

```typescript
emitter.on(events.UserRegistered, listeners.SendVerificationEmail)
```

### `emitter.once` — fires once, then auto-removes

Safe to use anywhere — self-cleaning, no memory leak risk.

```typescript
emitter.once(events.UserRegistered, (event) => {
  // runs exactly once
})
```

### `emitter.listen` — multiple listeners in one call

All listeners run in parallel.

```typescript
emitter.listen(events.OrderPlaced, [
  listeners.SendOrderConfirmation,
  listeners.UpdateInventory,
  listeners.NotifyWarehouse,
])
```

### `emitter.onAny` — fires for every event

Use only for global cross-cutting concerns (logging, tracing). Store the unsubscribe handle.

```typescript
// start/events.ts
const unsubscribe = emitter.onAny((name, event) => {
  logger.debug({ event: name }, 'Event emitted')
})

// If this were in a short-lived context, call unsubscribe() to clean up.
// In start/events.ts it lives for the app lifetime — no cleanup needed.
```

---

## Dependency Injection in Listeners

Listener classes are resolved through the IoC container. Inject services via the constructor:

```typescript
import { inject } from '@adonisjs/core'
import { events } from '#generated/events'
import OrderReportService from '#services/order_report_service'
import NotificationService from '#services/notification_service'

@inject()
export default class GenerateOrderReport {
  constructor(
    private reportService: OrderReportService,
    private notificationService: NotificationService,
  ) {}

  async handle(event: events.OrderPlaced) {
    const report = await this.reportService.generate(event.order)
    await this.notificationService.sendReport(event.order.userId, report)
  }
}
```

> `HttpContext` **cannot** be injected — events are async and the request may be long gone.

---

## Error Handling

Listeners run in parallel. If one throws, others are unaffected — but the error becomes
an unhandled promise rejection that **can crash your process**. Always register a global
error handler in `start/events.ts`.

```typescript
// start/events.ts
import emitter from '@adonisjs/core/services/emitter'
import logger from '@adonisjs/core/services/logger'

// ✅ Global error handler — catches errors from ALL listeners
emitter.onError((eventName, error, eventData) => {
  logger.error({
    event: String(eventName),
    error: error.message,
    stack: error.stack,
  }, 'Event listener error')

  // Optionally report to Sentry, Datadog, etc.
})
```

---

## ⚠️ Memory Leak Prevention

This is the most critical section. The AdonisJS emitter (backed by Emittery) holds strong references to every listener function registered with `on()`. If you register listeners outside `start/events.ts` without cleaning up, those references accumulate forever.

### Rule 1: Never call `emitter.on()` inside request handlers, loops, or short-lived code

Every call to `on()` stacks another listener. Over thousands of requests, this exhausts memory.

```typescript
// ❌ LEAK — new listener added on every request, never removed
export default class OrdersController {
  async store({ request }: HttpContext) {
    const order = await Order.create(request.body())

    // This registers a NEW listener on every single HTTP request
    emitter.on(events.OrderPlaced, (event) => {
      sendConfirmation(event.order)
    })

    events.OrderPlaced.dispatch(order)
  }
}

// ✅ CORRECT — dispatch the event; the listener lives in start/events.ts
export default class OrdersController {
  async store({ request }: HttpContext) {
    const order = await Order.create(request.body())
    events.OrderPlaced.dispatch(order)
  }
}
```

### Rule 2: Always store and call the unsubscribe function for dynamic listeners

If you must register a listener dynamically (e.g. in a service class, a test, or a command), always hold the returned unsubscribe handle and call it when done.

```typescript
// ❌ LEAK — unsubscribe handle is discarded, listener stays forever
class PaymentPoller {
  start() {
    emitter.on(events.PaymentReceived, this.handlePayment.bind(this))
  }
}

// ✅ CORRECT — unsubscribe handle is stored and called on stop
class PaymentPoller {
  #unsubscribe?: () => void

  start() {
    this.#unsubscribe = emitter.on(events.PaymentReceived, this.handlePayment.bind(this))
  }

  stop() {
    this.#unsubscribe?.()
  }
}
```

### Rule 3: Use `once()` for one-shot listeners — never `on()` with manual deregistration

```typescript
// ❌ FRAGILE — relies on manual cleanup being called; leaks if cleanup is missed
const handler = (event: events.UserVerified) => { /* ... */ }
emitter.on(events.UserVerified, handler)
// ...later...
emitter.off(events.UserVerified, handler)  // what if this is never reached?

// ✅ CORRECT — self-cleaning, guaranteed to run exactly once
emitter.once(events.UserVerified, (event) => {
  // runs once, unsubscribes itself automatically
})
```

### Rule 4: Always restore fakes in tests

`emitter.fake()` replaces the real emitter. Forgetting `emitter.restore()` leaks the fake
across tests, causing false assertions and listener accumulation.

```typescript
// ❌ LEAK in tests — fake is never restored, bleeds into subsequent tests
test('dispatches UserRegistered', async ({ client }) => {
  const fakeEmitter = emitter.fake()
  await client.post('/signup').form({ email: 'a@b.com', password: 'secret' })
  fakeEmitter.assertEmitted(events.UserRegistered)
  // restore() never called!
})

// ✅ CORRECT — cleanup registered before the test body runs
test('dispatches UserRegistered', async ({ client, cleanup }) => {
  const fakeEmitter = emitter.fake()
  cleanup(() => emitter.restore())   // ← runs even if the test fails

  await client.post('/signup').form({ email: 'a@b.com', password: 'secret' })
  fakeEmitter.assertEmitted(events.UserRegistered)
})
```

### Rule 5: Never use anonymous arrow functions with `off()`

`off()` matches listeners by reference. Anonymous functions are unique objects — you cannot remove them.

```typescript
// ❌ BUG — off() has no effect; different function reference
emitter.on(events.OrderPlaced, (e) => handleOrder(e))
emitter.off(events.OrderPlaced, (e) => handleOrder(e))  // different arrow fn!

// ✅ CORRECT — named reference, or use the unsubscribe handle from on()
function handleOrder(event: events.OrderPlaced) { /* ... */ }
emitter.on(events.OrderPlaced, handleOrder)
emitter.off(events.OrderPlaced, handleOrder)

// OR — preferred: use the returned unsubscribe handle
const unsubscribe = emitter.on(events.OrderPlaced, (e) => handleOrder(e))
unsubscribe()  // removes the exact listener, reference-safe
```

### Rule 6: Be careful with `onAny` in services

`onAny` catches every event. One registration per service instance is fine. Multiple registrations in e.g. a singleton that re-registers on each call will grow without bound.

```typescript
// ❌ LEAK — if this service is instantiated repeatedly, listeners stack up
class AuditService {
  setup() {
    emitter.onAny((name, data) => this.audit(name, data))
  }
}

// ✅ CORRECT — register once in start/events.ts, or guard with a flag
// start/events.ts
emitter.onAny((name, data) => {
  auditService.audit(name, data)
})
```

---

## Unsubscribing Patterns Summary

```typescript
// 1. Returned handle (preferred for dynamic listeners)
const off = emitter.on(events.OrderPlaced, handler)
off()

// 2. emitter.off (requires named function reference)
emitter.on(events.OrderPlaced, namedHandler)
emitter.off(events.OrderPlaced, namedHandler)

// 3. Clear all listeners for one event
emitter.clearListeners(events.OrderPlaced)
emitter.clearListeners('user:registered')

// 4. Nuclear option — clears everything (useful in test teardown)
emitter.clearAllListeners()
```

---

## Testing

### Fake the emitter — assert without running listeners

```typescript
import { test } from '@japa/runner'
import emitter from '@adonisjs/core/services/emitter'
import { events } from '#generated/events'

test.group('User signup', (group) => {
  test('emits UserRegistered after account creation', async ({ client, cleanup }) => {
    const fakeEmitter = emitter.fake()
    cleanup(() => emitter.restore())  // always restore, even on failure

    await client.post('/signup').form({
      email: 'user@example.com',
      password: 'secret123',
    })

    fakeEmitter.assertEmitted(events.UserRegistered)
  })

  test('does not emit on validation failure', async ({ client, cleanup }) => {
    const fakeEmitter = emitter.fake()
    cleanup(() => emitter.restore())

    await client.post('/signup').form({ email: 'not-an-email' })

    fakeEmitter.assertNotEmitted(events.UserRegistered)
  })
})
```

### Fake only specific events

Other events continue to fire their real listeners normally.

```typescript
emitter.fake([events.UserRegistered, events.OrderPlaced])
```

### Assertions

```typescript
const fakeEmitter = emitter.fake()

fakeEmitter.assertEmitted(events.UserRegistered)
fakeEmitter.assertNotEmitted(events.OrderUpdated)
fakeEmitter.assertEmittedCount(events.OrderUpdated, 3)
fakeEmitter.assertNoneEmitted()

// Assert with payload check
fakeEmitter.assertEmitted(events.OrderPlaced, ({ data }) => {
  return data.order.id === expectedOrderId
})
```

---

## Listeners and Heavy I/O — Dispatch a Job

`emitter.emit()` awaits all listeners **sequentially**. A listener that calls a service which sends email, hits a webhook, or generates a PDF will block that entire chain and hold the response.

**Rule:** If the work a listener triggers involves external I/O (email, webhooks, PDF generation, third-party APIs), dispatch a **job** instead of calling the service directly.

```typescript
// ❌ BAD — blocks the emitter; slow mail call holds everything behind it
@inject()
export default class SendOrderConfirmation {
  constructor(private mailService: MailService) {}

  async handle(event: events.OrderPlaced) {
    await this.mailService.sendConfirmation(event.order) // slow — blocks emitter
  }
}

// ✅ GOOD — dispatch a job; listener returns immediately; no memory leak risk
import SendOrderConfirmationJob from '#jobs/send_order_confirmation_job'

export default class SendOrderConfirmation {
  async handle(event: events.OrderPlaced) {
    await SendOrderConfirmationJob.dispatch({ orderId: event.order.id })
  }
}
```

When a service call is **fast and non-I/O** (e.g. writing an audit log row to the local DB), calling it directly from a listener is acceptable.

---

## Event & Listener Organisation

```
app/
├── events/
│   ├── user_registered.ts
│   ├── order_placed.ts
│   ├── payment_received.ts
│   └── subscription_cancelled.ts
└── listeners/
    ├── send_verification_email.ts
    ├── register_with_stripe.ts
    ├── send_order_confirmation.ts
    └── log_signup.ts

start/
└── events.ts   ← ALL emitter.on() / emitter.listen() calls live here
```

---

## Summary

**Do:**

- Define events as `BaseEvent` subclasses with typed constructors
- Put all `emitter.on()` / `emitter.listen()` registrations in `start/events.ts`
- Lazy-load listener imports: `() => import('#listeners/...')`
- Register `emitter.onError()` to prevent unhandled rejections crashing your app
- Use `once()` for one-shot listeners
- Store the unsubscribe handle when calling `on()` dynamically
- Restore fakes with `emitter.restore()` after every test using the `cleanup` hook
- Inject services into listeners via `@inject()` constructor DI

**Never:**

- Call `emitter.on()` inside request handlers, loops, or per-request code
- Discard the unsubscribe handle from a dynamic `on()` call
- Use anonymous arrow functions as arguments to `emitter.off()`
- Leave `emitter.fake()` unrestore'd after a test
- Put business logic directly in listeners — delegate to services
- Inject or use `HttpContext` in listeners
- Call a service directly from a listener when it performs I/O — dispatch a job instead (see below)
