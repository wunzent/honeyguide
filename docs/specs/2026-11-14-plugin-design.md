# Multi-Agent Hub plugin design

## Goal

Owner directive (2026-11-14): use the Hub workflow as a skill invoked from any project in Claude Code or Codex,
installed as a plugin. The repository root is the plugin (layout like obra/superpowers); the repository is public and
the plugin itself is `UNLICENSED`. Claude Code and Codex only. No Python helper, installer or cross-vendor delegation.

## Design

- Manifests: `.claude-plugin/plugin.json` + `marketplace.json`, `.codex-plugin/plugin.json` (`"skills": "./skills/"`),
  `.agents/plugins/marketplace.json`; same name (`multi-agent-hub`) and version.
- `skills/` holds only skills we ship:
  - `multi-agent-hub` (core: native agents, risk-based independent review, project-local records) with
    `references/brief.md`.
  - 11 engineering skills: api-and-interface-design, backend-api-safety, context-engineering, handoff, investigate-first,
    lean-build, safe-refactor, security-and-hardening, software-component, surgical-patch, verify-and-stop.
  - 6 skills written for this plugin: debug-mantra, scrutinize, post-mortem, management-talk, stay-on-track,
    cheap-delegation (the core skill points to them).
  - Third-party, byte copies with licence and source notes: `ub-mode` (unclebob/ub-mode), `find-skills`
    (vercel-labs/skills).
- EGM (google/elephant-goldfish-model, Apache-2.0) is a second plugin, `egm`, in `plugins/egm`: an unchanged copy with
  upstream's own manifests and layout, so its `egm:` namespace and relative links work as upstream wrote them. Licence,
  source and the sha256 manifest are in that folder. Both marketplaces list it (upstream ships a Codex manifest).
- `agents/hub-readonly.md`, `agents/hub-writer.md`: Claude plugin agents. `codex-agents/*.toml`: Codex plugins cannot
  ship agents; the owner copies these to `~/.codex/agents` or a trusted project's `.codex/agents`.
- Other third-party plugins are not vendored or linked; `docs/RECOMMENDED.md` lists Claude-only plugins the owner may
  install from their own official marketplaces.

## Checks

`tests/test_plugin.py` (standard library): manifests agree, frontmatter parses, no duplicate skill names, neutral
wording, delegation/retry/permission rules present, ub-mode and find-skills blobs equal upstream, EGM sha256 manifest.
Plus `claude plugin validate .` and `git diff --check`.
