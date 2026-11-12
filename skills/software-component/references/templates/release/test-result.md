# Test Result — {service} v{X.Y.Z}

| Field | Value |
|---|---|
| Commit | `{sha}` |
| Date run | YYYY-MM-DD (real run) |
| Environment | {local / CI / staging} |
| Runner | {name / CI job link} |

## Automated Tests

| Suite | Command | Passed | Failed | Skipped |
|---|---|---|---|---|
| {unit} | `{command}` | {n} | {n} | {n} |

## Regression vs Previous Release

| Metric | v{previous} | v{X.Y.Z} | Note |
|---|---|---|---|
| Tests passing | {n} | {n} | |
| {latency / error rate} | {value} | {value} | |

## Manual Checks

| # | Check | Result | By |
|---|---|---|---|
| 1 | {flow} | ✅ / ❌ | {name} |

## Known Issues Shipped

| Issue | Impact | Ticket |
|---|---|---|

ตัวเลขมาจากการรันจริงเท่านั้น; suite ที่ไม่ได้รันให้ระบุ "not run" พร้อมเหตุผล
