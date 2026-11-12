# Security Review — {service} ({YYYY-MM-DD})

File name: `security-review-YYYYMMDD.md` in the release folder it reviewed.

| Field | Value |
|---|---|
| Target | {service / repo} |
| Release | v{X.Y.Z} |
| Review date | YYYY-MM-DD |
| Reviewer | {name / agent + model} |
| Commit | `{sha}` |
| Frameworks | {stack} |
| Method | {manual review / tools used / scope of files} |

## Executive Summary

{two or three sentences: overall risk, what must be fixed before release}

| Severity | Count | Fixed |
|---|---|---|
| 🔴 Critical | {n} | {n} |
| 🟠 High | {n} | {n} |
| 🟡 Medium | {n} | {n} |
| 🔵 Low | {n} | {n} |
| ⚪ Info | {n} | {n} |

**Top priorities**: {F-nn, F-nn}

## Remediation Log

| Date | Finding | Status | Reference |
|---|---|---|---|
| YYYY-MM-DD | F-{nn} | ✅ FIXED / ⏳ Open / ➖ Accepted risk | {commit / ticket} |

## OWASP Mapping

| ID | Finding | Severity | OWASP |
|---|---|---|---|
| F-{nn} | {title} | 🟠 High | {A01 Broken Access Control} |

## Findings

### 🟠 F-{nn} — {title}

- **Where**: `{file}:{line}` (relative path)
- **Issue**: {what is wrong}
- **Impact**: {what an attacker could do}
- **Fix**: {recommended change}
- **Status**: {open / ✅ FIXED YYYY-MM-DD in `{sha}`}

Never paste secrets, tokens or personal data into a finding; write `***`.

## Controls Done Well

- {...}

## Roadmap

| Item | Priority | Target |
|---|---|---|

## Scope and Limitations / Deferred Checks

- {what was not reviewed and why}

Web front-ends use `W-{nn}` instead of `F-{nn}`.
