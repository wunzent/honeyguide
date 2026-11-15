// tests/unit/cache_manager.spec.ts
//
// Example: testing package logic in isolation (no AdonisJS app needed).

import { test } from '@japa/runner'
// import { CacheManager } from '../../src/cache_manager.js'

test.group('CacheManager | unit', () => {
  test('set and get a value', async ({ assert }) => {
    // const cache = new CacheManager({ driver: 'memory', ttl: 3600 })
    // await cache.connect()
    //
    // await cache.set('foo', 'bar')
    // const value = await cache.get('foo')
    //
    // assert.equal(value, 'bar')
    //
    // await cache.disconnect()
    assert.isTrue(true) // placeholder
  })

  test('returns null for missing key', async ({ assert }) => {
    // const cache = new CacheManager({ driver: 'memory', ttl: 3600 })
    // await cache.connect()
    //
    // const value = await cache.get('nonexistent')
    // assert.isNull(value)
    //
    // await cache.disconnect()
    assert.isTrue(true)
  })

  test('forget removes a key', async ({ assert }) => {
    // const cache = new CacheManager({ driver: 'memory', ttl: 3600 })
    // await cache.connect()
    //
    // await cache.set('foo', 'bar')
    // await cache.forget('foo')
    // const value = await cache.get('foo')
    //
    // assert.isNull(value)
    //
    // await cache.disconnect()
    assert.isTrue(true)
  })

  test('flush clears all keys', async ({ assert }) => {
    // const cache = new CacheManager({ driver: 'memory', ttl: 3600 })
    // await cache.connect()
    //
    // await cache.set('a', '1')
    // await cache.set('b', '2')
    // await cache.flush()
    //
    // assert.isNull(await cache.get('a'))
    // assert.isNull(await cache.get('b'))
    //
    // await cache.disconnect()
    assert.isTrue(true)
  })

  test('expired entries return null', async ({ assert }) => {
    // const cache = new CacheManager({ driver: 'memory', ttl: 1 })
    // await cache.connect()
    //
    // await cache.set('temp', 'value', 0) // TTL = 0 seconds → immediately expired
    //
    // // Small delay to ensure expiry
    // await new Promise((resolve) => setTimeout(resolve, 10))
    //
    // assert.isNull(await cache.get('temp'))
    //
    // await cache.disconnect()
    assert.isTrue(true)
  })
})

// ─────────────────────────────────────────────────────────────
// tests/integration/provider.spec.ts
//
// Example: testing the service provider with a real AdonisJS app.
// Uses @adonisjs/core test utilities to spin up a temporary app.
// ─────────────────────────────────────────────────────────────

// import { test } from '@japa/runner'
// import { IgnitorFactory } from '@adonisjs/core/factories'
// import { defineConfig } from '../../src/define_config.js'
//
// const BASE_URL = new URL('./tmp/', import.meta.url)
//
// test.group('MyCacheProvider | integration', (group) => {
//   group.each.setup(async () => {
//     // Clean up temp directory after each test
//     return async () => {
//       const { rm } = await import('node:fs/promises')
//       await rm(BASE_URL, { recursive: true, force: true })
//     }
//   })
//
//   test('registers cache manager in the container', async ({ assert }) => {
//     const ignitor = new IgnitorFactory()
//       .withCoreProviders()
//       .withCoreConfig()
//       .merge({
//         config: {
//           my_cache: defineConfig({
//             driver: 'memory',
//             ttl: 60,
//           }),
//         },
//         rcFileContents: {
//           providers: [
//             () => import('../../providers/my_cache_provider.js'),
//           ],
//         },
//       })
//       .create(BASE_URL)
//
//     const app = ignitor.createApp('web')
//     await app.init()
//     await app.boot()
//
//     const cache = await app.container.make('myCache')
//     assert.isDefined(cache)
//     assert.isFunction(cache.get)
//     assert.isFunction(cache.set)
//
//     await app.terminate()
//   })
//
//   test('defineConfig applies defaults', ({ assert }) => {
//     const config = defineConfig({ driver: 'redis' })
//
//     assert.equal(config.driver, 'redis')
//     assert.equal(config.ttl, 3600)       // default
//     assert.equal(config.prefix, 'cache:') // default
//   })
// })

// ─────────────────────────────────────────────────────────────
// bin/test.ts — Japa test runner entry point
// ─────────────────────────────────────────────────────────────

// import { configure, processCLIArgs, run } from '@japa/runner'
// import { assert } from '@japa/assert'
//
// processCLIArgs(process.argv.splice(2))
//
// configure({
//   files: ['tests/**/*.spec.ts'],
//   plugins: [assert()],
// })
//
// run()

// ─────────────────────────────────────────────────────────────
// Run tests
// ─────────────────────────────────────────────────────────────
//
// npm run test          # lint + test + coverage
// npm run quick:test    # test only (fast)
// npm run typecheck     # tsc --noEmit
