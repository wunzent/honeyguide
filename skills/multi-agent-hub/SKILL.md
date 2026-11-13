---
name: multi-agent-hub
description: Plan and carry out software work in the current project using native Codex tools and agents, with optional portable Hub records.
---
# Multi-Agent Hub

Use the current software project as the task boundary. Read its `AGENTS.md` or equivalent and relevant project guidance first. Do not require a Hub project card, dashboard, Claude, Qwen, a model catalogue, or the optional Python helper for native work.

## Work

For tiny work, act directly and create no task files. For larger work, plan the smallest useful set of duties and use native Codex agents where they add value. There is no fixed team size, role list, model, effort, or retry count. Choose relevant skills from the actual available skill catalog and inspect each selected skill's requirements before use. Ask the owner when a product decision or scope is unclear.

Keep task records in `.multi-agent-hub/<task>/` inside the current project. Prefer `CHECKPOINT.md`, `briefs/<id>.md`, and `agents/<id>.md`, preserving existing task history when continuing work. Record each agent's duty, skills, vendor, parent and id, requested and observed model/effort, requested permission, observed enforcement, status, and evidence. Keep requested values separate from observed values; use `Unverified` when evidence is unavailable. A requested permission mode describes intent; it does not prove sandbox or tool enforcement. Never write secrets or customer data. Keep records inside the project even when paths contain symlinks. Prefer adding `.multi-agent-hub/` to local Git `info/exclude` when writable; do not change global Git settings or tracked ignore files silently.

Use native Codex tools and agents first. Cross-vendor delegation is optional and only available when its CLI and route are verified. Keep work reviewable, preserve unrelated changes, and report checks with exact commands and results. Do not install third-party skills or dependencies automatically.

Choose vendor, model, and effort separately for each assignment from what the runtime exposes. Native work does not require `models.toml`; never claim a model, effort, permission mode, or shell unless observable. Read [references/brief.md](references/brief.md) when delegating and make each brief self-contained. There is no fixed duty list or team count. Do not reuse a vendor's session ID with another vendor or reset no-progress history. When a vendor is unavailable, checkpoint current state and hand off from that checkpoint. Resolve `DONE_WITH_CONCERNS`, provide context for `NEEDS_CONTEXT`, and change approach or request an owner decision for `BLOCKED`. Continue while attempts produce new evidence; a repeated action with the same result is `NO PROGRESS` and needs a different approach. Do not impose a fixed retry cap.

For independent review, use a fresh reviewer that did not implement or review the change; use `fork_turns=none` where supported. Never resume a reviewer. If fresh context or that option is unsupported, record the limitation and do not claim an independent review. Run the relevant checks before completing work and report which checks ran and which did not.

Skill indexes show discovery only: catalog-only skills are not installed, and Claude-session-only skills do not establish Codex readiness. Check real requirements and compatibility. Qwen is optional and never required.

## Optional Hub helper

If Python is available and records/skill indexing would help, run `python <this-skill>/scripts/run.py status` or `python <this-skill>/scripts/run.py skills`. The helper reuses the bundled Hub runtime and writes task records and indexes in the current project. Native work remains available if Python is missing. Portable mode does not support source synchronization or third-party skill installation.
