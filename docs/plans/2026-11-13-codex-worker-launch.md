# Codex worker launch plan

1. tools/hub.py: isolate only Windows standalone Codex child environment; remove CODEX_WINDOWS_REGISTERED_CORE from child copy at Popen boundary, retaining all sandbox/approval arguments and other environment values.
2. tests/test_hub.py: targeted regression for Codex vs Claude child marker, unchanged parent, security-variable retention, and resumed worker boundary if existing test seam permits; use existing fake CLI/fixture structure.
3. Run focused launcher/route/resume tests, then full tests once; distinguish environmental restrictions.
4. Review actual diff with a fresh independent Codex reviewer. Address correctness findings via implementer, not orchestrator.
5. Run actual patched delegate from inherited Desktop environment with Claude absent from child PATH: positive read, negative read-only sentinel write, positive workspace-write sentinel. Capture exact command outcomes and observed runtime model/effort.
6. Deliver patch, evidence, agent table, remaining limits. Preserve checkpoint and failure history. No unrelated discovery diagnostics or source cleanup.
