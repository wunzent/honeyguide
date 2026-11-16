# honeyguide

A plugin for Claude Code and Codex, published in the `wunzent-hub` marketplace as `honeyguide` (the repository root).

`honeyguide` plans and carries out software work with the active CLI's native agents, with
risk-based independent review and project-local records under `.honeyguide/`. No Python helper, installer or
cross-vendor delegation. The repository root is the plugin. The repository is public; the plugin is `UNLICENSED`.
Its entry point is the `orchestrate` skill (Claude Code: `/honeyguide:orchestrate`); the other skills are routed
from its table or used on their own (`/honeyguide:<skill>`).

## Layout

    .claude-plugin/       plugin.json, marketplace.json (Claude Code)
    .codex-plugin/        plugin.json
    .agents/plugins/      marketplace.json (Codex)
    skills/               34 skills of honeyguide (see below)
    agents/               Claude agents hub-readonly, hub-writer
    codex-agents/         optional Codex instruction presets (see Permissions)
    docs/                 specs, plans, audits, history/, RECOMMENDED.md (reference list only)
    tests/test_plugin.py  static checks (standard library only)

## Skills in honeyguide (34)

22 workflow skills that work with any language or framework, plus 12 `discover-*` gateways, one per technology domain.
Every task starts at `orchestrate`, which routes to the other skills through its table; the gateway column names the
skill to start a domain from. A gateway is short: it lists which third-party knowledge file answers which topic, and the
agent reads only those files (see Third-party content).

| Domain | Covers | Skills | Gateway |
|---|---|---|---|
| Workflow | Planning, native agents, independent review, checkpoints, long or looping work, context setup | 3: orchestrate, cheap-delegation, stay-on-track | orchestrate |
| Build | New features, small bug fixes, behaviour-preserving restructuring | 3: lean-build, surgical-patch, safe-refactor | orchestrate |
| Debug | Proving a cause (reproduce, trace, falsify, cross-check); browser devtools, pdb, GDB/LLDB, profiling, memory, production debugging | 2: investigate-first, discover-debugging | discover-debugging |
| Review and verify | Acceptance proof without scope growth; outsider review of a plan, PR or change; language and framework reviewer checklists (ECC, vendored) | 1: verify-and-stop | orchestrate |
| Review (step commands) | Fresh-reviewer code review of a diff with the matching language checklists; security review of a change | 2: code-review, security-scan | orchestrate |
| Learning | Project-local instincts with confidence scores written at delivery, evolved into a project skill; show, forget, evolve on request | 1: learn | learn |
| Pipeline | Plan before code and wait for go-ahead; test-first build; plan to a task list. Features: plan, tdd, implement, code-review, security-scan | 3: plan, tdd, tasks | plan |
| Coding discipline | Make it work, make it right, follow practice | 1: ub-mode | ub-mode |
| Frontend | Vue 3, Nuxt 5 prerelease (5.0.0-0; check your project's version), Pinia, Vite, Vitest, React, Next.js, accessibility, frontend performance | 1: discover-frontend | discover-frontend |
| Backend | AdonisJS v6, NestJS, Nitro v3 beta (3.0.260903; check your project's version; Nuxt server), REST, GraphQL, authentication, errors, versioning, rate limiting; endpoint safety and type contracts (any framework) | 3: discover-backend, api-and-interface-design, backend-api-safety | discover-backend |
| Database | PostgreSQL schema, migrations and queries, ORMs, connection pooling, Redis, MongoDB, Elasticsearch, DuckDB | 1: discover-database | discover-database |
| Caching | HTTP caching, CDN and edge, Redis patterns, invalidation, service workers | 1: discover-caching | discover-caching |
| Cloud | AWS, GCP, Cloudflare Workers, Terraform, Kubernetes, cloud cost | 1: discover-cloud | discover-cloud |
| DevOps | CI/CD, Docker and Compose, container security, logging, Prometheus, OpenTelemetry, alerting | 1: discover-devops | discover-devops |
| Collaboration | GitHub pull requests, issues and projects, repository settings, Actions, Dependabot | 1: discover-collaboration | discover-collaboration |
| Testing | Unit, integration and end-to-end tests, TDD, coverage strategy, load testing | 1: discover-testing | discover-testing |
| Security | OWASP, auth, secrets, data storage, supply chain, privacy (PDPA, GDPR); topic knowledge: authentication, authorization, OAuth2, input validation, secrets management, security headers, vulnerability assessment | 2: discover-security, security-and-hardening | discover-security |
| Mobile | React Native (setup, navigation, native modules, performance), SwiftUI architecture and navigation, Swift concurrency, SwiftData, iOS networking and testing | 1: discover-mobile | discover-mobile |
| Distributed systems | CAP, consensus (Raft, Paxos), CRDTs, logical and vector clocks, leader election, partitioning and sharding, replication, event sourcing, distributed locks, eventual consistency, probabilistic data structures; also for system-design interview preparation | 1: discover-distributed | discover-distributed |
| Documentation | SWC: solution overview, frontend, backend and mobile components, acceptance and test cases, traceability | 1: software-component | software-component |
| Reporting | Post-mortem of a fixed bug; reports for leadership shaped for the channel | 2: post-mortem, management-talk | orchestrate |
| Discovery | Researching skills or knowledge that are not here yet (the owner decides on installing) | 1: find-skills | find-skills |
| Design (recommended, not bundled) | Design specs and design decisions | `egm`, installed separately (see Recommended) | `/egm:egm-<skill>` |

### Third-party content

Unchanged upstream copies, all MIT, each with its `LICENSE` and a `SOURCE.md`. The gateway files live in
`skills/discover-*/references/<source>/` at their original relative paths, with a `manifest.sha256` that the tests
check; the ECC reviewer checklists live in `skills/verify-and-stop/references/ecc-reviewers/` the same way. Only documentation was copied: no scripts, code examples (except AdonisJS `.ts`/`.yml` examples, read-only text),
package or lock files. Upstream `SKILL.md` files are stored as `SKILL.upstream.md` so no CLI loads them as skills. The files are reference material; the project's own rules win.

`ub-mode` and `find-skills` are wrapped third-party skills: the `SKILL.md` is ours (honeyguide rules first, then the
overrides for that skill, for example commit and push only with the owner's OK, never install a skill by itself), and
it points at the unchanged upstream file in
`skills/<skill>/references/<source>/` (with `LICENSE`, `SOURCE.md` and `manifest.sha256`, like the gateway sources).

| Source | Commit | Licence | Where |
|---|---|---|---|
| unclebob/ub-mode | 3da62bf3fcfd2034de41f30d920d2739e566171f | MIT | `ub-mode` (wrapped) |
| vercel-labs/skills | b716f9dc2ba36b6aa8f0080615e5a3a6caeac63b | MIT | `find-skills` (wrapped) |
| antfu/skills (vue, nuxt, pinia, vite, vitest, nitro) | d524ed287eef22757297827ce42e3cad88abd20c | MIT | `discover-frontend`, `discover-backend` |
| HoangNguyen0403/agent-skills-standard (nestjs) | 24d9034d21d3b2ab5815236d20ba32a4e85c4c04 | MIT | `discover-backend` |
| omakei/adonisjs-architecture-skill (adonisjs) | 8ee242685af8974ad45179497ae384629144c2b8 | MIT | `discover-backend` |
| rand/cc-polymath (15 categories) | baa2df114416570f5e0e2961143d20e3716a2fc8 | MIT | all twelve `discover-*` gateways |
| affaan-m/ECC (19 reviewer checklists: agents/*-reviewer.md, used as checklists, not as agents) | d2ef2680594f9a17526a6e1a2e18b3d242c5d17b | MIT | `verify-and-stop`, `code-review`, `security-scan` |

`api-and-interface-design` and `security-and-hardening` are adapted from addyosmani/agent-skills
aeac41d4d005999432bb7312f7ff06383a91d59d (MIT), each with its `LICENSE` and an attribution line; they contain our
changes and are not byte copies. stay-on-track's context setup section takes ideas from that repository's
`context-engineering` skill, in our words.
stay-on-track's handoff section is adapted from Matt Pocock's `handoff` (MIT). The ideas behind `learn`, `plan`, `tdd`, `code-review`, `security-scan` and `tasks` come from ECC (affaan-m/ECC, MIT); `tasks` also borrows the task-list idea from github/spec-kit (MIT); those skills are written here in our own words, hook-free.

## Recommended

`egm` (Elephant-Goldfish Model, google/elephant-goldfish-model, Apache-2.0) is recommended for design specs and design
decisions. It is not part of this repository or installed by it. Install it from Google's own marketplace (the marketplace
and plugin are both named `egm`); the owner runs these, they change that CLI's user configuration:

Claude Code (terminal):

    claude plugin marketplace add google/elephant-goldfish-model
    claude plugin install egm@egm

Codex (terminal):

    codex plugin marketplace add google/elephant-goldfish-model
    codex plugin add egm@egm

Its skills are manual: type `/egm:egm-<skill>` (for example `/egm:egm-review <path>`); the orchestrator can only suggest
them.

Other optional tools (all MIT, none bundled; details, install commands and what each runs on its own are in
`docs/RECOMMENDED.md`):

| Tool | Use it for | CLIs | Runs on its own |
|---|---|---|---|
| `spec-kit` (github/spec-kit) | Full Spec-Driven Development in one project: constitution, spec, plan, tasks, implement | Claude Code, Codex (and others) | A Python CLI that writes `.specify/` and `/speckit-*` commands into the project |
| `antislop` (miqdadbadjuber/anti-slop) | Filtering generic AI-looking UI, copy and code | Claude Code, Codex | The Claude plugin starts a `node` MCP server (contrast checker) |
| `cc-polymath` (rand/cc-polymath) | Technology domains not bundled here (ML, Rust, math, networking, cryptography, ...) | Claude Code only | SessionStart/SubagentStart hooks that only print text |
| `ecc` (affaan-m/ECC) | Not recommended together with honeyguide: its own orchestration, memory and hooks overlap ours (honeyguide already bundles its reviewer checklists and re-implements a few of its ideas without hooks) | Claude Code, Codex | Many hooks that run code on tool use, prompts, stop and session events |

## Install

Run the `/plugin ...` lines inside a Claude Code session (or use `claude plugin ...` in a terminal) and the `codex`
lines in a terminal. These change that CLI's user configuration, so only the owner runs them.

Claude Code:

    /plugin marketplace add <path-or-git-url-of-this-repository>
    /plugin install honeyguide@wunzent-hub

Codex:

    codex plugin marketplace add <path-or-git-url-of-this-repository>
    codex plugin add honeyguide@wunzent-hub

Codex plugins cannot ship agents. The files in `codex-agents/` are optional instruction presets (copy
`hub-readonly.toml` and `hub-writer.toml` into `~/.codex/agents` or a trusted project's `.codex/agents`); they add
instructions only and enforce no sandbox.

### Permissions

- Claude Code: the `hub-readonly` and `hub-writer` agents ship with the plugin and their tool lists are enforced.
- Codex: children inherit the session sandbox, so a permission (including read-only) is the brief's rule only, recorded as `instruction`, never as enforced; this may be revisited when Codex offers per-child enforcement. The orchestrator still checks a writer's changed files against its brief's SCOPE. OS-enforced read-only is available through a separate `codex exec -s read-only` run that the owner approves.
- Subagents never publish, post, send, upload or push, and use no MCP or connector tool unless the brief names one a task really needs, read-only and noted in the agent record, and never for publishing, posting, sending, uploading or creating shared documents or artifacts.

## Update

Claude Code:

    /plugin marketplace update wunzent-hub
    claude plugin update honeyguide@wunzent-hub

Codex:

    codex plugin marketplace upgrade wunzent-hub

## Uninstall

Claude Code:

    /plugin uninstall honeyguide@wunzent-hub
    /plugin marketplace remove wunzent-hub

Codex:

    codex plugin remove honeyguide@wunzent-hub
    codex plugin marketplace remove wunzent-hub

## Limits

- Checked statically (`claude plugin validate .`, `tests/test_plugin.py`), not by installing into a live CLI profile.
- The `references/` of `ub-mode`, `find-skills` and the `discover-*` gateways, and `verify-and-stop/references/ecc-reviewers/`, are unchanged third-party copies at a pinned commit and are not updated automatically; their content is unreviewed upstream advice (the AdonisJS files in particular are one author's opinion).
- Recommended plugins (`egm`, others) are not part of this repository; `docs/RECOMMENDED.md` is a reference list only.
