// start/routes.ts
//
// Main route entry point. Import sub-files to keep things organized.
// AdonisJS preloads this file on boot.

import router from '@adonisjs/core/services/router'

// ── Import route files ────────────────────────────────────────
import './routes/web.js'
import './routes/api.js'
import './routes/admin.js'

// ── Health check (always public) ──────────────────────────────
router.get('/health', async () => ({ status: 'ok' }))

// ─────────────────────────────────────────────────────────────
// start/routes/web.ts
// ─────────────────────────────────────────────────────────────

// import router from '@adonisjs/core/services/router'
// import { middleware } from '#start/kernel'
//
// const HomeController = () => import('#controllers/home_controller')
// const AuthController = () => import('#controllers/auth_controller')
//
// // Public
// router.get('/', [HomeController, 'index']).as('home')
// router.get('/login', [AuthController, 'showLogin']).as('auth.login.show')
// router.post('/login', [AuthController, 'login']).as('auth.login')
// router.get('/register', [AuthController, 'showRegister']).as('auth.register.show')
// router.post('/register', [AuthController, 'register']).as('auth.register')
//
// // Authenticated web routes
// router
//   .group(() => {
//     router.post('/logout', [AuthController, 'logout']).as('auth.logout')
//     router.get('/dashboard', [DashboardController, 'index']).as('dashboard')
//   })
//   .use(middleware.auth())

// ─────────────────────────────────────────────────────────────
// start/routes/api.ts
// ─────────────────────────────────────────────────────────────

// import router from '@adonisjs/core/services/router'
// import { middleware } from '#start/kernel'
//
// const PostsController = () => import('#controllers/api/posts_controller')
// const CommentsController = () => import('#controllers/api/comments_controller')
// const ProfileController = () => import('#controllers/api/profile_controller')
//
// router
//   .group(() => {
//     // Public read endpoints
//     router.get('/posts', [PostsController, 'index']).as('posts.index')
//     router.get('/posts/:id', [PostsController, 'show']).as('posts.show')
//
//     // Authenticated endpoints
//     router
//       .group(() => {
//         router.post('/posts', [PostsController, 'store']).as('posts.store')
//         router.put('/posts/:id', [PostsController, 'update']).as('posts.update')
//         router.delete('/posts/:id', [PostsController, 'destroy']).as('posts.destroy')
//
//         router.resource('posts.comments', CommentsController).apiOnly()
//
//         router.get('/me', [ProfileController, 'show']).as('profile.show')
//         router.put('/me', [ProfileController, 'update']).as('profile.update')
//       })
//       .use(middleware.auth())
//   })
//   .prefix('/api/v1')
//   .as('api.v1')

// ─────────────────────────────────────────────────────────────
// start/routes/admin.ts
// ─────────────────────────────────────────────────────────────

// import router from '@adonisjs/core/services/router'
// import { middleware } from '#start/kernel'
//
// const DashboardController = () => import('#controllers/admin/dashboard_controller')
// const AdminUsersController = () => import('#controllers/admin/users_controller')
// const AdminPostsController = () => import('#controllers/admin/posts_controller')
// const AdminSettingsController = () => import('#controllers/admin/settings_controller')
//
// router
//   .group(() => {
//     router.get('/dashboard', [DashboardController, 'index']).as('dashboard')
//
//     router.resource('users', AdminUsersController)
//     router.resource('posts', AdminPostsController)
//
//     router.get('/settings', [AdminSettingsController, 'index']).as('settings.index')
//     router.put('/settings', [AdminSettingsController, 'update']).as('settings.update')
//   })
//   .prefix('/admin')
//   .as('admin')
//   .use(middleware.auth())
//   .use(middleware.admin())   // role-based guard
