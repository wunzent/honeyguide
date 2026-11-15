// providers/payment_provider.ts
//
// Registers PaymentManager as a singleton in the AdonisJS IoC container.
//
// MEMORY SAFETY:
// - The manager is a singleton — one instance for the app lifetime.
//   It is NOT created per-request, so no per-request memory growth.
// - On shutdown, flush() clears the bounded driver cache, releasing
//   any driver instances and their internal references.
// - No EventEmitter listeners are registered.

import type { ApplicationService } from '@adonisjs/core/types'
import { PaymentManager } from '#services/payment/payment_manager'

export default class PaymentProvider {
  constructor(protected app: ApplicationService) {}

  /**
   * Register bindings in the container.
   * Called once during application boot.
   */
  register() {
    // Singleton: one PaymentManager for the entire app lifetime.
    // The manager lazily creates drivers and caches them in a bounded Map.
    this.app.container.singleton(PaymentManager, () => {
      return new PaymentManager(this.app)
    })
  }

  /**
   * Called when the application is shutting down.
   * Flush the driver cache to release any held resources.
   */
  async shutdown() {
    try {
      const manager = await this.app.container.make(PaymentManager)
      manager.flush()
    } catch {
      // Container may not have the binding if boot failed — safe to ignore
    }
  }
}

// ─────────────────────────────────────────────────────────────────
// Registration in adonisrc.ts
// ─────────────────────────────────────────────────────────────────
//
// {
//   providers: [
//     // ...other providers
//     () => import('#providers/payment_provider'),
//   ]
// }

// ─────────────────────────────────────────────────────────────────
// .env.test — use null driver in tests
// ─────────────────────────────────────────────────────────────────
//
// PAYMENT_DRIVER=null

// ─────────────────────────────────────────────────────────────────
// Usage in controllers (automatic injection)
// ─────────────────────────────────────────────────────────────────
//
// import { inject } from '@adonisjs/core'
// import { PaymentManager } from '#services/payment/payment_manager'
//
// export default class OrdersController {
//   @inject()
//   async pay({ request, response }: HttpContext, payment: PaymentManager) {
//     const result = await payment.use().createPaymentIntent(
//       request.input('amount'),
//       request.input('currency', 'usd')
//     )
//     return response.ok({ data: result })
//   }
// }

// ─────────────────────────────────────────────────────────────────
// Usage via manual resolution
// ─────────────────────────────────────────────────────────────────
//
// import app from '@adonisjs/core/services/app'
// import { PaymentManager } from '#services/payment/payment_manager'
//
// const payment = await app.container.make(PaymentManager)
// const intent = await payment.use().createPaymentIntent(5000, 'usd')
//
// // Use a specific driver:
// const intent = await payment.use('paypal').createPaymentIntent(5000, 'usd')
