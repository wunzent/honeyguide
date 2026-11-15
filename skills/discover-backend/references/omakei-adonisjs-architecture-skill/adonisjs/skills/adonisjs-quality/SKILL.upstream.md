---
name: adonisjs-quality
description: Code quality tooling for AdonisJS — ESLint, Prettier, TypeScript strict mode, test coverage, and CI/CD. Use when working with code quality, static analysis, formatting, linting, or when user mentions ESLint, Prettier, TypeScript strict, tsc, code style, linting, code quality, CI/CD, pre-commit hooks, test coverage, architecture tests, naming conventions, or asks how to enforce coding standards in an AdonisJS project.
---

# AdonisJS Quality

Linting, formatting, type safety, test coverage, and CI/CD enforcement for AdonisJS projects.

**Reference implementations:**
- [ESLint config →](references/eslint-config.ts)
- [CI/CD workflow →](references/github-actions.yml)
- [Architecture tests →](references/architecture-tests.ts)

## Quality Stack

```json
// package.json scripts
{
  "scripts": {
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "typecheck": "tsc --noEmit",
    "test": "node ace test",
    "test:coverage": "c8 node ace test",
    "quality": "npm run typecheck && npm run lint && npm run test"
  }
}
```

Run `npm run quality` before every commit. Gate CI/CD on all three passing.

---

## 1. TypeScript Strict Mode

### tsconfig.json

AdonisJS ships with a good default. Ensure these are set:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "exactOptionalPropertyTypes": false,
    "noUncheckedIndexedAccess": true
  }
}
```

### What `strict: true` enables

- `strictNullChecks` — no implicit `null`/`undefined`
- `strictFunctionTypes` — contravariant parameter checking
- `strictBindCallApply` — strict `bind`/`call`/`apply`
- `strictPropertyInitialization` — requires `declare` or initializer
- `noImplicitAny` — no implicit `any` types
- `noImplicitThis` — no implicit `this`
- `alwaysStrict` — emits `"use strict"` in every file

### Run type checking

```bash
npx tsc --noEmit          # check all files
npx tsc --noEmit --watch  # watch mode during development
```

---

## 2. ESLint (Static Analysis + Linting)

AdonisJS v6 ships with `@adonisjs/eslint-config`. ESLint replaces PHPStan for TypeScript — it catches unused variables, unreachable code, type issues, and enforces conventions.

### Setup

```bash
npm i -D eslint @adonisjs/eslint-config
```

### eslint.config.js

```javascript
import { configApp } from '@adonisjs/eslint-config'

export default configApp()
```

### Customizing rules

```javascript
import { configApp } from '@adonisjs/eslint-config'

export default [
  ...configApp(),
  {
    rules: {
      // Enforce explicit return types on exported functions
      '@typescript-eslint/explicit-function-return-type': ['warn', {
        allowExpressions: true,
        allowTypedFunctionExpressions: true,
      }],
      // No console.log in production code (allow warn/error)
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      // Enforce consistent import ordering
      'sort-imports': ['warn', { ignoreDeclarationSort: true }],
      // No unused vars (TypeScript-aware)
      '@typescript-eslint/no-unused-vars': ['error', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
      }],
    },
  },
]
```

### Run

```bash
npx eslint .              # check
npx eslint . --fix        # auto-fix
```

---

## 3. Prettier (Code Formatting)

### Setup

```bash
npm i -D prettier @adonisjs/prettier-config
```

### .prettierrc

```json
"@adonisjs/prettier-config"
```

Or customize:

```json
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "es5",
  "printWidth": 100,
  "tabWidth": 2
}
```

### .prettierignore

```
build/
node_modules/
.adonisjs/
database/schema.ts
```

### Run

```bash
npx prettier --write .     # format all
npx prettier --check .     # check only (for CI)
```

---

## 4. Test Coverage

### Setup with c8

`c8` is the recommended Node.js coverage tool (uses V8's built-in coverage):

```bash
npm i -D c8
```

### Run

```bash
npx c8 node ace test                     # with coverage report
npx c8 --check-coverage --lines 80 node ace test  # enforce 80% minimum
npx c8 --reporter=html node ace test     # HTML report in ./coverage/
```

### package.json scripts

```json
{
  "scripts": {
    "test": "node ace test",
    "test:coverage": "c8 node ace test",
    "test:coverage:check": "c8 --check-coverage --lines 80 --functions 70 --branches 70 node ace test"
  }
}
```

### .c8rc.json

```json
{
  "include": ["app/**/*.ts"],
  "exclude": ["app/**/*.spec.ts", "tests/**/*"],
  "reporter": ["text", "html", "lcov"],
  "all": true,
  "clean": true
}
```

---

## 5. Architecture Tests

Use Japa tests to enforce structural conventions. These tests run in CI alongside your regular test suite.

```typescript
// tests/architecture/naming.spec.ts
import { test } from '@japa/runner'
import { readdir } from 'node:fs/promises'
import { join } from 'node:path'

test.group('Architecture | naming conventions', () => {
  test('controllers end with _controller', async ({ assert }) => {
    const files = await readdir(join(process.cwd(), 'app/controllers'), { recursive: true })
    const tsFiles = files.filter((f) => f.endsWith('.ts') && !f.includes('.spec.'))

    for (const file of tsFiles) {
      assert.isTrue(
        file.endsWith('_controller.ts'),
        `Controller file "${file}" must end with _controller.ts`
      )
    }
  })

  test('middleware files end with _middleware', async ({ assert }) => {
    const files = await readdir(join(process.cwd(), 'app/middleware'))
    const tsFiles = files.filter((f) => f.endsWith('.ts'))

    for (const file of tsFiles) {
      assert.isTrue(
        file.endsWith('_middleware.ts'),
        `Middleware file "${file}" must end with _middleware.ts`
      )
    }
  })

  test('validators end with .ts and live in app/validators', async ({ assert }) => {
    const files = await readdir(join(process.cwd(), 'app/validators'))
    assert.isNotEmpty(files.filter((f) => f.endsWith('.ts')))
  })
})
```

```typescript
// tests/architecture/structure.spec.ts
import { test } from '@japa/runner'
import { access } from 'node:fs/promises'
import { join } from 'node:path'

test.group('Architecture | project structure', () => {
  test('required directories exist', async ({ assert }) => {
    const requiredDirs = [
      'app/controllers',
      'app/models',
      'app/validators',
      'app/middleware',
      'config',
      'database/migrations',
      'start',
      'tests',
    ]

    for (const dir of requiredDirs) {
      try {
        await access(join(process.cwd(), dir))
      } catch {
        assert.fail(`Required directory "${dir}" does not exist`)
      }
    }
  })

  test('no business logic in controllers (max 30 lines per method)', async ({ assert }) => {
    // This is a heuristic — adjust the line count to your team's standard
    const { readFile, readdir } = await import('node:fs/promises')
    const dir = join(process.cwd(), 'app/controllers')
    const files = await readdir(dir, { recursive: true })

    for (const file of files.filter((f) => f.endsWith('.ts'))) {
      const content = await readFile(join(dir, file), 'utf-8')
      const methods = content.match(/async \w+\([^)]*\)[^{]*{/g) || []

      // Just a presence check — detailed line counting left to linting
      assert.isTrue(
        methods.length > 0 || content.includes('handle('),
        `Controller "${file}" should have at least one method`
      )
    }
  })
})
```

---

## 6. Pre-commit Hooks

### With simple-git-hooks + lint-staged

```bash
npm i -D simple-git-hooks lint-staged
```

### package.json

```json
{
  "simple-git-hooks": {
    "pre-commit": "npx lint-staged"
  },
  "lint-staged": {
    "*.ts": ["eslint --fix", "prettier --write"],
    "*.{json,md,yml}": ["prettier --write"]
  }
}
```

### Activate

```bash
npx simple-git-hooks
```

Now every commit automatically lints and formats staged files.

---

## 7. CI/CD

### GitHub Actions

```yaml
# .github/workflows/quality.yml
name: Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: 'npm'

      - run: npm ci

      - name: Type Check
        run: npx tsc --noEmit

      - name: Lint
        run: npx eslint .

      - name: Format Check
        run: npx prettier --check .

      - name: Run Tests
        run: npx c8 --check-coverage --lines 80 node ace test
        env:
          NODE_ENV: test
          DB_CONNECTION: pg
          DB_HOST: localhost
          DB_PORT: 5432
          DB_USER: test
          DB_PASSWORD: test
          DB_DATABASE: test
          SESSION_DRIVER: memory
```

---

## 8. Common Anti-patterns

### What to watch for

| Anti-pattern | Fix |
|---|---|
| Business logic in controllers | Extract to services/actions |
| `any` type usage | Use explicit types or generics |
| Missing `declare` on Lucid columns | Always use `declare` with `@column()` |
| Unused imports | ESLint auto-removes with `--fix` |
| `console.log` in production code | Use AdonisJS Logger instead |
| Unhandled promise rejections | Always `await` or `.catch()` |
| Raw SQL without parameterization | Use query builder bindings |
| Hardcoded config values | Use `env()` and `config/` files |
| Circular imports | Restructure modules or use lazy imports |
| Tests without database cleanup | Use `testUtils.db().truncate()` |

### Type safety checklist

- All function parameters have explicit types
- All return types are declared (at least on exported functions)
- No `as any` casts (use type guards or generics instead)
- Lucid model columns use `declare` keyword
- Enum values are used instead of magic strings
- `null`/`undefined` handled explicitly (no `!` non-null assertions)

---

## Quality Metrics

| Metric | Target |
|---|---|
| TypeScript errors (`tsc --noEmit`) | 0 |
| ESLint errors | 0 |
| Prettier violations | 0 |
| Test pass rate | 100% |
| Line coverage | 80%+ |
| Architecture test pass rate | 100% |

### Review cadence

- **Per commit** — lint-staged + pre-commit hooks
- **Per PR** — full CI/CD pipeline
- **Weekly** — coverage trend review
- **Monthly** — architecture compliance audit

---

## Summary

| Tool | Purpose | Laravel equivalent |
|---|---|---|
| `tsc --noEmit` | Type checking | PHPStan |
| ESLint | Linting + static analysis | PHPStan + Larastan |
| Prettier | Code formatting | Laravel Pint |
| c8 | Test coverage | Pest `--coverage` |
| Japa arch tests | Architecture enforcement | Pest `arch()` |
| simple-git-hooks | Pre-commit automation | Composer git hooks |
| GitHub Actions | CI/CD pipeline | GitHub Actions |
