# Multi-Agent Hub plugin design

## Goal

Owner directive (2026-11-14): use the Hub workflow as a skill invoked from any project in Claude Code or Codex, installed
as a plugin, instead of opening this Hub. One Agent Skill is the shared core; one marketplace in this repository packages
it for both CLIs. ChatGPT and other tools are out of scope.

## Design

1. `plugins/multi-agent-hub/` is self-contained (plugin installers copy only the plugin folder):
   - `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` (`"skills": "./skills/"`), same name and version.
   - `skills/multi-agent-hub/SKILL.md` + `references/brief.md`: the core, open-standard frontmatter only (`name`,
     `description`). Native agents only; two vendor lines (Claude `Agent` with `multi-agent-hub:hub-readonly|hub-writer`,
     Codex `spawn_agent` with `fork_turns=none`). No Python, helper, installer or cross-vendor delegation.
   - `skills/software-component/`: byte copy of `skills/software-component/` (source stays in `skills/`).
   - `agents/hub-readonly.md`, `agents/hub-writer.md`: Claude plugin agents.
   - `codex-agents/hub-readonly.toml`, `hub-writer.toml`: Codex plugins cannot ship agents; the owner places these in
     `~/.codex/agents` or a trusted project's `.codex/agents` to get an enforced read-only sandbox.
   - `README.md`: install, update, uninstall, limits.
2. Marketplaces at the repository root: `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`, both
   named `wunzent-hub`, listing `./plugins/multi-agent-hub`.
3. The Hub itself (`AGENTS.md`, `tools/hub.py`, `skills/`, `.claude/`, `.codex/`) is unchanged. Narrow exceptions: backend-api-safety frontmatter quoting (valid YAML) and neutral workflow wording in api-and-interface-design, security-and-hardening and lean-build (so the bundled copies work in any project); the hub's AGENTS.md still governs hub work. `feat/skill-first-hub`
   (portable helper + custom installer) is not merged; its security gate failed with 6 Important findings, all in code
   this design does not ship.

## Why

- Native plugin installers replace `install_hub_skill.py`, so no own code writes outside the project.
- Removing the helper removes the security-review findings (executable lookup, forged record fields, unconfined brief
  read, hardlink overwrite, junction ancestry, TOCTOU) instead of hardening them.

## Limits

- Records under `.multi-agent-hub/` are written by the model following the skill, not by a tool: no `attempt`
  NO PROGRESS check, no verified model for workers.
- Codex child read-only enforcement needs the owner-placed shells; otherwise the permission stays `Unverified`.
- Marketplace installation changes each CLI's user configuration; only the owner runs it.

## Bundled skills and 9arm

- The plugin bundles byte copies of the Hub skills api-and-interface-design, backend-api-safety, context-engineering,
  handoff, investigate-first, lean-build, safe-refactor, security-and-hardening, software-component, surgical-patch and
  verify-and-stop. `brief` stays out (hub-specific); `references/brief.md` replaces it. A test checks every copy equals
  its source.
- `9arm-skills` (thananon/9arm-skills) is listed in the Claude marketplace as a github source pinned to a commit; upstream
  ships its own `.claude-plugin/plugin.json`. Nothing of it is copied into this repository (no upstream licence). Codex has
  no entry (no `.codex-plugin` upstream); the plugin README gives manual steps.
- The plugin skill uses a retry cap (no third identical failing action; ask the owner after about 3 attempts) in
  place of the `NO PROGRESS` rule, which needs `hub.py attempt`.

## Verification

Focused tests (`tests/test_plugin.py`): manifests parse and agree; skill frontmatter is open-standard only; no helper,
installer or `models.toml` references; referenced files exist; `software-component` copy equals source; Codex shells
parse as TOML with the expected sandbox. Existing suite still passes. Live: Codex high-risk run with the branch's skill
in a disposable project (records before spawn, docs updated, tests pass). Not verified without the owner: marketplace
install on either CLI, Claude Code live run.
