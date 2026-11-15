// tests/functional/admin/users.spec.ts
//
// Tests for route protection: authentication, roles, and Bouncer policies.

import { test } from '@japa/runner'
import User from '#models/user'
import Post from '#models/post'
import testUtils from '@adonisjs/core/services/test_utils'

// ─────────────────────────────────────────────────────────────
// Authentication tests
// ─────────────────────────────────────────────────────────────

test.group('Protected routes | authentication', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('returns 401 when not authenticated', async ({ client }) => {
    const response = await client.get('/api/v1/me')
    response.assertStatus(401)
  })

  test('returns 200 when authenticated', async ({ client }) => {
    const user = await User.create({
      email: 'john@test.com',
      password: 'secret',
      role: 'user',
    })

    const response = await client
      .get('/api/v1/me')
      .loginAs(user)

    response.assertStatus(200)
    response.assertBodyContains({ email: 'john@test.com' })
  })
})

// ─────────────────────────────────────────────────────────────
// Role-based middleware tests
// ─────────────────────────────────────────────────────────────

test.group('Protected routes | admin middleware', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('allows admin to access admin routes', async ({ client }) => {
    const admin = await User.create({
      email: 'admin@test.com',
      password: 'secret',
      role: 'admin',
    })

    const response = await client
      .get('/admin/dashboard')
      .loginAs(admin)

    response.assertStatus(200)
  })

  test('returns 403 for non-admin users', async ({ client }) => {
    const user = await User.create({
      email: 'user@test.com',
      password: 'secret',
      role: 'user',
    })

    const response = await client
      .get('/admin/dashboard')
      .loginAs(user)

    response.assertStatus(403)
  })

  test('returns 401 for unauthenticated access to admin', async ({ client }) => {
    const response = await client.get('/admin/dashboard')
    response.assertStatus(401)
  })
})

// ─────────────────────────────────────────────────────────────
// Bouncer ability / policy tests
// ─────────────────────────────────────────────────────────────

test.group('Protected routes | post authorization', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('author can update their own post', async ({ client }) => {
    const author = await User.create({
      email: 'author@test.com',
      password: 'secret',
      role: 'user',
    })

    const post = await Post.create({
      title: 'Original Title',
      body: 'Original body',
      userId: author.id,
    })

    const response = await client
      .put(`/api/v1/posts/${post.id}`)
      .loginAs(author)
      .json({ title: 'Updated Title' })

    response.assertStatus(200)
    response.assertBodyContains({ title: 'Updated Title' })
  })

  test('non-author cannot update another user post', async ({ client }) => {
    const author = await User.create({
      email: 'author@test.com',
      password: 'secret',
      role: 'user',
    })
    const stranger = await User.create({
      email: 'stranger@test.com',
      password: 'secret',
      role: 'user',
    })

    const post = await Post.create({
      title: 'Author Post',
      body: 'Body',
      userId: author.id,
    })

    const response = await client
      .put(`/api/v1/posts/${post.id}`)
      .loginAs(stranger)
      .json({ title: 'Hijacked!' })

    response.assertStatus(403)
  })

  test('admin can delete any post', async ({ client }) => {
    const admin = await User.create({
      email: 'admin@test.com',
      password: 'secret',
      role: 'admin',
    })
    const author = await User.create({
      email: 'author@test.com',
      password: 'secret',
      role: 'user',
    })

    const post = await Post.create({
      title: 'Some Post',
      body: 'Body',
      userId: author.id,
    })

    const response = await client
      .delete(`/api/v1/posts/${post.id}`)
      .loginAs(admin)

    response.assertStatus(204)
  })

  test('non-admin non-author cannot delete post', async ({ client }) => {
    const author = await User.create({
      email: 'author@test.com',
      password: 'secret',
      role: 'user',
    })
    const stranger = await User.create({
      email: 'stranger@test.com',
      password: 'secret',
      role: 'user',
    })

    const post = await Post.create({
      title: 'Author Post',
      body: 'Body',
      userId: author.id,
    })

    const response = await client
      .delete(`/api/v1/posts/${post.id}`)
      .loginAs(stranger)

    response.assertStatus(403)
  })
})

// ─────────────────────────────────────────────────────────────
// Resource route middleware tests
// ─────────────────────────────────────────────────────────────

test.group('Protected routes | resource middleware', (group) => {
  group.each.setup(() => testUtils.db().truncate())

  test('public index route is accessible without auth', async ({ client }) => {
    const response = await client.get('/api/v1/posts')
    response.assertStatus(200)
  })

  test('store route requires authentication', async ({ client }) => {
    const response = await client
      .post('/api/v1/posts')
      .json({ title: 'New', body: 'Post' })

    response.assertStatus(401)
  })
})
