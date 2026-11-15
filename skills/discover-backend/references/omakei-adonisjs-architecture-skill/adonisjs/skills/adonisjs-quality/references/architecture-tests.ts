// tests/architecture/naming.spec.ts
//
// Architecture tests enforce structural conventions via the test suite.
// Run alongside regular tests in CI. Equivalent to Pest's arch() tests.

import { test } from '@japa/runner'
import { readdir, readFile, access } from 'node:fs/promises'
import { join, basename } from 'node:path'

const APP = join(process.cwd(), 'app')

/**
 * Helper: recursively list all .ts files in a directory.
 */
async function listTsFiles(dir: string): Promise<string[]> {
  try {
    const entries = await readdir(dir, { recursive: true, withFileTypes: false })
    return (entries as string[]).filter(
      (f) => f.endsWith('.ts') && !f.endsWith('.spec.ts') && !f.endsWith('.d.ts')
    )
  } catch {
    return [] // directory doesn't exist
  }
}

// ─────────────────────────────────────────────────────────────
// Naming conventions
// ─────────────────────────────────────────────────────────────

test.group('Architecture | naming', () => {
  test('controller files end with _controller.ts', async ({ assert }) => {
    const files = await listTsFiles(join(APP, 'controllers'))
    assert.isNotEmpty(files, 'No controller files found')

    for (const file of files) {
      assert.isTrue(
        file.endsWith('_controller.ts'),
        `"${file}" should end with _controller.ts`
      )
    }
  })

  test('middleware files end with _middleware.ts', async ({ assert }) => {
    const files = await listTsFiles(join(APP, 'middleware'))

    for (const file of files) {
      assert.isTrue(
        file.endsWith('_middleware.ts'),
        `"${file}" should end with _middleware.ts`
      )
    }
  })

  test('model files are snake_case', async ({ assert }) => {
    const files = await listTsFiles(join(APP, 'models'))

    for (const file of files) {
      const name = basename(file, '.ts')
      assert.match(
        name,
        /^[a-z][a-z0-9_]*$/,
        `Model file "${file}" should be snake_case`
      )
    }
  })

  test('enum files are snake_case', async ({ assert }) => {
    const files = await listTsFiles(join(APP, 'enums'))
    if (files.length === 0) return // enums are optional

    for (const file of files) {
      const name = basename(file, '.ts')
      assert.match(name, /^[a-z][a-z0-9_]*$/, `Enum file "${file}" should be snake_case`)
    }
  })

  test('validator files live in app/validators', async ({ assert }) => {
    try {
      await access(join(APP, 'validators'))
      const files = await listTsFiles(join(APP, 'validators'))
      assert.isNotEmpty(files, 'Validators directory exists but has no files')
    } catch {
      // validators directory not required for all projects
    }
  })
})

// ─────────────────────────────────────────────────────────────
// Project structure
// ─────────────────────────────────────────────────────────────

test.group('Architecture | structure', () => {
  test('required directories exist', async ({ assert }) => {
    const requiredDirs = [
      'app/controllers',
      'app/models',
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

  test('start/routes.ts exists', async ({ assert }) => {
    try {
      await access(join(process.cwd(), 'start/routes.ts'))
    } catch {
      assert.fail('start/routes.ts must exist')
    }
  })

  test('start/kernel.ts exists', async ({ assert }) => {
    try {
      await access(join(process.cwd(), 'start/kernel.ts'))
    } catch {
      assert.fail('start/kernel.ts must exist')
    }
  })
})

// ─────────────────────────────────────────────────────────────
// Code quality rules
// ─────────────────────────────────────────────────────────────

test.group('Architecture | code quality', () => {
  test('no console.log in app/ source files', async ({ assert }) => {
    const files = await listTsFiles(APP)

    for (const file of files) {
      const content = await readFile(join(APP, file), 'utf-8')
      const lines = content.split('\n')

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim()
        // Allow commented-out console.log
        if (line.startsWith('//') || line.startsWith('*')) continue

        assert.isFalse(
          line.includes('console.log('),
          `console.log found in "${file}" at line ${i + 1} — use Logger instead`
        )
      }
    }
  })

  test('controllers do not import from @adonisjs/lucid/services/db directly', async ({ assert }) => {
    const files = await listTsFiles(join(APP, 'controllers'))

    for (const file of files) {
      const content = await readFile(join(APP, 'controllers', file), 'utf-8')
      assert.isFalse(
        content.includes("from '@adonisjs/lucid/services/db'"),
        `Controller "${file}" should not import db directly — use models or inject a service`
      )
    }
  })

  test('models use declare keyword for column properties', async ({ assert }) => {
    const files = await listTsFiles(join(APP, 'models'))

    for (const file of files) {
      const content = await readFile(join(APP, 'models', file), 'utf-8')
      const columnLines = content
        .split('\n')
        .filter((line) => line.includes('@column'))

      // For each @column decorator, the next non-empty line should use 'declare'
      const lines = content.split('\n')
      for (let i = 0; i < lines.length; i++) {
        if (lines[i].includes('@column')) {
          // Find the next non-empty line
          let j = i + 1
          while (j < lines.length && lines[j].trim() === '') j++

          if (j < lines.length) {
            const propLine = lines[j].trim()
            // Skip if it's another decorator
            if (propLine.startsWith('@')) continue

            assert.isTrue(
              propLine.includes('declare '),
              `Model "${file}" line ${j + 1}: column property should use "declare" keyword`
            )
          }
        }
      }
    }
  })

  test('no hardcoded secrets in source files', async ({ assert }) => {
    const files = await listTsFiles(APP)
    const patterns = [
      /['"]sk_live_/,           // Stripe secret key
      /['"]sk_test_/,           // Stripe test key
      /['"]AKIA[A-Z0-9]{16}/,  // AWS access key
      /password\s*[:=]\s*['"][^'"]{8,}['"]/, // Hardcoded passwords
    ]

    for (const file of files) {
      const content = await readFile(join(APP, file), 'utf-8')

      for (const pattern of patterns) {
        assert.isFalse(
          pattern.test(content),
          `Potential hardcoded secret in "${file}" matching ${pattern}`
        )
      }
    }
  })
})

// ─────────────────────────────────────────────────────────────
// Dependency rules
// ─────────────────────────────────────────────────────────────

test.group('Architecture | dependencies', () => {
  test('models do not import controllers', async ({ assert }) => {
    const files = await listTsFiles(join(APP, 'models'))

    for (const file of files) {
      const content = await readFile(join(APP, 'models', file), 'utf-8')
      assert.isFalse(
        content.includes('#controllers/'),
        `Model "${file}" should not import from controllers — models are lower-level`
      )
    }
  })

  test('validators do not import models directly', async ({ assert }) => {
    const validatorDir = join(APP, 'validators')
    try {
      await access(validatorDir)
    } catch {
      return // no validators dir
    }

    const files = await listTsFiles(validatorDir)

    for (const file of files) {
      const content = await readFile(join(validatorDir, file), 'utf-8')
      // VineJS unique/exists rules are OK — they reference tables, not models
      // But direct model imports indicate coupling
      assert.isFalse(
        content.includes('#models/'),
        `Validator "${file}" should not import models directly`
      )
    }
  })
})
