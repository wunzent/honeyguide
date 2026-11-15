// configure.ts
//
// Configure hook — runs when the user executes:
//   node ace configure @your-org/adonis-my-cache
//
// Uses codemods to modify the user's AdonisJS project:
// - Publish config file from stubs
// - Register the provider in adonisrc.ts
// - Add environment variables to .env and start/env.ts
// - Optionally publish migrations, middleware, etc.

import ConfigureCommand from '@adonisjs/core/commands/configure'
import { stubsRoot } from './stubs/main.js'

export async function configure(command: ConfigureCommand) {
  const codemods = await command.createCodemods()

  // ── 1. Publish config file ──────────────────────────────
  // Copies stubs/config.stub → config/my_cache.ts in the user's project
  await codemods.makeUsingStub(stubsRoot, 'config.stub', {})

  // ── 2. Register the service provider ────────────────────
  await codemods.updateRcFile((rcFile) => {
    rcFile.addProvider('@your-org/adonis-my-cache/my_cache_provider')
  })

  // ── 3. Define environment variables ─────────────────────
  // Adds to .env (and .env.example if it exists)
  await codemods.defineEnvVariables({
    MY_CACHE_DRIVER: 'memory',
    REDIS_HOST: '127.0.0.1',
    REDIS_PORT: '6379',
  })

  // Adds validation rules to start/env.ts
  await codemods.defineEnvValidations({
    variables: {
      MY_CACHE_DRIVER: `Env.schema.enum(['memory', 'redis'] as const)`,
      REDIS_HOST: `Env.schema.string({ format: 'host' })`,
      REDIS_PORT: `Env.schema.number()`,
    },
    leadingComment: 'Variables for @your-org/adonis-my-cache',
  })

  // ── 4. (Optional) Publish migration stubs ───────────────
  // await codemods.makeUsingStub(stubsRoot, 'migration.stub', {
  //   migration: {
  //     tableName: 'cache_entries',
  //     folder: 'database/migrations',
  //   },
  // })

  // ── 5. (Optional) Register middleware ───────────────────
  // await codemods.registerMiddleware('named', [
  //   {
  //     path: '@your-org/adonis-my-cache/cache_middleware',
  //     name: 'cache',
  //   },
  // ])

  // ── 6. (Optional) Register commands ─────────────────────
  // await codemods.updateRcFile((rcFile) => {
  //   rcFile.addCommand('@your-org/adonis-my-cache/commands')
  // })
}

// ─────────────────────────────────────────────────────────────
// stubs/main.ts — Required: exports the stubs directory path
// ─────────────────────────────────────────────────────────────

// import { getDirname } from '@adonisjs/core/helpers'
// export const stubsRoot = getDirname(import.meta.url)

// ─────────────────────────────────────────────────────────────
// stubs/config.stub — Config file template
// ─────────────────────────────────────────────────────────────
//
// The stub uses Tempura syntax (handlebars-like).
// It gets published to the user's project as config/my_cache.ts.
//
// {{{
//   exports({ to: app.configPath('my_cache.ts') })
// }}}
// import env from '#start/env'
// import { defineConfig } from '@your-org/adonis-my-cache'
//
// const myCacheConfig = defineConfig({
//   driver: env.get('MY_CACHE_DRIVER', 'memory'),
//   prefix: 'cache:',
//   ttl: 3600,
//   redis: {
//     host: env.get('REDIS_HOST', '127.0.0.1'),
//     port: env.get('REDIS_PORT', 6379),
//   },
// })
//
// export default myCacheConfig

// ─────────────────────────────────────────────────────────────
// stubs/migration.stub — Migration template (optional)
// ─────────────────────────────────────────────────────────────
//
// {{{
//   exports({
//     to: app.migrationsPath(
//       `${new Date().getTime()}_create_{{ migration.tableName }}_table.ts`
//     )
//   })
// }}}
// import { BaseSchema } from '@adonisjs/lucid/schema'
//
// export default class extends BaseSchema {
//   protected tableName = '{{ migration.tableName }}'
//
//   async up() {
//     this.schema.createTable(this.tableName, (table) => {
//       table.increments('id')
//       table.string('key').unique().notNullable()
//       table.text('value').notNullable()
//       table.timestamp('expires_at').nullable()
//       table.timestamp('created_at', { useTz: true }).defaultTo(this.now())
//     })
//   }
//
//   async down() {
//     this.schema.dropTable(this.tableName)
//   }
// }
