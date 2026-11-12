# Message Contract — `{topic / queue name}`

| Version | Date | Producer(s) | Consumer(s) |
|---|---|---|---|
| {schema version} | YYYY-MM-DD | {service} | {service}, {service} |

The single place for an async interface between services. Worker specs link here instead of repeating it.
Path: `docs/contracts/{topic}.md` (or the folder the project card names).

## 1. Purpose

{one paragraph: what event or command this carries and why}

## 2. Transport

| Item | Value |
|---|---|
| Broker | {Kafka / queue / ...} |
| Topic / queue | `{name}` |
| Partition / ordering key | `{key}`: {what ordering this guarantees} |
| Retention | {duration} |
| DLQ | `{dlq name}` |

## 3. Headers

| Header | Type | Required | Meaning |
|---|---|---|---|
| `schema-version` | string | Yes | {...} |
| `{idempotency-key}` | string | Yes | {unique per logical message} |

## 4. Payload

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `{field}` | {type} | Yes / No | {...} | `{placeholder}` |

```json
{ "{field}": "{placeholder}" }
```

## 5. Guarantees

- Delivery: {at-least-once / ...}; consumers must be idempotent on `{key}`.
- Ordering: {per key / none}.
- Size limit: {bytes}.

## 6. Versioning

| Version | Change | Compatible? | Consumers updated |
|---|---|---|---|
| {v} | {change} | Yes / No | {list} |

A breaking change needs a new version value and every consumer updated before producers switch.

## 7. Error and Poison Messages

| Case | Consumer action |
|---|---|
| Unknown schema version | {DLQ + alert} |
| Invalid payload | {DLQ} |
