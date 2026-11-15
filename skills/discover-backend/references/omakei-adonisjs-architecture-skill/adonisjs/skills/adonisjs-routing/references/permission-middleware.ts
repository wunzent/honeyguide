// app/middleware/admin_middleware.ts
//
// Simple role-based guard — checks that the authenticated user
// has role === 'admin'. Use on route groups for admin areas.

import type { HttpContext } from '@adonisjs/core/http'
import type { NextFn } from '@adonisjs/core/types/http'

export default class AdminMiddleware {
  async handle({ auth, response }: HttpContext, next: NextFn) {
    const user = auth.getUserOrFail()

    if (user.role !== 'admin') {
      return response.forbidden({ error: 'Admin access required' })
    }

    await next()
  }
}

// ─────────────────────────────────────────────────────────────
// app/middleware/role_middleware.ts
//
// Parameterized role middleware — accepts the required role
// as an option. More flexible than a hardcoded AdminMiddleware.
// ─────────────────────────────────────────────────────────────

// import type { HttpContext } from '@adonisjs/core/http'
// import type { NextFn } from '@adonisjs/core/types/http'
//
// export default class RoleMiddleware {
//   async handle(
//     { auth, response }: HttpContext,
//     next: NextFn,
//     options: { role: string }
//   ) {
//     const user = auth.getUserOrFail()
//
//     if (user.role !== options.role) {
//       return response.forbidden({
//         error: `This action requires the "${options.role}" role`,
//       })
//     }
//
//     await next()
//   }
// }
//
// // Register in start/kernel.ts:
// //   role: () => import('#middleware/role_middleware'),
// //
// // Usage on routes:
// //   router.get('/admin', [Ctrl, 'index']).use(middleware.role({ role: 'admin' }))
// //   router.get('/editor', [Ctrl, 'index']).use(middleware.role({ role: 'editor' }))

// ─────────────────────────────────────────────────────────────
// app/middleware/can_middleware.ts
//
// Route-level Bouncer authorization middleware.
// Checks a named ability before the request reaches the controller.
// ─────────────────────────────────────────────────────────────

// import type { HttpContext } from '@adonisjs/core/http'
// import type { NextFn } from '@adonisjs/core/types/http'
// import * as abilities from '#abilities/main'
//
// type AbilityName = keyof typeof abilities
//
// export default class CanMiddleware {
//   async handle(ctx: HttpContext, next: NextFn, options: { ability: AbilityName }) {
//     const ability = abilities[options.ability]
//
//     if (!ability) {
//       throw new Error(`Unknown ability: "${options.ability}"`)
//     }
//
//     // bouncer.authorize throws E_AUTHORIZATION_FAILURE (403) on denial
//     await ctx.bouncer.authorize(ability)
//
//     await next()
//   }
// }
//
// // Register in start/kernel.ts:
// //   can: () => import('#middleware/can_middleware'),
// //
// // Usage on routes:
// //   router.get('/admin/users', [Ctrl, 'index'])
// //     .use(middleware.auth())
// //     .use(middleware.can({ ability: 'manageUsers' }))

// ─────────────────────────────────────────────────────────────
// start/kernel.ts — named middleware registry
// ─────────────────────────────────────────────────────────────

// import router from '@adonisjs/core/services/router'
//
// // Server-level middleware (runs on every request)
// router.use([
//   () => import('#middleware/container_bindings_middleware'),
//   () => import('@adonisjs/core/bodyparser_middleware'),
//   () => import('@adonisjs/session/session_middleware'),
// ])
//
// // Named middleware (explicitly assigned to routes)
// export const middleware = router.named({
//   auth: () => import('#middleware/auth_middleware'),
//   guest: () => import('#middleware/guest_middleware'),
//   admin: () => import('#middleware/admin_middleware'),
//   role: () => import('#middleware/role_middleware'),
//   can: () => import('#middleware/can_middleware'),
// })
