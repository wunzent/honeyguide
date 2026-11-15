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
    skills/               26 skills of honeyguide (see below)
    agents/               Claude agents hub-readonly, hub-writer
    codex-agents/         Codex agent shells (copy by hand, see below)
    docs/                 specs, plans, audits, history/, RECOMMENDED.md (reference list only)
    tests/test_plugin.py  static checks (standard library only)

## Skills in honeyguide (26)

17 workflow skills that work with any language or framework, plus 9 `discover-*` gateways, one per technology domain.
Every task starts at `orchestrate`, which routes to the other skills through its table; the gateway column names the
skill to start a domain from. A gateway is short: it lists which third-party knowledge file answers which topic, and the
agent reads only those files (see Third-party content).

| Domain | Covers | Skills | Gateway |
|---|---|---|---|
| Workflow | Planning, native agents, independent review, checkpoints, long or looping work, context setup | 4: orchestrate, cheap-delegation, stay-on-track, context-engineering | orchestrate |
| Build | New features, small bug fixes, behaviour-preserving restructuring | 3: lean-build, surgical-patch, safe-refactor | orchestrate |
| Debug | Proving a cause (reproduce, trace, falsify, cross-check); browser devtools, pdb, GDB/LLDB, profiling, memory, production debugging | 2: investigate-first, discover-debugging | discover-debugging |
| Review and verify | Acceptance proof without scope growth; outsider review of a plan, PR or change | 1: verify-and-stop | orchestrate |
| Coding discipline | Make it work, make it right, follow practice | 1: ub-mode | ub-mode |
| Frontend | Vue 3, Nuxt 5 prerelease (5.0.0-0; check your project's version), Pinia, Vite, Vitest, React, Next.js, accessibility, frontend performance | 1: discover-frontend | discover-frontend |
| Backend | AdonisJS v6, NestJS, Nitro v3 beta (3.0.260903; check your project's version; Nuxt server), REST, GraphQL, authentication, errors, versioning, rate limiting; endpoint safety and type contracts (any framework) | 3: discover-backend, api-and-interface-design, backend-api-safety | discover-backend |
| Database | PostgreSQL schema, migrations and queries, ORMs, connection pooling, Redis, MongoDB, Elasticsearch, DuckDB | 1: discover-database | discover-database |
| Caching | HTTP caching, CDN and edge, Redis patterns, invalidation, service workers | 1: discover-caching | discover-caching |
| Cloud | AWS, GCP, Cloudflare Workers, Terraform, Kubernetes, cloud cost | 1: discover-cloud | discover-cloud |
| DevOps | CI/CD, Docker and Compose, container security, logging, Prometheus, OpenTelemetry, alerting | 1: discover-devops | discover-devops |
| Collaboration | GitHub pull requests, issues and projects, repository settings, Actions, Dependabot | 1: discover-collaboration | discover-collaboration |
| Testing | Unit, integration and end-to-end tests, TDD, coverage strategy, load testing | 1: discover-testing | discover-testing |
| Security | OWASP, auth, secrets, data storage, supply chain, privacy (PDPA, GDPR) | 1: security-and-hardening | orchestrate |
| Documentation | SWC: solution overview, frontend, backend and mobile components, acceptance and test cases, traceability | 1: software-component | software-component |
| Reporting | Post-mortem of a fixed bug; reports for leadership shaped for the channel | 2: post-mortem, management-talk | orchestrate |
| Discovery | Finding and installing a skill that is not here | 1: find-skills | find-skills |
| Design (recommended, not bundled) | Design specs and design decisions | `egm`, installed separately (see Recommended) | `/egm:egm-<skill>` |

### Third-party content

Unchanged upstream copies, all MIT, each with its `LICENSE` and a `SOURCE.md`. The gateway files live in
`skills/discover-*/references/<source>/` at their original relative paths, with a `manifest.sha256` that the tests
check. Only documentation was copied: no scripts, code examples (except AdonisJS `.ts`/`.yml` examples, read-only text),
package or lock files. Upstream `SKILL.md` files are stored as `SKILL.upstream.md` so no CLI loads them as skills. The files are reference material; the project's own rules win.

| Source | Commit | Licence | Where |
|---|---|---|---|
| unclebob/ub-mode | 3da62bf3fcfd2034de41f30d920d2739e566171f | MIT | `ub-mode` |
| vercel-labs/skills | b716f9dc2ba36b6aa8f0080615e5a3a6caeac63b | MIT | `find-skills` |
| antfu/skills (vue, nuxt, pinia, vite, vitest, nitro) | d524ed287eef22757297827ce42e3cad88abd20c | MIT | `discover-frontend`, `discover-backend` |
| HoangNguyen0403/agent-skills-standard (nestjs) | 24d9034d21d3b2ab5815236d20ba32a4e85c4c04 | MIT | `discover-backend` |
| omakei/adonisjs-architecture-skill (adonisjs) | 8ee242685af8974ad45179497ae384629144c2b8 | MIT | `discover-backend` |
| rand/cc-polymath (12 categories) | baa2df114416570f5e0e2961143d20e3716a2fc8 | MIT | all nine `discover-*` gateways |

stay-on-track's handoff section is adapted from Matt Pocock's `handoff` (MIT).

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
| `cc-polymath` (rand/cc-polymath) | Technology domains not bundled here (mobile, security, distributed systems, ML, Rust, ...) | Claude Code only | SessionStart/SubagentStart hooks that only print text |
| `ecc` (affaan-m/ECC) | Not recommended together with honeyguide: its own orchestration, memory and hooks overlap ours | Claude Code, Codex | Many hooks that run code on tool use, prompts, stop and session events |

## Install

Run the `/plugin ...` lines inside a Claude Code session (or use `claude plugin ...` in a terminal) and the `codex`
lines in a terminal. These change that CLI's user configuration, so only the owner runs them.

Claude Code:

    /plugin marketplace add <path-or-git-url-of-this-repository>
    /plugin install honeyguide@wunzent-hub

Codex:

    codex plugin marketplace add <path-or-git-url-of-this-repository>
    codex plugin add honeyguide@wunzent-hub

Codex plugins cannot ship agents. To get an enforced read-only sandbox for review duties, copy
`codex-agents/hub-readonly.toml` and `codex-agents/hub-writer.toml` into `~/.codex/agents` (all projects) or a trusted
project's `.codex/agents`. Without them the permission of Codex children stays `Unverified`.

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
- `ub-mode`, `find-skills` and the `references/` of the `discover-*` gateways are unchanged third-party copies at a pinned commit and are not updated automatically; their content is unreviewed upstream advice (the AdonisJS files in particular are one author's opinion).
- Recommended plugins (`egm`, others) are not part of this repository; `docs/RECOMMENDED.md` is a reference list only.
