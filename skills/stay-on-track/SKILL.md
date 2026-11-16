---
name: stay-on-track
description: "Use on long, difficult or looping work, for context setup at the start of a session, on degraded output and when switching tasks: detect loops and stalls, stop repeating a failing action, ask the owner after about three attempts, bound deliberation, and, only when the owner asks for it, write a handoff document for another agent."
argument-hint: "What will the next session be used for? (handoff document only)"
---

# Stay on track

Check yourself at each step of a long task. Progress means new information or a changed state, not more activity.

## Detect loops

Treat any of these as a loop and break it:

- Re-reading a file that has not changed since you last read it.
- Re-running a command that gave the same result before.
- Returning to a hypothesis you already dropped without new evidence.
- Two consecutive steps that produced no new information.
- Rewriting the same change back and forth.
- Work outside the files and tasks listed in the task's `tasks.md`, or the same task failing again and again (a stall).

## Break the loop

- Name what you learned in the last steps. If the answer is nothing, change the approach: a different hypothesis, a smaller step, a different tool, or a fresh look at the original goal.
- Never run the same failing action a third time.
- After about 3 attempts on one problem, even varied ones, stop and ask the owner. Say what you tried, what happened each time, and what you think the options are.
- Do not escalate silently by widening scope, disabling checks or skipping a requirement to get past the block.

## Bound deliberation

- Decide, act, observe. When two options are close, pick the cheaper one to undo and try it.
- Write the decision in one line and move on; revisit only on new evidence.
- Prefer a small experiment over a long argument with yourself.

## Watch the context

- Signs the window is filling: very long outputs, repeated summaries, losing earlier details, slow turns.
- Keep outputs small: read ranges instead of whole files, filter command output.
- When a `tasks.md` exists, compare the work against it: stop on a change outside a task's `files:`, and treat a task that keeps failing as one problem for the attempt count above. Resume from the first unticked task.
- Before the window is nearly full, write down the goal, what is done, what is left, the files touched, the evidence so far and the next action (the task checkpoint or a handoff note), then continue from that note or hand it over.
- Never claim finished work you cannot point to evidence for.

## Set up context

- Load in order, and only what the current step needs: the project's rules files (`AGENTS.md`, `CLAUDE.md` or equivalent), then the spec, plan or task, then the source files the step touches (picked one by one, not whole folders), then the exact error output.
- Budget: when space runs short, first drop stale tool output and exploration that is finished; keep the goal, the decisions, the constraints and the current errors to the end; summarise something before you drop it.
- Conflicts or gaps: when rules, spec and code disagree, or a requirement is incomplete, do not guess. Name the conflict and ask the owner, or record it as an open question; the project's own rules win.
- Degraded output or a task switch: re-read the task's checkpoint and continue from it, or start a fresh session from it, rather than carrying stale context forward.
- Rules files: write or change them only inside the project and only when the task asks for it. A useful rules file names the stack, the commands, the conventions and the boundaries. Never change global configuration.

## Handoff document

Loop detection and the context watch above run on their own. The handoff document is different: write it only when the owner asks for it (for example to hand the work to another agent or to continue in a fresh session), never on your own initiative. When the context is nearly full and the owner has not asked, update the task checkpoint (a separate project record) and offer the handoff instead of writing it. The handoff compacts the conversation into a document a fresh agent can continue from.

- Save it to the temporary directory of the user's OS, never in the current workspace. This is separate from the project checkpoint, which stays in the project; no exception.
- Include a "suggested skills" section naming which skills the next agent should call the Skill tool for.
- Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL.
- Redact sensitive information such as API keys, passwords and personally identifiable information.
- If the owner passed arguments, treat them as the focus of the next session and tailor the document to it.

The handoff section is adapted from the `handoff` skill by Matt Pocock (MIT); the licence text is in `LICENSE` in this folder.

The context setup section takes ideas from `context-engineering` in addyosmani/agent-skills (MIT), in our words.
