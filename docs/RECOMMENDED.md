# Recommended plugins the owner may install (reference list)

Nothing here is installed or bundled by this repository. Review a plugin and its licence before installing it. The owner
runs the install commands; they change that CLI's user configuration.

- `egm` (Elephant-Goldfish Model, google/elephant-goldfish-model, Apache-2.0; Claude Code and Codex): draft design specs with context and review them with fresh reviewers. Skills are manual (`/egm:egm-<skill>`); the `orchestrate` skill can only suggest it. Both CLIs: marketplace `egm`, plugin `egm`.
  - Claude Code: `claude plugin marketplace add google/elephant-goldfish-model`, then `claude plugin install egm@egm`.
  - Codex: `codex plugin marketplace add google/elephant-goldfish-model`, then `codex plugin add egm@egm`.
  - Names verified 2026-11-15 from upstream `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` (main @ e4747323aab66157812cd3a71755f6447b2803a2) and its README install section. Reviews need a local executor and isolated subagents; the reviewer adapters are Claude Code agents (Codex behaviour unverified here).

Claude-only plugins from official marketplaces:

- `claude-security` (anthropics/claude-plugins-official): `/plugin marketplace add anthropics/claude-plugins-official`, then `/plugin install claude-security@claude-plugins-official`.
- `document-skills`, `example-skills`, `claude-api` (anthropics/skills): `/plugin marketplace add anthropics/skills`, then `/plugin install <name>@anthropic-agent-skills`.

Marketplace names were read from each upstream `.claude-plugin/marketplace.json`; if a command fails, check `/plugin`.
