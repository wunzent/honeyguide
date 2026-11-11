# Rebuild inventory (Phase 0) - 2026-11-11

Target: `C:\Users\Natthawut.j\Desktop\ALI\multi-agent-hub-v2` (git root, branch `master`, HEAD before rebuild
`3336cc156a3d971510f542d23b0f44d74f8dfd07`, 11 commits, no remote). Other folders are not targets:
`../multi-agent-hub` (v1, read-only reference), `../central-multi-agent-hub`, `../multi-agent-hub-v2-data` (old engine
data root), `../mah-v2-liveb` (LIVE-B disposable env) - none modified.

## Backup (verified before any deletion)
`C:\Users\Natthawut.j\Desktop\ALI\multi-agent-hub-v2-backups\20261111-173509\`
- `v2-all.bundle`: `git bundle --all`; a clone from it has HEAD `3336cc1` (same as the repo).
- `v2-worktree.tar`: the whole working tree except `.venv` (includes `.git`, uncommitted and untracked files, ignored
  `projects/`, `runtime/`, `config/` key material); 384 files extracted and compared byte-identical to the source.
- `SHA256SUMS` for both files. Restore: `git clone v2-all.bundle` or extract the tar.

## Decisions
| Item | Decision | Reason |
|---|---|---|
| `engine.py`, `scheduler.py`, `runner.py`, `state_writer.py`, `policy.py`, `approvals.py`, `hashing.py`, `worktree_manager.py`, `notify.py`, `agent_loader.py`, `model_router.py`, `adapters/` | delete | custom orchestration/guard engine; replaced by native orchestration + `tools/hub.py` |
| `bridge.py`, `hooks/pending.py`, `.claude/settings.json` (hook + bridge permissions) | delete | approval/pending ceremony of the old engine |
| `app.py` (Streamlit dashboard), `requirements.lock` | delete | no dashboard; hub.py is stdlib-only (`requirements.txt` keeps pytest) |
| `config/models.toml`, `config/policy.toml` | delete (tracked) | replaced by root `models.toml`; signed-policy era. Untracked `config/owner.pub*`, `config/policy.toml.sig` (owner key material) are left untouched |
| `delegation.py`, `tools/run-codex-step.ps1` | replace | logic folded into `tools/hub.py delegate` (both vendors, records, verification) |
| `tests/` (engine tests, fakes) | delete | they test removed code; new focused `tests/test_hub.py` |
| `agents/*.md` (engine roles) | replace | `agents/shared/` roles from v1, vendor-neutral |
| `projects/README.md` | delete | engine project registry; ignored `projects/live-a/` runtime data left in place (not deleted) |
| `AGENTS.md`, `CLAUDE.md` | adapt | orchestrator instructions for both vendors |
| `docs/WORKLOG.md` | keep | history |
| other `docs/*.md` (architecture, LIVE-A/B, Phase 1/2, plans, verification, session audit, migration, Luna) | keep, moved to `docs/legacy/` | research and evidence; not current instructions |
| `docs/*.baseline.json`, `.claude/settings.local.json` (untracked, owner's) | keep, untouched | owner files |
| `runtime/` (ignored) | keep | local delegation log |
| git history | keep | all commits remain; the legacy code is recoverable from any earlier commit |

## Reused, not rebuilt
- v1 role definitions -> `agents/shared/` (responsibilities kept, queue/worker/dashboard modes and fixed models dropped).
- v1 code-pm MODE: brief + context-engineering research -> `skills/brief/`.
- v2 cost-aware routing (verified/unverified/premium catalog, effort by work size) and the Desktop delegation
  verification (actual model/effort from Codex session files; Claude model from the CLI) -> `models.toml`, `hub.py`.
- v2 lesson: the `drive` no-progress window -> progress-based loop detection (`hub.py attempt`), no retry budget.
- Native: Claude Code Agent tool + `.claude/agents`; Codex multi-agent (`features.multi_agent = true`) + `.codex/agents`.

## Follow-up cleanup (owner: "ลบไฟล์ของเวอร์ชั่นก่อนหน้าออกให้หมด", 2026-11-11)
Removed from the working tree: `docs/legacy/` (git history keeps it), ignored `projects/` (engine runtime data), `runtime/`,
`config/` (old models/policy copies and retired signing key leftovers `owner.pub`, `owner.pub.old`, `policy.toml.sig`) and the
untracked `docs/*.baseline.json`. All are in `v2-worktree.tar` of the backup. Not touched: v1, the backups and older bundles,
`../multi-agent-hub-v2-data`, `../mah-v2-liveb`, `~/.mah-v2-owner`, global CLI configuration.
