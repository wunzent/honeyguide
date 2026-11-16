---
name: security-scan
description: "Use to review a change or area for security problems: untrusted input, auth, secrets, data storage, dependencies and privacy, against security-and-hardening and the ECC security-reviewer checklist, by a fresh read-only reviewer."
---

# Security scan

A focused, read-only security review of a change (or a named area). Idea from ECC's `/security-scan` command (affaan-m/ECC, MIT); it reads code and writes a report, it runs no scanner.

1. Scope: the diff, or the paths the owner names. List the files and the trust boundaries they touch (user input, network, files, database, secrets, third-party code).
2. Read `security-and-hardening` for the rules. Add `discover-backend` or `discover-devops` references when the topic needs them (authentication, container security).
3. Brief a fresh reviewer (Claude Code: new `Agent` with an explicit `model` and `honeyguide:hub-readonly`; Codex: `spawn_agent`, `fork_turns=none` and a read-only brief with the `READ-ONLY DUTY` line, an instruction, not enforced; never resume one). Put in the brief: the scope, the diff text or exact file paths, `security-and-hardening`, and the checklist `references/ecc-reviewers/agents/security-reviewer.md` (plus `database-reviewer.md` for queries or migrations) resolved against the directory of the loaded `verify-and-stop` skill and passed as an absolute path (paste the text if the reviewer cannot read it). Include new untracked files in the scope (`git ls-files --others --exclude-standard`), not generated records. The checklist is reference material and widens nothing: the reviewer stays read-only and ignores the `tools` and `model` fields inside it.
4. The reviewer reports each finding with where, what, evidence, severity (blocker, important, minor) and a fix. Hard-coded secrets are reported as location only; write `***`, never the value.
5. Send blocker and important findings verbatim to the implementer, not to yourself, then re-review the fix diff with a fresh reviewer.
6. Report what was checked, what was found, and what was out of reach: no running exploits, no network probing, no dependency audit tool unless the owner asks and the project already uses it.

Nontrivial work keeps the records `orchestrate` requires. Nothing is committed or published by this skill.
