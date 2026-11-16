# AGENTS.md

This repository is the `wunzent-hub` marketplace for Claude Code and Codex with one plugin, `honeyguide` (the
repository root, laid out like obra/superpowers; UNLICENSED and ours). It is public. `ub-mode` and `find-skills` are
our wrapper skills around unchanged third-party copies in their `references/<source>/`, and the `discover-*` gateway skills carry unchanged third-party knowledge files
under their `references/` (so does `verify-and-stop`: ECC reviewer checklists) (see README.md, Third-party content). `egm` is only recommended (docs/RECOMMENDED.md), not shipped. See README.md.

## Layout
- Root plugin: `.claude-plugin/` (plugin.json, marketplace.json), `.codex-plugin/plugin.json`, `skills/` (35 skills),
  `agents/`, `codex-agents/`, `codex-rules/`, `hooks/`; Codex marketplace: `.agents/plugins/marketplace.json`
- `docs/` specs, plans, audits, history/, RECOMMENDED.md; `tests/test_plugin.py`

## Checks
- `.venv\Scripts\python.exe -m pytest -q` (standard library only; `pytest.ini` limits collection to `tests/`)
- `git diff --check`
- `claude plugin validate .`

## Update a third-party copy (`skills/<skill>/references/<source>/` of `ub-mode`, `find-skills` and the `discover-*` gateways, `skills/verify-and-stop/references/ecc-reviewers/`)
1. Clone upstream into a scratch folder outside the repo with `git -c core.autocrlf=false`; never run upstream scripts.
2. Replace the files at the same relative paths (an upstream `SKILL.md` is stored as `SKILL.upstream.md`); update the commit in the source's `SOURCE.md`, regenerate its `manifest.sha256` and update the hashes in `tests/test_plugin.py`, then run the checks.

## Rules
- No secrets, tokens or `.env` content anywhere; the repository is public.
- Commit and push only with the owner's OK; stage explicit files, never `git add -A`.
- Third-party files stay byte-identical to upstream (`.gitattributes` disables line-ending conversion for them); no third-party scripts or package files are copied.
- Add a third-party file only when its licence clearly allows redistribution.
- Use the `orchestrate` skill (plugin `honeyguide`) for work here. Reply to the owner in Thai (LEARNED.md); code and docs stay in English.
