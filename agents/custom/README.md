# Custom roles

Create a role here only when no shared role fits. Same format as `agents/shared/*.md`:

```
---
name: <kebab-case>
description: <one line: what it does and when to use it>
tools: Read, Grep, Glob, Bash          # Claude tool list; omit Edit/Write for read-only roles
sandbox: read-only | workspace-write   # Codex sandbox
skills: <comma list of installed skills>
native: true                           # false = record-only, no native definition generated
---
<instructions: responsibilities, boundaries, reply format>
```

Then run `python tools/hub.py sync` to generate `.claude/agents/<name>.md` and `.codex/agents/<name>.toml`.
Temporary, single-use agents do not need a role file: describe them in the brief and keep the agent record.
Move a custom role to `agents/shared/` only when it proved useful across projects.
