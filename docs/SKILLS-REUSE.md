# Skills and research reuse (2026-11-11)

Produced in acceptance task `acc-research` by agent `researcher-1` (native Claude subagent, sonnet) from v1 research:
AS = `research/agent-skills-2026-10-27.md`, SK = `.agents/research/skills-research-2026-11-09.md`,
EF = `.agents/research/agent-efficiency-research-2026-10-21.md` (paths under `../multi-agent-hub/`).

| Priority | Finding | How the hub uses it |
|---|---|---|
| Context engineering / BRIEF | Compress context into a BRIEF of assigned rows/sources only, no resent rules (AS:25, AS:138); brief with paths and acceptance, results to files with a reference back (EF:46); stable part first (EF:45) | `skills/brief` (paths not pasted content, KNOWN FAILURES, short) ; worker output in `work/<task>/agents/<id>.last.md` |
| Native orchestration | Do not stack a skill router on Claude Code/Codex (AS:42); flat fan-out, personas do not call each other (AS:57); one job = one process (EF:54) | AGENTS.md: native subagents + hub.py only for cross-vendor; no router, no engine |
| Skill discovery | Skills load name+description, body on use (EF:11); one skill per job (EF:15); name skills used in the report (EF:25) | Orchestrator discovers installed skills and names them per brief; `Skills` field in agent records |
| Evidence-based debugging | Keep `investigate-first`, `surgical-patch` (AS:26) | researcher role + those skills |
| No-progress detection | Same verdict/error twice -> stop and change course (EF:54) | `hub.py attempt` fingerprints action+outcome; repetition -> NO PROGRESS (no fixed round cap or time budget, per owner directive) |
| Independent review | Review rubric in the existing reviewer (AS:22, AS:50); fresh-context adversarial review by risk (AS:29); EGM "goldfish" idea - borrow, do not install (SK:17, SK:113) | reviewer role, preferably the other vendor or a fresh context |
| Cost-aware delegation | Agents ~4x and multi-agent ~15x a chat; small jobs get a single worker (EF:52); external caps needed for Codex (EF:53) | AGENTS.md section 3, `models.toml`; tiny work done by the orchestrator itself |
| Task-specific skills | Accessibility/performance checklists only for UI acceptance (AS:54, AS:58); security only for risky diffs (AS:51); anti-slop as a ~10-rule UI checklist, not the full install (SK:15, SK:220) | named per brief from installed skills |

## Listed repositories
Covered by earlier research: addyosmani agent-skills (AS, commit aeac41d), anti-slop (SK:15, SK:71-76),
diagram-design (SK:19, use the installed `anthropic-skills:diagram-design`), elephant-goldfish-model (SK:17, SK:107),
graphify (installed skill, AS:25), lighthouse (tool mention only, AS:53).
**Not covered by any research file (not evaluated in this rebuild):** obra/superpowers, NousResearch/hermes-agent,
mattpocock/skills (several are installed as the `mattpocock-skills` plugin), anthropics/skills doc-coauthoring
(installed as `anthropic-skills:doc-coauthoring`), thananon/9arm-skills, neondatabase/agent-skills, antfu/skills,
ui-ux-pro-max (installed in Codex skills), material-design-icons, globalmpc/backendskills, addyosmani web-quality-skills.
No third-party skill was installed; evaluating the uncovered repositories is a separate, optional task.

2026-11-12 (owner request): `skills/context-engineering/` vendored verbatim from addyosmani/agent-skills commit aeac41d
(MIT, `LICENSE` copied alongside) and synced to `.claude/skills` and `.agents/skills` (project scope, both vendors).
EGM (google/elephant-goldfish-model v0.1.1, Apache-2.0, reviewed clone at commit 8414530) installed GLOBALLY in both
CLIs on the owner's explicit decision ("ติดตั้ง global ทั้งคู่"): `claude plugin marketplace add` + `install egm@egm`
(user scope, enabled) and `codex plugin marketplace add` + `add egm@egm` (enabled). Installed skill files equal the
reviewed clone (Claude's copy omits only TEST.md/test_scenarios.yaml); no hooks. Global config changes: `~/.claude/settings.json`
(enabledPlugins + extraKnownMarketplaces entries) and `~/.codex/config.toml` (`[plugins."egm@egm"]`, `[marketplaces.egm]`).
Pre-install copies: `ALI\multi-agent-hub-v2-backups\egm-install-20261112\`. Codex config hash was already
`5c8a65ea04eaf9c4` before the install (not the earlier `259cbae720916dc3`); after: `53a610a347ce0492`.
Use EGM selectively (heavy, one-question gates, design-only scope): comprehension goldfish on big briefs/PLANs/handoff
checkpoints, implementation-readiness before coding, `egm-drift-report` after a build. In Claude, invoke `/egm:egm-review`
etc. (the Skill tool refuses EGM skills by design).

obra/superpowers v7.0.2 (MIT, read-only clone at commit 22f0b46; NOT installed: its SessionStart hook injects mandatory
skill rules into every session). Borrowed and adapted (not copied): worker report contract with 4 statuses and a report
file (`skills/brief` CONTRACT), implementer rules (`coder.md`), reviewer brief = requirements + claims + diff file with
spec compliance first and severity calibration (`reviewer.md`, `skills/brief`), scoped re-review, fix rounds that resume
the same implementer and escalate on no progress (no round cap: AGENTS.md section 5), plan preflight, rulings ledger and
final review (AGENTS.md sections 4, 6, 7), Codex `fork_turns: "none"` (codex.md; not yet verified here), owner-chosen
branch/worktree before changes and plan/spec files in the target repo (owner decisions 2026-11-12, AGENTS.md section 1).
Not used: session-start hook, bash scripts and `.superpowers/` workspace, 5-round cap, visual brainstorming server.

Trendshift picks (2026-11-12, read-only clones in `C:\Users\Natthawut.j\src\trendshift\`):
- shadcn/improve 1.0.0 (MIT, cac56e1): INSTALLED globally on owner request - Claude plugin `improve@improve` (user scope;
  cache equals the reviewed clone) and Codex user skill `~/.codex/skills/improve` (copy + LICENSE; Codex config unchanged,
  hash 53a610a347ce0492). Pure Markdown, no hooks/scripts. Writes plans to `plans/` (its own convention), `--issues`
  publishes to GitHub only with the flag, `execute` needs Claude worktree isolation. Backups: `...-backups\improve-install-20261112\`.
- stevenmichaelthomas/numbrone (MIT, 0632b01): not installable here (needs herdr: macOS/Linux, `curl | sh`). Ideas:
  status only on change (working/blocked/review/done), reports written to make sense a month later, one-line
  `decision:` log (= our rulings), managers never edit the main checkout.
- ABLingss/awesome-agent-loops (MIT, 0eef240): a curated list; its installer pulls 30 unreviewed skills via `npx skills add`
  from about 20 repositories - not run. Notable entries: mattpocock `handoff`, `to-spec`, `to-tickets`.
- chenhg5/myco (MIT, f8a1bdd): installable (Windows preview exe, unsigned) but not installed: a hub server plus remote
  shell nodes that run commands as the user - outside this hub's scope and Security Gate NOT PASS. Ideas: message types
  task / reply / steer (correct a running task) / note, `fail --reason`, threads, self-contained task bodies, sender allow-list
  and audit log.
- lijiaqi-AI-Product-Manager/dsh-agent-compare (MIT, a041837): a DeepSeek Harness plugin only; not applicable to Claude/Codex.
  Idea: record why a candidate was picked.
- kenryu42/cc-safety-net 2.7.12 (MIT): INSTALLED globally on owner request in Claude and Codex (PreToolUse hook that blocks
  destructive commands and secret-file reads). Codex hook trusted by the owner; live block verified in both CLIs' hook paths.
  Details, tests and undo: `docs/DEEP-DIVE-2026-11-12.md#cc-safety-net`.
