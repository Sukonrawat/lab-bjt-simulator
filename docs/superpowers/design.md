# Design — BJT DC Bias Web App

## Goal
ให้ผู้ใช้กรอกค่าวงจร NPN Common Emitter 3 แบบไบอัส แล้วได้จุดทำงาน DC พร้อมสถานะภูมิภาค
ผ่านหน้าเว็บ Flask ที่แชร์ลิงก์ให้ทุกคนได้

## Constraints
- ไม่ใช้ JavaScript (ใบงานกำหนดให้ mode switch เป็น GET ปกติ)
- Python 3.10+, Flask, unittest เท่านั้น
- แยก engineering / HTTP / presentation ออกจากกัน
- 48 tests ต้องผ่าน

## Decisions
| ประเด็น | ทางเลือก | เหตุผล |
|---|---|---|
| โครงสร้างโมดูล | `dc_bias.py` + `app.py` | ทดสอบสมการได้อิสระ |
| โหมด | string key ใน MODES + field map | เพิ่มโหมดใหม่ได้ง่าย |
| Error | HTTP 400 + render ฟอร์มเดิม ไม่แนบ result | ป้องกัน stale results |
| หน่วย | SI ใน Python, mA/µA ตอนแสดง | ลดความสับสนเรื่อง kΩ |
| Public access | Cloudflare Quick Tunnel → :5001 | ไม่ต้องมี static IP / account |
