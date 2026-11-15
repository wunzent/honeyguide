// app/lib/service_manager.ts
//
// Generic, reusable manager base class for the driver pattern.
// Extend this for each external service (payment, email, sms, etc.).
//
// MEMORY SAFETY:
// - `drivers` Map is bounded: at most N entries where N = number of
//   configured driver names. This is set at boot time, not per-request.
// - No EventEmitter usage — drivers are plain objects with async methods.
// - `flush()` clears the cache; called automatically on app shutdown
//   if the provider implements `shutdown()`.
// - Drivers receive plain config values, not closures or app references.

import type { ApplicationService } from '@adonisjs/core/types'

/**
 * Base manager class for the driver pattern.
 *
 * @typeParam D - The driver interface that all drivers implement.
 *
 * Usage:
 * ```typescript
 * class PaymentManager extends ServiceManager<PaymentDriver> {
 *   protected configNamespace = 'payment'
 *
 *   protected createDriver(name: string): PaymentDriver {
 *     switch (name) {
 *       case 'stripe': return new StripeDriver(...)
 *       case 'null': return new NullDriver()
 *       default: throw new Error(`Unknown driver: ${name}`)
 *     }
 *   }
 * }
 * ```
 */
export abstract class ServiceManager<D> {
  /**
   * Cache of instantiated drivers.
   * Bounded by the number of driver names in config (typically 2–4).
   * NOT per-request — drivers are created once and reused.
   */
  private drivers = new Map<string, D>()

  constructor(protected app: ApplicationService) {}

  /**
   * The config namespace to read from. E.g. 'payment' reads
   * config('payment.default') and config('payment.drivers.*').
   */
  protected abstract configNamespace: string

  /**
   * Factory method to create a driver instance by name.
   * Subclasses read config from `this.app.config.get(...)`.
   */
  protected abstract createDriver(name: string): D

  /**
   * Get the name of the default driver from config.
   */
  protected getDefaultDriverName(): string {
    return this.app.config.get<string>(`${this.configNamespace}.default`, 'null')
  }

  /**
   * Get a driver instance by name (defaults to the configured default).
   * Creates the driver on first access, caches it for subsequent calls.
   */
  use(name?: string): D {
    const driverName = name ?? this.getDefaultDriverName()

    let driver = this.drivers.get(driverName)
    if (!driver) {
      driver = this.createDriver(driverName)
      this.drivers.set(driverName, driver)
    }

    return driver
  }

  /**
   * Clear all cached driver instances.
   * Call this on app shutdown or between tests.
   */
  flush(): void {
    this.drivers.clear()
  }
}
