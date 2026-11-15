// providers/my_cache_provider.ts
//
// Example service provider for a hypothetical cache package.
// Demonstrates: register, boot, ready, shutdown lifecycle hooks,
// container bindings, extending other services, and environment-scoped loading.

import type { ApplicationService } from '@adonisjs/core/types'

export default class MyCacheProvider {
  constructor(protected app: ApplicationService) {}

  /**
   * Register phase — runs before the app is booted.
   * Use for IoC container bindings. Do NOT resolve other providers here.
   */
  register() {
    this.app.container.singleton('myCache', async () => {
      const { CacheManager } = await import('../src/cache_manager.js')
      const config = this.app.config.get<any>('my_cache')
      return new CacheManager(config)
    })
  }

  /**
   * Boot phase — all providers are registered.
   * Use for extending other services (VineJS rules, Lucid macros, etc.).
   */
  async boot() {
    // Example: add a custom VineJS validation rule
    // const vine = await this.app.container.make('vine')
    // vine.string.macro('cacheKey', function () {
    //   return this.regex(/^[a-zA-Z0-9:._-]+$/)
    // })
  }

  /**
   * Ready phase — app is fully running.
   * Use for connecting to external services, starting background workers.
   */
  async ready() {
    // Only connect in web/test environments (not during ace commands)
    if (['web', 'test'].includes(this.app.getEnvironment())) {
      const cache = await this.app.container.make('myCache')
      await cache.connect()
    }
  }

  /**
   * Shutdown phase — app is gracefully exiting.
   * Use for closing connections, flushing buffers.
   */
  async shutdown() {
    const cache = await this.app.container.make('myCache')
    await cache.disconnect()
  }
}

// ─────────────────────────────────────────────────────────────
// src/cache_manager.ts — Core package logic
// ─────────────────────────────────────────────────────────────

// import type { MyCacheConfig } from './types.js'
//
// export class CacheManager {
//   private store = new Map<string, { value: string; expiresAt: number }>()
//   private connected = false
//
//   constructor(private config: MyCacheConfig) {}
//
//   async connect() {
//     // Connect to Redis, Memcached, etc.
//     this.connected = true
//   }
//
//   async disconnect() {
//     this.store.clear()
//     this.connected = false
//   }
//
//   async get(key: string): Promise<string | null> {
//     const entry = this.store.get(key)
//     if (!entry) return null
//     if (Date.now() > entry.expiresAt) {
//       this.store.delete(key)
//       return null
//     }
//     return entry.value
//   }
//
//   async set(key: string, value: string, ttlSeconds = 3600): Promise<void> {
//     this.store.set(key, {
//       value,
//       expiresAt: Date.now() + ttlSeconds * 1000,
//     })
//   }
//
//   async forget(key: string): Promise<boolean> {
//     return this.store.delete(key)
//   }
//
//   async flush(): Promise<void> {
//     this.store.clear()
//   }
// }

// ─────────────────────────────────────────────────────────────
// src/types.ts — Exported types
// ─────────────────────────────────────────────────────────────

// export interface MyCacheConfig {
//   driver: 'memory' | 'redis'
//   prefix?: string
//   ttl?: number
//   redis?: {
//     host: string
//     port: number
//     password?: string
//   }
// }

// ─────────────────────────────────────────────────────────────
// src/define_config.ts — Typed config helper
// ─────────────────────────────────────────────────────────────

// import type { MyCacheConfig } from './types.js'
//
// export function defineConfig(config: MyCacheConfig): MyCacheConfig {
//   return {
//     driver: 'memory',
//     prefix: 'cache:',
//     ttl: 3600,
//     ...config,
//   }
// }

// ─────────────────────────────────────────────────────────────
// services/main.ts — Singleton accessor
// ─────────────────────────────────────────────────────────────

// import app from '@adonisjs/core/services/app'
// import type { CacheManager } from '../src/cache_manager.js'
//
// let cache: CacheManager
//
// await app.booted(async () => {
//   cache = await app.container.make('myCache')
// })
//
// export default cache!

// ─────────────────────────────────────────────────────────────
// index.ts — Main entry point
// ─────────────────────────────────────────────────────────────

// export { configure } from './configure.js'
// export { defineConfig } from './src/define_config.js'
// export { CacheManager } from './src/cache_manager.js'
// export type { MyCacheConfig } from './src/types.js'
