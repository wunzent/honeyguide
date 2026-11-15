# wunzent-hub: multi-agent-hub and egm

Two plugins for Claude Code and Codex in one marketplace (`wunzent-hub`): `multi-agent-hub` (the repository root) and `egm` (`plugins/egm`).

`multi-agent-hub`: It plans and carries out software work with the active CLI's native agents, with
risk-based independent review and project-local records under `.multi-agent-hub/`. No Python helper, installer or
cross-vendor delegation. The repository root is the plugin. The repository is public; the plugin is `UNLICENSED`.
Its entry point is the `orchestrate` skill (Claude Code: `/multi-agent-hub:orchestrate`); the other skills are routed
from its table or used on their own (`/multi-agent-hub:<skill>`).

## Layout

    .claude-plugin/       plugin.json, marketplace.json (Claude Code)
    .codex-plugin/        plugin.json
    .agents/plugins/      marketplace.json (Codex)
    skills/               17 skills of multi-agent-hub (see below)
    agents/               Claude agents hub-readonly, hub-writer
    codex-agents/         Codex agent shells (copy by hand, see below)
    plugins/egm/          the `egm` plugin: unchanged upstream copy with LICENSE, SOURCE.md, manifest.sha256
    docs/                 specs, plans, audits, history/, RECOMMENDED.md (reference list only)
    tests/test_plugin.py  static checks (standard library only)

## Skills in multi-agent-hub (17)

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

## The egm plugin (7 skills)

`egm` is google/elephant-goldfish-model at commit `964a4f1` (Apache-2.0), copied unchanged into `plugins/egm` with
upstream's own manifests, so its names are upstream's: skills `/egm:egm-bootstrap`, `egm-brainstorm`, `egm-draft`,
`egm-drift-report`, `egm-resolve`, `egm-review`, `egm-review-loop`, and Claude reviewer agents `egm:egm-<name>`. See
`plugins/egm/SOURCE.md`. Reviews need a local executor and isolated subagents. Upstream ships a Codex manifest, so Codex
can install it; the 10 reviewer adapters are Claude Code agents (Codex behaviour unverified in a live session).

## Install

Run the `/plugin ...` lines inside a Claude Code session (or use `claude plugin ...` in a terminal) and the `codex`
lines in a terminal. These change that CLI's user configuration, so only the owner runs them.

Claude Code:

    /plugin marketplace add <path-or-git-url-of-this-repository>
    /plugin install multi-agent-hub@wunzent-hub
    /plugin install egm@wunzent-hub

Codex:

    codex plugin marketplace add <path-or-git-url-of-this-repository>
    codex plugin add multi-agent-hub@wunzent-hub
    codex plugin add egm@wunzent-hub

Codex plugins cannot ship agents. To get an enforced read-only sandbox for review duties, copy
`codex-agents/hub-readonly.toml` and `codex-agents/hub-writer.toml` into `~/.codex/agents` (all projects) or a trusted
project's `.codex/agents`. Without them the permission of Codex children stays `Unverified`.

## Update

Claude Code:

    /plugin marketplace update wunzent-hub
    claude plugin update multi-agent-hub@wunzent-hub
    claude plugin update egm@wunzent-hub

Codex:

    codex plugin marketplace upgrade wunzent-hub

## Uninstall

Claude Code:

    /plugin uninstall multi-agent-hub@wunzent-hub
    /plugin uninstall egm@wunzent-hub
    /plugin marketplace remove wunzent-hub

Codex:

    codex plugin remove multi-agent-hub@wunzent-hub
    codex plugin remove egm@wunzent-hub
    codex plugin marketplace remove wunzent-hub

## Limits

- Checked statically (`claude plugin validate .`, `tests/test_plugin.py`), not by installing into a live CLI profile.
- Third-party files are byte copies at a pinned commit and are not updated automatically.
- Other third-party plugins are not part of this repository; `docs/RECOMMENDED.md` is a reference list only.
