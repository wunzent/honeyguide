# Brief

## Work brief

```text
ROLE: <duty for this assignment>
TASK: <slug>
GOAL: <observable outcome>
SCOPE: <files and limits>
INPUTS: <paths and relevant sections>
DECISIONS: <binding choices, or none>
CONTEXT: <self-contained requirements, constraints, and acceptance details>
CHECKS: <exact commands>
DONE WHEN: <acceptance conditions>
REPORT: <what changed, checks, findings, concerns>
```

Keep each brief self-contained and bounded. For every high-risk delegation, including re-review, create/read the task checkpoint and that assignment's brief, then create a planned record with a local id, planned status, requested metadata and observed values `Unverified`. Use a new record for each assignment. Verify the exact checkpoint, brief and record paths exist through a tool before native spawn. After spawn, update that planned record with the actual returned id and status; do not create it retroactively. If runtime permissions prohibit spawning, record review as BLOCKED. For lower-risk delegations, write the brief and agent record before spawning. Include selected skills and read their instructions before assigning them. Include only context the worker cannot read from the project. Do not paste conversation history, credentials, or customer data.

Keep an agent record with duty, skills, vendor, parent/id, requested and observed model/effort/permission, status, and evidence. A requested permission mode is not proof of enforcement; record what the runtime actually exposes, or `Unverified`.

Reviewers must be fresh and independent of implementation and prior review. Use `fork_turns=none` where supported, and never resume a reviewer. If fresh context is unsupported, record that limitation and do not describe the review as independent. Run relevant checks before completion and state what ran and what remains unrun.

Assess whether independent review is needed from risk: external contracts or money, data writes, auth/permissions, install/filesystem boundaries, integrations, and concurrency require it. Tiny equivalent internal changes may be self-verified with a reason. Implementers update affected component documentation; reviewers check code/document consistency. Internal-only changes need no irrelevant docs.
