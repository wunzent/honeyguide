# AdonisJS Package Structure

Detailed breakdown of the [official pkg-starter-kit](https://github.com/adonisjs/pkg-starter-kit) structure and what each piece does.

## Directory Layout

```
my-package/
├── bin/
│   └── test.ts                 # Japa test runner entry point
├── providers/
│   ├── my_package_provider.ts  # Service provider — IoC bindings + lifecycle hooks
│   └── README.md               # Docs for the providers directory
├── src/
│   ├── my_service.ts           # Core logic of the package
│   ├── types.ts                # Exported TypeScript types/interfaces
│   ├── define_config.ts        # Typed config helper (like defineConfig)
│   └── README.md               # Docs for the src directory
├── services/
│   └── main.ts                 # Singleton service accessor (convenience import)
├── stubs/
│   ├── config.stub             # Config file template (published to user project)
│   ├── migration.stub          # Database migration template (optional)
│   └── main.ts                 # Exports the stubs directory path
├── tests/
│   ├── unit/
│   │   └── my_service.spec.ts  # Unit tests
│   └── integration/
│       └── provider.spec.ts    # Integration tests with app context
├── .github/
│   └── workflows/
│       └── checks.yml          # CI pipeline (lint + test + typecheck)
├── configure.ts                # Configure hook — runs on `node ace configure`
├── index.ts                    # Main entry — re-exports public API
├── eslint.config.js            # ESLint (flat config)
├── tsconfig.json               # TypeScript config (extends @adonisjs/tsconfig)
├── tsnode.esm.js               # TS-Node + SWC loader for tests
├── package.json                # Package metadata, exports, files, peerDeps
├── LICENSE.md
└── README.md
```

## Key Files Explained

### `index.ts` — Main entry point

Everything the user imports from your package goes through here.

```typescript
export { configure } from './configure.js'
export { defineConfig } from './src/define_config.js'
export { MyService } from './src/my_service.js'
export type { MyPackageConfig } from './src/types.js'
```

### `configure.ts` — Post-install hook

Runs when the user executes `node ace configure @your-org/my-package`. Uses codemods to modify the user's project:

- Publish stub files (config, migrations)
- Register the provider in `adonisrc.ts`
- Define environment variables
- Add middleware or commands

### `providers/*.ts` — Service provider

Hooks into the AdonisJS application lifecycle. This is how your package becomes part of the app's IoC container.

### `stubs/*.stub` — Template files

Stub files use Tempura (handlebars-like) syntax. They get copied to the user's project during `configure`. Built-in variables available in stubs: `{{ app }}`, `{{ name }}`, etc.

### `services/main.ts` — Singleton accessor

Provides a convenient import like `import myPackage from '@your-org/my-package/services/main'`. Resolves the singleton from the container after the app has booted.

### `tsnode.esm.js` — Test loader

Enables running TypeScript tests directly using TS-Node with the SWC compiler. The starter kit uses this in `bin/test.ts`.

## package.json Anatomy

```json
{
  "name": "@your-org/adonis-my-package",
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
  },

  "devDependencies": {
    "@adonisjs/core": "^6.0.0",
    "@adonisjs/eslint-config": "^2.0.0",
    "@adonisjs/prettier-config": "^1.0.0",
    "@adonisjs/tsconfig": "^1.0.0",
    "@japa/assert": "^3.0.0",
    "@japa/runner": "^3.0.0",
    "c8": "^10.0.0",
    "typescript": "^5.0.0"
  },

  "scripts": {
    "build": "npm run compile",
    "compile": "tsup",
    "test": "npm run lint && c8 npm run quick:test",
    "quick:test": "node --import=./tsnode.esm.js bin/test.ts",
    "typecheck": "tsc --noEmit",
    "lint": "eslint .",
    "format": "prettier --write ."
  }
}
```

## What Gets Published to npm

Only the `build/` directory contents listed in `files` are published. Source TypeScript is never uploaded. The `exports` field controls what import paths are available to consumers.

## Naming Conventions

The starter kit uses **snake_case** for files (enforced by ESLint):

- `my_service.ts` (not `MyService.ts`)
- `my_package_provider.ts` (not `MyPackageProvider.ts`)
- `define_config.ts` (not `defineConfig.ts`)

Classes inside files use **PascalCase** as normal TypeScript convention.
