# Rollback Plan — {service} v{X.Y.Z}

## 1. Triggers

rollback เมื่อข้อใดข้อหนึ่งเป็นจริงหลัง deploy:
- {error rate เกิน n% นาน m นาที}
- {flow สำคัญใช้งานไม่ได้: ...}
- {ตรวจความถูกต้องของข้อมูลไม่ผ่าน}

## 2. Decision Matrix

| Situation | Action | Who decides |
|---|---|---|
| App พัง, schema ไม่เปลี่ยน | deploy image เดิมใหม่ | {role} |
| App พัง, migration ที่ย้อนกลับได้รันไปแล้ว | image เดิม + down migration | {role} |
| migration ที่ย้อนกลับไม่ได้รันไปแล้ว | แก้ไปข้างหน้า; restore จาก backup เมื่อได้รับ {approval} เท่านั้น | {role} |

## 3. Steps (in order)

1. {ประกาศ rollback}
2. {deploy `{previous image:tag}` ใหม่}
3. {รัน `{rollback.sql}` / down migration} (ประมาณ {นาที})
4. {คืนค่า config / flag}

## 4. Verify After Rollback

- [ ] {health check}
- [ ] {smoke flow}
- [ ] {ตรวจข้อมูล}

## 5. Time Estimates

| Step | Estimate |
|---|---|
| Redeploy | {min} |
| Database rollback | {min} |
| Total | {min} |
