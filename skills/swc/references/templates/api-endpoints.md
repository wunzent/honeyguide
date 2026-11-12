# {System} API Endpoints

อ้างอิงจาก: {plan / requirement document path}
มาตรฐานการเขียน: `references/backend-standard.md` (skill `swc`)

เอกสารนี้เป็น endpoint inventory และ document tracker กลางของ `{api-repo}`: ทุก endpoint ต้องมีแถวที่นี่ และสถานะของ
API Spec / API Flow Chart / OpenAPI / Test / Dev ตรงกับของจริง (อัปเดตในงานเดียวกับที่เปลี่ยน endpoint)

## Frontend Usage Audit ({YYYY-MM-DD})

ตรวจการเรียกใช้จริงเทียบกับ `{frontend-repo}` (วิธีตรวจ: {เช่น สแกน API client ทั้ง repo}):

- **⚠️ DEPRECATED** = frontend ไม่เรียกใช้แล้ว (ถูกแทนหรือเลิกใช้)
- **ℹ️ คงไว้** = frontend ไม่เรียก แต่มี client อื่นใช้โดยตั้งใจ (ระบุว่าใคร)
- **🆕** = frontend ใช้จริงแต่เดิมเอกสารยังไม่มี

## Status Legend

| Icon | Status | Meaning |
| --- | --- | --- |
| ✅ | `Completed` | เสร็จสมบูรณ์ / พร้อมใช้งาน |
| 📋 | `In Progress` | กำลังดำเนินการ |
| ❌ | `Not Started` | ยังไม่ได้เริ่ม |
| ⚠️ | `Partial` | Spec พร้อมแต่ implementation ยังไม่ตรง Spec |
| `-` | N/A | ไม่มี / ไม่เกี่ยวข้อง |

## Column Legend

| Column | ความหมาย |
| --- | --- |
| **API Spec** | ลิงก์ไปไฟล์ `api-spec/{group}/{METHOD}-{NAME}.md` |
| **API Flow Chart** | ลิงก์ไปไฟล์ `api-flow-chart/{group}/{METHOD}-{NAME}.md` |
| **OpenAPI** | สถานะการเพิ่ม endpoint เข้า OpenAPI / Swagger spec |
| **Test** | สถานะ functional / integration tests ตามมาตรฐานการทดสอบของ repo |
| **Dev API** | สถานะการพัฒนา (route / controller / service / data access ครบ) |

## {Group name}

{หนึ่งประโยค: กลุ่มนี้ทำอะไร, tenant-scoped หรือไม่, auth แบบไหน}

> **สถานะ**: {สรุปสั้น ๆ ของกลุ่ม: อะไรครบ อะไรค้าง, migration รันที่ไหนแล้ว}

| Method | Path | Meaning | API Spec | API Flow Chart | OpenAPI | Test | Dev API |
| --- | --- | --- | --- | --- | --- | --- | --- |
| {GET} | `/api/{resource}` | {ทำอะไร} | [{GET-RESOURCE}](./api-spec/{group}/{GET-RESOURCE}.md) | [{GET-RESOURCE}](./api-flow-chart/{group}/{GET-RESOURCE}.md) | ❌ | ❌ | ❌ |

## Summary

| Group | Endpoints | API Spec | Flow Chart | OpenAPI | Test | Dev API |
| --- | --- | --- | --- | --- | --- | --- |
| {group} | {n} | {done}/{n} | {done}/{n} | {done}/{n} | {done}/{n} | {done}/{n} |
| **Total** | **{n}** | | | | | |
