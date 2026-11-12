# Project cards

One file per target repository the hub works on: `projects/<name>.md` (name: lowercase, dashes). The orchestrator writes
it the first time it works on a repo (from README, AGENTS.md/CLAUDE.md, manifests, CI config, `git log --oneline -20`),
asks the owner to confirm the summary, and updates it when something changes. Briefs cite `projects/<name>.md#Commands`
instead of re-deriving commands. Never put secrets, tokens or customer data here.

Template:

```markdown
# <name>
Path: <absolute path>    Default branch: <main|master>    Summary: <one line used to route requests>
<one paragraph: what the project is and who it is for>

## Stack
## Layout          <!-- directories that matter -->
## Commands        <!-- install, dev server, lint, typecheck, test, build: exact commands -->
## Conventions     <!-- branching, commit style, plan/spec location, anything a contributor must know -->
## Route here      <!-- kinds of requests that belong to this project, with keywords -->
## Not here        <!-- requests that sound related but belong elsewhere -->
## Decisions       <!-- dated owner decisions that bind future work, one line each -->
```
