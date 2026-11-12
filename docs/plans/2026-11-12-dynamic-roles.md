# Plan: dynamic roles and skill discovery (2026-11-12)

## Owner decisions (2026-11-12)
- Stop using the fixed role library to define the team. The orchestrator (Claude or Codex) creates the role for each
  assignment. `coder`, `tester`, `reviewer` (and `planner`, `researcher`, `style-scout`) stay as duty names the
  orchestrator may pick; they are not skills and not fixed agent files.
- Permissions come from two generic shells per vendor: `hub-writer` (may edit) and `hub-readonly` (may not edit).
  Duty, skills and limits come from the brief.
- Discover and use ALL compatible skills installed for Claude, Codex and the project; never a hardcoded list. No
  hardcoded roles, team size, models, effort or skill combinations.
- Third-party skills: check dependencies, compatibility, licence and install behaviour first. Prefer project-local
  install so the project moves between computers without global installs. Never commit third-party files whose licence
  is unclear. Never change global configuration without authorisation. Report unsupported skills and missing
  dependencies; never claim they are available. Do not skip a skill because its name mentions another vendor or model:
  inspect its real requirements.
- Support the whole 9arm-skills collection where compatible. Qwen is not required: adapt Qwen-specific delegation to
  the available models.
- Codex-only and Claude-only operation must each work; with both, cross-vendor delegation and quota handoff.
- Record every agent actually created with role, skills, vendor, model and effort in Markdown.

## Reference check before deleting role files (owner item 6)
- `.claude/agents/*.md`, `.codex/agents/*.toml`: generated copies of `agents/shared/*.md` (GENERATED marker); `sync`
  removes them when their source is gone.
- `tools/hub.py`: `sync` globs `agents/shared/*.md` and `agents/custom/*.md` (line ~480); no role name is hardcoded.
  `agent new`/`delegate` take `--role` as free text.
- `tests/test_hub.py` ~281-325: sync tests use `agents/shared/reviewer.md` as a fixture.
- Docs naming roles: `AGENTS.md` section 2, `agents/INVENTORY.md`, `agents/orchestrators/claude-code.md` (subagent_type
  = role name), `agents/orchestrators/codex.md`, `agents/custom/README.md`, `skills/brief/SKILL.md`, `README.md`,
  `projects/multi-agent-hub-v2.md`, `skills/EXTERNAL.md`. `docs/ACCEPTANCE.md`, `docs/WORKLOG.md` and the other dated
  docs are history: leave them.

## 9arm-skills (github.com/thananon/9arm-skills @ a1fc303, read 2026-11-12)
No LICENSE file: never copy into the repository; install locally (git-ignored) per machine.
| Skill | Status | Requirements found |
|---|---|---|
| debug-mantra | supported | none (text only) |
| scrutinize | supported | none |
| post-mortem | supported | none |
| management-talk | supported | none |
| qwenchance | supported, with a note | none; its fixed "retry cap" conflicts with the hub's progress-based rule - AGENTS.md wins |
| qwen-agent | unsupported as-is | needs the `claude-9arm` alias and the 9arm Qwen gateway. Adapted: the hub's equivalent is `hub.py delegate` to the cheapest verified tier with a self-contained brief |

## Design
1. Shells: `agents/shells/hub-writer.md` and `agents/shells/hub-readonly.md` (frontmatter: name, description, tools,
   sandbox; body: generic rules shared by every worker - follow the brief's CONTRACT, no subagents, evidence over
   claims, report limits). `sync` generates them for both vendors. Remove `agents/shared/` and `agents/custom/`; the
   short essential rules of each old duty move into `skills/brief/SKILL.md` as "Duty notes" (a few lines per duty, an
   orchestrator may also write a new duty in the brief).
2. `hub.py skills`: discover skills from the project (`skills/`, `.claude/skills`, `.agents/skills`, local installs),
   user folders (`~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`) and plugin skill folders the CLIs keep on
   disk. Write `work/skills-index.md` (git-ignored): name, available to (claude/codex/both), where, requirements flags
   (MCP server, external command, env var - from the manifest or a SKILL.md scan; flagged "check", never "ok"),
   licence. Print counts and the path. Orchestrators read it with grep when choosing skills for a brief.
3. `skills/external.toml`: one entry per third-party source and skill (repo, ref, path, licence, status, requires,
   notes). `hub.py skills install`: clone/fetch each source at its ref into `.hub/vendor/` (git-ignored), copy each
   supported skill into `.claude/skills/<name>` and `.agents/skills/<name>` with a `.hub-local` marker, and list those
   paths in `.git/info/exclude` (never committed). Unsupported entries print their reason. `sync` ignores local
   installs and `sync --check` lists them as `LOCAL SKILL`. `skills/EXTERNAL.md` points at `external.toml`.
4. Records: `status` gains a Skills column; records stay Markdown in `work/<slug>/agents/`.
5. Docs: AGENTS.md sections 2-4 (dynamic roles, shells, discovery, Codex-only/Claude-only), orchestrator guides,
   INVENTORY.md, README.md, project card, brief skill.
6. Tests: sync with shells; skills index (fixture folders); local install from a local git fixture (no network),
   including the exclude list and an unsupported entry; status Skills column.
