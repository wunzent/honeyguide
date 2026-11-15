// app/policies/order_policy.ts
//
// Full Bouncer policy for the Order model.
// Demonstrates: permission delegation, ownership, state checks,
// method composition, admin bypass, and custom denial messages.

import User from '#models/user'
import Order from '#models/order'
import { BasePolicy } from '@adonisjs/bouncer'
import { AuthorizationResponse } from '@adonisjs/bouncer'
import { Permission } from '#enums/permission'

export default class OrderPolicy extends BasePolicy {
  // ── Admin bypass ────────────────────────────────────────
  // Runs before every policy method.
  // Return true → allow unconditionally.
  // Return undefined → fall through to the specific method.
  // NEVER return false here — that blocks everyone.

  before(user: User): boolean | undefined {
    if (user.role === 'super_admin') {
      return true
    }
    return undefined
  }

  // ── Standard CRUD ───────────────────────────────────────

  /** Can the user list orders? (index) */
  viewAny(user: User): boolean {
    return user.hasPermission(Permission.ListOrders)
  }

  /** Can the user view this specific order? (show) */
  view(user: User, order: Order): boolean {
    return user.hasPermission(Permission.ViewOrders)
      && this.isOwner(user, order)
  }

  /** Can the user create orders? (store) */
  create(user: User): boolean {
    return user.hasPermission(Permission.CreateOrders)
  }

  /** Can the user update this order? (update) */
  update(user: User, order: Order): boolean {
    return user.hasPermission(Permission.UpdateOrders)
      && this.isOwner(user, order)
      && order.isEditable
  }

  /** Can the user delete this order? (destroy) */
  delete(user: User, order: Order): boolean {
    return user.hasPermission(Permission.DeleteOrders)
      && order.isPending
  }

  // ── Custom actions ──────────────────────────────────────

  /** Can the user cancel this order? Reuses update + state check. */
  cancel(user: User, order: Order): boolean {
    return this.update(user, order) && order.isCancellable
  }

  /** Can the user ship this order? Admin or warehouse role only. */
  ship(user: User, order: Order): boolean {
    return ['admin', 'warehouse'].includes(user.role)
      && order.isPaid
  }

  /**
   * Can the user publish/finalize this order?
   * Returns AuthorizationResponse for custom denial messages.
   */
  publish(user: User, order: Order): boolean | AuthorizationResponse {
    if (!this.isOwner(user, order)) {
      return AuthorizationResponse.deny('You can only publish your own orders')
    }
    if (!order.isReadyToPublish) {
      return AuthorizationResponse.deny('Order must have items and a shipping address')
    }
    return true
  }

  // ── Private helpers ─────────────────────────────────────

  private isOwner(user: User, order: Order): boolean {
    return order.customerId === user.customerId
  }
}

// ─────────────────────────────────────────────────────────────
// app/policies/post_policy.ts — second example (simpler)
// ─────────────────────────────────────────────────────────────

// import User from '#models/user'
// import Post from '#models/post'
// import { BasePolicy } from '@adonisjs/bouncer'
// import { AuthorizationResponse } from '@adonisjs/bouncer'
//
// export default class PostPolicy extends BasePolicy {
//   viewAny(_user: User): boolean {
//     return true // anyone logged in can list posts
//   }
//
//   view(_user: User, post: Post): boolean {
//     return post.isPublished // only published posts are visible
//   }
//
//   create(user: User): boolean {
//     return user.isEmailVerified
//   }
//
//   update(user: User, post: Post): boolean {
//     return user.id === post.authorId
//   }
//
//   delete(user: User, post: Post): boolean {
//     return user.id === post.authorId || user.role === 'admin'
//   }
//
//   publish(user: User, post: Post): boolean | AuthorizationResponse {
//     if (user.id !== post.authorId) {
//       return AuthorizationResponse.deny('Only the author can publish')
//     }
//     if (!post.title || !post.body) {
//       return AuthorizationResponse.deny('Post needs a title and body')
//     }
//     return true
//   }
// }

// ─────────────────────────────────────────────────────────────
// Usage in controllers
// ─────────────────────────────────────────────────────────────

// import OrderPolicy from '#policies/order_policy'
//
// export default class OrdersController {
//   async index({ bouncer }: HttpContext) {
//     await bouncer.with(OrderPolicy).authorize('viewAny')
//     return Order.query().apply((s) => s.withRelated()).paginate(1, 20)
//   }
//
//   async show({ bouncer, params }: HttpContext) {
//     const order = await Order.findOrFail(params.id)
//     await bouncer.with(OrderPolicy).authorize('view', order)
//     return order
//   }
//
//   async store({ bouncer, request }: HttpContext) {
//     await bouncer.with(OrderPolicy).authorize('create')
//     const data = await request.validateUsing(createOrderValidator)
//     return Order.create(data)
//   }
//
//   async update({ bouncer, request, params }: HttpContext) {
//     const order = await Order.findOrFail(params.id)
//     await bouncer.with(OrderPolicy).authorize('update', order)
//     order.merge(request.only(['title', 'notes']))
//     await order.save()
//     return order
//   }
//
//   async destroy({ bouncer, params, response }: HttpContext) {
//     const order = await Order.findOrFail(params.id)
//     await bouncer.with(OrderPolicy).authorize('delete', order)
//     await order.delete()
//     return response.noContent()
//   }
//
//   // Include permissions in response for frontend UI
//   async showWithPermissions({ bouncer, params }: HttpContext) {
//     const order = await Order.findOrFail(params.id)
//     await bouncer.with(OrderPolicy).authorize('view', order)
//
//     return {
//       order: order.serialize(),
//       can: {
//         update: await bouncer.with(OrderPolicy).allows('update', order),
//         delete: await bouncer.with(OrderPolicy).allows('delete', order),
//         cancel: await bouncer.with(OrderPolicy).allows('cancel', order),
//       },
//     }
//   }
// }
