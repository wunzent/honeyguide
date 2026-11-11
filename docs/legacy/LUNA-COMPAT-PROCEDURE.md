# gpt-6-luna compatibility procedure

Status: offline checks **PASS** (2026-11-11). Live checks **NOT RUN** — each needs separate owner approval.
Until a live check passes, `gpt-6-luna` stays in `unverified_models` and the Hub router and the Desktop
launcher both refuse it. Security Gate: **NOT PASS**.

## Why Luna is not used today

The audit of the last 10 coder launches (2026-11-11) found every one on `gpt-6.1-sol`. The Desktop launcher
defaulted to Sol (now removed: tier, model, effort and reason are mandatory and checked against
`config/models.toml`), and the Hub takes its default model from the policy `fallback` list, so tiers only
lowered effort. Luna has execution evidence from v1 (its own folder, Nov 9) but none under v2's isolated
worker arguments.

## Offline evidence (no model call, no login)

| Check | Result |
|---|---|
| Codex model catalog (`~/.codex/models_cache.json`, read-only) | `gpt-6-luna` listed; efforts low–max; same `unified_exec` shell and freeform patch tool as Sol; context window 272k (Sol 500k) |
| Hub isolated argv (`CodexAdapter.build`) | Luna and Sol argv identical except the `-m` value; `--ignore-user-config`, `--ignore-rules`, elevated sandbox, `mcp_servers={}`, 12 disabled features kept |
| Hub router (`resolve`) | Luna refused: `needs owner: model not live-verified`, also with `allow_premium=True` |
| `codex debug prompt-input` with the same flags, throwaway `CODEX_HOME` | exit 0 for both models; same tool list size; only the model-specific instruction message differs (Luna 18.6k vs Sol 22.4k chars) |
| Owner `~/.codex/config.toml` | hash unchanged before/after |
| Installed Codex CLI | `codex-cli 0.167.0` (matches the policy pin) |

Offline checks cannot show whether Luna completes a coding step correctly, follows the scope rules, or
how much quota it uses.

## Live check L1 — Desktop delegation (1 model call, optional paired Sol call)

- Throwaway git repo under the scratch area: one source file with a known bug and one failing test.
- Brief: fix the bug, edit only that file, run the one test command, end with a `REPORT:` line.
- Run `codex exec -m gpt-6-luna -c model_reasoning_effort=low -s workspace-write -C <throwaway>` once
  (a dedicated probe, not the Desktop launcher, which keeps refusing Luna until it is verified).
- Optional: the same brief once on `gpt-6.1-sol` at low effort, for a token comparison.

PASS: exit 0; the session record shows `gpt-6-luna` / `low`; the test passes; only the allowed file changed;
no edits outside the throwaway repo; owner config hash unchanged. Record duration and total tokens.

## Live check L2 — Hub-managed worker (1 model call)

- In the disposable environment (`mah-v2-liveb`), never in the real hub config: a verification-only copy of
  `models.toml` without Luna in `unverified_models`, and a `routine` task with a `hub-tier` block.
- One coder run on a throwaway target repo through the engine, with the full isolated argv.

PASS: argv contains every isolation flag and `-m gpt-6-luna`; the session record confirms the model; scope
check passes; the task reaches review; owner config hash unchanged.

**Dependency:** LIVE-B stopped because the Codex CLI wrote a trust entry into the owner config. L2 uses the
same Codex worker path, so it is expected to hit the same tripwire until Codex isolation V1–V3 are resolved.
Run L1 first; run L2 only after V1–V3, or accept that it may stop at the tripwire.

## STOP conditions

Owner config or Claude settings change; any edit outside the throwaway repo; the session record shows a
different model than requested; a usage limit; any unexpected network or permission prompt. Do not retry
automatically.

## After a PASS (separate approval)

1. Remove `gpt-6-luna` from `unverified_models`.
2. Add a tier-to-model mapping (routine → `codex:gpt-6-luna`) next to `[routing.tiers]`, so the Hub default
   changes model as well as effort; complex and security-sensitive work keeps Sol at high effort.
3. The Desktop launcher then accepts Luna for routine tasks only (it already enforces that rule).
