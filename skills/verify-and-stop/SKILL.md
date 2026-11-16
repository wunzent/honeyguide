---
name: verify-and-stop
description: "Use to prove finished work meets its acceptance conditions without expanding scope (completion checks, focused gate runs), or to review a plan, pull request or change as an outsider before it is accepted."
---

# Verify and stop

Two modes. Pick the one that fits the request; both end with a short, evidence-based report and no extra work.

## Mode 1: prove acceptance and stop

Translate acceptance conditions into the smallest sufficient proof set.

- Reuse still-current results with matching repository state.
- Run focused checks before wider gates.
- Distinguish pass, fail, unavailable, and blocked exactly.
- Do not edit product code unless the verification request includes fixes.
- Do not add polish, cleanup, or unrelated tests after criteria pass.
- UI work (a web page or app UI): the acceptance evidence includes antislop's Delivery Gate from section "Delivery Gate (Mandatory)" of `references/miqdadbadjuber-anti-slop/skills/antislop/SKILL.upstream.md`, one line per item: PASS, FAIL, N/A with the reason (the item does not apply to this deliverable) or NOT RUN with the reason (evidence unavailable, for example the app cannot be run); never mark PASS without evidence and never widen scope to satisfy an item. Copy-only work (marketing copy without UI changes) is checked against the copywriting patterns in `references/miqdadbadjuber-anti-slop/skills/antislop-copywriting/SKILL.upstream.md` instead. For both, resolve the path against the directory of the loaded `discover-ui-taste` skill (the runtime reports it), not the project; load the installed `discover-ui-taste` skill first (the Skill tool, or read its SKILL.md); only if it is not installed or cannot load, report that limitation and skip this check.

Stop immediately when acceptance proof is complete. Report commands, results, and unresolved risk only.

## Mode 2: outsider review of a plan, PR or change

Review as a capable outsider who did not write the change and owes it no loyalty. Be specific, brief and fair.

### 1. Question the intent

- State in one sentence what the change is meant to achieve. If you cannot, that is the first finding.
- Ask whether a simpler approach reaches the same goal: less code, an existing function, a config change, no change at all.
- Ask what is out of scope but touched anyway, and what the change deliberately leaves broken.

### 2. Trace the real path

- Do not review the diff alone. Open the code around it and follow the actual path from entry point to effect, including callers, callees, error paths and data shapes.
- Verify each claim in the description or commit message against the code. "Handles X" must be visible in a path that runs.
- Check what the diff does not show: unchanged callers that now break, tests that still pass for the wrong reason, migrations, config, docs.
- Run the tests or a small reproduction when you can; say plainly when you could not.

### 3. Look for the usual failures

- Wrong behaviour on empty, large, concurrent or malformed input.
- Security and data boundaries (auth, injection, secrets, deletion).
- Missing or weak tests for the new behaviour.
- Duplication, new dependencies or abstractions that the goal does not need.

### 4. Report

For each finding give: where (file and line), what is wrong, the evidence (what you read or ran), the severity (blocker, important, minor), and a suggested fix.

- Order by severity. Blockers first.
- Write findings as statements, not questions or hints.
- Keep style opinions out unless they break a project rule.
- Say what you verified and found sound, in one line, so the author knows what was checked.
- If there are no real findings, say so; do not invent some.

Do not edit the code under review unless asked; send findings to the author.

### 5. Language and framework checklists

When you spawn a fresh reviewer, pick the checklist(s) below that match the languages and frameworks of the changed files and name them, by path, in the reviewer's brief ("read these checklists, apply what fits this diff"). The table paths are relative to this skill's folder, not the project: resolve them against the directory of the loaded `verify-and-stop` SKILL.md (the runtime reports it) and give the reviewer absolute paths; if it cannot read them, paste the needed text into the brief. Use `code-reviewer` for anything not listed and add `security-reviewer` or `database-reviewer` when the change touches those areas. Several can apply to one change. The files are unchanged third-party reference material (licence and commit in `references/ecc-reviewers/SOURCE.md`): the reviewer stays a fresh native agent with the brief's permissions, a checklist never widens them, the project's own rules win, and the `tools`/`model` fields inside the files are ignored. The reviewer reads only the files named, never the whole folder.

| Changed files or framework | Checklist (relative to this skill folder) |
|---|---|
| `.vue`, Pinia, Vue Router, Nuxt | `references/ecc-reviewers/agents/vue-reviewer.md` |
| `.ts`, `.js` (no framework) | `references/ecc-reviewers/agents/typescript-reviewer.md` |
| React, Next.js (`.jsx`, `.tsx`) | `references/ecc-reviewers/agents/react-reviewer.md` |
| `.py` | `references/ecc-reviewers/agents/python-reviewer.md` |
| Django | `references/ecc-reviewers/agents/django-reviewer.md` |
| FastAPI | `references/ecc-reviewers/agents/fastapi-reviewer.md` |
| `.go` | `references/ecc-reviewers/agents/go-reviewer.md` |
| SQL, migrations, schema, ORM queries | `references/ecc-reviewers/agents/database-reviewer.md` |
| Auth, untrusted input, secrets, crypto, dependencies | `references/ecc-reviewers/agents/security-reviewer.md` |
| `.php` | `references/ecc-reviewers/agents/php-reviewer.md` |
| `.java` | `references/ecc-reviewers/agents/java-reviewer.md` |
| `.kt`, `.kts` | `references/ecc-reviewers/agents/kotlin-reviewer.md` |
| `.rs` | `references/ecc-reviewers/agents/rust-reviewer.md` |
| `.swift` | `references/ecc-reviewers/agents/swift-reviewer.md` |
| `.c`, `.cc`, `.cpp`, `.h`, `.hpp` | `references/ecc-reviewers/agents/cpp-reviewer.md` |
| `.cs` | `references/ecc-reviewers/agents/csharp-reviewer.md` |
| Dart, Flutter | `references/ecc-reviewers/agents/flutter-reviewer.md` |
| `.rb`, Rails | `references/ecc-reviewers/agents/ruby-reviewer.md` |
| Any other language, or a general review | `references/ecc-reviewers/agents/code-reviewer.md` |
