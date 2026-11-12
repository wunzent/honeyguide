# Deploy Checklist — {service} v{X.Y.Z}

ติ๊กเฉพาะสิ่งที่ทำจริง; ระบุผู้ทำและเวลาไว้ข้างแต่ละกลุ่ม

## Pre-deploy ({name}, YYYY-MM-DD HH:MM)

- [ ] test ทั้งหมดใน test-result.md ผ่านบน commit ที่จะ release
- [ ] ตั้งค่า environment variable ตาม manifest.md §4 ใน {environment} แล้ว
- [ ] สำรองฐานข้อมูลแล้ว: {ที่ไหน}
- [ ] ตรวจ migration แล้ว; อันที่ย้อนกลับไม่ได้ระบุไว้ใน rollback-plan.md
- [ ] ผู้ deploy อ่าน rollback plan แล้ว
- [ ] แจ้งช่วงเวลา deploy ให้ผู้เกี่ยวข้องแล้ว

## Deploy

- [ ] รัน migration ({ลำดับ})
- [ ] deploy {image:tag}
- [ ] {feature flag / config switch}

## Post-deploy Verification

- [ ] health / readiness endpoint ปกติ
- [ ] smoke test: {flow สำคัญ}
- [ ] log และ error rate ปกติเป็นเวลา {นาที}
- [ ] {jobs / consumers} ทำงานอยู่ lag ปกติ

## Rollback Readiness

- [ ] image เดิม `{image:tag}` ยังใช้ได้
- [ ] ผู้ตัดสินใจ rollback พร้อมติดต่อ: {ชื่อ}

## Sign-off

| Role | Name | Date | Result |
|---|---|---|---|
| Deployer | {name} | YYYY-MM-DD | ✅ / ❌ |
| Reviewer | {name} | YYYY-MM-DD | ✅ / ❌ |
