---
name: adonisjs-controllers
description: Thin HTTP layer controllers for AdonisJS v6. Controllers contain zero domain logic, only HTTP concerns. Use when working with controllers, HTTP layer, API vs web patterns, or when user mentions controllers, routes, HttpContext, or HTTP responses in an AdonisJS project.
---

# AdonisJS Controllers

Controllers are **extremely thin**. They handle **HTTP concerns only** and contain **zero domain logic**.

**Related guides:**

- [Actions](../adonisjs-actions/SKILL.md) - Single-purpose domain operations controllers delegate to
- [Validation](../adonisjs-validation/SKILL.md) - VineJS request validation patterns
- [Services](https://docs.adonisjs.com/guides/concepts/container-services) - Services contain domain/business logic
- [Routing](https://docs.adonisjs.com/guides/basics/routing) - Route definitions and resource helpers
- [HTTP Context](https://docs.adonisjs.com/guides/basics/http-context) - Request, response, auth, params
- [Dependency Injection](https://docs.adonisjs.com/guides/concepts/dependency-injection) - IoC container and `@inject`

---

## Philosophy

**Controllers should ONLY:**

1. Destructure and read from `HttpContext` (`request`, `params`, `auth`, `session`)
2. Validate input (via VineJS validators)
3. Call services or actions (injected via constructor or `@inject`)
4. Return responses (JSON, redirects, views)

**Controllers should NEVER:**

- Contain domain logic or business rules
- Query the database directly (e.g. `Post.query()` inside a controller)
- Perform calculations or data transformations
- Handle complex conditional branching beyond HTTP concerns

---

## File Naming & Location

AdonisJS v6 uses **snake_case** for all files and directories.

```
# ✅ CORRECT — snake_case filenames
app/controllers/posts_controller.ts
app/controllers/users_controller.ts
app/controllers/order_items_controller.ts

# ❌ INCORRECT — PascalCase filenames (v5 style)
app/Controllers/Http/PostsController.ts
```

### Scaffold with Ace

```bash
node ace make:controller posts
# → app/controllers/posts_controller.ts

node ace make:controller posts --resource
# → scaffold with all seven RESTful method stubs

node ace make:controller cancel_order --singular
# → app/controllers/cancel_order_controller.ts (invokable)
```

---

## Controller Naming Conventions

Controller **class names** use PascalCase with the `Controller` suffix. The file name uses snake_case.

### Standard Resource Controllers

```ts
// ✅ CORRECT — plural resource name
export default class PostsController {}       // app/controllers/posts_controller.ts
export default class UsersController {}       // app/controllers/users_controller.ts
export default class OrderItemsController {}  // app/controllers/order_items_controller.ts

// ❌ INCORRECT — singular
export default class PostController {}
export default class UserController {}
```

### Nested Resource Controllers

For nested resources, combine parent (singular) + child (plural):

```ts
// Route: /posts/:post_id/comments
export default class PostCommentsController {}  // app/controllers/post_comments_controller.ts

// Route: /orders/:order_id/items
export default class OrderItemsController {}    // app/controllers/order_items_controller.ts
```

**Pattern:** `{ParentSingular}{ChildPlural}Controller`

---

## RESTful Methods Only

Controllers **must only** use AdonisJS's standard RESTful method names.

### Standard RESTful Methods

**For full web applications (with forms/views):**

| Method    | HTTP Verb | Purpose                               |
|-----------|-----------|---------------------------------------|
| `index`   | GET       | List all resources                    |
| `create`  | GET       | Show form to create a new resource    |
| `store`   | POST      | Persist a newly created resource      |
| `show`    | GET       | Display a single resource             |
| `edit`    | GET       | Show form to edit an existing resource|
| `update`  | PUT/PATCH | Persist updates to an existing resource|
| `destroy` | DELETE    | Remove a resource                     |

**For APIs (no HTML forms):**

- Use: `index`, `show`, `store`, `update`, `destroy`
- **APIs must NOT include `create` or `edit`** — those are for rendering HTML forms

### Forbidden Method Names

Never use custom method names on a resource controller:

```ts
// ❌ INCORRECT
export default class OrdersController {
  async all() {}      // Use index
  async get() {}      // Use show
  async add() {}      // Use store
  async remove() {}   // Use destroy
  async cancel() {}   // Extract to CancelOrderController (invokable)
}
```

---

## Non-RESTful Actions: Invokable (Single-Action) Controllers

If an endpoint doesn't fit standard RESTful methods, **extract it to its own invokable controller** with a `handle` method.

```ts
// app/controllers/cancel_order_controller.ts
import type { HttpContext } from '@adonisjs/core/http'
import { inject } from '@adonisjs/core'
import OrderService from '#services/order_service'

@inject()
export default class CancelOrderController {
  constructor(private orderService: OrderService) {}

  async handle({ params, response }: HttpContext) {
    const order = await this.orderService.cancel(params.id)
    return response.json({ data: order })
  }
}
```

```ts
// start/routes.ts
router.resource('orders', () => import('#controllers/orders_controller'))
router.post('/orders/:id/cancel', () => import('#controllers/cancel_order_controller'))
```

**Why invokable controllers?**

- Single Responsibility Principle
- Intent is clear from the controller's name
- Independently testable
- Prevents bloated resource controllers

---

## Importing Controllers in Routes

AdonisJS v6 recommends **lazy-loading** controllers for better boot performance and HMR support.

### Lazy Import (Recommended)

```ts
// start/routes.ts
import router from '@adonisjs/core/services/router'

const PostsController = () => import('#controllers/posts_controller')

router.get('/posts', [PostsController, 'index'])
router.get('/posts/:id', [PostsController, 'show'])
router.post('/posts', [PostsController, 'store'])
```

### Using the Resource Helper

```ts
router.resource('posts', () => import('#controllers/posts_controller'))

// Nested resource
router.resource('posts.comments', () => import('#controllers/post_comments_controller'))
```

### Barrel File (Generated)

If using the `#generated/controllers` barrel file:

```ts
import { controllers } from '#generated/controllers'

router.resource('posts', controllers.Posts)
```

---

## Dependency Injection

Use `@inject()` and constructor injection to receive services. AdonisJS's IoC container handles instantiation.

```ts
// app/controllers/posts_controller.ts
import type { HttpContext } from '@adonisjs/core/http'
import { inject } from '@adonisjs/core'
import PostService from '#services/post_service'

@inject()
export default class PostsController {
  constructor(private postService: PostService) {}

  async index({ response }: HttpContext) {
    const posts = await this.postService.getAll()
    return response.json({ data: posts })
  }
}
```

For method-level injection (when the service itself requires `HttpContext`):

```ts
import { inject } from '@adonisjs/core'
import type { HttpContext } from '@adonisjs/core/http'
import PostService from '#services/post_service'

export default class PostsController {
  @inject()
  async index({ response }: HttpContext, postService: PostService) {
    const posts = await postService.getAll()
    return response.json({ data: posts })
  }
}
```

---

## Full Resource Controller Example

```ts
// app/controllers/orders_controller.ts
import type { HttpContext } from '@adonisjs/core/http'
import { inject } from '@adonisjs/core'
import OrderService from '#services/order_service'
import { createOrderValidator, updateOrderValidator } from '#validators/order_validator'

@inject()
export default class OrdersController {
  constructor(private orderService: OrderService) {}

  async index({ response }: HttpContext) {
    const orders = await this.orderService.paginate()
    return response.json({ data: orders })
  }

  async show({ params, response }: HttpContext) {
    const order = await this.orderService.findOrFail(params.id)
    return response.json({ data: order })
  }

  async store({ request, response }: HttpContext) {
    const payload = await request.validateUsing(createOrderValidator)
    const order = await this.orderService.create(payload)
    return response.created({ data: order })
  }

  async update({ params, request, response }: HttpContext) {
    const payload = await request.validateUsing(updateOrderValidator)
    const order = await this.orderService.update(params.id, payload)
    return response.json({ data: order })
  }

  async destroy({ params, response }: HttpContext) {
    await this.orderService.delete(params.id)
    return response.noContent()
  }
}
```

---

## Validation with VineJS

Validation lives in `app/validators/`, not in controllers. Use `request.validateUsing()` to apply a validator.

```ts
// app/validators/post_validator.ts
import vine from '@vinejs/vine'

export const createPostValidator = vine.compile(
  vine.object({
    title: vine.string().minLength(3).maxLength(255),
    body: vine.string().minLength(10),
  })
)

export const updatePostValidator = vine.compile(
  vine.object({
    title: vine.string().minLength(3).maxLength(255).optional(),
    body: vine.string().minLength(10).optional(),
  })
)
```

```ts
// In controller
async store({ request, response }: HttpContext) {
  const payload = await request.validateUsing(createPostValidator)
  const post = await this.postService.create(payload)
  return response.created({ data: post })
}
```

Validation errors automatically return a `422 Unprocessable Entity` with structured error messages. This is handled by the global exception handler in `app/exceptions/handler.ts`, which catches `E_VALIDATION_ERROR` and formats it as a structured HTTP response — no `try/catch` needed in the controller.

---

## Authorization with Bouncer

Use Bouncer policies for authorization — either inline or via middleware.

```ts
// Inline in controller action
async update({ bouncer, params, request, response }: HttpContext) {
  const post = await Post.findOrFail(params.id)
  await bouncer.authorize('editPost', post)

  const payload = await request.validateUsing(updatePostValidator)
  const updated = await this.postService.update(post, payload)
  return response.json({ data: updated })
}
```

```ts
// Via route middleware
router
  .put('/posts/:id', [PostsController, 'update'])
  .use(middleware.can('editPost'))
```

---

## Response Types

### JSON (200 OK)

```ts
return response.json({ data: post })
// or simply: return { data: post }
```

### Created (201)

```ts
return response.created({ data: post })
```

### No Content (204)

```ts
return response.noContent()
```

### Redirect

```ts
return response.redirect().toRoute('posts.show', { id: post.id })
```

### Not Found / Errors

Throw exceptions — AdonisJS's exception handler converts them to proper HTTP responses:

```ts
import { errors } from '@adonisjs/lucid'

// Using Lucid's findOrFail — throws ModelNotFoundException → 404 automatically
const post = await Post.findOrFail(params.id)
```

---

## Route Model Binding

AdonisJS supports route model binding via the `@adonisjs/route-model-binding` package:

```ts
// start/routes.ts
router.get('/posts/:post', [PostsController, 'show'])
router.put('/posts/:post', [PostsController, 'update'])
```

```ts
// app/controllers/posts_controller.ts
import Post from '#models/post'

export default class PostsController {
  async show({ params }: HttpContext) {
    // Without route model binding — manual fetch
    const post = await Post.findOrFail(params.post)
    return response.json({ data: post })
  }
}
```

---

## Controller Testing

Use Japa API tests (`testUtils.db()` and `client`) to test controllers at the HTTP layer.

```ts
// tests/functional/posts.spec.ts
import { test } from '@japa/runner'

test.group('Posts controller', (group) => {
  group.each.setup(() => testUtils.db().withGlobalTransaction())

  test('returns a list of posts', async ({ client }) => {
    const user = await UserFactory.create()

    const response = await client
      .get('/posts')
      .loginAs(user)

    response.assertStatus(200)
    response.assertBodyContains({ data: [] })
  })

  test('creates a post', async ({ client }) => {
    const user = await UserFactory.create()

    const response = await client
      .post('/posts')
      .loginAs(user)
      .json({ title: 'Hello World', body: 'Post body here.' })

    response.assertStatus(201)
    response.assertBodyContains({ data: { title: 'Hello World' } })
  })

  test('returns 422 when validation fails', async ({ client }) => {
    const user = await UserFactory.create()

    const response = await client
      .post('/posts')
      .loginAs(user)
      .json({})

    response.assertStatus(422)
  })

  test('returns 401 when unauthenticated', async ({ client }) => {
    const response = await client.get('/posts')
    response.assertStatus(401)
  })
})
```

---

## Common Mistakes

### ❌ Domain Logic in Controller

```ts
// BAD
async store({ request, response }: HttpContext) {
  const data = request.only(['title', 'body', 'user_id'])
  const post = await Post.create(data)
  await post.load('tags')
  await NotificationService.notifyFollowers(post)
  return response.created({ data: post })
}
```

### ✅ Delegate to a Service

```ts
// GOOD
async store({ request, response }: HttpContext) {
  const payload = await request.validateUsing(createPostValidator)
  const post = await this.postService.create(payload)
  return response.created({ data: post })
}
```

---

### ❌ Direct Database Queries in Controller

```ts
// BAD
async index({ response }: HttpContext) {
  const posts = await Post.query()
    .where('published', true)
    .orderBy('created_at', 'desc')
    .paginate(1, 20)
  return response.json({ data: posts })
}
```

### ✅ Use a Service or Repository

```ts
// GOOD
async index({ response }: HttpContext) {
  const posts = await this.postService.getPublished()
  return response.json({ data: posts })
}
```

---

### ❌ Fat Constructors / Non-HTTP Concerns

```ts
// BAD
export default class PostsController {
  constructor(
    private postService: PostService,
    private mailer: MailService,
    private cache: CacheService,
    private logger: LogService,
    private search: SearchService
  ) {}
}
```

**If your controller needs more than 1–2 injected services, your controller is doing too much.** Extract logic into a dedicated service or action class.

---

## Summary

**Controllers are HTTP adapters — nothing more.**

1. Receive the HTTP request via `HttpContext`
2. Validate input with `request.validateUsing()`
3. Authorize with `bouncer.authorize()`
4. Call a service or action with clean data
5. Return an HTTP response

**Every line of domain logic belongs in a Service, not a Controller.**
