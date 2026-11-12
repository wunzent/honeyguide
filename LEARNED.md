# Learned - how the owner wants work done

Read at the start of every session (both vendors). One general rule per line, at most about 20. When the owner corrects
you, add or merge a line here (replace a line it contradicts) and log it: `hub.py log feedback --text "..."`.
Project-specific detail goes in `projects/<name>.md`, not here. This file is the single source for the owner's hub
preferences: vendor memories point here instead of copying rules. While this list has fewer than 10 lines, end a
delivered task that needed rework with one short question about what to do differently.

- Keep the hub minimal and native: no retry budgets, custom engines, dashboards, signing or new frameworks.
- Preserve the owner's own formatting; style is not a defect unless it breaks something or a project rule.
- Ask which branch (current, new, or a new worktree) before changing a target repo.
- Plans and specs live in the target repo (`docs/plans/`, `docs/specs/` or the repo's own place).
- In review or migration phases fix only confirmed blockers; no cosmetic refactoring unless asked.
- Report simulated, unverified and not-run results as exactly that; keep gate statuses explicit.
- Third-party skills and plugins: clone and read first; the owner decides on installing and on global vs project scope.
- Reply to the owner in Thai; code, hub records and the hub's own docs stay in English.
- Project documentation (skill `software-component`) is Thai prose; headings, column names, statuses, technical terms,
  identifiers and paths stay in English, as in the owner's reference set. Mermaid: current version (11.x) syntax for
  every diagram (flowchart, sequenceDiagram, stateDiagram-v2, erDiagram); the old v8.8.0 limit is dropped.
- In this hub the project rules win over the older v1 workflow in the owner's global `~/.claude/CLAUDE.md` (roles.json,
  task cards, 3-round/60-minute limits): roles are routed per assignment and there is no round or time budget.
