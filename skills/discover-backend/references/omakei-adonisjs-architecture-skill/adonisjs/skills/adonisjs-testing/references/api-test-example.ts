// tests/functional/posts/store.spec.ts
//
// Full example of a functional API test for creating a post.
// Demonstrates: auth, validation, database assertions, cleanup.

import { test } from '@japa/runner'
import User from '#models/user'
import Post from '#models/post'
import testUtils from '@adonisjs/core/services/test_utils'

test.group('Posts | store', (group) => {
  // Clean database between every test for full isolation
  group.each.setup(() => testUtils.db().truncate())

  // ── Happy Path ──────────────────────────────────────────────

  test('creates a post with valid data', async ({ client, assert }) => {
    // Arrange
    const user = await User.create({
      email: 'author@example.com',
      password: 'secret123',
    })

    // Act
    const response = await client
      .post('/api/posts')
      .loginAs(user)
      .json({
        title: 'My First Post',
        body: 'This is the body of my post.',
      })

    // Assert — response
    response.assertStatus(201)
    response.assertBodyContains({
      data: {
        title: 'My First Post',
        body: 'This is the body of my post.',
      },
    })

    // Assert — database
    const post = await Post.findBy('title', 'My First Post')
    assert.isNotNull(post)
    assert.equal(post!.userId, user.id)
  })

  // ── Validation ──────────────────────────────────────────────

  test('returns 422 when title is missing', async ({ client }) => {
    const user = await User.create({
      email: 'author@example.com',
      password: 'secret123',
    })

    const response = await client
      .post('/api/posts')
      .loginAs(user)
      .json({ body: 'No title here' })

    response.assertStatus(422)
    response.assertBodyContains({
      errors: [{ field: 'title', rule: 'required' }],
    })
  })

  test('returns 422 when title is too short', async ({ client }) => {
    const user = await User.create({
      email: 'author@example.com',
      password: 'secret123',
    })

    const response = await client
      .post('/api/posts')
      .loginAs(user)
      .json({ title: 'Hi', body: 'Valid body content' })

    response.assertStatus(422)
    response.assertBodyContains({
      errors: [{ field: 'title', rule: 'minLength' }],
    })
  })

  // ── Authentication ──────────────────────────────────────────

  test('returns 401 when not authenticated', async ({ client }) => {
    const response = await client
      .post('/api/posts')
      .json({ title: 'Sneaky Post', body: 'No auth' })

    response.assertStatus(401)
  })

  // ── Edge Cases ──────────────────────────────────────────────

  test('trims whitespace from title', async ({ client }) => {
    const user = await User.create({
      email: 'author@example.com',
      password: 'secret123',
    })

    const response = await client
      .post('/api/posts')
      .loginAs(user)
      .json({
        title: '   Spaces Everywhere   ',
        body: 'Body text',
      })

    response.assertStatus(201)
    response.assertBodyContains({
      data: { title: 'Spaces Everywhere' },
    })
  })
})
