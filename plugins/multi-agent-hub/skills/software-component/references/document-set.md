# Document Set — เอกสารอะไรมีบ้าง อยู่ที่ไหน และอะไรต้องเปลี่ยนพร้อมกัน

ชุดเอกสารโปรเจกต์ที่ครบถ้วน (path ทั้งหมดอิงจาก docs root ของโปรเจกต์ ซึ่ง project card อาจย้าย root ได้)
สร้างเฉพาะเอกสารที่งานนั้นแตะต้อง template อยู่ใน `templates/` และทุก template เป็น placeholder เท่านั้น

```
{docs-root}/
├── Plan.md                                  plan-master.md
├── PLAN_{SERVICE}.md                        plan-service.md (รวม feature plan)
├── UI_SPEC.md                               ui-design-system.md            (ไม่บังคับ)
├── Workflow/{Process}.md                    workflow.md
├── docs/business/{NN}_{MODULE}.md           business-module.md             (ไม่บังคับ)
├── docs/contracts/{topic}.md                message-contract.md
├── DB/
│   ├── Data Dictionary/DATA_DICT.md + {NN}_{Module}.md     data-dictionary.md
│   └── ER Diagrams/ER_DIAGRAMS.md + {NN}_{Module}.md       er-diagram.md
├── Deployments/
│   ├── {service}/PRODUCTION_DEPLOYMENT.md   release/production-readiness.md
│   └── {service}/v{X.Y.Z}/                  release/release.md, manifest.md, checklist.md,
│                                             rollback-plan.md, test-result.md, security-review.md
└── app/
    ├── {http-api}/                          (HTTP service แบบแยกตาม endpoint)
    │   ├── API-ENDPOINTS.md                 api-endpoints.md
    │   ├── USER-MATRIX.md                   user-matrix.md
    │   ├── api-spec/{group}/{METHOD}-{NAME}.md        backend-standard.md
    │   ├── api-spec/{group}/SCHEMA.md                 table-schema.md
    │   └── api-flow-chart/{group}/{METHOD}-{NAME}.md  backend-standard.md
    ├── {small-http-service}/                (endpoint น้อย, external API, webhook receiver)
    │   ├── api-spec/{SERVICE}.md            program-spec.md
    │   └── api-flow-chart/{METHOD}-{NAME}.md
    ├── {worker-service}/                    (consumer / producer / poller / scheduler)
    │   ├── {service}-spec/{service}-spec.md            service-spec.md
    │   └── {service}-flowchart/{service}-flowchart.md  service-flowchart.md
    ├── {web-app}/
    │   ├── SWC-Overview.md                  swc-overview.md
    │   ├── Testing-Overview.md              testing-overview.md
    │   ├── SWC/{module}/solution-overview.md   solution-overview.md
    │   ├── SWC/{module}/traceability.md        traceability.md
    │   ├── SWC/{module}/shared.md              shared.md
    │   ├── SWC/{module}/page-{page}-{spec|diagram|wireframe}.md   page-spec.md, page-diagram.md,
    │   │                                        page-wireframe.md (templates/)
    │   ├── SWC/{module}/{component}-{spec|diagram}.md     frontend-standard.md section 8
    │   └── Testing/{module}-{page}-testing.md          page-testing.md
    └── {mobile-app}/                        (โครงเดียวกับ {web-app}; คำศัพท์: mobile-standard.md)
        ├── SWC-Overview.md, Testing-Overview.md, SWC/{module}/...   เหมือน {web-app}
        └── {component}-spec/{component}-spec.md   service-spec.md แบบ on-device
                                                   (listener, sync job, background worker; ไม่มี broker)
```

**ไม่มี backend** (mobile app, desktop tool, static site): ตัด `{http-api}`, `API-ENDPOINTS`, `USER-MATRIX`,
message contract และรายการ `Deployments/` ของ server ออก `solution-overview.md` และ `traceability.md` อยู่ใน
`SWC/{module}/` ของ app ที่เป็นเจ้าของ module เสมอ (ไม่แยก FE/BE; มี SWC folder เดียว) data access ทำหน้าที่แทน API

หมายเลข module `{NN}` ใช้ร่วมกันระหว่างไฟล์ business module, data dictionary และ ER ใช้วันที่แบบ ISO
(YYYY-MM-DD) ทุกที่ ชื่อไฟล์สะกดตามด้านบนทุกตัวอักษร (`PLAN_` ตัวพิมพ์ใหญ่, `API-ENDPOINTS`) เพราะลิงก์ใน server ส่วนใหญ่แยกตัวพิมพ์เล็ก/ใหญ่

## Update together (งานเดียวกัน commit เดียวกัน)

| When this changes | Also update |
|---|---|
| endpoint (เพิ่ม / แก้ / ลบ) | api-spec + api-flow-chart ของมัน, แถวใน API-ENDPOINTS.md, แถวใน USER-MATRIX.md |
| page หรือ component | spec, diagram, header ของ wireframe (Last Updated), แถวใน SWC-Overview |
| test ของ page | `Testing/{module}-{page}-testing.md` แล้วจึงแถวใน Testing-Overview |
| พฤติกรรมของ worker | service-spec และ service-flowchart (version และวันที่เดียวกัน); message contract ถ้า payload เปลี่ยน |
| table หรือ column | migration + table-schema (ถ้า feature มี) แล้ว regenerate data dictionary + ER + index ทั้งสอง |
| business process | ไฟล์ Workflow ไฟล์เดียว; page และ endpoint ลิงก์ไปเท่านั้น |
| release | โฟลเดอร์ใหม่ `Deployments/{service}/v{X.Y.Z}/`; plan คัดลอกสถานะ ไม่ติดตามซ้ำสองที่ |

## Rules (เรียนรู้จากชุดเอกสารจริง)

- ลิงก์เป็น relative เสมอ ห้ามใช้ absolute path และห้ามใช้ path จากเครื่องของคนอื่น
- หนึ่งข้อเท็จจริงมีที่เดียว: ห้ามมี workflow, schema หรือ screen flow ซ้ำในอีกรูปแบบหนึ่ง ไฟล์ที่ถูกแทนที่ย้ายไป
  `_deprecated_v{n}/` หรือมี "Superseded by ..." ไว้บนสุด
- เซลล์ใน tracker สั้นๆ (ไอคอนสถานะ + ไม่กี่คำ) คำอธิบาย ตัวเลข และบทเรียนไปอยู่ในเอกสารที่ลิงก์
- ประวัติไปอยู่ใน section Change Log ไม่ใช่บรรทัด "Previous:" ซ้อนใน header หรือประโยคยาวใน "Last Updated"
- Plan เก็บ task; spec เก็บสิ่งที่สร้างแล้ว; Deployments เก็บสิ่งที่ส่งมอบแล้ว ห้ามปนทั้งสามอย่างในไฟล์เดียว
- ตัวเลข วันที่ และคำว่า "passed" มาจากการรันจริงเท่านั้น มิฉะนั้นใช้ ❌ / 📋 พร้อมเหตุผล
- Mermaid (กฎข้อเดียว): ใช้ syntax ของ Mermaid ปัจจุบัน (11.x) สำหรับทุก diagram: `flowchart TD`/`flowchart LR`,
  `sequenceDiagram`, `stateDiagram-v2`, `erDiagram` (ชื่อมี underscore เช่น TABLE_A, VARCHAR_255 ใช้ได้)
  ASCII ใช้กับ wireframe และ layout หน้าจอเท่านั้น ทุก template ทำตามกฎนี้
- ภาษา: เขียนเอกสารเป็นภาษาไทย; heading, ชื่อคอลัมน์ในตาราง, ค่า status, ศัพท์เทคนิค, identifier ในโค้ด
  และชื่อไฟล์/path คงเป็นภาษาอังกฤษตาม reference set

## Headers (นโยบายเดียว; ไฟล์อื่นชี้มาที่นี่)

| Document type | Header |
|---|---|
| SWC specs ที่ไม่ใช่ versioned (page / component / endpoint spec, shared, solution-overview, diagram) | **Last Updated** และเพิ่ม **Status**, **Evidence** (Current / Proposed / POC / Verified), **REQ Refs**, **Owner** เมื่อโปรเจกต์ติดตาม REQ/AC (project card ระบุ หรือมีรหัส REQ/AC อยู่แล้ว); รูปแบบอยู่ใน `swc-central.md` section 4 |
| Wireframe | **Last Updated**, **Status** (Draft / In Review / Approved / Implemented), **Version**, **Designer**, **Reviewed by**, **Figma** (ใช้ — เมื่อไม่มี) เสมอ เพราะเป็นเอกสารออกแบบ |
| Plans (รวม feature plan: ใช้ **Feature**, **Status** Draft / Approved / Done, **Last Updated**, **Refs** แทน Version + Date), worker/program specs, data dictionary, ER, releases (ชนิดที่มี version) | **Version** + **Date** (worker/program spec เพิ่ม Status/Evidence/REQ Refs/Owner เมื่อติดตาม REQ/AC) |
| Workflow, tracker (SWC-Overview, Testing-Overview, API-ENDPOINTS, USER-MATRIX), index, traceability, work log | **Last Updated** อย่างเดียว |

เอกสารอื่นเพิ่ม Status/Evidence ได้เมื่อมีประโยชน์ แต่ไม่บังคับ
