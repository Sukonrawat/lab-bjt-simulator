---
name: browser-acceptance-check
description: ตรวจรับ A1–A5 ของ Lab 03 บน browser จริง แล้วรายงานผลเป็นตาราง
---

# Browser Acceptance Check — Lab 03

ใช้เมื่อต้องการยืนยันว่าเว็บแอปทำงานจริงบน browser ไม่ใช่แค่ test client

## เครื่องมือ
Playwright MCP ไม่พร้อมใช้ในเครื่องนี้ (ไม่มี node/npx) → ใช้ **OpenCode Browser** แทน
(อนุญาตให้ใช้ browser tool อื่นทดแทนได้ตามใบงาน)

## ขั้นตอน
1. เปิด public link (หรือ `http://127.0.0.1:5001/`) ด้วย browser
2. ทำตาม Minimum Demo 6 ข้อใน README
3. สำหรับแต่ละ case  record: **case ID | วิธีตรวจ | ค่าคาดหมาย | ค่าที่เห็นจริง | PASS/FAIL**
4. ถ้าคลิกปุ่มไม่ตอบสนอง ให้ใช้ `browser.evaluate` เรียก `form.submit()` แล้วอ่านตารางผลลัพธ์
5. บันทึกผลลง `docs/validation.md` ส่วนที่ 10 โดยระบุชื่อเครื่องมือที่ใช้จริง

## เกณฑ์ A1–A5
A1 divider → IC 1.230 mA, VCE 8.052 V · A2 fixed RB=1M → 1.130 mA, 9.514 V
A3 emitter RE=1k → 1.026 mA, 8.705 V · A4 emitter RE=2k → 0.940 mA, 8.033 V
A5 fixed RB=0 → HTTP 400 + "RB ต้องมากกว่า 0" + ไม่มีตารางผลลัพธ์
