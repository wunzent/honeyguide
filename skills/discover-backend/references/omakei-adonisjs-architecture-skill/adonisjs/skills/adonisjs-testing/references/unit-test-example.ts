// tests/unit/values/money.spec.ts
//
// Full example of a unit test for a value object.
// Demonstrates: assert style, throws, grouped tests, datasets.

import { test } from '@japa/runner'
import { Money } from '#values/money'

test.group('Money | creation', () => {
  test('creates from cents', ({ assert }) => {
    const money = Money.fromCents(2999)

    assert.equal(money.amount, 2999)
    assert.equal(money.currency, 'USD')
  })

  test('creates from dollars', ({ assert }) => {
    const money = Money.fromDollars(29.99)

    assert.equal(money.amount, 2999)
    assert.equal(money.currency, 'USD')
  })

  test('rounds correctly from dollars', ({ assert }) => {
    // Floating point: 19.99 * 100 = 1998.9999...
    const money = Money.fromDollars(19.99)
    assert.equal(money.amount, 1999)
  })

  test('creates zero money', ({ assert }) => {
    const money = Money.zero()

    assert.equal(money.amount, 0)
    assert.isTrue(money.isZero())
  })

  test('accepts custom currency', ({ assert }) => {
    const money = Money.fromCents(500, 'eur')
    assert.equal(money.currency, 'EUR')
  })

  test('throws on negative amount', ({ assert }) => {
    assert.throws(
      () => Money.fromCents(-100),
      'Amount cannot be negative'
    )
  })
})

test.group('Money | arithmetic', () => {
  test('adds two values', ({ assert }) => {
    const a = Money.fromDollars(10)
    const b = Money.fromDollars(5.50)
    const result = a.add(b)

    assert.equal(result.formatted(), '15.50')
    // Original values are unchanged (immutability)
    assert.equal(a.formatted(), '10.00')
  })

  test('subtracts two values', ({ assert }) => {
    const a = Money.fromDollars(20)
    const b = Money.fromDollars(7.50)
    const result = a.subtract(b)

    assert.equal(result.formatted(), '12.50')
  })

  test('multiplies by scalar', ({ assert }) => {
    const price = Money.fromDollars(9.99)
    const result = price.multiply(3)

    assert.equal(result.formatted(), '29.97')
  })

  test('throws on currency mismatch', ({ assert }) => {
    const usd = Money.fromDollars(10)
    const eur = Money.fromCents(500, 'EUR')

    assert.throws(
      () => usd.add(eur),
      'Currency mismatch'
    )
  })
})

test.group('Money | comparison', () => {
  test('equal values are equal', ({ assert }) => {
    const a = Money.fromCents(1000)
    const b = Money.fromDollars(10)

    assert.isTrue(a.equals(b))
  })

  test('different amounts are not equal', ({ assert }) => {
    const a = Money.fromCents(1000)
    const b = Money.fromCents(999)

    assert.isFalse(a.equals(b))
  })

  test('different currencies are not equal', ({ assert }) => {
    const a = Money.fromCents(1000, 'USD')
    const b = Money.fromCents(1000, 'EUR')

    assert.isFalse(a.equals(b))
  })

  test('greater than', ({ assert }) => {
    const a = Money.fromDollars(20)
    const b = Money.fromDollars(10)

    assert.isTrue(a.greaterThan(b))
    assert.isFalse(b.greaterThan(a))
  })
})

test.group('Money | formatting', () => {
  test('formats as decimal string')
    .with([
      { cents: 0, expected: '0.00' },
      { cents: 1, expected: '0.01' },
      { cents: 100, expected: '1.00' },
      { cents: 2999, expected: '29.99' },
      { cents: 10050, expected: '100.50' },
    ])
    .run(({ assert }, { cents, expected }) => {
      const money = Money.fromCents(cents)
      assert.equal(money.formatted(), expected)
    })
})

// ---------------------------------------------------------------------------
// Example using the expect (Jest) style for comparison
// ---------------------------------------------------------------------------

test.group('Money | expect style', () => {
  test('creates and formats correctly', ({ expect }) => {
    const money = Money.fromDollars(42.50)

    expect(money.amount).toBe(4250)
    expect(money.currency).toBe('USD')
    expect(money.formatted()).toBe('42.50')
    expect(money.isZero()).toBe(false)
  })

  test('add returns new instance', ({ expect }) => {
    const a = Money.fromDollars(10)
    const b = Money.fromDollars(5)
    const result = a.add(b)

    expect(result).not.toBe(a)  // different reference (immutable)
    expect(result.amount).toBe(1500)
  })

  test('throws on negative', ({ expect }) => {
    expect(() => Money.fromCents(-1)).toThrow('Amount cannot be negative')
  })
})
