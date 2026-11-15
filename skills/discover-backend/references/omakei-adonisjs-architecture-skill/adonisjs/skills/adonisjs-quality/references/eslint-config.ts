// eslint.config.js
//
// ESLint flat config for AdonisJS projects.
// Uses @adonisjs/eslint-config as the base, with custom overrides
// for stricter type safety and project conventions.

import { configApp } from '@adonisjs/eslint-config'

export default [
  ...configApp(),

  // ── Project-wide overrides ──────────────────────────────
  {
    rules: {
      // Require explicit return types on exported functions.
      // Helps catch accidental return type changes and improves readability.
      '@typescript-eslint/explicit-function-return-type': ['warn', {
        allowExpressions: true,
        allowTypedFunctionExpressions: true,
        allowHigherOrderFunctions: true,
      }],

      // No console.log — use AdonisJS Logger instead.
      // Allow console.warn and console.error for edge cases.
      'no-console': ['warn', { allow: ['warn', 'error'] }],

      // Unused variables are errors (underscore prefix allowed).
      '@typescript-eslint/no-unused-vars': ['error', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
      }],

      // Prefer `const` over `let` when variable is never reassigned.
      'prefer-const': 'error',

      // No `var` — always use `const` or `let`.
      'no-var': 'error',

      // Enforce consistent use of type imports.
      '@typescript-eslint/consistent-type-imports': ['error', {
        prefer: 'type-imports',
        fixStyle: 'inline-type-imports',
      }],

      // No floating promises — every async call must be awaited or handled.
      '@typescript-eslint/no-floating-promises': 'error',

      // Discourage `any` — use `unknown` and narrow with type guards.
      '@typescript-eslint/no-explicit-any': 'warn',

      // No non-null assertions (!) — handle nullability explicitly.
      '@typescript-eslint/no-non-null-assertion': 'warn',
    },
  },

  // ── Test files: relax some rules ────────────────────────
  {
    files: ['tests/**/*.ts'],
    rules: {
      // Tests can use console for debugging
      'no-console': 'off',
      // Tests don't need explicit return types
      '@typescript-eslint/explicit-function-return-type': 'off',
      // Tests can use any for mock/fake setup
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },

  // ── Config files: relax ─────────────────────────────────
  {
    files: ['config/**/*.ts', 'start/**/*.ts', 'database/**/*.ts'],
    rules: {
      '@typescript-eslint/explicit-function-return-type': 'off',
    },
  },
]

// ─────────────────────────────────────────────────────────────
// .prettierrc — Prettier configuration
// ─────────────────────────────────────────────────────────────
//
// Option 1: Extend AdonisJS preset
// "@adonisjs/prettier-config"
//
// Option 2: Custom config
// {
//   "semi": false,
//   "singleQuote": true,
//   "trailingComma": "es5",
//   "printWidth": 100,
//   "tabWidth": 2,
//   "arrowParens": "always",
//   "endOfLine": "lf"
// }

// ─────────────────────────────────────────────────────────────
// .prettierignore
// ─────────────────────────────────────────────────────────────
//
// build/
// node_modules/
// .adonisjs/
// database/schema.ts
// coverage/

// ─────────────────────────────────────────────────────────────
// tsconfig.json — strict settings (merge with AdonisJS defaults)
// ─────────────────────────────────────────────────────────────
//
// {
//   "compilerOptions": {
//     "strict": true,
//     "noUnusedLocals": true,
//     "noUnusedParameters": true,
//     "noImplicitReturns": true,
//     "noFallthroughCasesInSwitch": true,
//     "forceConsistentCasingInFileNames": true,
//     "noUncheckedIndexedAccess": true
//   }
// }
