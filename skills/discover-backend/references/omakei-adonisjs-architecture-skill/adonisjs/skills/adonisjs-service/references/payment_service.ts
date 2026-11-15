// app/services/payment/payment_manager.ts
//
// Concrete manager for payment drivers.
// Registered as a singleton in the IoC container via PaymentProvider.

import { ServiceManager } from '#lib/service_manager'
import type { PaymentDriver } from './contracts/payment_driver.js'
import { StripeDriver } from './drivers/stripe_driver.js'
import { NullPaymentDriver } from './drivers/null_driver.js'

export class PaymentManager extends ServiceManager<PaymentDriver> {
  protected configNamespace = 'payment'

  protected createDriver(name: string): PaymentDriver {
    switch (name) {
      case 'stripe': {
        const cfg = this.app.config.get<any>('payment.drivers.stripe')
        return new StripeDriver(cfg.apiKey, cfg.webhookSecret)
      }

      case 'null':
        return new NullPaymentDriver()

      default:
        throw new Error(
          `Unknown payment driver "${name}". ` +
          `Available: stripe, null`
        )
    }
  }
}

// ─────────────────────────────────────────────────────────────────
// app/services/payment/contracts/payment_driver.ts
// ─────────────────────────────────────────────────────────────────

/**
 * Returned by all payment driver methods.
 * Vendor-agnostic shape — maps from Stripe / PayPal / etc.
 */
export interface PaymentIntentResult {
  id: string
  amount: number
  currency: string
  status: 'succeeded' | 'pending' | 'failed'
}

/**
 * Contract that every payment driver must implement.
 * Keep this minimal — only the operations your app actually uses.
 */
export interface PaymentDriver {
  createPaymentIntent(amount: number, currency: string): Promise<PaymentIntentResult>
  refundPayment(paymentIntentId: string, amount?: number): Promise<boolean>
  retrievePaymentIntent(paymentIntentId: string): Promise<PaymentIntentResult>
}

// ─────────────────────────────────────────────────────────────────
// app/services/payment/drivers/stripe_driver.ts
// ─────────────────────────────────────────────────────────────────

/**
 * Stripe implementation of PaymentDriver.
 *
 * MEMORY SAFETY:
 * - No static connector cache. The driver instance lives inside the
 *   PaymentManager's bounded Map. One instance per app lifetime.
 * - Uses native fetch() which is stateless — no persistent socket pool.
 * - Constructor receives plain strings, not closures or app references.
 */
export class StripeDriver implements PaymentDriver {
  private readonly baseUrl = 'https://api.stripe.com'

  constructor(
    private readonly apiKey: string,
    private readonly webhookSecret: string
  ) {}

  async createPaymentIntent(amount: number, currency: string): Promise<PaymentIntentResult> {
    const response = await this.request('POST', '/v1/payment_intents', {
      amount: String(amount),
      currency,
    })

    return this.mapResult(response)
  }

  async refundPayment(paymentIntentId: string, amount?: number): Promise<boolean> {
    const body: Record<string, string> = { payment_intent: paymentIntentId }
    if (amount !== undefined) body.amount = String(amount)

    const response = await this.request('POST', '/v1/refunds', body)
    return response.ok
  }

  async retrievePaymentIntent(paymentIntentId: string): Promise<PaymentIntentResult> {
    const response = await this.request('GET', `/v1/payment_intents/${paymentIntentId}`)
    return this.mapResult(response)
  }

  // ── Private helpers ──────────────────────────────────

  private async request(
    method: string,
    path: string,
    body?: Record<string, string>
  ): Promise<Response & { data?: any }> {
    const options: RequestInit = {
      method,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    }

    if (body && method !== 'GET') {
      options.body = new URLSearchParams(body)
    }

    const response = await fetch(`${this.baseUrl}${path}`, options)

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Stripe API error (${response.status}): ${text}`)
    }

    return response
  }

  private async mapResult(response: Response): Promise<PaymentIntentResult> {
    const data = await response.json()
    return {
      id: data.id,
      amount: data.amount,
      currency: data.currency,
      status: this.mapStatus(data.status),
    }
  }

  private mapStatus(stripeStatus: string): PaymentIntentResult['status'] {
    switch (stripeStatus) {
      case 'succeeded': return 'succeeded'
      case 'requires_payment_method':
      case 'requires_confirmation':
      case 'processing':
        return 'pending'
      default:
        return 'failed'
    }
  }
}

// ─────────────────────────────────────────────────────────────────
// app/services/payment/exceptions/payment_exception.ts
// ─────────────────────────────────────────────────────────────────

export class PaymentException extends Error {
  constructor(message: string, public readonly code: string) {
    super(message)
    this.name = 'PaymentException'
  }

  static failedRequest(detail: string): PaymentException {
    return new PaymentException(
      `Payment request failed: ${detail}`,
      'PAYMENT_REQUEST_FAILED'
    )
  }

  static cardDeclined(): PaymentException {
    return new PaymentException('Card was declined', 'CARD_DECLINED')
  }

  static notFound(id: string): PaymentException {
    return new PaymentException(
      `Payment intent "${id}" not found`,
      'PAYMENT_NOT_FOUND'
    )
  }
}
