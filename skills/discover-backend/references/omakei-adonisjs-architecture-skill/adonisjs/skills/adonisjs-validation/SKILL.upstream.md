---
name: adonisjs-vinejs-validation
description: VineJS validation patterns for AdonisJS. Use when working with form validation, request validation, custom validation rules, custom error messages, error reporters, conditional validation, data transformation, reusable schemas, schema composition, custom schema types, or any VineJS usage in an AdonisJS project. Also trigger when user mentions validators, vine, validation messages, field context, validation helpers, or extending VineJS.
---

# AdonisJS VineJS Validation

Comprehensive guide for using VineJS validation in AdonisJS projects. Covers custom messages, conditional validation, data transformation, reusable schemas, custom error reporters, field context, helpers, and custom schema types.

**Related guides:**

- [DTOs](../adonisjs-dtos/SKILL.md) - DTOs are built from validated VineJS output
- [Controllers](../adonisjs-controllers/SKILL.md) - Controllers call `request.validateUsing()` at the HTTP boundary

**Reference implementations:**
- [Custom error reporter →](references/json_api_error_reporter.ts)
- [Custom schema type (Money) →](references/vine_money.ts)
- [Custom rule (unique) →](references/unique_rule.ts)
- [Global messages setup →](references/global_messages.ts)

## Basic Usage

```typescript
// app/validators/post.ts
import vine from '@vinejs/vine'

export const createPostValidator = vine.compile(
  vine.object({
    title: vine.string().trim().minLength(6).maxLength(255),
    slug: vine.string().trim().alphaNumeric({ allow: ['dash'] }),
    body: vine.string().trim().escape(),
    publishedAt: vine.date().optional(),
  })
)
```

```typescript
// app/controllers/posts_controller.ts
import { createPostValidator } from '#validators/post'

export default class PostsController {
  async store({ request }: HttpContext) {
    const payload = await request.validateUsing(createPostValidator)
    // payload is fully typed — use it directly
  }
}
```

> You do not need `try/catch` — the global exception handler in `app/exceptions/handler.ts` catches `E_VALIDATION_ERROR` and converts it to a `422 Unprocessable Entity` response automatically.

---

## 1. Custom Messages per Validation Rule

Messages are defined as key-value pairs. The key is either the rule name (applies globally) or `field.rule` (targets a specific field).

```typescript
// start/validator.ts
import vine, { SimpleMessagesProvider } from '@vinejs/vine'

vine.messagesProvider = new SimpleMessagesProvider(
  {
    // Global rule messages (apply to every field using this rule)
    'required': 'The {{ field }} field is required',
    'string': 'The {{ field }} field must be a string',
    'email': 'Please provide a valid email address',
    'minLength': 'The {{ field }} field must be at least {{ min }} characters',
    'maxLength': 'The {{ field }} field must not exceed {{ max }} characters',

    // Field-specific messages (override global for a specific field)
    'username.required': 'Please choose a username for your account',
    'username.minLength': 'Username must be at least {{ min }} characters',
    'password.confirmed': 'Password and confirmation do not match',

    // Nested field messages (dot notation)
    'profile.bio.maxLength': 'Bio must not exceed {{ max }} characters',

    // Array element messages (wildcard or specific index)
    'contacts.*.email.required': 'Each contact must have an email',
    'contacts.0.email.required': 'Primary contact email is required',
  },
  // Optional: human-readable field name substitutions
  {
    first_name: 'first name',
    last_name: 'last name',
    dob: 'date of birth',
  }
)
```

**Interpolation placeholders** — `{{ field }}` is always available. Rule-specific placeholders vary: `{{ min }}`, `{{ max }}`, `{{ size }}`, `{{ format }}`, `{{ otherField }}`, etc. Check the VineJS docs for each rule's available placeholders.

---

## 2. Conditional Validation

### requiredWhen — comparison-based

```typescript
vine.object({
  accountType: vine.enum(['personal', 'business']),
  companyName: vine
    .string()
    .optional()
    .requiredWhen('accountType', '=', 'business'),
})
```

Supported operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `notIn`.

### requiredWhen — callback for complex logic

```typescript
vine.object({
  country: vine.string(),
  state: vine.string().optional(),
  address: vine
    .string()
    .optional()
    .requiredWhen((field) => {
      return field.parent.country === 'US' && 'state' in field.parent
    }),
})
```

### requiredIfExists / requiredIfAnyExists

```typescript
vine.object({
  firstName: vine.string().optional().requiredIfExists('lastName'),
  lastName: vine.string().optional().requiredIfExists('firstName'),
})

vine.object({
  password: vine.string().optional().requiredIfAnyExists(['email', 'username']),
})
```

### requiredIfMissing / requiredIfAnyMissing

```typescript
vine.object({
  email: vine.string().optional(),
  phone: vine.string().optional().requiredIfMissing('email'),
})
```

### Unions — type-safe conditional schemas

For complex conditional shapes where different fields apply based on a discriminator, use `vine.group`:

```typescript
const guideSchema = vine.group([
  vine.group.if(
    (data) => vine.helpers.isTrue(data.is_hiring_guide),
    {
      is_hiring_guide: vine.literal(true),
      guide_id: vine.string(),
      amount: vine.number(),
    }
  ),
  vine.group.else({
    is_hiring_guide: vine.literal(false),
  }),
])

const bookingValidator = vine.compile(
  vine
    .object({
      visitor_name: vine.string(),
    })
    .merge(guideSchema)
)
```

---

## 3. Data Transformation

### transform — post-validation output conversion

```typescript
import { DateTime } from 'luxon'

vine.object({
  publishedAt: vine
    .date({ formats: { utc: true } })
    .transform((date) => DateTime.fromJSDate(date)),
})
```

### parse — pre-validation input normalization

```typescript
vine.object({
  tags: vine
    .array(vine.string())
    .parse((value) => {
      // Accept comma-separated string or array
      if (typeof value === 'string') return value.split(',').map((s) => s.trim())
      return value
    }),
})
```

### Built-in mutations on string

```typescript
vine.string().trim()               // strip whitespace
vine.string().toLowerCase()        // lowercase
vine.string().toUpperCase()        // uppercase
vine.string().normalizeEmail()     // normalize email formatting
vine.string().escape()             // HTML-escape
```

---

## 4. Reusable Schemas

VineJS intentionally keeps schema composition simple. Prefer some duplication over complex abstractions.

### Clone — reuse a type with different modifiers

```typescript
const userSchema = vine.object({
  username: vine.string(),
})

const postSchema = vine.object({
  title: vine.string(),
  author: userSchema.clone().nullable(),
})
```

### getProperties — spread into a new object

```typescript
const addressFields = vine.object({
  street: vine.string(),
  city: vine.string(),
  zip: vine.string(),
})

const orderValidator = vine.compile(
  vine.object({
    ...addressFields.getProperties(),
    orderNumber: vine.string(),
  })
)
```

### pick / omit — select specific fields

```typescript
const fullUser = vine.object({
  id: vine.number(),
  username: vine.string(),
  email: vine.string().email(),
  password: vine.string(),
  role: vine.string(),
})

const publicUser = vine.object({
  ...fullUser.pick(['id', 'username', 'email']),
})

const editableUser = vine.object({
  ...fullUser.omit(['id', 'role']),
})
```

### partial — make all or specific fields optional

```typescript
export const createUserValidator = vine.create({
  username: vine.string(),
  email: vine.string().email(),
  password: vine.string(),
})

// All fields optional (for PATCH updates)
export const updateUserValidator = vine.create(
  createUserValidator.schema.partial()
)

// Only specific fields optional
export const patchUserValidator = vine.create(
  createUserValidator.schema.partial(['email', 'username'])
)

// Combine partial + omit
export const editProfileValidator = vine.create(
  createUserValidator.schema.partial(['email']).omit(['password'])
)
```

### vine.helpers.optional — shorthand

```typescript
const optionalAddress = vine.helpers.optional({
  street: vine.string(),
  city: vine.string(),
  zip: vine.string(),
})
// Equivalent to marking each field .optional() individually
```

---

## 5. Custom Error Reporter

**[View full implementation →](references/json_api_error_reporter.ts)**

A reporter controls how validation errors are collected and formatted. Implement the `ErrorReporterContract` interface:

```typescript
import { errors } from '@vinejs/vine'
import type { FieldContext, ErrorReporterContract } from '@vinejs/vine/types'

export class JSONAPIErrorReporter implements ErrorReporterContract {
  hasErrors: boolean = false
  errors: any[] = []

  report(message: string, rule: string, field: FieldContext, meta?: any) {
    this.hasErrors = true
    this.errors.push({
      code: rule,
      detail: message,
      source: { pointer: field.wildCardPath },
      ...(meta ? { meta } : {}),
    })
  }

  createError() {
    return new errors.E_VALIDATION_ERROR(this.errors)
  }
}
```

Register globally, per-schema, or per-validation call:

```typescript
// Global
vine.errorReporter = () => new JSONAPIErrorReporter()

// Per schema
const validator = vine.create({})
validator.errorReporter = () => new JSONAPIErrorReporter()

// Per validation call
await validator.validate(data, {
  errorReporter: () => new JSONAPIErrorReporter(),
})
```

---

## 6. Field Context

The `field` object is available in custom rules, union conditionals, `parse`, and `transform` callbacks. Key properties:

| Property | Description |
|---|---|
| `value` | Current field value (`unknown`) |
| `data` | Root data object (shared, read-only) |
| `meta` | Shared metadata across all fields |
| `parent` | Parent object/array (or `data` if top-level) |
| `name` | Field name (or array index) |
| `wildCardPath` | Dot-notation path with `*` for arrays |
| `getFieldPath()` | Dot-notation path with actual array indices |
| `isValid` | `false` if any prior rule failed |
| `isValidDataType` | `false` if type check itself failed |
| `isDefined` | `false` when value is `null` / `undefined` |
| `isArrayMember` | `true` when inside an array |
| `mutate(newValue, field)` | Replace the output value |
| `report(message, rule, field, args?)` | Report an error |

**Using field context in a custom rule:**

```typescript
vine.createRule((value, options, field) => {
  // Access sibling fields
  const otherValue = field.parent.otherField

  // Access root data
  const userId = field.data.userId

  // Access shared metadata (passed at validation time)
  const locale = field.meta.locale

  // Mutate the output
  field.mutate(String(value).toUpperCase(), field)

  // Report an error
  field.report('Something went wrong', 'myRule', field, { key: 'extra' })
})
```

---

## 7. Helpers

Accessible via `vine.helpers`. Designed to handle HTML form serialization quirks.

**Type checking & coercion:**

```typescript
vine.helpers.isTrue(value)      // true for: true, 1, "1", "true", "on"
vine.helpers.isFalse(value)     // true for: false, 0, "0", "false"
vine.helpers.isString(value)    // narrows type to string
vine.helpers.isObject(value)    // plain object (excludes null, arrays)
vine.helpers.isArray(value)     // narrows type to array
vine.helpers.isNumeric(value)   // number or numeric string
vine.helpers.asNumber(value)    // cast to Number (NaN on failure)
vine.helpers.asBoolean(value)   // cast to boolean (null on failure)
```

**Schema helpers:**

```typescript
vine.helpers.optional({         // mark all fields optional in one call
  name: vine.string(),
  age: vine.number(),
})
```

**Validator.js methods** (also on `vine.helpers`):

`isEmail`, `isURL`, `isAlpha`, `isAlphaNumeric`, `isIP`, `isUUID`, `isAscii`, `isCreditCard`, `isIBAN`, `isJWT`, `isLatLong`, `isMobilePhone`, `isPassportNumber`, `isPostalCode`, `isSlug`, `isDecimal`, `isHexColor`

---

## 8. Custom Schema Type

**[View full implementation →](references/vine_money.ts)**

A custom schema type wraps a data type validator + optional rules into a chainable API (like `vine.string()` or `vine.number()`).

### Step 1 — Create the validation rule

```typescript
import vine from '@vinejs/vine'
import type { FieldContext } from '@vinejs/vine/types'

const isMoney = vine.createRule((value: unknown, _options: undefined, field: FieldContext) => {
  const numericValue = vine.helpers.asNumber(value)

  if (Number.isNaN(numericValue)) {
    field.report('The {{ field }} field must be a valid monetary amount', 'money', field)
    return
  }

  // Transform cents into a Money value object
  field.mutate({ amount: numericValue, currency: 'USD' }, field)
})
```

### Step 2 — Create the schema class

```typescript
import { BaseLiteralType } from '@vinejs/vine'
import type { FieldOptions, Validation } from '@vinejs/vine/types'

type MoneyOutput = { amount: number; currency: string }

export class VineMoney extends BaseLiteralType<string | number, MoneyOutput, MoneyOutput> {
  constructor(options?: FieldOptions, validations?: Validation<any>[]) {
    super(options, validations || [])
    this.dataTypeValidator = isMoney()
  }

  clone() {
    return new VineMoney(this.cloneOptions(), this.cloneValidations()) as this
  }
}
```

### Step 3 — Use directly

```typescript
const schema = vine.object({
  product_id: vine.string(),
  amount: new VineMoney(),
})
```

### Step 4 — Extend the Vine builder (optional)

```typescript
import { Vine } from '@vinejs/vine'

Vine.macro('money', function () {
  return new VineMoney()
})

declare module '@vinejs/vine' {
  interface Vine {
    money(): VineMoney
  }
}

// Now use:  vine.money()
```

---

## Directory Structure

```
app/
├── validators/
│   ├── auth.ts
│   ├── post.ts
│   └── user.ts
├── validation/
│   ├── reporters/
│   │   └── json_api_error_reporter.ts
│   ├── rules/
│   │   └── unique.ts
│   └── types/
│       └── vine_money.ts
start/
└── validator.ts          # global messages & reporter config
```

---

## Summary

| Topic | Key API |
|---|---|
| Custom messages | `SimpleMessagesProvider`, `MessagesProviderContact` |
| Conditional validation | `.requiredWhen()`, `.requiredIfExists()`, `vine.group` |
| Data transformation | `.transform()`, `.parse()`, `.trim()`, `.toLowerCase()` |
| Reusable schemas | `.clone()`, `.getProperties()`, `.pick()`, `.omit()`, `.partial()` |
| Error reporters | `ErrorReporterContract`, `vine.errorReporter` |
| Field context | `field.data`, `field.parent`, `field.meta`, `field.mutate()` |
| Helpers | `vine.helpers.isTrue()`, `.asNumber()`, `.isEmail()`, etc. |
| Custom schema types | `BaseLiteralType`, `Vine.macro()`, `vine.createRule()` |
