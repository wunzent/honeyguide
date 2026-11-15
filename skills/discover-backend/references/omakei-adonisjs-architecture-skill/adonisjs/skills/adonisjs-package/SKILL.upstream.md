---
name: adonisjs-packages
description: Package development and extraction of reusable code for AdonisJS using the official pkg-starter-kit. Use when working with package development, creating npm packages, extracting reusable code, writing service providers, configure hooks, stubs, codemods, or when user mentions packages, npm packages, extract package, reusable code, package development, publish package, service provider for a package, starter kit, or asks how to create an AdonisJS addon/plugin.
---

# AdonisJS Package Development

Creating reusable AdonisJS packages using the official [pkg-starter-kit](https://github.com/adonisjs/pkg-starter-kit). Covers project setup, service providers, configure hooks, stubs, testing, publishing, and when to extract code into a package.

**Reference implementations:**
- [Package structure walkthrough →](references/package-structure.md)
- [Service provider example →](references/example_provider.ts)
- [Configure hook example →](references/example_configure.ts)
- [Testing a package →](references/testing_package.ts)

---

## When to Extract

Extract to a package when:

1. Pattern is used across **3+ projects**
2. Code is **stable and well-tested**
3. It has **clear boundaries** (not tangled with app-specific logic)
4. Maintenance cost is **justified by reuse**

**Don't extract** when the code is still evolving, project-specific, or tightly coupled to your domain models.

---

## Quick Start

### 1. Scaffold from the starter kit

```bash
npx giget@latest gh:adonisjs/pkg-starter-kit my-package
cd my-package
npm install
```

### 2. Update package.json

```json
{
  "name": "@your-org/adonis-my-package",
  "description": "What the package does",
  "version": "1.0.0",
  "type": "module",
  "main": "build/index.js",
  "types": "build/index.d.ts",
  "exports": {
    ".": "./build/index.js",
    "./types": "./build/src/types.js",
    "./services/main": "./build/services/main.js",
    "./my_package_provider": "./build/providers/my_package_provider.js"
  },
  "files": [
    "build/src",
    "build/providers",
    "build/stubs",
    "build/services",
    "build/index.d.ts",
    "build/index.js",
    "build/configure.d.ts",
    "build/configure.js"
  ],
  "peerDependencies": {
    "@adonisjs/core": "^6.0.0"
  }
}
```

### 3. Write your code

Place source code in `src/`, the service provider in `providers/`, and stubs in `stubs/`.

### 4. Build and test

```bash
npm run build        # Compile TypeScript → build/
npm run test         # Run Japa tests
npm run quick:test   # Tests only (no lint/coverage)
npm run typecheck    # tsc --noEmit
```

### 5. Publish

```bash
npm publish --access public
```

---

## Package Structure

```
my-package/
├── bin/
│   └── test.ts               # Japa test entry point
├── providers/
│   └── my_package_provider.ts # Service provider (IoC bindings)
├── src/
│   ├── my_service.ts          # Core package logic
│   ├── types.ts               # Exported types/interfaces
│   └── define_config.ts       # Config validation helper
├── services/
│   └── main.ts                # Singleton service accessor (like @adonisjs/mail/services/main)
├── stubs/
│   ├── config.stub            # Config file template
│   ├── migration.stub         # Migration template (optional)
│   └── main.ts                # Stubs directory export
├── tests/
│   └── my_service.spec.ts
├── configure.ts               # Configure hook (node ace configure)
├── index.ts                   # Main package entry point (re-exports)
├── eslint.config.js
├── tsconfig.json
├── package.json
└── README.md
```

---

## Key Components

### 1. Entry point (`index.ts`)

Re-exports everything users need to import:

```typescript
// index.ts
export { configure } from './configure.js'
export { defineConfig } from './src/define_config.js'
export { MyService } from './src/my_service.js'
```

### 2. Service provider

Registers bindings in the AdonisJS IoC container. This is how your package hooks into the app lifecycle.

```typescript
// providers/my_package_provider.ts
import type { ApplicationService } from '@adonisjs/core/types'
import { MyService } from '../src/my_service.js'

export default class MyPackageProvider {
  constructor(protected app: ApplicationService) {}

  register() {
    this.app.container.singleton('myPackage', () => {
      const config = this.app.config.get<any>('my_package')
      return new MyService(config)
    })
  }

  async boot() {
    // Called after all providers have registered
    // Extend other services here (e.g. add VineJS rules, add macros)
  }

  async ready() {
    // App is fully booted and ready to accept requests
  }

  async shutdown() {
    // Cleanup: close connections, flush caches
    const service = await this.app.container.make('myPackage')
    await service.disconnect?.()
  }
}
```

**Provider lifecycle methods:**

| Method | When | Use for |
|---|---|---|
| `register()` | Before boot | Container bindings, config reads |
| `boot()` | After all providers registered | Extending other services (VineJS, Lucid macros) |
| `start()` | After boot, before ready | Actions that ready depends on |
| `ready()` | App fully running | Start background workers, connect to external services |
| `shutdown()` | App shutting down | Cleanup connections, flush state |

### 3. Configure hook (`configure.ts`)

Runs when the user does `node ace configure @your-org/adonis-my-package`. Publishes config files, registers the provider, adds env vars, etc.

```typescript
// configure.ts
import ConfigureCommand from '@adonisjs/core/commands/configure'
import { stubsRoot } from './stubs/main.js'

export async function configure(command: ConfigureCommand) {
  const codemods = await command.createCodemods()

  // 1. Publish config file from stub
  await codemods.makeUsingStub(stubsRoot, 'config.stub', {})

  // 2. Register the service provider in adonisrc.ts
  await codemods.updateRcFile((rcFile) => {
    rcFile.addProvider('@your-org/adonis-my-package/my_package_provider')
  })

  // 3. Add environment variables to .env and start/env.ts
  await codemods.defineEnvVariables({
    MY_PACKAGE_API_KEY: '',
  })

  await codemods.defineEnvValidations({
    variables: {
      MY_PACKAGE_API_KEY: `Env.schema.string()`,
    },
  })
}
```

### 4. Stubs

Template files that get published to the user's project:

```
{{# config/my_package.ts #}}
import env from '#start/env'
import { defineConfig } from '@your-org/adonis-my-package'

const myPackageConfig = defineConfig({
  apiKey: env.get('MY_PACKAGE_API_KEY'),
  debug: false,
})

export default myPackageConfig
```

```typescript
// stubs/main.ts — required to export the stubs directory path
import { getDirname } from '@adonisjs/core/helpers'
export const stubsRoot = getDirname(import.meta.url)
```

### 5. Config validation (`define_config.ts`)

Provide a typed config helper so users get autocomplete:

```typescript
// src/define_config.ts
export interface MyPackageConfig {
  apiKey: string
  debug?: boolean
  timeout?: number
}

export function defineConfig(config: MyPackageConfig): MyPackageConfig {
  return {
    debug: false,
    timeout: 5000,
    ...config,
  }
}
```

### 6. Service accessor (`services/main.ts`)

Provide a convenient singleton import (like `@adonisjs/mail/services/main`):

```typescript
// services/main.ts
import app from '@adonisjs/core/services/app'
import { MyService } from '../src/my_service.js'

let service: MyService

await app.booted(async () => {
  service = await app.container.make('myPackage')
})

export default service!
```

---

## Peer Dependencies

**Critical rule:** AdonisJS framework packages (`@adonisjs/core`, `@adonisjs/lucid`, etc.) must be **peer dependencies**, never main dependencies. Otherwise, the user's app loads a duplicate copy.

```json
{
  "peerDependencies": {
    "@adonisjs/core": "^6.0.0"
  },
  "peerDependenciesMeta": {
    "@adonisjs/lucid": {
      "optional": true
    }
  },
  "devDependencies": {
    "@adonisjs/core": "^6.0.0",
    "@adonisjs/lucid": "^20.0.0"
  }
}
```

---

## Testing a Package

Use Japa (same as app testing). The starter kit provides `bin/test.ts`:

```typescript
// bin/test.ts
import { configure, processCLIArgs, run } from '@japa/runner'
import { assert } from '@japa/assert'

processCLIArgs(process.argv.splice(2))
configure({
  files: ['tests/**/*.spec.ts'],
  plugins: [assert()],
})
run()
```

Test your service logic in isolation:

```typescript
// tests/my_service.spec.ts
import { test } from '@japa/runner'
import { MyService } from '../src/my_service.js'

test.group('MyService', () => {
  test('does the thing', ({ assert }) => {
    const service = new MyService({ apiKey: 'test', debug: false })
    const result = service.doSomething('input')
    assert.equal(result, 'expected')
  })
})
```

For integration tests that need the full AdonisJS app, use `@adonisjs/core` test utilities to create a temporary app instance. See the [official packages](https://github.com/adonisjs/mail/tree/develop/tests) for patterns.

Run:

```bash
npm run test          # lint + test + coverage
npm run quick:test    # test only
```

---

## Publishing Checklist

1. **package.json** — correct `name`, `version`, `description`, `exports`, `files`, `peerDependencies`
2. **Build** — `npm run build` compiles to `build/`
3. **Tests pass** — `npm run test`
4. **Type check** — `npm run typecheck`
5. **README** — installation, configuration, usage examples
6. **LICENSE** — MIT or your choice
7. **Semver** — use semantic versioning

### User installation flow

```bash
npm i @your-org/adonis-my-package
node ace configure @your-org/adonis-my-package
```

The configure hook registers the provider, publishes config, and sets env vars automatically.

---

## Core AdonisJS Ecosystem Packages

Packages you'll commonly use or depend on:

| Package | Purpose |
|---|---|
| `@adonisjs/core` | Framework core (always a peer dep) |
| `@adonisjs/lucid` | SQL ORM (Active Record) |
| `@adonisjs/auth` | Authentication (session, tokens, basic) |
| `@adonisjs/bouncer` | Authorization (abilities, policies) |
| `@adonisjs/mail` | Email sending (SMTP, SES, Mailgun, etc.) |
| `@adonisjs/session` | Session management |
| `@adonisjs/redis` | Redis client |
| `@adonisjs/limiter` | Rate limiting |
| `@adonisjs/drive` | File storage (local, S3, GCS) |
| `@vinejs/vine` | Validation |
| `edge.js` | Templating engine |
| `@japa/runner` | Test runner |

---

## Summary

| Component | Purpose | Laravel equivalent |
|---|---|---|
| `index.ts` | Main entry point, re-exports | Package root `src/` |
| `providers/*.ts` | Service provider (IoC bindings) | `PackageServiceProvider.php` |
| `configure.ts` | Post-install setup hook | `php artisan vendor:publish` |
| `stubs/*.stub` | Template files for user project | Publishable stubs |
| `src/define_config.ts` | Typed config helper | `config/package.php` |
| `services/main.ts` | Singleton accessor | Facade |
| `package.json` exports | Subpath exports | Composer autoload |
| `peerDependencies` | Framework as peer dep | Composer require |
