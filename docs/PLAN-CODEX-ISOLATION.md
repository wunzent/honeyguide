# Plan — Codex worker isolation (Rev 1, PLANNING ONLY)

Owner decision: "DECISION: APPROVED — PLANNING ONLY". No code change and no live run is approved yet.
Security Gate stays **NOT PASS**. LIVE-B stays **NOT COMPLETED**.

## 1. Problem (from LIVE-B run `R-20261111032828-705d`)
- The Codex CLI wrote `[projects.'…\mah-v2-liveb\target'] trust_level = "trusted"` into the owner's
  `~/.codex/config.toml` during worker start-up. The existing LIVE-A target entry was most likely written the same way.
- Workers load the owner's whole Codex setup: `config.toml` (MCP servers `node_repl`/`atlassian`, 13 plugins, a Postman
  hook, project trust entries, `[windows] sandbox`), execpolicy `rules/`, personal skills, memories and goals.

## 2. Findings (read-only investigation, Codex CLI 0.167.0, 2026-11-11)
All probes used `codex --help` texts and `codex debug prompt-input` (renders the model-visible prompt; no model call).
The owner's `config.toml` hash was checked after every probe: **unchanged**.
| # | Finding | Consequence |
|---|---|---|
| F1 | `exec --ignore-user-config`: "Do not load `$CODEX_HOME/config.toml`; auth still uses `CODEX_HOME`". Also available on `exec resume`. | Drops the owner's MCP servers, plugins, hooks, trust entries and other settings while keeping the **same login**. No credentials are copied. |
| F2 | `exec --ignore-rules`: do not load user/project execpolicy `.rules` | Removes the owner's command allow-rules from workers. |
| F3 | A fresh, empty `CODEX_HOME` logs **"Windows sandbox selection: disabled"**. The owner's home logs `elevated`; its one-time setup marker is `~/.codex/.sandbox/setup_marker.json`. | A separate worker `CODEX_HOME` would lose the elevated sandbox, and setting it up again may need admin rights (the owner has none on this device). `--ignore-user-config` also drops `[windows] sandbox`, so the hub **must pass `-c windows.sandbox="elevated"` explicitly**. |
| F4 | A separate `CODEX_HOME` has no `auth.json`. Copying it would duplicate credentials, and token refresh could break the owner's own login. | **Rejected:** separate `CODEX_HOME`. |
| F5 | Disabling features removes plugin skills, but personal skills still load from `~/.codex/skills` (31) **and `~/.agents/skills` (44)**. The latter is found through the OS, not `CODEX_HOME`/`USERPROFILE`. `skip_host_skill_discovery` has no effect. | A per-skill `-c 'skills.config=[{path="…/SKILL.md", enabled=false}]'` **does** remove a skill (tested). The hub can generate this list automatically. |
| F6 | Default features include apps, browser_use, computer_use, in_app_browser, memories, goals, hooks, plugins, remote_plugin and multi_agent. `--disable <feature>` works per run. | Disable them per run; no owner config change. |
| F7 | The hub already passes `features.multi_agent=false`. A "multi_agent_role" text block still renders, but `additional_tools` is empty. | Informational. |
| F8 | Sessions, logs, history and SQLite state are written to `~/.codex` (state, not config). | Kept on purpose, because session **resume** needs them (`--ephemeral` would break resume). |

## 3. Design (minimal, automatic, no owner setup)
Same `CODEX_HOME` (the owner's login and elevated sandbox setup), but **no user configuration**. The Codex worker argv
becomes:
```
node codex.js exec [resume <id>] --json -C <worktree> -s workspace-write|read-only
  --ignore-user-config --ignore-rules
  -c windows.sandbox="elevated" -c mcp_servers={}
  --disable apps --disable plugins --disable remote_plugin --disable hooks --disable memories --disable goals
  --disable multi_agent --disable browser_use --disable browser_use_external --disable in_app_browser
  --disable computer_use --disable skill_mcp_dependency_install
  -c skills.config=[{path=…,enabled=false}, …]
  -m <model> -c model_reasoning_effort=<effort> -o <run>/last.md -
```
`skills.config` is built at spawn time from the `SKILL.md` files under `~/.codex/skills`, `~/.agents/skills` and
`~/.codex/skills/.system` (paths only, never contents). The hub reads only file names.

Fail-closed guards (hub side):
1. **Owner-config guard:** SHA-256 of `~/.codex/config.toml` before and after every Codex run. If it changed, the run is
   `failed` / `codex_owner_config_changed`, the result is discarded, a `security.owner_config_changed` event is
   emitted and the task goes to needs-you. There is no automatic restore.
2. **Verified-CLI pin:** `config/policy.toml [codex] verified_version = "0.167.0"`. A Codex worker with a write sandbox is
   refused (needs-you) when `codex --version` differs, because the isolation was verified per version.
3. **Flag support:** an unknown option or invalid value in stderr → `codex_isolation_unsupported`, needs-you, no
   fallback to the old argv (same rule as Claude R1).
4. Existing checks unchanged: worktree path policy, scope check, tests, reviewer, auto-commit rules, N1 resume guard.

Unchanged: model routing, effort, `-s` mode per template, `-o last.md`, session ids and resume (same `CODEX_HOME`), and
the 2-process cap.

## 4. Files (implementation, after approval)
| File | Change |
|---|---|
| `adapters/codex_cli.py` | new argv flags, the skills-disable list, isolation-unsupported classification |
| `runner.py` | owner-config hash before/after for Codex runs; fail-closed handling |
| `engine.py` | verified-version check before a Codex spawn (needs-you) |
| `config/policy.toml` | `[codex] verified_version` (a policy edit makes earlier approvals invalid — expected) |
| `tests/test_adapters.py`, `tests/test_live_a_fixes.py`, `tests/fakes/fake_codex.py` | argv pinned; config-changed → fail closed; version mismatch → no spawn; unsupported flag → no fallback; resume keeps the flags |
Coder: Codex (direct exec); independent Claude review; full suite; scoped local commit (same rules as before).

## 5. Verification plan (each live step needs separate owner approval)
- **V0 (offline):** full suite; argv and guards pinned by tests.
- **V1 (one minimal live Codex run, disposable repo):** a trivial edit in the worktree. Check:
  - the owner `config.toml` hash is unchanged (the trust-entry question);
  - the owner sandbox log shows `selection: elevated` in the run window;
  - login works without new credentials;
  - no MCP, plugin or hook activity in the stream;
  - normal coding inside the worktree works.
- **V2:** session resume with the same flags.
- **V3:** re-run LIVE-B A0–A12 (procedure unchanged) only after V1 passes.

## 6. Limitations and open risks
- **Trust write under `--ignore-user-config` is unverified.** If Codex still persists trust entries, guard 1 fails every
  run on a new repo. Fallback options then need an owner decision; none is chosen here. Repos the owner already trusts
  would not trigger a write.
- The sandbox selection is controlled only by the explicit `-c windows.sandbox="elevated"`. The hub cannot read the
  selection per run reliably: the owner's other Codex sessions write to the same log, which has no PIDs.
- The elevated sandbox limits **writes** and (per its design) network. Reads of the owner's files remain possible
  (confidentiality is not covered). Its exact writable roots (for example `%TEMP%`) are to be measured by LIVE-B.
- Workers still write session, log and SQLite state into `~/.codex`.
- The hub's own Python test step still runs coder-written code outside any sandbox (threat T6).
- The verified-version pin means every Codex update needs a short re-verification before workers run.
- STOP conditions checked: no owner configuration is disabled or edited, no new credentials, and no broader
  permissions are needed. Guard 1 detects but cannot prevent a CLI write to the owner config.
