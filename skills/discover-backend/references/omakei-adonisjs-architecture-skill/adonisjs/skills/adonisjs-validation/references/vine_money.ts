// app/validation/types/vine_money.ts

import vine, { BaseLiteralType, Vine } from '@vinejs/vine'
import type { FieldContext, FieldOptions, Validation } from '@vinejs/vine/types'

/**
 * The output shape of the Money schema type after validation.
 * Represents a monetary amount in the smallest unit (cents).
 */
type MoneyOutput = {
  amount: number
  currency: string
}

// ---------------------------------------------------------------------------
// Step 1 — Create the validation rule
// ---------------------------------------------------------------------------

/**
 * Validates that the input is a valid monetary amount (numeric)
 * and transforms it into a MoneyOutput object.
 *
 * Accepts both numbers and string representations of numbers
 * (as HTML forms serialize everything to strings).
 */
const isMoney = vine.createRule(
  (value: unknown, _options: undefined, field: FieldContext) => {
    const numericValue = vine.helpers.asNumber(value)

    if (Number.isNaN(numericValue)) {
      field.report(
        'The {{ field }} field must be a valid monetary amount',
        'money',
        field
      )
      return
    }

    if (numericValue < 0) {
      field.report(
        'The {{ field }} field must not be negative',
        'money.positive',
        field
      )
      return
    }

    // Transform the raw numeric input into a Money value object
    field.mutate({ amount: numericValue, currency: 'USD' } satisfies MoneyOutput, field)
  }
)

// ---------------------------------------------------------------------------
// Step 2 — Create the schema class
// ---------------------------------------------------------------------------

/**
 * VineMoney schema class.
 *
 * Generic parameters for BaseLiteralType:
 *   1. Input type  — what the user sends (string or number from form/JSON)
 *   2. Output type — what you get after validation
 *   3. CamelCase output type — same as output when no transformation needed
 */
export class VineMoney extends BaseLiteralType<string | number, MoneyOutput, MoneyOutput> {
  constructor(options?: FieldOptions, validations?: Validation<any>[]) {
    super(options, validations || [])
    this.dataTypeValidator = isMoney()
  }

  /**
   * Clone is required by VineJS for schema composition (.clone(), .optional(), etc.)
   */
  clone() {
    return new VineMoney(
      this.cloneOptions(),
      this.cloneValidations()
    ) as this
  }

  // -------------------------------------------------------------------------
  // Add custom chainable methods here if needed.
  // For example: minAmount, maxAmount, currency, etc.
  // -------------------------------------------------------------------------
}

// ---------------------------------------------------------------------------
// Step 3 (optional) — Extend the Vine builder
// ---------------------------------------------------------------------------

/**
 * Add vine.money() method so it can be used like vine.string() or vine.number().
 */
Vine.macro('money', function () {
  return new VineMoney()
})

/**
 * TypeScript declaration merging to make vine.money() type-safe.
 */
declare module '@vinejs/vine' {
  interface Vine {
    money(): VineMoney
  }
}

// ---------------------------------------------------------------------------
// Usage
// ---------------------------------------------------------------------------
//
// import vine from '@vinejs/vine'
// import './validation/types/vine_money.js'  // side-effect import to register the macro
//
// const schema = vine.object({
//   product_id: vine.string(),
//   price: vine.money(),              // validates as numeric, outputs MoneyOutput
//   discount: vine.money().optional(),
// })
