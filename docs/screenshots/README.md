# Screenshots

หลักฐานหน้าจอที่ commit ไว้เป็นผลจาก **OpenCode Browser** (รันจริงกับ Flask ที่
`127.0.0.1:5001` หลัง restart เพื่อให้ template ล่าสุดมีผล):

- `lab04-dc-desktop.png` — แท็บ DC หลังกด Run Simulation:
  `Success`, `Engine: ngspice`, `ngspice-47 : Circuit level simulation program`,
  3 กราฟ (Bode gain/phase + waveform), netlist/log ของ DC/AC/Transient,
  caption `Input / Output waveforms · Time (s)`
- `lab04-transient-desktop.png` — แท็บ Transient หลังกด Run Simulation:
  `Input frequency 1000 Hz`, 3 กราฟ, netlist/log ของ AC/Transient
- `lab04-lab03-modes.png` — หน้า `/simulator` แสดง panel **`Analytical DC Bias (Lab 3) · ใช้ได้ทั้ง 3 โหมด`**
  พร้อมลิงก์ `/?mode=divider`, `/?mode=fixed`, `/?mode=emitter`

สภาพแวดล้อมนี้ไม่มี Playwright MCP/node/npx และไม่ได้ใช้ Impeccable skill จริง
จึงใช้ OpenCode Browser แทน และบันทึกข้อจำกัดไว้ใน `docs/validation.md` ข้อ 19

**Before-state: NOT SUBMITTED** — ไม่มี screenshot ของ UI ก่อนปรับปรุงเก็บไว้
จึงไม่สร้างหลักฐานขึ้นมาเอง; ใช้การอธิบายการเปลี่ยนแปลงใน `docs/validation.md` ข้อ 24 แทน

การตรวจ responsive 390 px ใช้การวัด DOM (`scrollWidth == clientWidth == 390`)
ใน browser มากกว่าภาพที่ถูก scale — ดู `docs/validation.md` ข้อ 17/B8
