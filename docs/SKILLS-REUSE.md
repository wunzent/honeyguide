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
