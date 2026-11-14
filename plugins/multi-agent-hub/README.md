# Multi-Agent Hub plugin

Plan and carry out software work in any project with the active CLI's native agents (Claude Code or Codex), with
risk-based independent review and project-local records under `.multi-agent-hub/`. One shared skill
(`multi-agent-hub`) plus the bundled `software-component` documentation skill. No Python, helper or installer: the
CLI's own plugin installer does the copying.

Contents: `skills/multi-agent-hub`, `skills/software-component` (byte copy of the Hub's `skills/software-component`),
`agents/` (Claude plugin agents `hub-readonly`, `hub-writer`), `codex-agents/` (Codex agent shells to place by hand).

## Install

Claude Code (run inside a Claude Code session; the same steps exist in a terminal as `claude plugin marketplace add ...` and `claude plugin install ...`):

    /plugin marketplace add <path-or-git-url-of-this-repository>
    /plugin install multi-agent-hub@wunzent-hub

Codex (run in a terminal):

    codex plugin marketplace add <path-or-git-url-of-this-repository>
    codex plugin add multi-agent-hub@wunzent-hub

Both change that CLI's user configuration, so only the owner runs them.

Codex plugins cannot ship agents. To get an enforced read-only sandbox for review duties, copy
`codex-agents/hub-readonly.toml` and `codex-agents/hub-writer.toml` into `~/.codex/agents` (all projects) or a trusted
project's `.codex/agents`. Without them the permission of Codex children stays `Unverified`.

## Update

Claude Code: in a session, `/plugin marketplace update wunzent-hub`; then in a terminal (there is no session form of
update) `claude plugin update multi-agent-hub@wunzent-hub`, and restart the session.
Codex: `codex plugin marketplace upgrade wunzent-hub`, then reinstall with `codex plugin add multi-agent-hub@wunzent-hub`.
Re-copy `codex-agents/*.toml` if they changed. The Claude commands were not run here; if one differs in your CLI version, check `claude plugin --help` or `/plugin`.

## Uninstall

Claude Code: in a session, `/plugin uninstall multi-agent-hub@wunzent-hub`, then `/plugin marketplace remove wunzent-hub`.
Codex (terminal): `codex plugin remove multi-agent-hub@wunzent-hub`, then `codex plugin marketplace remove wunzent-hub`; delete any
copied `hub-*.toml` shells. Project records in `.multi-agent-hub/` stay until you delete them.

## Limits

- Records are written by the model following the skill, not by a tool: no `attempt` NO PROGRESS check and no verified
  model for workers.
- Codex child read-only enforcement needs the owner-placed shells above.
- Native agents of the active CLI only: no cross-vendor delegation.
- `.multi-agent-hub/` may show as untracked in a project; do not commit it (add it to `.git/info/exclude` if wanted).
- Marketplace installation was not verified on either CLI here, and no live Claude Code run was done.
