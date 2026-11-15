---
name: adonisjs-policies
description: Authorization policies for resource access control in AdonisJS using Bouncer. Use when working with authorization, permissions, access control, policies, abilities, or when user mentions policies, authorization, permissions, can, ability checks, bouncer, role-based access, ownership checks, who can do what, or asks how to restrict actions to specific users or roles in an AdonisJS project.
---

# AdonisJS Policies

Policies encapsulate authorization logic per model using `@adonisjs/bouncer`. Each policy groups all permission checks for a resource — ownership, role, state — into a single, testable class.

**Reference implementations:**
- [Full policy example (OrderPolicy) →](references/order_policy.ts)
- [Abilities (standalone gate-style) →](references/abilities.ts)
- [Testing policies →](references/testing_policies.ts)

**Related skills:**
- [Routing & Permissions](../adonisjs-routing/SKILL.md) — route-level authorization with middleware

---

## When to Use

| Use | When |
|---|---|
| **Policy** | Authorization for a specific model (can this user edit *this* post?) |
| **Ability** | Authorization not tied to a model (can this user access the admin area?) |
| **Middleware** | Route-level guard before the controller runs |

---

## Policy Structure

```typescript
// app/policies/order_policy.ts
import User from '#models/user'
import Order from '#models/order'
import { BasePolicy } from '@adonisjs/bouncer'
import { AuthorizationResponse } from '@adonisjs/bouncer'

export default class OrderPolicy extends BasePolicy {
  /**
   * Can the user list orders?
   * Permission check only — no model instance needed.
   */
  viewAny(user: User): boolean {
    return user.hasPermission('orders:list')
  }

  /**
   * Can the user view this specific order?
   * Permission + ownership check.
   */
  view(user: User, order: Order): boolean {
    return user.hasPermission('orders:view')
      && order.customerId === user.customerId
  }

  /**
   * Can the user create orders?
   */
  create(user: User): boolean {
    return user.hasPermission('orders:create')
  }

  /**
   * Can the user update this order?
   * Permission + ownership + state check.
   */
  update(user: User, order: Order): boolean {
    return user.hasPermission('orders:update')
      && order.customerId === user.customerId
      && order.isEditable
  }

  /**
   * Can the user delete this order?
   * Permission + state check.
   */
  delete(user: User, order: Order): boolean {
    return user.hasPermission('orders:delete')
      && order.isPending
  }

  /**
   * Custom action: can the user cancel this order?
   * Reuses update check + state check.
   */
  cancel(user: User, order: Order): boolean {
    return this.update(user, order)
      && order.isCancellable
  }

  /**
   * Return AuthorizationResponse for custom denial messages.
   */
  publish(user: User, order: Order): boolean | AuthorizationResponse {
    if (order.customerId !== user.customerId) {
      return AuthorizationResponse.deny('You can only publish your own orders')
    }
    if (!order.isReadyToPublish) {
      return AuthorizationResponse.deny('Order is not ready to be published')
    }
    return true
  }
}
```

---

## Standard Policy Methods

Follow these conventions for CRUD actions (maps to controller methods):

| Policy method | Controller action | Needs model? |
|---|---|---|
| `viewAny(user)` | `index` | No |
| `view(user, model)` | `show` | Yes |
| `create(user)` | `store` | No |
| `update(user, model)` | `update` | Yes |
| `delete(user, model)` | `destroy` | Yes |

**Custom methods** for non-standard actions:

| Policy method | Use case |
|---|---|
| `cancel(user, order)` | Cancel an order |
| `approve(user, document)` | Approve a document |
| `publish(user, post)` | Publish a post |
| `restore(user, model)` | Restore soft-deleted |
| `ship(user, order)` | Ship an order |

---

## Using Policies in Controllers

### authorize (throws 403 on failure)

```typescript
import OrderPolicy from '#policies/order_policy'

export default class OrdersController {
  async index({ bouncer }: HttpContext) {
    await bouncer.with(OrderPolicy).authorize('viewAny')
    // ... return orders
  }

  async show({ bouncer, params }: HttpContext) {
    const order = await Order.findOrFail(params.id)
    await bouncer.with(OrderPolicy).authorize('view', order)
    return order
  }

  async store({ bouncer, request }: HttpContext) {
    await bouncer.with(OrderPolicy).authorize('create')
    const data = await request.validateUsing(createOrderValidator)
    return Order.create(data)
  }

  async update({ bouncer, request, params }: HttpContext) {
    const order = await Order.findOrFail(params.id)
    await bouncer.with(OrderPolicy).authorize('update', order)
    order.merge(request.only(['title', 'notes']))
    await order.save()
    return order
  }

  async destroy({ bouncer, params, response }: HttpContext) {
    const order = await Order.findOrFail(params.id)
    await bouncer.with(OrderPolicy).authorize('delete', order)
    await order.delete()
    return response.noContent()
  }

  // Custom action
  async cancel({ bouncer, params }: HttpContext) {
    const order = await Order.findOrFail(params.id)
    await bouncer.with(OrderPolicy).authorize('cancel', order)
    await order.stateMachine('status').transitionTo('cancelled')
    return order
  }
}
```

### allows / denies (check without throwing)

```typescript
async show({ bouncer, params }: HttpContext) {
  const order = await Order.findOrFail(params.id)
  const canEdit = await bouncer.with(OrderPolicy).allows('update', order)
  const canCancel = await bouncer.with(OrderPolicy).allows('cancel', order)

  return {
    order: order.serialize(),
    permissions: { canEdit, canCancel },
  }
}
```

---

## Key Patterns

### 1. Delegate to a permission system

```typescript
view(user: User, order: Order): boolean {
  return user.hasPermission('orders:view')
    && order.customerId === user.customerId
}
```

### 2. Ownership checks

```typescript
update(user: User, order: Order): boolean {
  return order.customerId === user.customerId
}
```

### 3. State checks

```typescript
delete(user: User, order: Order): boolean {
  return user.hasPermission('orders:delete')
    && order.isPending
}
```

### 4. Combine existing methods

```typescript
cancel(user: User, order: Order): boolean {
  return this.update(user, order)
    && order.isCancellable
}
```

### 5. Admin bypass

```typescript
/**
 * before() runs before every policy method.
 * Return true to allow, return undefined to continue to the specific method.
 * Never return false here — that would block everyone.
 */
before(user: User): boolean | undefined {
  if (user.role === 'super_admin') {
    return true  // super admins can do everything
  }
  return undefined  // continue to the specific policy method
}
```

### 6. Custom denial messages

```typescript
publish(user: User, post: Post): boolean | AuthorizationResponse {
  if (user.id !== post.authorId) {
    return AuthorizationResponse.deny('Only the author can publish', 403)
  }
  return true
}
```

### 7. Guest access

```typescript
/**
 * Allow guests (unauthenticated) to view.
 * Use `allowGuest` decorator or accept user as nullable.
 */
view(user: User | null, post: Post): boolean {
  if (post.isPublished) return true
  if (!user) return false
  return user.id === post.authorId
}
```

---

## Permission Enum

```typescript
// app/enums/permission.ts
export enum Permission {
  ListOrders = 'orders:list',
  ViewOrders = 'orders:view',
  CreateOrders = 'orders:create',
  UpdateOrders = 'orders:update',
  DeleteOrders = 'orders:delete',
  CancelOrders = 'orders:cancel',

  ListUsers = 'users:list',
  ManageUsers = 'users:manage',

  AccessAdmin = 'admin:access',
  ViewAnalytics = 'analytics:view',
}
```

Add a helper to your User model:

```typescript
// app/models/user.ts
export default class User extends BaseModel {
  @column()
  declare permissions: string[]  // stored as JSON array in DB

  hasPermission(permission: string): boolean {
    return this.permissions.includes(permission)
  }

  hasAnyPermission(...permissions: string[]): boolean {
    return permissions.some((p) => this.permissions.includes(p))
  }

  hasAllPermissions(...permissions: string[]): boolean {
    return permissions.every((p) => this.permissions.includes(p))
  }
}
```

---

## Abilities vs Policies

For authorization not tied to a specific model, use standalone abilities:

```typescript
// app/abilities/main.ts
import { Bouncer } from '@adonisjs/bouncer'
import User from '#models/user'

export const accessAdmin = Bouncer.ability((user: User) => {
  return user.role === 'admin'
})

export const viewAnalytics = Bouncer.ability((user: User) => {
  return user.hasPermission(Permission.ViewAnalytics)
})
```

Use in controllers:

```typescript
import { accessAdmin } from '#abilities/main'

async dashboard({ bouncer }: HttpContext) {
  await bouncer.authorize(accessAdmin)
  // ...
}
```

---

## Directory Structure

```
app/
├── abilities/
│   └── main.ts              # Standalone abilities (gate-style)
├── enums/
│   └── permission.ts        # Permission enum
├── models/
│   └── user.ts              # hasPermission() helper
└── policies/
    ├── order_policy.ts
    ├── post_policy.ts
    └── user_policy.ts
```

---

## Summary

**Policies should:**
- Use permission enums (not magic strings)
- Check ownership when the resource belongs to a user
- Check model state when the action depends on it (e.g. only pending orders can be deleted)
- Delegate to the permission system for role/permission checks
- Reuse other policy methods for compound checks (`cancel` calls `update`)
- Use `AuthorizationResponse.deny()` for custom error messages
- Use `before()` for admin bypass — return `undefined` to fall through
- Stay simple and focused — one policy per model
