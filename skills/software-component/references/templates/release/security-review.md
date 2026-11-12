# Security Review — {service} ({YYYY-MM-DD})

ชื่อไฟล์: `security-review-YYYYMMDD.md` ในโฟลเดอร์ release ที่ตรวจ

| Field | Value |
|---|---|
| Target | {service / repo} |
| Release | v{X.Y.Z} |
| Review date | YYYY-MM-DD |
| Reviewer | {name / agent + model} |
| Commit | `{sha}` |
| Frameworks | {stack} |
| Method | {manual review / เครื่องมือที่ใช้ / ขอบเขตไฟล์} |

## Executive Summary

{สองถึงสามประโยค: ความเสี่ยงโดยรวม และสิ่งที่ต้องแก้ก่อน release}

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
- **Issue**: {ปัญหาคืออะไร}
- **Impact**: {ผู้โจมตีทำอะไรได้}
- **Fix**: {วิธีแก้ที่แนะนำ}
- **Status**: {open / ✅ FIXED YYYY-MM-DD in `{sha}`}

ห้ามวาง secret, token หรือข้อมูลส่วนบุคคลใน finding; ให้เขียน `***`

## Controls Done Well

- {...}

## Roadmap

| Item | Priority | Target |
|---|---|---|

## Scope and Limitations / Deferred Checks

- {สิ่งที่ไม่ได้ตรวจและเหตุผล}

web front-end ใช้ `W-{nn}` แทน `F-{nn}`
