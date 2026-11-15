# AGENTS.md

This repository is the `wunzent-hub` marketplace for Claude Code and Codex with two plugins: `multi-agent-hub` (the
repository root, laid out like obra/superpowers; UNLICENSED and ours) and `egm` (`plugins/egm`, an unchanged copy of
google/elephant-goldfish-model). It is public. `ub-mode` and `find-skills` in `skills/` are also unchanged third-party
copies. See README.md.

## Layout
- Root plugin: `.claude-plugin/` (plugin.json, marketplace.json), `.codex-plugin/plugin.json`, `skills/` (17 skills),
  `agents/`, `codex-agents/`; Codex marketplace: `.agents/plugins/marketplace.json`
- `plugins/egm/` (7 skills): upstream layout, its own manifests, `LICENSE`, `SOURCE.md`, `manifest.sha256`
- `docs/` specs, plans, audits, history/, RECOMMENDED.md; `tests/test_plugin.py`

## Checks
- `.venv\Scripts\python.exe -m pytest -q` (standard library only; `pytest.ini` limits collection to `tests/`)
- `git diff --check`
- `claude plugin validate .` and `claude plugin validate plugins\egm`

## Update egm or another third-party copy
1. Clone upstream into a scratch folder outside the repo with `git -c core.autocrlf=false`; never run upstream scripts.
2. Replace the files at the same relative paths; update the commit in SOURCE.md.
3. Regenerate `plugins/egm/manifest.sha256` (`sha256sum` of each file except SOURCE.md and the manifest, paths relative to `plugins/egm`) and run the checks.

## Rules
- No secrets, tokens or `.env` content anywhere; the repository is public.
- Commit and push only with the owner's OK; stage explicit files, never `git add -A`.
- Third-party files stay byte-identical to upstream (`.gitattributes` disables line-ending conversion for them).
- Add a third-party file only when its licence clearly allows redistribution.
- Use the `multi-agent-hub` skill for work here. Reply to the owner in Thai (LEARNED.md); code and docs stay in English.
