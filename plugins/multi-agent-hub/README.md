# Multi-Agent Hub plugin

Plan and carry out software work in any project with the active CLI's native agents (Claude Code or Codex), with
risk-based independent review and project-local records under `.multi-agent-hub/`. One shared skill
(`multi-agent-hub`) plus the Hub's other skills bundled as byte copies (see Contents). No Python, helper or installer: the
CLI's own plugin installer does the copying.

Contents: `skills/multi-agent-hub`, `skills/<name>` for api-and-interface-design, backend-api-safety, context-engineering, handoff, investigate-first,
lean-build, safe-refactor, security-and-hardening, software-component, surgical-patch and verify-and-stop (byte copies of the
Hub's `skills/<name>`; `brief` is not bundled, `skills/multi-agent-hub/references/brief.md` replaces it),
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

## 9arm skills (optional, third party)

Claude Code: the same marketplace lists `9arm-skills` (thananon/9arm-skills, pinned to commit
`a1fc303b274ed06c32d405ba5a6db00ded6e5663`; upstream ships its own plugin manifest, and no file of it is copied here):

    /plugin install 9arm-skills@wunzent-hub

Codex: upstream has no Codex plugin, so there is no marketplace entry. Manual steps in a terminal:

    git clone https://github.com/thananon/9arm-skills
    cd 9arm-skills && git checkout a1fc303b274ed06c32d405ba5a6db00ded6e5663

Then copy `skills/engineering/debug-mantra`, `skills/engineering/scrutinize`, `skills/engineering/post-mortem`,
`skills/productivity/management-talk` and `skills/productivity/qwenchance` into `~/.codex/skills/`. Do not copy
`qwen-agent` (needs a Qwen gateway). Upstream has no stated licence; check it before reuse.

## EGM skills (optional, third party)

`google/elephant-goldfish-model` (Apache-2.0, pinned in the Claude marketplace to commit
`964a4f1ecd333961375c35cb37ed09364dab5e4e`; it ships its own plugin manifest and no file of it is copied here) provides
design with context and review with fresh-eyes reviewers (`egm-bootstrap`, `egm-brainstorm`, `egm-draft`, `egm-review`,
`egm-review-loop`, `egm-resolve`, `egm-drift-report`).

Claude Code: `/plugin install egm@wunzent-hub`

Codex (terminal; upstream has its own marketplace named `egm`):

    codex plugin marketplace add google/elephant-goldfish-model
    codex plugin add egm@egm

## Website design and Base44 (optional, third party, both CLIs)

Claude Code: `/plugin install uxkin@wunzent-hub` and `/plugin install base44@wunzent-hub` (pinned to commits
`c9425694cbf77ca13c067ae100a34eeec5a2856e` and `8a7fc77304c8a9ab995d68aa5cdcbce6eddb631b`; each ships its own plugin
manifest, nothing is copied here). `uxkin` also ships an MCP server per its manifest; read it before enabling. `base44` is
only useful with Base44.

Codex (terminal):

    codex plugin marketplace add uxkin/agent
    codex plugin add uxkin@uxkin
    codex plugin marketplace add base44/skills
    codex plugin add base44@base44
    codex plugin add base44-sandbox@base44

What works on both CLIs:

| Plugin | Claude Code | Codex | Notes |
|---|---|---|---|
| multi-agent-hub (with the bundled hub skills and ub-mode) | `/plugin install multi-agent-hub@wunzent-hub` | `codex plugin add multi-agent-hub@wunzent-hub` | Codex agent shells are placed by hand |
| egm | `/plugin install egm@wunzent-hub` | `codex plugin add egm@egm` | |
| uxkin | `/plugin install uxkin@wunzent-hub` | `codex plugin add uxkin@uxkin` | website design |
| base44 | `/plugin install base44@wunzent-hub` | `codex plugin add base44@base44` | Base44 only |
| 9arm-skills | `/plugin install 9arm-skills@wunzent-hub` | manual copy (above) | |

Claude-only plugins are listed, not installed, in [RECOMMENDED.md](RECOMMENDED.md).

## ub-mode (bundled, MIT)

`skills/ub-mode` is a byte copy of unclebob/ub-mode (SKILL.md and LICENSE) at commit
`3da62bf3fcfd2034de41f30d920d2739e566171f`; see `skills/ub-mode/SOURCE.md`. It has no source under the Hub's `skills/`.
Its quality gates refer to unclebob/crapper, dryer and mutator, which are not bundled; without them those gates are
skipped and reported.

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
