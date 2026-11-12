# Agent inventory

The orchestrator creates the duty in each assignment's brief. There is no fixed role library, team size or skill
combination. Vendor, model and effort are chosen per assignment using `models.toml` and AGENTS.md.

## Permission shells
| Shell | Permissions | Source |
|---|---|---|
| hub-writer | may edit within the approved scope | `agents/shells/hub-writer.md` |
| hub-readonly | Claude: Read/Grep/Glob only; Codex: read-only sandbox | `agents/shells/hub-readonly.md` |

Read-only duties needing commands use Codex hub-readonly or `hub.py delegate` with explicit limits.

`python tools/hub.py sync` generates `.claude/agents/<shell>.md` and `.codex/agents/<shell>.toml`.
Shells carry no fixed model, duty or skill list. Briefs carry the duty, skills, scope, limits and CONTRACT.
`coder`, `tester`, `reviewer`, `planner`, `researcher` and `style-scout` are optional duty names;
see `skills/brief/SKILL.md` for essentials to include. A new duty needs no agent file or sync.

## Orchestrators
| Orchestrator | Instructions | Native agents | CLI workers |
|---|---|---|---|
| Claude Code | `CLAUDE.md` -> `AGENTS.md`, `agents/orchestrators/claude-code.md` | Agent tool, permission shell | `hub.py delegate --to claude` or `--to codex` |
| Codex | `AGENTS.md`, `agents/orchestrators/codex.md` | multi-agent, permission shell | `hub.py delegate --to codex` or `--to claude` |

Each vendor works alone; with both, cross-vendor review and quota handoff are available.
Every actual agent has a Markdown record in `work/<task>/agents/` with duty, skills, vendor, model and effort.
Inspect with `python tools/hub.py status <task>`; unknown runtime values stay Unverified.

## Skills
Run `python tools/hub.py skills`; search `work/skills-index.md` and read relevant SKILL.md files before selection.
The index covers project, user and on-disk plugin skills, including local installs. Catalog entries are labelled
`catalog (not installed)` and excluded from available counts. Plugin cache entries show activation unverified.
Location does not prove compatibility, plugin activation or dependencies: requirement flags mean check, never ok.
Inspect real requirements regardless of vendor/model names. Hub-owned sources: `skills/`;
approved third-party manifest: `skills/external.toml`; policy: `skills/EXTERNAL.md`.
Local copies have `.hub-local` and git exclude entries; generated files have GENERATED markers.

## Retired definitions
`agents/shared/` and `agents/custom/` were replaced by generic shells on 2026-11-12.
`sync` removes stale GENERATED definitions and preserves unmarked owner files. Globals are untouched.
