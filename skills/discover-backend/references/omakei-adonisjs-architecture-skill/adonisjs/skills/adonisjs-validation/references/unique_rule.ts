// app/validation/rules/unique.ts

import vine from '@vinejs/vine'
import { VineString, VineNumber } from '@vinejs/vine'
import db from '@adonisjs/lucid/services/db'
import type { FieldContext } from '@vinejs/vine/types'

// ---------------------------------------------------------------------------
// Options
// ---------------------------------------------------------------------------

type UniqueOptions = {
  table: string
  column: string
  /** Optional: exclude a specific row by ID (useful for updates) */
  exceptId?: number | string
  /** Optional: column name for the exception (defaults to 'id') */
  idColumn?: string
}

// ---------------------------------------------------------------------------
// Rule implementation
// ---------------------------------------------------------------------------

/**
 * Queries the database to ensure the field's value is unique
 * within the specified table and column.
 *
 * Skips the check if the value is not a string/number (let other
 * rules handle type validation) or if prior rules already failed.
 */
async function unique(
  value: unknown,
  options: UniqueOptions,
  field: FieldContext
) {
  if (typeof value !== 'string' && typeof value !== 'number') {
    return
  }

  if (!field.isValid) {
    return
  }

  let query = db
    .from(options.table)
    .select(options.column)
    .where(options.column, value)

  // Exclude a specific row (e.g. the current user during profile update)
  if (options.exceptId !== undefined) {
    query = query.whereNot(options.idColumn ?? 'id', options.exceptId)
  }

  const row = await query.first()

  if (row) {
    field.report(
      'The {{ field }} field is not unique',
      'unique',
      field
    )
  }
}

// ---------------------------------------------------------------------------
// Create the VineJS rule
// ---------------------------------------------------------------------------

export const uniqueRule = vine.createRule(unique, {
  async: true,
})

// ---------------------------------------------------------------------------
// Extend VineString and VineNumber with a chainable .unique() method
// ---------------------------------------------------------------------------

VineString.macro('unique', function (this: VineString, options: UniqueOptions) {
  return this.use(uniqueRule(options))
})

VineNumber.macro('unique', function (this: VineNumber, options: UniqueOptions) {
  return this.use(uniqueRule(options))
})

/**
 * TypeScript declaration merging for type safety.
 */
declare module '@vinejs/vine' {
  interface VineString {
    unique(options: UniqueOptions): this
  }
  interface VineNumber {
    unique(options: UniqueOptions): this
  }
}

// ---------------------------------------------------------------------------
// Usage examples
// ---------------------------------------------------------------------------
//
// import vine from '@vinejs/vine'
// import './validation/rules/unique.js'  // side-effect import to register macros
//
// // Basic unique check
// const createUserValidator = vine.compile(
//   vine.object({
//     email: vine.string().email().unique({ table: 'users', column: 'email' }),
//     username: vine.string().unique({ table: 'users', column: 'username' }),
//   })
// )
//
// // Unique check excluding current user (for updates)
// const updateUserValidator = vine.compile(
//   vine.object({
//     email: vine
//       .string()
//       .email()
//       .unique({ table: 'users', column: 'email', exceptId: userId }),
//   })
// )
//
// // Using the rule directly (without the macro)
// import { uniqueRule } from '#validation/rules/unique'
//
// vine.object({
//   code: vine.string().use(
//     uniqueRule({ table: 'products', column: 'sku' })
//   ),
// })
