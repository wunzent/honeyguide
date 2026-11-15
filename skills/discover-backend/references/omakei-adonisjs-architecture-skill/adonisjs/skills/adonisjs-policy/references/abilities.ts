// app/abilities/main.ts
//
// Standalone Bouncer abilities — equivalent to Laravel Gates.
// Use for authorization checks NOT tied to a specific model instance.

import { Bouncer } from '@adonisjs/bouncer'
import User from '#models/user'
import { Permission } from '#enums/permission'

// ── Role-based abilities ──────────────────────────────────

/** Can the user access the admin panel? */
export const accessAdmin = Bouncer.ability((user: User) => {
  return user.role === 'admin' || user.role === 'super_admin'
})

/** Can the user manage other users? */
export const manageUsers = Bouncer.ability((user: User) => {
  return user.hasPermission(Permission.ManageUsers)
})

/** Can the user view the analytics dashboard? */
export const viewAnalytics = Bouncer.ability((user: User) => {
  return user.hasAnyPermission(Permission.ViewAnalytics, Permission.AccessAdmin)
})

/** Can the user manage application settings? */
export const manageSettings = Bouncer.ability((user: User) => {
  return user.role === 'super_admin'
})

// ─────────────────────────────────────────────────────────────
// Usage in controllers
// ─────────────────────────────────────────────────────────────
//
// import { accessAdmin, viewAnalytics } from '#abilities/main'
//
// // Throws 403 if not authorized
// await bouncer.authorize(accessAdmin)
//
// // Check without throwing
// const canViewAnalytics = await bouncer.allows(viewAnalytics)

// ─────────────────────────────────────────────────────────────
// Usage on routes (via custom middleware)
// ─────────────────────────────────────────────────────────────
//
// router.get('/admin/analytics', [AnalyticsController, 'index'])
//   .use(middleware.auth())
//   .use(middleware.can({ ability: 'viewAnalytics' }))

// ─────────────────────────────────────────────────────────────
// app/enums/permission.ts — Permission enum
// ─────────────────────────────────────────────────────────────

// export enum Permission {
//   // Orders
//   ListOrders = 'orders:list',
//   ViewOrders = 'orders:view',
//   CreateOrders = 'orders:create',
//   UpdateOrders = 'orders:update',
//   DeleteOrders = 'orders:delete',
//   CancelOrders = 'orders:cancel',
//
//   // Users
//   ListUsers = 'users:list',
//   ManageUsers = 'users:manage',
//
//   // Admin
//   AccessAdmin = 'admin:access',
//   ViewAnalytics = 'analytics:view',
//   ManageSettings = 'settings:manage',
// }

// ─────────────────────────────────────────────────────────────
// app/models/user.ts — Permission helpers on the model
// ─────────────────────────────────────────────────────────────

// import { BaseModel, column } from '@adonisjs/lucid/orm'
//
// export default class User extends BaseModel {
//   @column()
//   declare role: string
//
//   @column()
//   declare permissions: string[]   // stored as JSON array
//
//   @column()
//   declare customerId: number
//
//   @column()
//   declare isEmailVerified: boolean
//
//   hasPermission(permission: string): boolean {
//     return this.permissions.includes(permission)
//   }
//
//   hasAnyPermission(...permissions: string[]): boolean {
//     return permissions.some((p) => this.permissions.includes(p))
//   }
//
//   hasAllPermissions(...permissions: string[]): boolean {
//     return permissions.every((p) => this.permissions.includes(p))
//   }
// }
