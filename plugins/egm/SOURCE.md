# Source: Elephant-Goldfish Model (EGM)

- Repository: https://github.com/google/elephant-goldfish-model
- Commit: `964a4f1ecd333961375c35cb37ed09364dab5e4e`
- Licence: Apache-2.0 (`LICENSE` in this folder, copied from the upstream repository root; upstream has no NOTICE file)
- Change: none. Every file except this `SOURCE.md` and `manifest.sha256` is a byte copy (fetched with `core.autocrlf=false`; no upstream script was run). The plugin name is upstream's own: `egm`.
- Layout (same relative positions as upstream, so links and `${CLAUDE_PLUGIN_ROOT}` paths resolve inside this folder):
  - `.claude-plugin/plugin.json` (upstream's Claude manifest, lists the adapters), `.claude-plugin/icon.png`, `.claude-plugin/agents/*.md` (10 Claude adapters, `egm-*`)
  - `.codex-plugin/plugin.json` (upstream's Codex manifest; `"skills": "./skills/"`), `assets/icon.svg` (referenced by it)
  - `skills/egm-*` (7 skills: bootstrap, brainstorm, draft, drift-report, resolve, review, review-loop)
  - `agents/*.md` (10 canonical personas), `resources/`, `docs/{claude,codex,harnesses}.md`, `TESTING.md`
- Left out: upstream's marketplace files (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, others); our own marketplaces list this plugin. Also left out: the rest of upstream (site/, tests/, other docs, manifests for other tools).
- Integrity: `manifest.sha256` (paths relative to this folder, manifests included) lists the sha256 of every copied file; `tests/test_plugin.py` verifies it.
- Skills spawn isolated reviewer subagents and need a local executor; no hooks, MCP servers or install steps.
- Codex: upstream ships a Codex manifest, so the plugin is also listed in `.agents/plugins/marketplace.json`. The Claude adapters (`.claude-plugin/agents`) are Claude-only; behaviour on Codex was not verified here.
