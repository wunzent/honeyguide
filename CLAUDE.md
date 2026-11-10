# Desktop orchestrator

- At the start of every turn run `.venv\Scripts\python.exe bridge.py pending --brief`.
- Questions to the owner include context, impact, 2–4 options with consequences, and a default (or none).
- Never run `owner_console.py`. Never type or ask for a passphrase in chat. Tell the owner the exact command to run in their own terminal: `.venv\Scripts\python.exe owner_console.py approve PROJECT TASK` (or `answer PROJECT TASK QID --answer "OPTION"` for an owner-signed question).
- Relay answers only for relay-class questions, quoting the owner's exact words with `bridge.py relay-answer PROJECT TASK QID --quote "WORDS" --option "OPTION"`.
- Security Gate stays **NOT PASS** in manual trusted approval mode.
- No push, merge, deploy, or cleanup. Never modify `../multi-agent-hub`.
