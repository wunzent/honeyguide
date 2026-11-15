---
name: surgical-patch
description: "Use when fixing a bug whose cause is already known, or making a small behavior change, at the narrowest responsible layer, with regression proof and preserved surrounding behavior."
---

# Surgical patch

Reproduce failure first when economical; otherwise capture strongest available evidence.

- Trace symptom to responsible mechanism.
- Change narrowest layer that owns incorrect behavior.
- Preserve unrelated behavior and user changes.
- Avoid cleanup, renaming, and abstraction outside fix.
- Add only regression proof relevant to task.

Run focused proof plus nearest affected gate. Stop when failure is fixed and regression proof passes.
