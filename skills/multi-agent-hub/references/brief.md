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

Keep each brief self-contained and bounded. Include only context the worker cannot read from the project. Do not paste conversation history, credentials, or customer data.

Nontrivial work (any spawn or high risk) must have `.multi-agent-hub/<task>/` records written before the first spawn: checkpoint, this brief as `briefs/<id>.md`, and an agent record per spawn. Keep an agent record with duty, skills, vendor, parent/id, requested and observed model/effort/permission, status, and evidence. A requested permission mode is not proof of enforcement; record what the runtime actually exposes, or `Unverified`.

Implementer duty: implement only the assigned slice with the smallest correct diff. When purpose, interface, behaviour, dependencies or operations of a component change, update that component's documentation in the same task (`software-component` when available); internal, behaviour-preserving work changes no documentation. Self-review scope and error paths and run the assigned checks. After findings, append fix evidence to the same report.

Review is required before completion for high-risk changes (money, auth, security, data loss, public interface, cross-component or non-trivial multi-file logic); trivial work needs none. The reviewer is read-only and checks code-documentation consistency as well as correctness; findings go back to the implementer and the fix gets a fresh re-review of the fix diff. If no fresh reviewer is possible, report "not independently reviewed".

Reviewers must be fresh and independent of implementation and prior review. Use `fork_turns=none` where supported, and never resume a reviewer. If fresh context is unsupported, record that limitation and do not describe the review as independent. Run relevant checks before completion and state what ran and what remains unrun.
