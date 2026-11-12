# External skills and plugins (not shipped in this repo)

Skills in `skills/` travel with the repo. Everything below was installed per machine on the owner's computer
(2026-11-12) and is only listed here, so it costs no context until someone looks it up. Read this file only when a
brief or task needs a capability that is not in your native skill list.

Rule: if a task needs a skill or plugin from this list and it is not installed where you run, do not copy or install
it yourself. Tell the owner: "This task needs skill/plugin `<name>` (<vendor>, source <source>). Please install it,
or tell me to continue without it." Then continue without it only if the owner says so. Installing third-party
items follows LEARNED.md (clone and read first; the owner decides on scope).

`Vendor` = which CLI had it (Claude: `~/.claude/skills`; Codex: `~/.codex/skills` or `~/.agents/skills`).
`Source` comes from `~/.agents/.skill-lock.json` where recorded. `License` = a LICENSE file was present.
Retired: `swc` and `swc-central` (replaced by `skills/software-component`; remove them from `~/.claude/skills`).

## Skills
| Skill | Vendor | Source | License | What it does |
|---|---|---|---|---|
| adonisjs-backend | Claude, Codex | not recorded | no | Use when adding or changing code in an AdonisJS (v6) backend API: routes, controllers,... |
| agent-reach | Codex | not recorded | no | (no description) |
| api-security-best-practices | Codex | not recorded | no | Implement secure API design patterns including authentication, authorization, input... |
| browser-testing-with-devtools | Claude, Codex | not recorded | yes | Tests in real browsers via Chrome DevTools MCP. Use when building or debugging... |
| caveman | Codex | not recorded | no | (no description) |
| chatgpt-apps | Codex | not recorded | yes | Build, scaffold, refactor, and troubleshoot ChatGPT Apps SDK applications that combine... |
| cli-creator | Codex | not recorded | yes | Build a composable CLI for Codex from API docs, an OpenAPI spec, existing curl... |
| code-refactoring-refactor-clean | Codex | not recorded | no | You are a code refactoring expert specializing in clean code principles, SOLID design... |
| code-reviewer | Codex | not recorded | no | Elite code review expert specializing in modern AI-powered code |
| coding-standards | Codex | not recorded | no | Guide for writing clean, maintainable code following industry best practices and... |
| commit | Codex | not recorded | no | Create commits and commit messages following Sentry conventions, and append successful... |
| create-adaptable-composable | Codex | vuejs-ai/skills | no | Create a library-grade Vue composable that accepts maybe-reactive inputs (MaybeRef /... |
| docker-expert | Codex | not recorded | no | Docker containerization expert with deep knowledge of multi-stage builds, image... |
| document-writer | Codex | onmax/nuxt-skills | no | Use when writing blog posts or documentation markdown files - provides writing style... |
| domain-modeling | Codex | not recorded | no | Build and sharpen a project's domain model. Use when discussing codebase terminology,... |
| figma | Codex | not recorded | yes | Use the Figma MCP server to fetch design context, screenshots, variables, and assets... |
| figma-code-connect-components | Codex | not recorded | yes | Connects Figma design components to code components using Code Connect mapping tools.... |
| figma-create-design-system-rules | Codex | not recorded | yes | Generates custom design system rules for the user's codebase. Use when user says... |
| figma-implement-design | Codex | not recorded | yes | Translates Figma designs into production-ready application code with 1:1 visual... |
| graphify | Claude, Codex | not recorded | no | Use for any question about a codebase, its architecture, file relationships, or... |
| grill-with-docs | Codex | not recorded | no | A relentless interview to sharpen a plan or design, which also creates docs (ADR's and... |
| grilling | Codex | not recorded | no | Grill the user relentlessly about a plan, decision, or idea. Use when the user wants... |
| i18n-localization | Codex | not recorded | no | Internationalization and localization patterns. Detecting hardcoded strings, managing... |
| improve | Codex | not recorded | yes | Survey any codebase as a senior advisor and produce prioritized, self-contained... |
| migration | Claude, Codex | not recorded | no | Implement reversible compatibility-safe transitions. Use for schema, data, API,... |
| motion | Codex | onmax/nuxt-skills | no | Use when adding animations with Motion Vue (motion-v) - provides motion component API,... |
| mui | Codex | not recorded | no | Material-UI v7 component library patterns including sx prop styling, theme... |
| nuxt | Codex | onmax/nuxt-skills | no | Use when working on Nuxt 4+ projects - provides server routes, file-based routing,... |
| nuxt-better-auth | Codex | onmax/nuxt-skills | no | Use when implementing auth in Nuxt apps with @onmax/nuxt-better-auth - provides... |
| nuxt-content | Codex | onmax/nuxt-skills | no | Use when working with Nuxt Content v3, markdown content, or CMS features in Nuxt -... |
| nuxt-modules | Codex | onmax/nuxt-skills | no | Use when creating Nuxt modules: (1) Published npm modules (@nuxtjs/, nuxt-), (2) Local... |
| nuxt-seo | Codex | onmax/nuxt-skills | no | Nuxt SEO meta-module with robots, sitemap, og-image, schema-org. Use when configuring... |
| nuxt-studio | Codex | onmax/nuxt-skills | no | Use when working with Nuxt Studio, the self-hosted open-source CMS for Nuxt Content... |
| nuxt-ui | Codex | onmax/nuxt-skills | no | Use when building styled UI with @nuxt/ui v4 components - create forms with... |
| nuxthub | Codex | onmax/nuxt-skills | no | Use when building NuxtHub v0.10.6 applications - provides database (Drizzle ORM with... |
| playwright | Codex | not recorded | yes | Use when the task requires automating a real browser from the terminal (navigation,... |
| pnpm | Codex | onmax/nuxt-skills | no | Use when managing Node.js dependencies with pnpm - install packages, configure... |
| ponytail | Codex | not recorded | no | (no description) |
| ponytail-help | Codex | not recorded | no | (no description) |
| refactor | Codex | not recorded | no | Code refactoring best practices based on Martin Fowler's catalog and Clean Code... |
| reka-ui | Codex | onmax/nuxt-skills | no | Use when building with Reka UI (headless Vue components) - provides component API,... |
| screenshot | Codex | not recorded | yes | Use when the user explicitly asks for a desktop or system screenshot (full screen,... |
| security-best-practices | Codex | not recorded | yes | Perform language and framework specific security best-practice reviews and suggest... |
| security-threat-model | Codex | not recorded | yes | Repository-grounded threat modeling that enumerates trust boundaries, assets, attacker... |
| shadcn | Codex | not recorded | no | shadcn/ui component library best practices and patterns (formerly shadcn-ui). This... |
| svg-animations | Codex | not recorded | no | Create beautiful, performant SVG animations and illustrations. Use this skill when the... |
| technical-docs-writing | Codex | not recorded | no | Write, rewrite, audit, or review technical documentation using a... |
| ui-ux-designer | Codex | not recorded | no | Create interface designs, wireframes, and design systems. Masters |
| ui-ux-pro-max | Codex | not recorded | no | UI/UX design intelligence. 50 styles, 21 palettes, 50 font pairings, 20 charts, 9... |
| ui-visual-validator | Codex | not recorded | no | Rigorous visual validation expert specializing in UI testing, |
| vite | Codex | onmax/nuxt-skills | no | Vite build tool configuration, plugin API, SSR, and Vite 8 Rolldown migration. Use... |
| vitest | Codex | onmax/nuxt-skills | no | Use when writing unit/integration tests for Vite projects - configure... |
| vue | Codex | onmax/nuxt-skills | no | Use when editing .vue files, creating Vue 3 components, writing composables, or... |
| vue-best-practices | Codex | vuejs-ai/skills | no | MUST be used for Vue.js tasks. Strongly recommends Composition API with `<script... |
| vue-debug-guides | Codex | vuejs-ai/skills | no | Vue 3 debugging and error handling for runtime errors, warnings, async failures, and... |
| vue-jsx-best-practices | Codex | vuejs-ai/skills | no | JSX syntax in Vue (e.g., class vs className, JSX plugin config). |
| vue-options-api-best-practices | Codex | vuejs-ai/skills | no | Vue 3 Options API style (data(), methods, this context). Each reference shows Options... |
| vue-pinia-best-practices | Codex | vuejs-ai/skills | no | Pinia stores, state management patterns, store setup, and reactivity with stores. |
| vue-router-best-practices | Codex | vuejs-ai/skills | no | Vue Router 4 patterns, navigation guards, route params, and route-component lifecycle... |
| vue-testing-best-practices | Codex | vuejs-ai/skills | no | Use for Vue.js testing. Covers Vitest, Vue Test Utils, component testing, mocking,... |
| vueuse | Codex | onmax/nuxt-skills | no | Use when working with VueUse composables - track mouse position with useMouse, manage... |
| web-design-guidelines | Codex | not recorded | no | Review UI code for Web Interface Guidelines compliance. Use when asked to "review my... |
| web-ui-vuetify | Codex | not recorded | no | Material Design component library for Vue 3 |
| writing-web-documentation | Codex | onmax/nuxt-skills | no | Write, rewrite, review, and organize developer-facing documentation for web software... |
| zod | Codex | not recorded | no | Zod schema validation best practices for type safety, parsing, and error handling.... |

## Claude plugins
Install: `claude plugin marketplace add <marketplace>` then `claude plugin install <plugin>@<marketplace> --scope user`.
"claude.ai" = synced from the owner's claude.ai account (enable there, not from the CLI).
| Plugin | Version | Marketplace / source |
|---|---|---|
| cc-safety-net | 2.7.12 | cc-marketplace (GitHub kenryu42/cc-marketplace) |
| egm | 0.1.1 | egm (GitHub google/elephant-goldfish-model) |
| improve | 1.0.0 | improve (GitHub shadcn/improve) |
| understand-anything | 2.9.8 | understand-anything (GitHub Egonex-AI/Understand-Anything) |
| website-design | 1.0.0 | claude.ai |
| claude-security | 0.11.0 | claude.ai |
| vectorlab-ux-skills | 1.0.0 | claude.ai |
| agent-estimate | 0.8.0 | claude.ai |
| design-skills | 1.0.0 | claude.ai |
| mattpocock-skills | 1.2.3 | claude.ai |
| agent-engineering | 0.3.2 | claude.ai |
| caveman | 1.1.2 | claude.ai |
| engineering | 1.2.0 | claude.ai |
| design | 1.2.0 | claude.ai |
| base44 | 1.0.0-beta.1 | claude.ai |

## Codex plugins
Install: `codex plugin marketplace add <source>` then `codex plugin add <plugin>@<marketplace>`.
"bundled" = ships with the Codex app (openai-primary-runtime / openai-bundled); nothing to install.
| Plugin | Version | Marketplace / source |
|---|---|---|
| documents, pdf, spreadsheets, presentations, template-creator | 26.1111 | bundled (openai-primary-runtime) |
| codex-app-tools, browser, unified-computer-use, chrome, computer-use, visualize | 26.1106 / 1.0.91 | bundled (openai-bundled) |
| cc-safety-net | 2.7.12 | cc-marketplace (GitHub kenryu42/cc-safety-net) |
| egm | 0.1.1 | egm (GitHub google/elephant-goldfish-model) |
