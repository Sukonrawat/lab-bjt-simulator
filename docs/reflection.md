# Reflection — Lab 03

สิ่งที่ได้เรียนรู้จากการขยายจาก Lab 02 (Voltage Divider เดี่ยว ๆ) มาเป็น 3 โหมด:

1. **Separation of concerns ช่วยมาก** — พอสมการอยู่ใน `dc_bias.py` เพียงที่เดียว การเพิ่ม Fixed/Emitter
   ไม่ต้องแตะ template หรือ route เลย จึงไม่มีโอกาสให้ตัวเลขในหน้าเว็บกับ backend คลาดกัน
2. **โหมดควรเป็นข้อมูล ไม่ใช่ URL structure** — การใช้ทั้ง `?mode=` และ hidden field ทำให้ลิงก์
   แชร์ได้ (`/?mode=emitter`) โดยไม่ต้องเพิ่ม route ใหม่
3. **Validation ต้องตามโหมด** — A5 (RB=0) สอนให้เห็นว่าถ้าเติม default อัตโนมัติตอน POST
   Error จะหายไปและแสดง stale results ได้ ต้อง fail closed เสมอ
4. **การให้ public link ไม่เหมือนการรัน local** — ต้องปิด debug, เปลี่ยน port เพราะ AirPlay
   ใช้ 5000 และใช้ tunnel แทนการเปิด port บน router โดยตรง
5. **สิ่งที่ยังทำไม่ได้** — quick tunnel ได้ URL แบบสุ่มและหายเมื่อ restart ถ้าจะใช้จริงถาวร
   ต้อง deploy บน platform ที่มี domain คงที่
