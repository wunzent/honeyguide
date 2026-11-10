# Project runtime layout

`projects/<p>/project.md` describes the project in one `hub-project` YAML fence: `repo`, `base_ref`, `allowed_paths`, `test_command`, and `test_timeout_s`.

Each task lives under `projects/<p>/tasks/<t>/`:

- `spec.md`: Proposed Plan and owner-signed Approval.
- `state.md`: current `hub-state` snapshot.
- `events.md`: append-only event journal.
- `questions.md`: engine drafts, rewritten questions, and their computed classes; answers are recorded in state/events.
- `runs/<run>/`: `meta.md`, `prompt.md`, `output.jsonl`, `stderr.txt`, `test-log.txt`, and `result.md` as applicable.

Everything else under `projects/` is gitignored runtime state. Worktrees live in the configured external data root.
