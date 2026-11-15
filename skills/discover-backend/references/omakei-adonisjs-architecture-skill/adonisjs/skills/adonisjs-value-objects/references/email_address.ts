// app/values/email_address.ts

import { InvalidArgumentException } from '@adonisjs/core/exceptions'

export class EmailAddress {
  public readonly value: string

  private constructor(email: string) {
    const normalized = email.trim().toLowerCase()

    if (!EmailAddress.isValid(normalized)) {
      throw new InvalidArgumentException(`Invalid email address: ${email}`)
    }

    this.value = normalized
  }

  /**
   * Create an EmailAddress from a raw string.
   * Normalizes to lowercase and validates format.
   */
  static create(raw: string): EmailAddress {
    return new EmailAddress(raw)
  }

  /**
   * Restore from a database / serialized value (alias for create).
   */
  static fromRaw(raw: string): EmailAddress {
    return new EmailAddress(raw)
  }

  /**
   * Extract the domain portion of the email.
   */
  get domain(): string {
    return this.value.split('@')[1]
  }

  /**
   * Extract the local part (before the @).
   */
  get localPart(): string {
    return this.value.split('@')[0]
  }

  /**
   * Check value equality with another EmailAddress.
   */
  equals(other: EmailAddress): boolean {
    return this.value === other.value
  }

  /**
   * Serialize for JSON responses or Lucid persistence.
   */
  serialize(): string {
    return this.value
  }

  /**
   * Return the string representation.
   */
  toString(): string {
    return this.value
  }

  /**
   * Basic email format validation.
   * For production, consider using VineJS on the boundary instead.
   */
  private static isValid(email: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  }
}
