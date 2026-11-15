// app/services/payment/drivers/null_driver.ts
//
// Deterministic fake driver for testing.
// Returns predictable data without any HTTP calls.
//
// Use by setting PAYMENT_DRIVER=null in .env.test.
// For failure scenarios, create a FailingPaymentDriver (see below).

import { randomUUID } from 'node:crypto'
import type { PaymentDriver, PaymentIntentResult } from '../contracts/payment_driver.js'

/**
 * Null driver — always succeeds, no network calls.
 * Ideal for the 90% of tests that don't care about payment internals.
 */
export class NullPaymentDriver implements PaymentDriver {
  /** Track calls for assertion in tests (optional). */
  readonly calls: Array<{ method: string; args: any[] }> = []

  async createPaymentIntent(amount: number, currency: string): Promise<PaymentIntentResult> {
    this.calls.push({ method: 'createPaymentIntent', args: [amount, currency] })

    return {
      id: `pi_test_${randomUUID().slice(0, 8)}`,
      amount,
      currency,
      status: 'succeeded',
    }
  }

  async refundPayment(paymentIntentId: string, amount?: number): Promise<boolean> {
    this.calls.push({ method: 'refundPayment', args: [paymentIntentId, amount] })
    return true
  }

  async retrievePaymentIntent(paymentIntentId: string): Promise<PaymentIntentResult> {
    this.calls.push({ method: 'retrievePaymentIntent', args: [paymentIntentId] })

    return {
      id: paymentIntentId,
      amount: 0,
      currency: 'usd',
      status: 'succeeded',
    }
  }

  /** Reset tracked calls between tests. */
  reset(): void {
    this.calls.length = 0
  }
}

// ─────────────────────────────────────────────────────────────────
// Failing driver — for testing error paths
// ─────────────────────────────────────────────────────────────────

/**
 * Driver that always fails. Use to test error handling, retries, etc.
 *
 * Usage in tests:
 *   app.container.swap(PaymentManager, () => {
 *     const mgr = new PaymentManager(app)
 *     // Override the default to return the failing driver
 *     return { use: () => new FailingPaymentDriver('Card declined'), flush: () => {} }
 *   })
 */
export class FailingPaymentDriver implements PaymentDriver {
  constructor(private readonly errorMessage: string = 'Payment failed') {}

  async createPaymentIntent(): Promise<PaymentIntentResult> {
    throw new Error(this.errorMessage)
  }

  async refundPayment(): Promise<boolean> {
    return false
  }

  async retrievePaymentIntent(): Promise<PaymentIntentResult> {
    throw new Error(this.errorMessage)
  }
}
