// app/abilities/main.ts
//
// Bouncer abilities — standalone authorization checks.
// Equivalent to Laravel Gates. Define once, use anywhere.

import User from '#models/user'
import Post from '#models/post'
import { Bouncer } from '@adonisjs/bouncer'

// ── Simple abilities (no model) ───────────────────────────────

/** Can the user access the admin area? */
export const accessAdmin = Bouncer.ability((user: User) => {
  return user.role === 'admin'
})

/** Can the user manage (CRUD) other users? */
export const manageUsers = Bouncer.ability((user: User) => {
  return user.role === 'admin'
})

/** Can the user view the analytics dashboard? */
export const viewAnalytics = Bouncer.ability((user: User) => {
  return ['admin', 'analyst'].includes(user.role)
})

// ── Model-scoped abilities ────────────────────────────────────

/** Can the user edit this specific post? */
export const editPost = Bouncer.ability((user: User, post: Post) => {
  return user.id === post.userId
})

/** Can the user delete this specific post? */
export const deletePost = Bouncer.ability((user: User, post: Post) => {
  return user.id === post.userId || user.role === 'admin'
})

/** Can the user publish this specific post? */
export const publishPost = Bouncer.ability((user: User, post: Post) => {
  if (user.id !== post.userId) return false
  return post.status === 'draft' && !!post.title && !!post.body
})

// ─────────────────────────────────────────────────────────────
// Usage in controllers
// ─────────────────────────────────────────────────────────────
//
// import { editPost, deletePost } from '#abilities/main'
//
// export default class PostsController {
//   async update({ bouncer, request, params }: HttpContext) {
//     const post = await Post.findOrFail(params.id)
//     await bouncer.authorize(editPost, post)    // throws 403 on failure
//     post.merge(request.only(['title', 'body']))
//     await post.save()
//     return post
//   }
//
//   // Check without throwing
//   async show({ bouncer, params, response }: HttpContext) {
//     const post = await Post.findOrFail(params.id)
//     const canEdit = await bouncer.allows(editPost, post)
//     return { post: post.serialize(), canEdit }
//   }
// }

// ─────────────────────────────────────────────────────────────
// app/policies/post_policy.ts
//
// Bouncer policy — groups all authorization for a model.
// Equivalent to Laravel Policy classes.
// ─────────────────────────────────────────────────────────────

// import User from '#models/user'
// import Post from '#models/post'
// import { BasePolicy } from '@adonisjs/bouncer'
// import { AuthorizationResponse } from '@adonisjs/bouncer'
//
// export default class PostPolicy extends BasePolicy {
//   /**
//    * Anyone can view a post.
//    */
//   view(_user: User, _post: Post) {
//     return true
//   }
//
//   /**
//    * Only verified users can create posts.
//    */
//   create(user: User) {
//     return user.isEmailVerified
//   }
//
//   /**
//    * Only the author can edit their post.
//    */
//   edit(user: User, post: Post) {
//     return user.id === post.userId
//   }
//
//   /**
//    * Author or admin can delete.
//    */
//   delete(user: User, post: Post) {
//     if (user.role === 'admin') return true
//     return user.id === post.userId
//   }
//
//   /**
//    * Return AuthorizationResponse for custom denial messages.
//    */
//   publish(user: User, post: Post) {
//     if (user.id !== post.userId) {
//       return AuthorizationResponse.deny('Only the author can publish', 403)
//     }
//     if (!post.title || !post.body) {
//       return AuthorizationResponse.deny('Post must have a title and body to publish')
//     }
//     return true
//   }
// }

// ─────────────────────────────────────────────────────────────
// Usage with policies in controllers
// ─────────────────────────────────────────────────────────────
//
// import PostPolicy from '#policies/post_policy'
//
// export default class PostsController {
//   async update({ bouncer, request, params }: HttpContext) {
//     const post = await Post.findOrFail(params.id)
//
//     // authorize via policy
//     await bouncer.with(PostPolicy).authorize('edit', post)
//
//     post.merge(request.only(['title', 'body']))
//     await post.save()
//     return post
//   }
//
//   async destroy({ bouncer, params, response }: HttpContext) {
//     const post = await Post.findOrFail(params.id)
//     await bouncer.with(PostPolicy).authorize('delete', post)
//     await post.delete()
//     return response.noContent()
//   }
//
//   async publish({ bouncer, params }: HttpContext) {
//     const post = await Post.findOrFail(params.id)
//     await bouncer.with(PostPolicy).authorize('publish', post)
//     post.status = 'published'
//     await post.save()
//     return post
//   }
// }
