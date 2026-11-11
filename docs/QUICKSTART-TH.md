# เริ่มใช้ Multi-Agent Hub

เปิดโฟลเดอร์ hub เป็น working directory แล้วระบุเป้าหมาย ขอบเขตไฟล์ และวิธีตรวจรับงานให้ orchestrator
คำสั่งด้านล่างใช้ `python` ตามเอกสาร; บนเครื่องนี้ให้ใช้ `.venv\Scripts\python.exe` แทน `python`
แทน `<slug>` ด้วยชื่องาน และแทนข้อความ `...` ด้วยรายละเอียดจริงก่อนรัน

## เริ่มงานจาก Claude Code

เปิดโฟลเดอร์นี้ใน Claude Code (Desktop Code tab หรือ `claude`) แล้วบอกงานและขอบเขต
Claude อ่าน `CLAUDE.md` และ `AGENTS.md` แล้วสร้าง checkpoint เลือกทีม และบันทึก agent ตามงาน

```text
python tools/hub.py task new <slug> --objective "..." --scope "..." --orchestrator claude
```

## เริ่มงานจาก Codex

เปิดโฟลเดอร์นี้ใน Codex (Desktop หรือ `codex`) เป็น trusted project แล้วบอกงานและขอบเขต
Codex อ่าน `AGENTS.md` โดยตรง และใช้ขั้นตอนเดียวกัน; งานเล็กทำเองได้โดยไม่ต้องตั้งทีม

```text
python tools/hub.py task new <slug> --objective "..." --scope "..." --orchestrator codex
```

## ดูทีมและสถานะ agent

ดูตาราง role, vendor, model/effort ที่ร้องขอและที่ตรวจพบ รวมถึงสถานะด้วย:

```text
python tools/hub.py status <slug>
```

อ่านรายละเอียดใน `work/<slug>/agents/*.md` และผล worker ใน `work/<slug>/agents/<id>.last.md`
ค่าที่ CLI ไม่รายงานต้องแสดงเป็น `Unknown` หรือ `Unverified`

## ย้ายงานไปอีก vendor (checkpoint)

ให้ orchestrator อัปเดต `work/<slug>/CHECKPOINT.md` ด้วยงานที่เสร็จ งานค้าง หลักฐาน และขั้นตอนถัดไป

```text
python tools/hub.py checkpoint <slug> --section "Completed work" --text "..."
```

เปิดอีก vendor แล้วส่งข้อความ: “Continue task `<slug>` from `work/<slug>/CHECKPOINT.md`.”
ทำต่อจาก checkpoint โดยไม่ทำงานที่เสร็จแล้วซ้ำ และห้ามใช้ session id ของ vendor เดิมกับอีก vendor

## เมื่อ quota หมด

เมื่อ worker คืน exit 4 หรือ session ถูกจำกัด ให้บันทึก checkpoint และตรวจว่าอีก vendor ทำต่อได้หรือไม่
ให้ orchestrator ส่ง brief ที่อ้าง checkpoint ไปอีก vendor; ถ้าทั้งคู่ทำต่อไม่ได้ ให้หยุดและรายงานเจ้าของ
สถานะการตรวจสอบ: **real quota failover NOT VERIFIED**; **simulated quota handoff PASS**
ผลจำลองยืนยันเฉพาะการส่งต่องานแบบจำลอง ไม่ได้ยืนยันการสลับเมื่อ quota จริงหมด

## ข้อจำกัด

- **Security Gate NOT PASS**
- กฎใน prompt ไม่บังคับขอบเขต filesystem; ต้องอาศัย CLI sandbox และ tool permissions ซึ่ง Claude Code ไม่มี OS sandbox
- การเรียก Claude จาก Codex ต้องใช้ network และเขียน session ใต้ user profile; ถ้าถูกบล็อก ให้รายงานข้อจำกัด
- เลือกเฉพาะ model ที่ verified; ห้ามแก้ global CLI config, credentials หรือ account settings
- ทำงานเฉพาะขอบเขตที่อนุมัติ; ห้าม push, merge, deploy หรือ commit หากเจ้าของไม่ได้อนุญาต และห้ามส่ง secrets ให้ agent
