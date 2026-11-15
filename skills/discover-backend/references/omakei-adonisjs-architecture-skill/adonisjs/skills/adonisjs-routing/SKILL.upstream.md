---
name: adonisjs-routing
description: Routing, middleware, and permission patterns for AdonisJS. Use when working with routes, route groups, resource routes, named routes, middleware, route-level authorization, permission guards, role-based access, or when user mentions routing, middleware, named middleware, route protection, auth guards, RBAC, abilities, bouncer, route organization, API versioning, or any route/middleware configuration in an AdonisJS project.
---

# AdonisJS Routing & Permissions

Patterns for organizing routes, applying middleware, and protecting routes with role/permission-based authorization using AdonisJS Bouncer.

**Related guides:**

- [Policies](../adonisjs-policy/SKILL.md) - Bouncer policies for per-model authorization
- [Controllers](../adonisjs-controllers/SKILL.md) - Controllers that use route-level authorization

**Reference implementations:**
- [Route organization patterns →](references/route-organization.ts)
- [Permission middleware →](references/permission-middleware.ts)
- [Bouncer abilities & policies →](references/bouncer-policies.ts)
- [Testing protected routes →](references/testing-protected-routes.ts)

---

## Route Basics

### Defining routes

```typescript
// start/routes.ts
import router from '@adonisjs/core/services/router'

// Lazy-import controllers (tree-shaken, loaded on demand)
const PostsController = () => import('#controllers/posts_controller')
const UsersController = () => import('#controllers/users_controller')

router.get('/', async () => 'Hello World')
router.get('/posts', [PostsController, 'index'])
router.post('/posts', [PostsController, 'store'])
router.get('/posts/:id', [PostsController, 'show'])
router.put('/posts/:id', [PostsController, 'update'])
router.delete('/posts/:id', [PostsController, 'destroy'])
```

### Named routes

```typescript
router.get('/posts', [PostsController, 'index']).as('posts.index')
router.get('/posts/:id', [PostsController, 'show']).as('posts.show')

// Use in controllers / views:
// route('posts.show', { id: 1 }) → '/posts/1'
```

### Resource routes (RESTful CRUD)

```typescript
router.resource('posts', PostsController)
// Generates:
//   GET    /posts          → index     → posts.index
//   GET    /posts/create   → create    → posts.create
//   POST   /posts          → store     → posts.store
//   GET    /posts/:id      → show      → posts.show
//   GET    /posts/:id/edit → edit      → posts.edit
//   PUT    /posts/:id      → update    → posts.update
//   DELETE /posts/:id      → destroy   → posts.destroy

// API-only (no create/edit form routes)
router.resource('posts', PostsController).apiOnly()

// Nested resources
router.resource('posts.comments', CommentsController)
// → /posts/:post_id/comments, /posts/:post_id/comments/:id, etc.
```

---

## Route Groups

### Prefix + named groups

```typescript
router
  .group(() => {
    router.resource('posts', PostsController)
    router.resource('users', UsersController)
  })
  .prefix('/api/v1')
  .as('api.v1')
// Routes: api.v1.posts.index, api.v1.users.store, etc.
```

### Middleware on groups

```typescript
import { middleware } from '#start/kernel'

// All routes in the group require authentication
router
  .group(() => {
    router.resource('posts', PostsController)
    router.get('/dashboard', [DashboardController, 'index'])
  })
  .use(middleware.auth())

// Nested groups with layered middleware
router
  .group(() => {
    // Public
    router.get('/posts', [PostsController, 'index'])
    router.get('/posts/:id', [PostsController, 'show'])

    // Authenticated
    router
      .group(() => {
        router.post('/posts', [PostsController, 'store'])
        router.put('/posts/:id', [PostsController, 'update'])
        router.delete('/posts/:id', [PostsController, 'destroy'])
      })
      .use(middleware.auth())
  })
  .prefix('/api')
```

### Resource routes with selective middleware

```typescript
router
  .resource('posts', PostsController)
  .use(['store', 'update', 'destroy'], middleware.auth())

// Or all actions
router
  .resource('posts', PostsController)
  .use('*', middleware.auth())
```

---

## Middleware

### Three middleware stacks

| Stack | Scope | Example |
|---|---|---|
| **Server** | Every HTTP request (even no-route matches) | Static files, CORS |
| **Router** | Every request that matches a route | Body parser, session |
| **Named** | Explicitly assigned to routes/groups | Auth, role check |

### Creating named middleware

```bash
node ace make:middleware admin
```

```typescript
// app/middleware/admin_middleware.ts
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
```

### Registering named middleware

```typescript
// start/kernel.ts
import router from '@adonisjs/core/services/router'

router.use([
  () => import('#middleware/container_bindings_middleware'),
  () => import('@adonisjs/core/bodyparser_middleware'),
  () => import('@adonisjs/session/session_middleware'),
])

export const middleware = router.named({
  auth: () => import('#middleware/auth_middleware'),
  guest: () => import('#middleware/guest_middleware'),
  admin: () => import('#middleware/admin_middleware'),
  can: () => import('#middleware/can_middleware'),
})
```

### Middleware with parameters

```typescript
// app/middleware/role_middleware.ts
export default class RoleMiddleware {
  async handle({ auth, response }: HttpContext, next: NextFn, options: { role: string }) {
    const user = auth.getUserOrFail()

    if (user.role !== options.role) {
      return response.forbidden({ error: `Requires "${options.role}" role` })
    }

    await next()
  }
}

// Usage on routes
router.get('/admin', [AdminController, 'index']).use(middleware.role({ role: 'admin' }))
```

---

## Permission Patterns

### Pattern 1: Role-based middleware

Simplest approach — check the user's `role` column directly:

```typescript
// Middleware
router
  .group(() => {
    router.resource('users', AdminUsersController)
    router.get('/settings', [AdminSettingsController, 'index'])
  })
  .prefix('/admin')
  .use(middleware.auth())
  .use(middleware.admin())   // checks user.role === 'admin'
```

### Pattern 2: Bouncer abilities (gate-style)

AdonisJS `@adonisjs/bouncer` provides Laravel Gate-equivalent authorization:

```typescript
// app/abilities/main.ts
import User from '#models/user'
import Post from '#models/post'
import { Bouncer } from '@adonisjs/bouncer'

export const editPost = Bouncer.ability((user: User, post: Post) => {
  return user.id === post.userId
})

export const deletePost = Bouncer.ability((user: User, post: Post) => {
  return user.id === post.userId || user.role === 'admin'
})

export const manageUsers = Bouncer.ability((user: User) => {
  return user.role === 'admin'
})
```

Use in controllers:

```typescript
// app/controllers/posts_controller.ts
import { editPost, deletePost } from '#abilities/main'

export default class PostsController {
  async update({ bouncer, request, params }: HttpContext) {
    const post = await Post.findOrFail(params.id)

    // Throws 403 if not authorized
    await bouncer.authorize(editPost, post)

    post.merge(request.only(['title', 'body']))
    await post.save()
    return post
  }

  async destroy({ bouncer, params }: HttpContext) {
    const post = await Post.findOrFail(params.id)
    await bouncer.authorize(deletePost, post)
    await post.delete()
  }
}
```

### Pattern 3: Bouncer policies (per-model authorization)

Group all authorization for a model into a policy class:

```typescript
// app/policies/post_policy.ts
import User from '#models/user'
import Post from '#models/post'
import { BasePolicy } from '@adonisjs/bouncer'
import { AuthorizationResponse } from '@adonisjs/bouncer'

export default class PostPolicy extends BasePolicy {
  view(_user: User, _post: Post) {
    return true // anyone can view
  }

  create(user: User) {
    return user.isVerified
  }

  edit(user: User, post: Post) {
    return user.id === post.userId
  }

  delete(user: User, post: Post) {
    if (user.role === 'admin') return true
    return user.id === post.userId
  }

  // Return AuthorizationResponse for custom messages
  publish(user: User, post: Post) {
    if (user.id !== post.userId) {
      return AuthorizationResponse.deny('Only the author can publish')
    }
    if (!post.title || !post.body) {
      return AuthorizationResponse.deny('Post must have a title and body')
    }
    return true
  }
}
```

Use in controllers:

```typescript
import PostPolicy from '#policies/post_policy'

export default class PostsController {
  async update({ bouncer, request, params }: HttpContext) {
    const post = await Post.findOrFail(params.id)
    await bouncer.with(PostPolicy).authorize('edit', post)

    post.merge(request.only(['title', 'body']))
    await post.save()
    return post
  }
}
```

### Pattern 4: Route-level permission middleware

Create a reusable `can` middleware that checks Bouncer abilities on the route:

```typescript
// app/middleware/can_middleware.ts
import type { HttpContext } from '@adonisjs/core/http'
import type { NextFn } from '@adonisjs/core/types/http'
import * as abilities from '#abilities/main'

type AbilityName = keyof typeof abilities

export default class CanMiddleware {
  async handle(ctx: HttpContext, next: NextFn, options: { ability: AbilityName }) {
    const ability = abilities[options.ability]

    if (!ability) {
      throw new Error(`Unknown ability: "${options.ability}"`)
    }

    await ctx.bouncer.authorize(ability)
    await next()
  }
}

// Usage on routes:
router.get('/admin/users', [AdminUsersController, 'index'])
  .use(middleware.auth())
  .use(middleware.can({ ability: 'manageUsers' }))
```

---

## Route Organization

### File splitting for large apps

```typescript
// start/routes.ts
import router from '@adonisjs/core/services/router'
import './routes/api.js'
import './routes/web.js'
import './routes/admin.js'
```

```typescript
// start/routes/api.ts
import router from '@adonisjs/core/services/router'
import { middleware } from '#start/kernel'

const PostsController = () => import('#controllers/api/posts_controller')
const UsersController = () => import('#controllers/api/users_controller')

router
  .group(() => {
    router.resource('posts', PostsController).apiOnly()
    router.resource('users', UsersController).apiOnly()
  })
  .prefix('/api/v1')
  .as('api.v1')
  .use(middleware.auth())
```

```typescript
// start/routes/admin.ts
import router from '@adonisjs/core/services/router'
import { middleware } from '#start/kernel'

const DashboardController = () => import('#controllers/admin/dashboard_controller')
const AdminUsersController = () => import('#controllers/admin/users_controller')

router
  .group(() => {
    router.get('/dashboard', [DashboardController, 'index']).as('dashboard')
    router.resource('users', AdminUsersController)
  })
  .prefix('/admin')
  .as('admin')
  .use(middleware.auth())
  .use(middleware.admin())
```

### API versioning

```typescript
router.group(() => {
  router.resource('posts', PostsControllerV1).apiOnly()
}).prefix('/api/v1').as('api.v1')

router.group(() => {
  router.resource('posts', PostsControllerV2).apiOnly()
}).prefix('/api/v2').as('api.v2')
```

---

## Useful Route Commands

```bash
node ace list:routes          # List all registered routes
node ace make:controller Post # Create a controller
node ace make:middleware Admin # Create middleware
```

---

## Directory Structure

```
app/
├── abilities/
│   └── main.ts                # Bouncer abilities (gate-style)
├── controllers/
│   ├── api/
│   │   └── posts_controller.ts
│   └── admin/
│       ├── dashboard_controller.ts
│       └── users_controller.ts
├── middleware/
│   ├── auth_middleware.ts
│   ├── admin_middleware.ts
│   ├── can_middleware.ts
│   └── role_middleware.ts
└── policies/
    └── post_policy.ts
start/
├── kernel.ts                  # Named middleware registry
├── routes.ts                  # Entry point (imports sub-files)
└── routes/
    ├── api.ts
    ├── web.ts
    └── admin.ts
```

---

## Summary

| Concept | AdonisJS equivalent |
|---|---|
| Route definition | `router.get()`, `router.post()`, `router.resource()` |
| Named routes | `.as('posts.index')`, `route('posts.show', { id })` |
| Route groups | `router.group(() => {}).prefix().use()` |
| Middleware (global) | Router-level in `start/kernel.ts` |
| Middleware (named) | `router.named({})` in `start/kernel.ts` |
| Middleware on resources | `.use(['store', 'destroy'], middleware.auth())` |
| Gate / ability | `Bouncer.ability()` → `bouncer.authorize(ability)` |
| Policy (model-level) | `BasePolicy` class → `bouncer.with(Policy).authorize()` |
| Route-level permission | Custom `can` middleware referencing Bouncer abilities |
| Role check | Simple middleware checking `user.role` |
