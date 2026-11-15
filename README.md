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
    skills/               17 skills of honeyguide (see below)
    agents/               Claude agents hub-readonly, hub-writer
    codex-agents/         Codex agent shells (copy by hand, see below)
    docs/                 specs, plans, audits, history/, RECOMMENDED.md (reference list only)
    tests/test_plugin.py  static checks (standard library only)

## Skills in honeyguide (17)

| Skill | What it is |
|---|---|
| orchestrate | Core workflow: native agents, risk-based independent review, records, and the routing table from work type to skill |
| cheap-delegation | Give mechanical, low-risk work to the cheapest native model |
| investigate-first | Prove the cause before any fix: reproduce, trace, falsify, cross-check |
| verify-and-stop | Prove acceptance without scope growth; outsider review of a plan, PR or change |
| post-mortem | Engineering record of a fixed bug |
| management-talk | Rewrite engineering content for leadership and the channel |
| stay-on-track | Loop detection, three-attempt rule, handoff document (adapted from Matt Pocock's `handoff`, MIT) |
| api-and-interface-design, backend-api-safety, context-engineering, lean-build, safe-refactor, security-and-hardening, software-component, surgical-patch | Engineering skills |
| ub-mode | Coding discipline (unclebob/ub-mode, MIT, unchanged) |
| find-skills | Skill discovery helper (vercel-labs/skills, MIT, unchanged) |

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
them. See `docs/RECOMMENDED.md`.

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
- `ub-mode` and `find-skills` are unchanged third-party copies at a pinned commit and are not updated automatically.
- Recommended plugins (`egm`, others) are not part of this repository; `docs/RECOMMENDED.md` is a reference list only.
