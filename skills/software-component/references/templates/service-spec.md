# {service-name} — Service Specification

| Version | Date | Plan | Flowchart | Message contract |
|---|---|---|---|---|
| {X.Y.Z} | YYYY-MM-DD | [PLAN_{SERVICE}.md]({relative}) | [{service}-flowchart.md](../{service}-flowchart/{service}-flowchart.md) | [{contract}.md]({relative}) |

> **v{X.Y} changed**: {สิ่งที่เปลี่ยนจากเวอร์ชันก่อน; ลบออกเมื่อไม่จำเป็นแล้ว ประวัติไปอยู่ใน Change Log}

ใช้กับ service ที่ไม่มี public HTTP API: queue/stream consumer, producer, poller, scheduler
Path: `<service>/<service>-spec/<service>-spec.md` ไฟล์นี้และ flowchart ต้องอยู่ใน commit เดียวกัน

**Required**: 1 Scope, 5 Process Flow, 8 Data Interactions (ถ้ามี), 12 Error Handling, 15 Known Gaps และ section
ที่เพิ่มท้ายไฟล์ (AC, Test Cases, Usage Notes, Change Log) **Optional (ตัด heading ออก หรือเขียน
`not applicable` + เหตุผล)**: 3 Configuration, 4 Broker, 6 Downstream, 7 Retry, 9 Status Lifecycle, 10 Jobs,
11 HTTP Endpoints, 13 Logging, 14 Graceful Shutdown, 16 Data Protection (บังคับเมื่อจัดการข้อมูลส่วนบุคคลหรือการเงิน)

**แบบ On-device / in-process** (component ที่ทำงานในแอปมือถือ ไม่มี broker หรือ server): ตัด 4 และ 11;
แทน 3 ด้วย settings หรือ build flag ของแอป; แทน 6 ด้วย OS/framework API ที่เรียก; แทน 7 ด้วยกฎ retry หรือ
re-subscribe; แทน 14 ด้วย lifecycle event (start, stop, rebind, process death) Message contract: not applicable

## 1. Scope

**Does**
- {responsibility}

**Does not do** (and where it is done)

| Item | Where it is done |
|---|---|
| {work that looks like it belongs here} | {other service / job} |

## 2. Folder Structure

```
{service}/
├── {entry point}
├── {config}
└── {modules}
```

## 3. Configuration

| Variable | Description | Default | Required |
|---|---|---|---|
| `{ENV_VAR}` | {meaning} | `{default}` | Yes / No |

Secret ระบุเฉพาะชื่อ ห้ามใส่ค่าในเอกสาร

## 4. Broker Configuration (consumer and/or producer)

| Key | Value | Why |
|---|---|---|
| Topic / queue | `{topic}` | {...} |
| Group / subscription | `{group}` | {...} |
| Commit mode | {manual / auto} | {...} |
| Offset reset / start position | {earliest / latest} | {...} |
| Poll interval / batch size | {n} | {...} |

## 5. Process Flow

```
1. Receive / claim {message | batch of records}
2. Parse headers, check schema version and {channel}
   → invalid: {poison-pill action, e.g. send to DLQ and commit}
3. Idempotency check by {key} → already processed: skip and commit
4. {main work}
5. Update status {table.column}: {from} → {to}
6. Commit / acknowledge
```

## 6. Downstream Integration

| Target | Call | Required params / headers | Timeout |
|---|---|---|---|
| {provider / service} | {operation} | {params} | {ms} |

## 7. Retry Policy

| Attempt | Backoff | Action |
|---|---|---|
| 1..{n} | {delay} | retry |
| > {n} | — | send to `{dlq-topic}`, mark `{FAILED}` |

## 8. Data Interactions

| Table | Operation | Columns / condition | Note |
|---|---|---|---|
| `{table}` | SELECT / UPDATE / INSERT | {...} | {locking, e.g. row lock with skip-locked} |

## 9. Status Lifecycle

| Transition | Trigger | Owner (this service / other) |
|---|---|---|
| `{FROM}` → `{TO}` | {event} | {...} |

## 10. Scheduled / Maintenance Jobs (if any)

| Job | Interval (env) | Selects | Action | No-op when | Safety |
|---|---|---|---|---|---|
| {name} | `{ENV_VAR}` = {value} | {records chosen, e.g. stuck longer than threshold} | {reset / clean / retry} | {nothing matches} | {threshold, batch cap, lock} |

## 11. HTTP Endpoints (operational only)

| Method | Path | Returns |
|---|---|---|
| GET | `/healthz` | process alive |
| GET | `/readyz` | dependencies reachable ({list}) |

## 12. Error Handling

| Scenario | Action |
|---|---|
| {dependency down} | {retry / pause / alert} |

## 13. Logging and Observability

- Must log: {id, การเปลี่ยน status, ลำดับ attempt, ระยะเวลา}
- Must NOT log: {เนื้อหา message, ข้อมูลส่วนบุคคล, secret}
- Metrics / alerts: {lag threshold, error rate, ขนาด DLQ}

## 14. Graceful Shutdown

1. Stop taking new {messages | records}
2. Finish in-flight work within {timeout}
3. Commit / release locks, close connections

## 15. Known Gaps

| Gap | Status | Env / flag | Code path exists? |
|---|---|---|---|
| {not implemented yet} | ⚠️ NOT IMPL | `{ENV_VAR}` | Yes / No |

## 16. Data Protection

- Data handled: {ชนิดข้อมูล เช่น ส่วนบุคคล / การเงิน / device identifier}
- Storage and encryption: {เก็บที่ไหน, at rest / in transit}
- Retention and deletion: {ระยะเวลา, ใครลบ}
- Backup / export: {รวมหรือไม่ เพราะอะไร}
- Review needed: {policy, store หรือ legal review, เจ้าของ}

## 17. Acceptance Criteria

| AC | REQ | Given / When / Then | Evidence |
|---|---|---|---|
| AC-{nn}-{mm} | REQ-{nn} | {one checkable behavior} | Proposed |

## 18. Test Cases

| ID | Level | Ref | Scenario | Input / Setup | Expected | Real or Mock | Status |
|---|---|---|---|---|---|---|---|
| UT-{nn}-{mm} | Unit | AC-{nn}-{mm} | {scenario} | {setup} | {expected} | Mock | Not written |

## 19. Usage Notes

`not needed` + เหตุผล หรือหมายเหตุสำหรับผู้เรียกหรือผู้พึ่งพา service นี้

## 20. Change Log

| Date | Code | Change | Reason | Impact | By |
|---|---|---|---|---|---|

**Last Updated**: YYYY-MM-DD
