# Message Contract — `{topic / queue name}`

| Version | Date | Producer(s) | Consumer(s) |
|---|---|---|---|
| {schema version} | YYYY-MM-DD | {service} | {service}, {service} |

ที่เดียวสำหรับ async interface ระหว่าง service; worker spec ลิงก์มาที่นี่ ไม่เขียนซ้ำ
Path: `docs/contracts/{topic}.md` (หรือโฟลเดอร์ที่ project card ระบุ)

## 1. Purpose

{หนึ่งย่อหน้า: message นี้ส่ง event หรือ command อะไร และเพราะอะไร}

## 2. Transport

| Item | Value |
|---|---|
| Broker | {Kafka / queue / ...} |
| Topic / queue | `{name}` |
| Partition / ordering key | `{key}`: {รับประกันลำดับแบบไหน} |
| Retention | {duration} |
| DLQ | `{dlq name}` |

## 3. Headers

| Header | Type | Required | Meaning |
|---|---|---|---|
| `schema-version` | string | Yes | {...} |
| `{idempotency-key}` | string | Yes | {ไม่ซ้ำต่อหนึ่ง message เชิงตรรกะ} |

## 4. Payload

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `{field}` | {type} | Yes / No | {...} | `{placeholder}` |

```json
{ "{field}": "{placeholder}" }
```

## 5. Guarantees

- Delivery: {at-least-once / ...}; consumer ต้อง idempotent ตาม `{key}`
- Ordering: {per key / none}
- Size limit: {bytes}

## 6. Versioning

| Version | Change | Compatible? | Consumers updated |
|---|---|---|---|
| {v} | {change} | Yes / No | {list} |

breaking change ต้องใช้ค่า version ใหม่ และ consumer ทุกตัวต้องอัปเดตก่อน producer สลับไปใช้

## 7. Error and Poison Messages

| Case | Consumer action |
|---|---|
| Unknown schema version | {DLQ + alert} |
| Invalid payload | {DLQ} |
