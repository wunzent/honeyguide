# Claude Code as Orchestrator

Open this hub in Claude Code and follow `AGENTS.md` (`CLAUDE.md` imports it for Claude Code).
Codex must trust the project to load `.codex/` definitions. Use only exposed features; never change global configuration.

## Discover and choose
Run `python tools/hub.py skills`, search `work/skills-index.md` and read matching SKILL.md files.
Discover project/user/plugin skills dynamically. Check real requirements and native plugin activation, even for
skills naming another model/vendor. Requirement flags mean check. Approved project-local third-party installation:
`hub.py skills install`; source/ref/licence/status/adaptations are in `skills/external.toml`.
Unsupported qwen-agent delegation maps to `hub.py delegate` with a suitable verified model and a self-contained brief;
Qwen is not required. No global changes or unclear-licence files in commits.

## Native agents
- Definitions: `.claude/agents/hub-writer.md` and `hub-readonly.md`, from `agents/shells/` via `hub.py sync`.
- Use the Agent tool: `subagent_type` = permission shell, with a suitable verified model. The brief defines the
  duty (`--role` in records), scope, skills and limits. Never use a duty name as the agent type.
- Record first: `hub.py agent new <task> --role <duty> --vendor claude --model <model> --effort <effort>
  --assignment "..." --parent claude-orchestrator --skills <selected> --kind native`; update after completion.
- Native effort/model may not be exposed; actual values stay Unverified unless observed in runtime evidence.
  Give the child a self-contained brief without conversation history. Resume implementers for fixes, use fresh reviewers.
- Claude tool permissions are not an OS sandbox. Native hub-readonly has only Read/Grep/Glob, without Bash.
  Read-only duties needing commands use Codex hub-readonly (read-only sandbox) or `hub.py delegate` with explicit limits.

## CLI workers and quota
`python tools/hub.py delegate <task> --to <codex|claude> --role <duty> --model <verified-model> --effort <effort>
--brief <file> --reason "..." --parent <orchestrator> --skills <selected> [--cwd <repo>] [--write] [--allow-shell]`

Use native or same-vendor CLI workers when only Claude Code is available. With both, delegate to Codex when suitable.
No fixed model, effort, team size or skill combination; follow `models.toml` and AGENTS.md per assignment.
Codex CLI uses read-only/workspace-write sandbox modes; Claude CLI has Read/Glob/Grep, Edit/Write under `--write`,
and Bash only with `--allow-shell`. CLI workers receive duty and generic contract through their brief.
Network/profile writes may be blocked by the active sandbox: report the limit, never change global permissions.
Record every actual spawn and inspect `hub.py status <task>`; unexposed actual model/effort stay Unverified.
On quota loss update `work/<task>/CHECKPOINT.md`, then hand remaining work to the other vendor with a handoff brief.
Never reuse session IDs across vendors or redo completed work; if neither can continue, report the block.
