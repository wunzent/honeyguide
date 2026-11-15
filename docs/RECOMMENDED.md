# Recommended plugins the owner may install (reference list)

Nothing here is installed or bundled by this repository. Review a plugin and its licence before installing it. The owner
runs the install commands; they change that CLI's user configuration.

- `egm` (Elephant-Goldfish Model, google/elephant-goldfish-model, Apache-2.0; Claude Code and Codex): draft design specs with context and review them with fresh reviewers. Skills are manual (`/egm:egm-<skill>`); the `orchestrate` skill can only suggest it. Both CLIs: marketplace `egm`, plugin `egm`.
  - Claude Code: `claude plugin marketplace add google/elephant-goldfish-model`, then `claude plugin install egm@egm`.
  - Codex: `codex plugin marketplace add google/elephant-goldfish-model`, then `codex plugin add egm@egm`.
  - Names verified 2026-11-15 from upstream `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` (main @ e4747323aab66157812cd3a71755f6447b2803a2) and its README install section. Reviews need a local executor and isolated subagents; the reviewer adapters are Claude Code agents (Codex behaviour unverified here).

Other optional tools (checked 2026-11-16 from each upstream README and manifest; all MIT):

- `spec-kit` (github/spec-kit; Claude Code, Codex and many other agents): Spec-Driven Development (constitution, specify,
  plan, tasks, implement, converge), plus bug-fix and idea-assessment extensions. Overlaps `orchestrate` and `egm`; use it
  when a project wants the full SDD process. It is a Python CLI (Python 3.11+, uv) that writes `.specify/` and the
  `/speckit-*` commands into the project, so install it per project, not as a plugin.
  - `uv tool install specify-cli`, then in the project `specify init --here --integration claude` (or `codex`).
- `antislop` (miqdadbadjuber/anti-slop; Claude Code and Codex): six skills that filter generic AI-looking UI, copy,
  mobile layout and code comments. The Claude plugin also starts a local `node` MCP server (contrast checker) through
  `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/contrast-mcp-launcher.mjs`. Marketplace `anti-slop`, plugin `antislop`.
  - Claude Code: `/plugin marketplace add miqdadbadjuber/anti-slop`, then `/plugin install antislop@anti-slop`.
  - Codex: `codex plugin marketplace add miqdadbadjuber/anti-slop`, then `codex plugin add antislop@anti-slop`.
- `cc-polymath` (rand/cc-polymath; Claude Code only, no Codex manifest): 23 `discover-*` gateways over about 800
  knowledge files. Twelve of its categories are already bundled here under `skills/discover-*`; install it only for the
  others (mobile, security, distributed systems, protocols, ML, Rust, math and more), and expect overlapping gateway
  names (`discover-frontend` and so on). Ships SessionStart/SubagentStart hooks that only print text, a `/skills`
  command and four agents. Its `marketplace.json` names the marketplace `cc-polymath-marketplace` while its README shows
  `cc-polymath@cc-polymath`; if one fails, try the other.
  - Claude Code: `/plugin marketplace add rand/cc-polymath`, then `/plugin install cc-polymath@cc-polymath-marketplace`.
- `ecc` (affaan-m/ECC; Claude Code and Codex): a full agent harness (about 314 skills, 71 agents, memory, continuous
  learning, rules, and hooks that run code on tool use, prompts, compaction, stop and session events; hooks on by
  default with minimal/standard/strict profiles). Not recommended alongside honeyguide: its orchestration, memory and
  hooks overlap and can conflict with the `orchestrate` rules. Use it on its own, or read individual skills (for example
  `nuxt4-patterns`, `vue-patterns`, `nestjs-patterns`, `postgres-patterns`) as reference.
  - Claude Code: `/plugin marketplace add https://github.com/affaan-m/ECC`, then `/plugin install ecc@ecc`.
  - Codex: `codex plugin marketplace add affaan-m/ECC`, then `codex plugin add ecc@ecc` (its Codex hooks need an
    explicit trust decision).

Claude-only plugins from official marketplaces:


- `claude-security` (anthropics/claude-plugins-official): `/plugin marketplace add anthropics/claude-plugins-official`, then `/plugin install claude-security@claude-plugins-official`.
- `document-skills`, `example-skills`, `claude-api` (anthropics/skills): `/plugin marketplace add anthropics/skills`, then `/plugin install <name>@anthropic-agent-skills`.

Marketplace names were read from each upstream `.claude-plugin/marketplace.json`; if a command fails, check `/plugin`.
