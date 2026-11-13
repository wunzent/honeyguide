# Codex CLI child process launch

The desktop tool process exports CODEX_WINDOWS_REGISTERED_CORE=1. A standalone npm Codex CLI worker inherits it and attempts an app-registered Core launch despite having no packaged-app identity. Actual A/B evidence: inherited marker -> BLOCKED, removing that single marker from the subprocess environment -> CORE_LAUNCH_PROBE_OK, actual gpt-6-luna/low, read-only sandbox unchanged. Evidence: main checkout work/codex-only-gaps/live/launch-environment-ab.json and agents/runtime-launch-probe-{1,2}.

For Windows Codex CLI delegation only, copy the parent environment and omit CODEX_WINDOWS_REGISTERED_CORE for the child. Do not mutate os.environ, remove other variables, change sandbox/approval flags, change globals, or affect Claude/non-Windows routes. Apply to new and resumed workers through the shared Popen boundary.

Regression proof must cover Codex removal, Claude retention, parent-environment retention and security-related variable retention. Live checks must prove shell execution, a read-only negative write and workspace-write positive write on disposable sentinel files. Do not infer enforcement from a launch failure or model self-report. Named native permission-shell selection remains outside this exposed API. Security Gate NOT PASS until separately verified.

Owner approved a new worktree on fix/codex-worker-launch. Existing main and other worktrees remain untouched. Owner subsequently authorized committing the reviewed patch and merging it into main. No push or dependency installation is authorized.
