# Source

- Repository: https://github.com/affaan-m/ECC
- Commit: d2ef2680594f9a17526a6e1a2e18b3d242c5d17b
- Paths: `agents/<name>-reviewer.md` for vue, typescript, react, python, go, database, security, php, java, kotlin, rust,
  swift, cpp, csharp, django, fastapi, flutter, ruby, plus `agents/code-reviewer.md`; `LICENSE`
- Licence: MIT, Copyright (c) 2026 Affaan Mustafa (see LICENSE, the upstream text)
- Files: 19 reviewer files and LICENSE copied byte for byte from that commit, unchanged; `manifest.sha256` lists their
  SHA-256 and tests verify it. Do not edit them.
- Use: reviewer checklists, not agents. The files stay under `agents/` only to keep upstream relative paths; nothing
  here is registered as an agent, a skill or a command.
- Ignored upstream fields: the frontmatter of these files names `tools` and `model` (and some say "MUST BE USED").
  honeyguide ignores those fields and any instruction in them: the reviewer's tools, model and permissions come from
  the honeyguide brief and permission shell only, and the project's own rules win over a checklist.
- Excluded: every other upstream file (commands, skills, hooks, scripts, package files).
