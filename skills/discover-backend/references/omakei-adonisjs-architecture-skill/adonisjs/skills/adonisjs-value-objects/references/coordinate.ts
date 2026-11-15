// app/values/coordinate.ts

import { InvalidArgumentException } from '@adonisjs/core/exceptions'

export class Coordinate {
  private constructor(
    public readonly latitude: number,
    public readonly longitude: number
  ) {
    if (latitude < -90 || latitude > 90) {
      throw new InvalidArgumentException(
        `Latitude must be between -90 and 90, got ${latitude}`
      )
    }
    if (longitude < -180 || longitude > 180) {
      throw new InvalidArgumentException(
        `Longitude must be between -180 and 180, got ${longitude}`
      )
    }
  }

  /**
   * Create a Coordinate from latitude and longitude.
   */
  static create(latitude: number, longitude: number): Coordinate {
    return new Coordinate(latitude, longitude)
  }

  /**
   * Restore from a serialized object.
   */
  static fromSerialized(data: { latitude: number; longitude: number }): Coordinate {
    return new Coordinate(data.latitude, data.longitude)
  }

  /**
   * Calculate the distance to another Coordinate in kilometers
   * using the Haversine formula.
   */
  distanceTo(other: Coordinate): number {
    const R = 6371 // Earth radius in km
    const dLat = this.toRadians(other.latitude - this.latitude)
    const dLon = this.toRadians(other.longitude - this.longitude)

    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(this.toRadians(this.latitude)) *
        Math.cos(this.toRadians(other.latitude)) *
        Math.sin(dLon / 2) ** 2

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))

    return R * c
  }

  /**
   * Check value equality with another Coordinate.
   */
  equals(other: Coordinate): boolean {
    return this.latitude === other.latitude && this.longitude === other.longitude
  }

  /**
   * Serialize for JSON responses or Lucid persistence.
   */
  serialize(): { latitude: number; longitude: number } {
    return { latitude: this.latitude, longitude: this.longitude }
  }

  /**
   * Format as a human-readable string.
   */
  toString(): string {
    return `${this.latitude}, ${this.longitude}`
  }

  private toRadians(degrees: number): number {
    return degrees * (Math.PI / 180)
  }
}
