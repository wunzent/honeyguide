---
name: adonisjs-exceptions
description: Custom exceptions with static factories and self-contained HTTP responses. Use when working with error handling, custom exceptions, business rule violations, or when user mentions exceptions, custom exception, error handling, HTTP exceptions, exception handler, AdonisJS exceptions.
---

# AdonisJS Exceptions

Custom exceptions use **static factory methods** and extend the base `Exception` class. Each exception owns its own HTTP response and reporting logic — the global handler is only for cross-cutting concerns.

**Related guides:**

- [Actions](../adonisjs-actions/SKILL.md) - Throw exceptions from actions/services to signal business rule violations
- Global handler (`app/exceptions/handler.ts`) — cross-cutting error formatting and monitoring

---

## Custom Exception Structure

```typescript
// app/exceptions/order_exception.ts
import { Exception } from '@adonisjs/core/exceptions'
import { HttpContext } from '@adonisjs/core/http'
import type Order from '#models/order'

export default class OrderException extends Exception {
  // ─── Static Factory Methods ───────────────────────────────────────────────

  static notFound(orderId: string | number) {
    return new this(`Order ${orderId} not found.`, { status: 404, code: 'E_ORDER_NOT_FOUND' })
  }

  static cannotCancel(order: Order) {
    return new this(
      `Order ${order.uuid} cannot be cancelled in its current state.`,
      { status: 400, code: 'E_ORDER_CANNOT_CANCEL' }
    )
  }

  static insufficientStock(productName: string) {
    return new this(
      `Insufficient stock for product: ${productName}`,
      { status: 422, code: 'E_INSUFFICIENT_STOCK' }
    )
  }

  static paymentFailed(reason: string) {
    return new this(`Payment failed: ${reason}`, { status: 402, code: 'E_PAYMENT_FAILED' })
  }

  // ─── Self-contained HTTP Response ─────────────────────────────────────────

  handle(error: this, { response, request }: HttpContext) {
    // JSON for API requests, plain text for others
    if (request.accepts(['json'])) {
      return response.status(error.status).send({
        code: error.code,
        message: error.message,
      })
    }

    return response.status(error.status).send(error.message)
  }

  // ─── Self-contained Reporting ─────────────────────────────────────────────

  report(error: this, { logger, auth }: HttpContext) {
    // 4xx client errors: log at warn level, not error
    if (error.status < 500) {
      logger.warn({ code: error.code, userId: auth.user?.id }, error.message)
      return
    }

    logger.error({ code: error.code, userId: auth.user?.id }, error.message)
  }
}
```

---

## Usage

### Throwing in services / actions

```typescript
import OrderException from '#exceptions/order_exception'

// Throw directly
throw OrderException.notFound(orderId)
throw OrderException.cannotCancel(order)
throw OrderException.insufficientStock(product.name)
```

### Guard methods in services

Group all precondition checks into a private `guard()` method, keeping the happy path clean:

```typescript
// app/services/cancel_order_service.ts
import { inject } from '@adonisjs/core'
import OrderException from '#exceptions/order_exception'
import type Order from '#models/order'

@inject()
export default class CancelOrderService {
  async handle(order: Order): Promise<Order> {
    this.guard(order)

    order.status = 'cancelled'
    await order.save()

    return order
  }

  private guard(order: Order): void {
    if (!order.canBeCancelled()) {
      throw OrderException.cannotCancel(order)
    }
  }
}
```

### Multiple guards

```typescript
private guard(order: Order): void {
  if (!order.isPending()) {
    throw OrderException.cannotProcess(order)
  }

  if (!order.hasItems()) {
    throw OrderException.orderHasNoItems(order)
  }

  if (!order.user.isActive()) {
    throw OrderException.userInactive(order.userId)
  }
}
```

---

## Key Patterns

### 1. Static factory methods

Named constructors make throw sites read like prose and carry all context:

```typescript
// ✅ Descriptive, typed, carries context
throw OrderException.notFound(orderId)

// ❌ Generic, no context, no type
throw new Error('Not found')
```

Each factory receives only what it needs to build a helpful message:

```typescript
static notFound(orderId: string | number) {
  return new this(`Order ${orderId} not found.`, { status: 404, code: 'E_ORDER_NOT_FOUND' })
}
```

### 2. HTTP status + error code

Always pass both `status` and `code` to the `Exception` constructor:

```typescript
new this('Message', { status: 404, code: 'E_ORDER_NOT_FOUND' })
```

The `code` is a machine-readable constant (screaming snake case, prefixed with `E_`) that clients and monitoring tools can key on without parsing the message string.

### 3. Descriptive messages with context

Include the entity identifier and the reason — messages should explain *what* failed and *why*:

```typescript
// ✅ Good — who, what, why
`Order ${order.uuid} cannot be cancelled in its current state.`
`Insufficient stock for product: ${productName}`
`Payment failed: ${reason}`

// ❌ Bad — generic, no context
'Cannot cancel order'
'Stock error'
```

### 4. `handle()` — self-contained HTTP response

When a custom exception implements `handle()`, it produces its own HTTP response and the global handler is bypassed. Use content negotiation to serve the right format:

```typescript
handle(error: this, { response, request }: HttpContext) {
  if (request.accepts(['json'])) {
    return response.status(error.status).send({
      code: error.code,
      message: error.message,
    })
  }

  return response.status(error.status).send(error.message)
}
```

### 5. `report()` — self-contained logging

When an exception implements `report()`, it controls its own logging. Separate severity by status range:

```typescript
report(error: this, { logger, auth }: HttpContext) {
  if (error.status < 500) {
    logger.warn({ code: error.code }, error.message)
    return
  }
  logger.error({ code: error.code, userId: auth.user?.id }, error.message)
}
```

---

## Real-World Examples

### Payment exception

```typescript
// app/exceptions/payment_exception.ts
import { Exception } from '@adonisjs/core/exceptions'
import { HttpContext } from '@adonisjs/core/http'

export default class PaymentException extends Exception {
  static declined(last4: string) {
    return new this(`Card ending in ${last4} was declined.`, {
      status: 402,
      code: 'E_PAYMENT_DECLINED',
    })
  }

  static insufficientFunds() {
    return new this('Insufficient funds.', { status: 402, code: 'E_INSUFFICIENT_FUNDS' })
  }

  static gatewayTimeout(gateway: string) {
    return new this(`Payment gateway ${gateway} timed out.`, {
      status: 503,
      code: 'E_GATEWAY_TIMEOUT',
    })
  }

  handle(error: this, { response }: HttpContext) {
    return response.status(error.status).send({ code: error.code, message: error.message })
  }

  report(error: this, { logger, auth }: HttpContext) {
    logger.error(
      { code: error.code, userId: auth.user?.id },
      'Payment error: %s',
      error.message
    )
  }
}
```

### Authorization exception

```typescript
// app/exceptions/authorization_exception.ts
import { Exception } from '@adonisjs/core/exceptions'
import { HttpContext } from '@adonisjs/core/http'

export default class AuthorizationException extends Exception {
  static notAllowed(action: string, resource: string) {
    return new this(`You are not allowed to ${action} this ${resource}.`, {
      status: 403,
      code: 'E_NOT_ALLOWED',
    })
  }

  static ownershipRequired(resource: string) {
    return new this(`You do not own this ${resource}.`, {
      status: 403,
      code: 'E_OWNERSHIP_REQUIRED',
    })
  }

  handle(error: this, { response }: HttpContext) {
    return response.status(403).send({ code: error.code, message: error.message })
  }

  // 403s are expected — don't report them (or log at warn only)
  report(error: this, { logger }: HttpContext) {
    logger.warn({ code: error.code }, error.message)
  }
}
```

---

## Global Exception Handler

`app/exceptions/handler.ts` handles everything that doesn't have a self-contained `handle()` method. Keep it focused on cross-cutting concerns.

```typescript
// app/exceptions/handler.ts
import app from '@adonisjs/core/services/app'
import { HttpContext, ExceptionHandler } from '@adonisjs/core/http'
import type { StatusPageRange, StatusPageRenderer } from '@adonisjs/core/types/http'
import { errors as vineErrors } from '@vinejs/vine'

export default class HttpExceptionHandler extends ExceptionHandler {
  /**
   * Show Youch error pages in development; bare message in production.
   */
  protected debug = !app.inProduction

  /**
   * Render custom HTML status pages in production only.
   */
  protected renderStatusPages = app.inProduction

  /**
   * Custom HTML pages for common status codes (HTML/Inertia apps).
   * Not needed for pure API apps.
   */
  protected statusPages: Record<StatusPageRange, StatusPageRenderer> = {
    '404': (error, { view }) => view.render('pages/errors/not_found', { error }),
    '500..599': (error, { view }) => view.render('pages/errors/server_error', { error }),
  }

  /**
   * Don't report these status codes — they are expected client errors.
   */
  protected ignoreStatuses = [400, 401, 403, 404, 422]

  /**
   * Don't report these error codes — they are expected application errors.
   */
  protected ignoreCodes = ['E_VALIDATION_ERROR', 'E_UNAUTHORIZED_ACCESS', 'E_ROUTE_NOT_FOUND']

  async handle(error: unknown, ctx: HttpContext) {
    // Normalize VineJS validation errors to a consistent shape
    if (error instanceof vineErrors.E_VALIDATION_ERROR) {
      ctx.response.status(422).send({
        code: 'E_VALIDATION_ERROR',
        errors: error.messages,
      })
      return
    }

    return super.handle(error, ctx)
  }

  async report(error: unknown, ctx: HttpContext) {
    return super.report(error, ctx)
  }

  /**
   * Extra context attached to every error report.
   */
  protected context(ctx: HttpContext) {
    return {
      requestId: ctx.request.id(),
      userId: ctx.auth.user?.id,
      url: ctx.request.url(true),
      ip: ctx.request.ip(),
    }
  }
}
```

---

## When to Use What

| Scenario | Use |
|---|---|
| Business rule violation (e.g. cannot cancel order) | Custom exception with static factory |
| Domain entity not found | Custom exception with static factory |
| Cross-cutting format change (e.g. all 422s → custom shape) | Global handler `handle()` |
| Third-party error monitoring (Sentry, Bugsnag) | Global handler `report()` |
| Generic runtime error | `throw new Exception('msg', { status: 500 })` |

---

## Common HTTP Status Codes

| Code | Meaning | Use when |
|---|---|---|
| `400` | Bad Request | Business rule violation |
| `401` | Unauthorized | Not authenticated |
| `402` | Payment Required | Payment failed / required |
| `403` | Forbidden | Authenticated but not allowed |
| `404` | Not Found | Entity does not exist |
| `409` | Conflict | State conflict (e.g. duplicate) |
| `422` | Unprocessable Entity | Validation / semantic failure |
| `503` | Service Unavailable | External dependency down |
| `500` | Internal Server Error | Unexpected runtime failure |

---

## Directory Structure

```
app/
└── exceptions/
    ├── handler.ts              ← global handler (cross-cutting)
    ├── order_exception.ts
    ├── payment_exception.ts
    ├── authorization_exception.ts
    └── subscription_exception.ts
```

---

## Testing

```typescript
import { test } from '@japa/runner'
import OrderException from '#exceptions/order_exception'

test.group('CancelOrderService', () => {
  test('throws OrderException.cannotCancel when order is not cancellable', async ({ assert }) => {
    const order = await OrderFactory.merge({ status: 'completed' }).create()

    await assert.rejects(
      () => new CancelOrderService().handle(order),
      (error) => {
        assert.instanceOf(error, OrderException)
        assert.equal(error.status, 400)
        assert.equal(error.code, 'E_ORDER_CANNOT_CANCEL')
      }
    )
  })

  test('returns 400 with code when request accepts JSON', async ({ client }) => {
    const order = await OrderFactory.merge({ status: 'completed' }).create()

    const response = await client
      .delete(`/orders/${order.id}`)
      .header('Accept', 'application/json')

    response.assertStatus(400)
    response.assertBodyContains({ code: 'E_ORDER_CANNOT_CANCEL' })
  })
})
```

---

## Summary

**Exceptions should:**

- Extend `@adonisjs/core/exceptions`'s `Exception` class
- Use static factory methods named after the failure condition
- Pass both `status` and `code` to the constructor
- Include the entity identifier and reason in the message
- Implement `handle()` for a self-contained HTTP response
- Implement `report()` to control logging severity per status range
- Be named `{Entity}Exception` and live in `app/exceptions/`

**Exceptions should NOT:**

- Use bare `new Error()` for domain errors
- Build error messages without context
- Let the global handler deal with domain-specific errors
- Log 4xx client errors at `error` level (use `warn`)
- Include internal stack details in production HTTP responses
