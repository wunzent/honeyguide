// app/validation/reporters/json_api_error_reporter.ts

import { errors } from '@vinejs/vine'
import type { FieldContext, ErrorReporterContract } from '@vinejs/vine/types'

/**
 * Custom error reporter that formats validation errors
 * according to the JSON:API specification.
 *
 * @see https://jsonapi.org/format/#errors
 */
export class JSONAPIErrorReporter implements ErrorReporterContract {
  /**
   * Flag indicating whether one or more errors have been reported.
   */
  hasErrors: boolean = false

  /**
   * Collection of error objects formatted per JSON:API spec.
   */
  errors: Array<{
    code: string
    detail: string
    source: { pointer: string }
    meta?: Record<string, any>
  }> = []

  /**
   * Called by VineJS to report a validation error.
   *
   * @param message  - The resolved error message
   * @param rule     - The name of the rule that failed
   * @param field    - The field context with path and metadata
   * @param meta     - Optional metadata from the validation rule
   */
  report(
    message: string,
    rule: string,
    field: FieldContext,
    meta?: Record<string, any>
  ) {
    this.hasErrors = true

    this.errors.push({
      code: rule,
      detail: message,
      source: {
        pointer: field.wildCardPath,
      },
      ...(meta ? { meta } : {}),
    })
  }

  /**
   * Creates and returns the validation error instance.
   * VineJS calls this after all rules have been evaluated.
   */
  createError() {
    return new errors.E_VALIDATION_ERROR(this.errors)
  }
}
