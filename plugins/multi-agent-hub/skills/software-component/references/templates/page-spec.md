# Page Spec: `/{path}`

**Module**: {Module Name} (Phase {N})
**Path**: `/{path}`
**Layout**: `layout.vue`
**Auth Required**: Full Token
<!-- validate-skills: example -->
**Ref Diagram**: [page-{name}-diagram.md](./page-{name}-diagram.md)
**Ref Shared**: [shared.md](./shared.md)
**Last Updated**: YYYY-MM-DD
<!-- เมื่อติดตาม REQ/AC ให้เพิ่ม: -->
**Status**: Draft | In Review | Approved | Implemented (when REQ/AC are tracked)
**Evidence**: Current | Proposed | POC | Verified (when REQ/AC are tracked)
**REQ Refs**: REQ-nn (when REQ/AC are tracked)
**Owner**: @name หรือ — (when REQ/AC are tracked)

---

## 1. UI Conditions

| Condition | แสดง/ซ่อน |
|---|---|
| กำลัง submit | ปุ่ม disabled + spinner |
| Error `ERROR_CODE` | แสดง inline error |

---

## 2. Click Flow

```
1. User กระทำอะไร
2. FE: Zod validate
   → ถ้า error: แสดง inline validation
3. FE: METHOD /api/path {body}
4. Response:
   a. Success → ทำอะไร
   b. ERROR_CODE → แสดงอะไร
```

---

## 3. API

| Action | Method | Endpoint | Request Body |
|---|---|---|---|
| Action name | POST | `/api/path` | `{field}` |

**Error Codes:**
| Code | HTTP | UI Action |
|---|---|---|
| `ERROR_CODE` | 4xx | UI action |

---

## 4. Screen Workflow

```
┌─────────────────────────────────────────────┐
│  [Screen: /path]  เข้าหน้า                  │
│  → GET /api/resource                        │
│                                              │
│  ⏳ Loading                                  │
│     └─ แสดง Skeleton Loader                 │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Response                                   │
│  ├─ 200 + มีข้อมูล  → แสดง content         │
│  └─ 401             → [/login]              │
└─────────────────────────────────────────────┘
```

---

## 5. i18n Keys (ถ้าหน้ามีข้อความที่แปล)

| Key | TH | EN | Used in |
|---|---|---|---|
| `{module.page.key}` | {ข้อความไทย} | {English text} | {component / section} |

---

## 6. Implementation Status (YYYY-MM-DD)

| Feature | Status | Note |
|---|---|---|
| {feature} | ✅ / ⚠️ / ❌ | {ส่วนที่ยังไม่ตรง spec, ไฟล์ที่เกี่ยวข้อง} |

---

## 7. Open Items

1. {งานค้าง / คำถามที่ยังไม่ปิด, เจ้าของ, เงื่อนไขที่ทำให้ปิดได้}

---

## 8. Acceptance Criteria

| AC | REQ | Given / When / Then | Evidence |
|---|---|---|---|
| AC-{nn}-{mm} | REQ-{nn} | {one checkable behavior} | Proposed |

## 9. Test Cases

| ID | Level | Ref | Scenario | Input / Setup | Expected | Real or Mock | Status |
|---|---|---|---|---|---|---|---|
| UT-{nn}-{mm} | Unit | AC-{nn}-{mm} | {scenario} | {setup} | {expected} | Mock | Not written |

## 10. Manual Notes

`not needed` + เหตุผล หรือหนึ่ง block `MAN-{nn}` ตาม swc-central.md section 9 งาน planning-only (Evidence Proposed):
เขียนทุก block เป็น "not publishable" เพราะคู่มือมาจากพฤติกรรมที่เป็น Current หรือ Verified เท่านั้น

## 11. Change Log

| Date | Code | Change | Reason | Impact | By |
|---|---|---|---|---|---|
