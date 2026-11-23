# Design Note — Lab 03

## สิ่งที่ตัดสินใจ

1. **แยก engineering ออกจาก HTTP เสมอ** — `dc_bias.py` เป็นโมดูลบริสุทธิ์ รับ dict ค่า SI คืน
   `BiasResult` ทำให้เทสต์สมการได้โดยไม่ต้องรัน server และไม่เสี่ยงให้ HTML แทรกสมการ
2. **โหมดเป็น query/field เดียว** — ใช้ `?mode=` สำหรับ GET switching และ hidden `mode` ใน POST
   ฟอร์ม ทำให้ไม่ต้องพึ่ง path เพิ่มเติมและเปิดลิงก์ตรงไปโหมดไหนก็ได้
3. **ฟอร์มตามโหมด** — field list มาจาก `MODE_FIELDS` ทั้งฝั่ง render และ validation จึงไม่มี
   สถานะที่ R1/R2/RE โผล่ในโหมด Fixed
4. **Fail closed** — ทุก validation error คืน HTTP 400 พร้อมข้อความไทย และไม่ส่ง result กลับ
   (ป้องกัน stale results แบบ A5)
5. **Warning แยกจาก region** — Cutoff/Saturation เป็น region, ส่วน "ใกล้ saturation" เป็น warning
   ใน region Forward-Active เพื่อไม่ให้ badge ผิด แต่ยังแจ้งผู้ใช้

## สิ่งที่ไม่ทำ
- ไม่ใช้ JavaScript (ตามใบงาน) — mode switch เป็น GET form ธรรมดา
- ไม่ clamp ค่า saturation — รายงานค่าที่สมการให้ พร้อมเตือนว่าสมมติฐานอาจใช้ไม่ได้
- ไม่ใส่ AC/SPICE/FET ตามขอบเขต Lab 03

## Public link
ใช้ Cloudflare Quick Tunnel เพราะเครื่อง lab ไม่มี static IP และไม่ต้องการ account
ข้อเสียคือ URL เปลี่ยนทุกครั้งที่ restart tunnel — ถ้าต้องการถาวรต้อง deploy จริง
