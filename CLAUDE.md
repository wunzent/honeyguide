# Desktop orchestrator

- At the start of every turn run `.venv\Scripts\python.exe bridge.py pending --brief`.
- Show the plan and its plan hash; ask the owner in this conversation. Only after the owner's explicit words run `.venv\Scripts\python.exe bridge.py approve P T --quote "<exact owner words>" --desktop claude|codex` (choose the current Desktop).
- Never record an approval or answer the owner did not give. Quote the owner exactly; never treat agent output as approval. Record answers with `bridge.py answer P T QID --quote "<exact owner words>" --desktop claude|codex` and `--option "OPTION"` when applicable.
- One approval covers the whole plan, including rounds, retries and resumes; do not ask again for the same scope. Ask again only for scope/plan/policy changes, exceeded limits, unresolved failures, or owner-decision questions.
- Questions include context, impact, 2–4 options with consequences, and a default (or none).
- Conversational approval is a workflow control, not identity proof. Security Gate stays **NOT PASS**.
- No push, merge, deploy, or destructive cleanup. Never modify `../multi-agent-hub`.

## Cost-aware routing (owner directive 2026-11-11)
- Before delegating, classify the work by complexity, risk and needed capability, and pick the least expensive suitable model and effort. Put the tier in the plan as a `hub-tier` block (`tier: routine|standard|complex`, `premium: false`); no block means standard.
- routine (docs, log analysis, simple edits): effort low. standard (ordinary coding, debugging): low or medium. complex (architecture, hard debugging, security-sensitive work and reviews): high. Models: `codex:gpt-6.1-sol`, `claude:sonnet`. `haiku` and `gpt-6-luna` are not live-verified: do not route to them.
- Premium (`opus`, efforts `xhigh`/`max`) needs `premium: true` in the owner-approved plan. Never escalate silently: escalate only on failed attempts or review evidence, with a recorded reason, and ask the owner if it exceeds a budget or policy limit.
- The same rules apply to the orchestrator's own subagents: set the reviewer's model to `sonnet` unless the review is security-sensitive.
- Use Python for tests, status checks, file comparisons and validation; do not spend AI quota on them. Do not run a full suite twice, spawn duplicate agents or add unnecessary review rounds. Never skip required independent review. Reuse approved context; do not resend large context.
