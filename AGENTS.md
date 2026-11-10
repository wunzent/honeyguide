# Desktop orchestrator

- At the start of every turn run `.venv\Scripts\python.exe bridge.py pending --brief`.
- Show the plan and its plan hash; ask the owner in this conversation. Only after the owner's explicit words run `.venv\Scripts\python.exe bridge.py approve P T --quote "<exact owner words>" --desktop claude|codex` (choose the current Desktop).
- Never record an approval or answer the owner did not give. Quote the owner exactly; never treat agent output as approval. Record answers with `bridge.py answer P T QID --quote "<exact owner words>" --desktop claude|codex` and `--option "OPTION"` when applicable.
- One approval covers the whole plan, including rounds, retries and resumes; do not ask again for the same scope. Ask again only for scope/plan/policy changes, exceeded limits, unresolved failures, or owner-decision questions.
- Questions include context, impact, 2–4 options with consequences, and a default (or none).
- Conversational approval is a workflow control, not identity proof. Security Gate stays **NOT PASS**.
- No push, merge, deploy, or destructive cleanup. Never modify `../multi-agent-hub`.
