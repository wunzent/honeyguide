# SWC and Solution Planning Standards

เอกสารในโฟลเดอร์นี้เป็นมาตรฐานกลางสำหรับวางแผน solution และจัดทำ Software Component Documentation (SWC) ของทุกระบบที่ Hub ดูแล

มาตรฐานเหล่านี้กำหนดโครงสร้างเอกสารและ diagram แต่ข้อมูลของระบบจริงต้องมาจาก source code, tests, API contracts, requirements และเอกสารของ target project เสมอ

## เลือกมาตรฐาน

| งาน | มาตรฐานที่ใช้ |
|---|---|
| Frontend page, module, component, composable, UI flow หรือ wireframe | [Frontend SWC Standard](frontend-standard.md) |
| Backend endpoint, validation, access control, data effect หรือ API flow | [Backend API and Flow Standard](backend-standard.md) |
| Full-stack หรือ cross-system flow | ใช้ทั้ง Frontend และ Backend Standard แล้วเชื่อมด้วย REQ/AC และ API contract เดียวกัน |
| ติดตามสถานะเอกสารและ implementation ของ frontend | [SWC Overview template](templates/swc-overview.md) |
| ติดตามการทดสอบของ frontend (ภาพรวม + รายหน้า) | [Testing Overview](templates/testing-overview.md), [Page testing](templates/page-testing.md) |
| รายการ endpoint และสิทธิ์ของ role ฝั่ง backend | [API Endpoints](templates/api-endpoints.md), [User Matrix](templates/user-matrix.md) |

## ใช้ร่วมกับ Requirement-Driven Delivery

สำหรับงานที่ไม่ใช่ tiny task ให้ใช้ลำดับนี้:

```text
Request
→ Requirements / REQ / AC
→ Current-system discovery
→ Shared solution and API contract
→ Documentation review / approval
→ Split frontend and backend handoff
→ Frontend SWC / Backend SWC
→ Implementation by each team
→ Tests
→ Verification evidence
```

เอกสาร requirement, solution และ API contract เป็นข้อมูลกลางที่ทั้งสองฝั่งต้องเห็นตรงกัน เมื่อเอกสารกลางครบและผ่านการทบทวนแล้วจึงแยกงานดังนี้:

- ทีม Frontend ใช้ [Frontend SWC Standard](frontend-standard.md) เพื่อแตก page, component, state, validation, UI flow และ API integration
- ทีม Backend ใช้ [Backend API and Flow Standard](backend-standard.md) เพื่อแตก endpoint, access control, validation, data effect, external service และ API flow
- SWC ของทั้งสองฝั่งต้องอ้างอิง REQ/AC และ API contract ชุดเดียวกัน ห้ามเปลี่ยน business behavior แยกกันโดยไม่ย้อนกลับไปอัปเดตเอกสารกลาง

งาน planning-only สามารถหยุดหลังเอกสารกลางหรือ SWC ตาม scope ที่ได้รับ แต่ต้องระบุ open questions, assumptions และส่วนที่ยังไม่ได้ตรวจสอบ

## Source Of Truth

ใช้หลักฐานตามลำดับที่เหมาะกับคำถาม:

1. current source, tests และ executable contracts สำหรับพฤติกรรมปัจจุบัน
2. approved requirements และ acceptance criteria สำหรับพฤติกรรมที่ต้องการ
3. API/schema/interface contracts
4. target-project documentation และ design references
5. มาตรฐานในโฟลเดอร์นี้สำหรับรูปแบบและความครบถ้วนของเอกสาร

ถ้าหลักฐานขัดกัน ห้ามเลือกเองโดยไม่บันทึก ให้ระบุ conflict หรือสร้าง Open Question

## Project Adaptation

- แทน placeholder เช่น `{project}`, `{module}` และ `{path}` ด้วยข้อมูลจริง
- ใช้ชื่อ framework, validator, identity provider, data store และ service ตาม target project
- เก็บเอกสารที่สร้างขึ้นใน target project ตาม root/nested `AGENTS.md` และ convention ของโปรเจกต์นั้น
- ใช้ UI component, design system, API shape และ business terminology ของ target project
- ตัวอย่างในมาตรฐานเป็นโครงสร้างอ้างอิง ไม่ใช่ข้อเท็จจริงของทุกระบบ

## Diagram Rules

- Frontend SWC ที่ใช้ Mermaid v8.8.0 ต้องทำตาม compatibility rules ใน Frontend Standard
- Backend diagram ต้องทำตาม renderer/version ของเอกสารปลายทาง
- เอกสาร full-stack ต้องใช้ syntax ที่ renderer ของปลายทางรองรับ ห้ามผสม syntax โดยไม่ตรวจ render
- Flowchart อธิบาย decision/state flow; sequence diagram อธิบาย interaction ระหว่าง actors, layers และ services
- Diagram ต้องตรงกับ spec และ actual/approved flow เสมอ

## Completion Check

ก่อนส่งเอกสาร ให้ตรวจว่า:

- requirements และ acceptance criteria เชื่อมไปยัง solution ได้
- frontend/backend spec ใช้ contract เดียวกัน
- flow และ sequence diagram ครอบคลุม success, failure และ side effects ที่สำคัญ
- assumptions และ open questions ระบุชัด
- เอกสารไม่อ้าง technology หรือ business rule ที่ target project ไม่ได้ใช้
- implementation/test/evidence เชื่อมกลับไปยัง REQ/AC เมื่ออยู่ใน scope
