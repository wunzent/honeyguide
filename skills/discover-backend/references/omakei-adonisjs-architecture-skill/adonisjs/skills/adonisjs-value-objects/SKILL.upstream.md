---
name: adonisjs-value-objects
description: Immutable value objects for domain values in AdonisJS (TypeScript). Use when working with domain values, immutable objects, or when user mentions value objects, immutable values, domain values, money objects, coordinate objects, email address objects, or any typed domain concept in an AdonisJS project. Also trigger when user wants to encapsulate validation, equality, or arithmetic for a domain primitive.
---

# AdonisJS Value Objects

Value objects are **simple, immutable objects** representing domain concepts, implemented in TypeScript for AdonisJS projects.

**Related guides:**

- [DTOs](../adonisjs-dtos/SKILL.md) - DTOs are for data transfer between layers; value objects are for domain concepts with behavior
- [Enums](../adonisjs-enums/SKILL.md) - Use enums for finite sets of named values; value objects for complex domain primitives with logic

## When to Use

**Use value objects when:**
- Complex domain value with behavior (e.g. Money, EmailAddress, Coordinate)
- Immutability is required
- Rich validation logic at construction time
- Need equality comparison by value (not reference)
- Encapsulating domain rules and arithmetic

**Use DTOs when:**
- Transferring data between layers (controller → service, service → response)
- No domain behavior needed

## Simple Value Object

```typescript
// app/values/process_result.ts

import { ProcessResultStatus } from '#enums/process_result_status'

export class ProcessResult {
  private constructor(
    public readonly result: ProcessResultStatus,
    public readonly message: string | null = null
  ) {}

  static success(message?: string): ProcessResult {
    return new ProcessResult(ProcessResultStatus.Success, message ?? null)
  }

  static skip(message?: string): ProcessResult {
    return new ProcessResult(ProcessResultStatus.Skip, message ?? null)
  }

  static fail(message?: string): ProcessResult {
    return new ProcessResult(ProcessResultStatus.Fail, message ?? null)
  }

  isSuccess(): boolean {
    return this.result === ProcessResultStatus.Success
  }

  isFail(): boolean {
    return this.result === ProcessResultStatus.Fail
  }

  isSkip(): boolean {
    return this.result === ProcessResultStatus.Skip
  }
}
```

**Supporting enum:**

```typescript
// app/enums/process_result_status.ts

export enum ProcessResultStatus {
  Success = 'success',
  Skip = 'skip',
  Fail = 'fail',
}
```

## Money Value Object

**[View full implementation →](references/money.ts)**

## Usage Examples

### ProcessResult

```typescript
// In services / actions
return ProcessResult.success('Order processed successfully')
return ProcessResult.skip('Order already processed')
return ProcessResult.fail('Payment declined')

// Checking results
if (result.isSuccess()) {
  // Handle success
}

if (result.isFail()) {
  // Handle failure
}
```

### Money

```typescript
// Creating money values
const price = Money.fromDollars(29.99)
const tax = Money.fromDollars(2.40)
const shipping = Money.fromCents(500) // $5.00

// Operations (returns new instances — immutable)
const subtotal = price.add(tax)
const total = subtotal.add(shipping)

// Multiplication
const bulkPrice = price.multiply(10)

// Display
console.log(total.formatted()) // "37.39"

// Comparison
if (total.equals(expectedTotal)) {
  // Amounts match
}
```

### EmailAddress

```typescript
// Creating email values
const email = EmailAddress.create('User@Example.COM')
console.log(email.value)   // "user@example.com"
console.log(email.domain)  // "example.com"

// Equality
email.equals(EmailAddress.create('USER@example.com')) // true
```

## Key Patterns

### 1. Immutability

Use `readonly` properties and never expose setters:

```typescript
public readonly amount: number
public readonly currency: string
```

### 2. Static Factory Methods

Named constructors for common creation scenarios:

```typescript
static fromDollars(dollars: number): Money
static fromCents(cents: number): Money
static success(message?: string): ProcessResult
static create(raw: string): EmailAddress
```

### 3. Private Constructor

Force use of factory methods to ensure validation always runs:

```typescript
private constructor(/* ... */) {}
```

### 4. Domain Logic

Encapsulate domain rules inside the value object:

```typescript
add(other: Money): Money {
  this.assertSameCurrency(other)
  return new Money(this.amount + other.amount, this.currency)
}
```

### 5. Return New Instances

Operations always return new instances to preserve immutability:

```typescript
add(other: Money): Money {
  return new Money(this.amount + other.amount, this.currency)
}
```

### 6. Value Equality

Implement `equals()` for comparison by value instead of reference:

```typescript
equals(other: Money): boolean {
  return this.amount === other.amount && this.currency === other.currency
}
```

### 7. Serialization for Lucid

When persisting value objects via Lucid models, use `serialize` / `fromRaw` pairs:

```typescript
// In the value object
serialize(): string {
  return this.value
}

static fromRaw(raw: string): EmailAddress {
  return EmailAddress.create(raw)
}

// On the Lucid model — use a custom getter/setter or @beforeSave / @afterFind
class User extends BaseModel {
  @column()
  declare email: string

  get emailAddress(): EmailAddress {
    return EmailAddress.create(this.email)
  }
}
```

## Directory Structure

```
app/
├── values/
│   ├── money.ts
│   ├── process_result.ts
│   ├── coordinate.ts
│   └── email_address.ts
└── enums/
    └── process_result_status.ts
```

## Summary

**Value objects in AdonisJS/TypeScript:**
- Are immutable (`readonly` properties, private constructor)
- Have static factory methods for construction
- Validate at construction time (throw on invalid input)
- Encapsulate domain logic and arithmetic
- Return new instances from operations
- Implement `equals()` for value-based comparison
- Use `serialize()` / `fromRaw()` for Lucid integration

**Use for domain concepts with behavior, not simple data transfer.**
