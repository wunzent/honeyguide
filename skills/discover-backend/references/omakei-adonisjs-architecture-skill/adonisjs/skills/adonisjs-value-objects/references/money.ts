// app/values/money.ts

import { InvalidArgumentException } from '@adonisjs/core/exceptions'

export class Money {
  private constructor(
    public readonly amount: number,
    public readonly currency: string
  ) {
    if (!Number.isInteger(amount)) {
      throw new InvalidArgumentException('Amount must be an integer (cents)')
    }
    if (amount < 0) {
      throw new InvalidArgumentException('Amount cannot be negative')
    }
  }

  /**
   * Create a Money instance from a cent value.
   */
  static fromCents(cents: number, currency: string = 'USD'): Money {
    return new Money(cents, currency.toUpperCase())
  }

  /**
   * Create a Money instance from a dollar (major unit) value.
   * Rounds to the nearest cent to avoid floating-point issues.
   */
  static fromDollars(dollars: number, currency: string = 'USD'): Money {
    return new Money(Math.round(dollars * 100), currency.toUpperCase())
  }

  /**
   * Create a zero-value Money instance.
   */
  static zero(currency: string = 'USD'): Money {
    return new Money(0, currency.toUpperCase())
  }

  /**
   * Add another Money value (must share the same currency).
   * Returns a new instance.
   */
  add(other: Money): Money {
    this.assertSameCurrency(other)
    return new Money(this.amount + other.amount, this.currency)
  }

  /**
   * Subtract another Money value (must share the same currency).
   * Returns a new instance.
   */
  subtract(other: Money): Money {
    this.assertSameCurrency(other)
    return new Money(this.amount - other.amount, this.currency)
  }

  /**
   * Multiply by a scalar. Rounds to the nearest cent.
   * Returns a new instance.
   */
  multiply(multiplier: number): Money {
    return new Money(Math.round(this.amount * multiplier), this.currency)
  }

  /**
   * Return the amount formatted as a decimal string (e.g. "29.99").
   */
  formatted(): string {
    return (this.amount / 100).toFixed(2)
  }

  /**
   * Return the amount in the major unit (e.g. dollars).
   */
  toDollars(): number {
    return this.amount / 100
  }

  /**
   * Check value equality with another Money instance.
   */
  equals(other: Money): boolean {
    return this.amount === other.amount && this.currency === other.currency
  }

  /**
   * Check if this amount is greater than another.
   */
  greaterThan(other: Money): boolean {
    this.assertSameCurrency(other)
    return this.amount > other.amount
  }

  /**
   * Check if this amount is less than another.
   */
  lessThan(other: Money): boolean {
    this.assertSameCurrency(other)
    return this.amount < other.amount
  }

  /**
   * Check if this is a zero amount.
   */
  isZero(): boolean {
    return this.amount === 0
  }

  /**
   * Serialize to a plain object (useful for JSON responses or Lucid).
   */
  serialize(): { amount: number; currency: string } {
    return { amount: this.amount, currency: this.currency }
  }

  /**
   * Restore from a serialized plain object.
   */
  static fromSerialized(data: { amount: number; currency: string }): Money {
    return new Money(data.amount, data.currency)
  }

  /**
   * Assert that two Money instances share the same currency.
   */
  private assertSameCurrency(other: Money): void {
    if (this.currency !== other.currency) {
      throw new InvalidArgumentException(
        `Currency mismatch: cannot combine ${this.currency} with ${other.currency}`
      )
    }
  }
}
