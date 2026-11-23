# Validation — Lab 02 + Lab 03

## 1. คำนวณอิสระ: Voltage Divider (ชุดอ้างอิงใบ Lab)

กำหนด `VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V`

```
VTH = 12 × 22k/(100k+22k) = 2.1639344 V
RTH = 100k × 22k / 122k   = 18.032787 kΩ
IB  = (2.1639344−0.70)/(18032.787+101×1000) = 1.2298581e−5 A
IC  = 100·IB = 1.2298581 mA
IE  = 101·IB = 1.2421567 mA
VE  = IE·RE  = 1.2421567 V
VB  = VE+VBE = 1.9421567 V
VC  = 12 − IC·2.2k = 9.2943122 V
VCE = VC−VE = 8.0521554 V  → Forward-Active
```

## 2–7. ประวัติ Lab 02 (A1–A7 เดิม)
ตรวจย้อนกลับได้จาก git history และชุด test เดิมของ Lab 02 (Voltage Divider เพียงโหมดเดียว)

## 8. คำนวณอิสระ: Fixed Bias (A2)
`VCC=12, RB=1 MΩ, RC=2.2 kΩ, β=100, VBE=0.70`

```
IB  = (12−0.70)/1e6 = 11.3 µA
IC  = 1.130 mA
VE  = 0, VB = 0.70 V
VC  = 12 − 1.130mA×2.2k = 9.514 V
VCE = 9.514 V  → Forward-Active
```

## 9. คำนวณอิสระ: Emitter Bias (A3, A4)
`VCC=12, RB=1 MΩ, RC=2.2 kΩ, β=100, VBE=0.70`

| RE | IB | IC | VE | VC | VCE |
|---|---|---|---|---|---|
| 1 kΩ (A3) | 10.263 µA | 1.026 mA | 1.037 V | 9.742 V | 8.705 V |
| 2 kΩ (A4) | 9.401 µA | 0.940 mA | 1.899 V | 9.932 V | 8.033 V |

RE เพิ่มขึ้น → IB ลดลง → IC ลดลง ตามที่ใบงานคาดหมาย

## 10. ผลรัน Browser จริง (A1–A5, OpenCode Browser)

| Case | วิธีตรวจ | ค่าคาดหมาย | ค่าที่เห็นจริง | ผล |
|---|---|---|---|---|---|
Public link ที่ใช้ตรวจ: <https://constraints-humanity-misc-salary.trycloudflare.com>

| A1 | POST `/calculate` divider ค่าเริ่มต้น (กดปุ่มผ่าน browser) | IC 1.230 mA, VCE 8.052 V | `VB 1.942 V, VE 1.242 V, VC 9.294 V, VCE 8.052 V, IC 1.230 mA`, badge Forward-Active | PASS |
| A2 | เปลี่ยนโหมด Fixed, RB=1M | IC 1.130 mA, VCE 9.514 V | ตรงตามคำนวณอิสระ | PASS |
| A3 | เปลี่ยนโหมด Emitter, RE=1k | IC 1.026 mA, VCE 8.705 V | ตรงตามคำนวณอิสระ | PASS |
| A4 | Emitter, เปลี่ยน RE=2000 | IC ลดลงเหลือ 0.940 mA | IC 0.940 mA, VCE 8.033 V | PASS |
| A5 | Fixed, RB=0 | HTTP 400, ข้อความ "RB ต้องมากกว่า 0", ไม่มีตารางผล | ตรงตามเกณฑ์ | PASS |

> เครื่องมือที่ใช้จริง: **OpenCode Browser** (Playwright MCP ไม่พร้อมใช้เพราะไม่มี node/npx)

## 11. Automated tests (Lab 03 baseline)
`python -m unittest discover -s tests -v` → **Ran 81 tests … OK**
(48 Lab 03 [25 engineering + 23 HTTP] + 33 Lab 04; 1 real-engine test ข้ามถ้าไม่ตั้ง NGSPICE_BIN)

---

# Lab 04 · BJT Amplifier Simulator — Validation

## 12. สภาพแวดล้อมจริง (Baseline & Tool Check)

| รายการ | ผลตรวจจริง |
|---|---|
| Lab 03 เดิม | 48 tests OK ก่อนเริ่ม Lab 04 |
| Python | `.venv` เดิมจาก Lab 03 |
| Flask | เดิม + route ใหม่ `/simulator`, `/simulate` |
| ngspice | **ไม่มีติดตั้งอยู่แล้ว** → build จาก source **ngspice-47** ด้วย clang/gcc บน macOS |
| configure flags | `--without-x --disable-debug --disable-openmp --with-readline=no` (จำเป็น เพราะ OpenMP/readline บน Command Line Tools พัง) |
| ตำแหน่ง | `/Users/sukonrawatsukkeaw/.local/ngspice-47/bin/ngspice` |
| ผล `--version` | `ngspice-47 : Circuit level simulation program / Compiled with KLU Direct Linear Solver` |
| BJT model | `.model QNPN NPN(IS=1E-14 BF=100 VAF=100)` |
| Git | เดิมไม่ใช่ repo → `git init` เมื่อจบ Lab 04 |
| Playwright MCP | **NOT RUN** — ไม่มี node/npx |
| Impeccable skill | **NOT RUN** — ไม่มี skill นี้ใน OpenCode สภาพแวดล้อมนี้ ใช้ self-review แทน |
| เครื่องมือ browser จริง | OpenCode Browser (Navigate / Snapshot / Evaluate / Screenshot) |

## 13. วิธีเรียก ngspice และอ่านผล

```python
subprocess.run([binary, "-b", "-o", log_path, deck], timeout=30,
               cwd=tempdir, capture_output=True, text=True)
```

- **ไม่ใช้ `-r`** เพราะ ngspice จะข้าม `.PRINT` เมื่อมีการขอ raw file → ไฟล์ log จะว่าง
- **ไม่ใช้ `shell=True`** — ส่ง list ของ args และ validate ตัวเลขก่อนประกอบ netlist เสมอ
- `.PRINT` ของ ngspice **แบ่งเป็นหลายตารางและซ้ำ header `Index` ทุก ~57 แถว**
  → parser แยก block ตาม header แล้วต่อ array ให้ครบ 801 จุด (AC) / 1608 จุด (tran)
- `I(VCC)` รวมกระแสตัวหาร R1/R2 ด้วย → `IC` มาจาก `(VCC−VC)/RC` แทน
- `VP()` ใน ngspice-47 ที่ build นี้เขียนออกมาเป็น **radian** (ทดสอบ RC: 1 Hz → `-6.28310e-03`)
  →คูณ `180/π` ก่อนแสดงเป็น degree

## 14. ผล DC `.op` (Input fixture: VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, Cin=Cout=10u, RL=10k)

| Node | ผล ngspice .op | หมายเหตุ |
|---|---|---|
| VB | **1.949 V** | |
| VE | **1.289 V** | |
| VC | **9.189 V** | |
| VCE | **7.900 V** | VC−VE |
| IC | **1.278 mA** | (12−9.189)/2.2k |

Analytical reference จาก Lab 03 (`β=100, VBE=0.70V` คงที่) ให้ `IC=1.230 mA, VCE=8.052 V`
→ ต่างจาก SPICE เพราะโมเดลต่างกัน (SPICE ใช้ BJT exponential + VAF) แสดงแยกกันในหน้าเว็บ ไม่บังคับให้เท่ากัน

## 15. AC `.ac DEC 100 1 100MEG` (Vin 10 mV peak @ 1 kHz)

| ความถี่ | Gain | Phase |
|---|---|---|
| 100 Hz | 4.859 dB | ≈ −179.4° |
| 1 kHz (max) | **4.860 dB** | **−179.7°** |
| 10 kHz | 4.860 dB | ≈ −180.0° |

Bode plot 2 กราฟ (gain/phase) สร้างจาก array 801 จุดจริง มีแกน log frequency, หน่วย dB/deg
และ tick labels ที่มาจาก min/max ของข้อมูล ไม่มีค่าสำเร็จรูปฝังไว้

## 16. Transient `.tran` (10 mV peak, 1 kHz, 4 periods)

| ปริมาณ | ค่า |
|---|---|
| Vin peak | 0.0100 V |
| Vout peak | 0.017 V |
| Samples | 1608 |
| Correlation(Vin,Vout) | **−1.0000** → กลับเฟส ~180° ตาม Common-Emitter |

เปลี่ยน amplitude เป็น 20 mV / 2 kHz → `Vin peak 0.0200 V`, `Vout peak 0.035 V`,
tick ของแกน voltage เปลี่ยนจาก `±0.0175` เป็น `±0.0350 V` (หลักฐานว่ากราฟมาจากรันใหม่)

## 17. Acceptance B1–B8 (ผลรันจริงบน OpenCode Browser)

| Case | วิธีตรวจ | ผลที่เห็นจริง | ผล |
|---|---|---|---|
| **B1 Regression** | เปิด `/?mode=divider|fixed|emitter` แล้ว submit แบบฟอร์มจริง | Divider `1.230 mA / 8.052 V`, Fixed `1.130 mA / 9.514 V`, Emitter `1.026 mA / 8.705 V` — ตรง A1–A3 เดิมทุกตัว | **PASS** |
| **B2 DC SPICE** | `/simulator` → Run DC | badge **Success**, `Engine: ngspice` + เวอร์ชัน, ตาราง VB 1.949 / VE 1.289 / VC 9.189 / VCE 7.900 / IC 1.278 mA, มี `<details>` netlist+log จริง และ Analytical reference แยกต่างหาก | **PASS** |
| **B3 Change RE** | เปลี่ยน RE 1000→1500 แล้ว Run DC ซ้ำ | log netlist แสดง `RE e 0 1500`; IC **1.278→0.900 mA**, VCE **7.900→8.656 V** (ไม่ค้างค่าเดิม) | **PASS** |
| **B4 AC** | Run AC | gain **4.86 dB @ 490 Hz**, phase **−179.7°**, polyline 267 จุด/กราฟ, มีแกน `Frequency (Hz, log scale)` / `Gain (dB)` / `Phase (deg)` | **PASS** |
| **B5 Transient** | Run `.tran` ที่ 10 mV/1 kHz | 2 waveform (Vin teal / Vout orange), axis `Time (s)` + `Voltage (V)`, correlation **−1.0000** + ข้อความกลับเฟส | **PASS** |
| **B6 Change Source** | เปลี่ยนเป็น 20 mV / 2 kHz แล้ว Run ซ้ำ | `SIN(0 0.02 2000)` ใน netlist, Vout peak **0.017→0.035 V**, y-tick เปลี่ยนตามข้อมูล | **PASS** |
| **B7 Invalid / Fail** | (a) RE=0 ใน browser ปกติ (b) รัน server ที่ `NGSPICE_BIN=/no/such/ngspice` แล้ว submit | (a) HTTP 400, `RE (Ω) ต้องอยู่ระหว่าง 0.001 ถึง 1e+06`, status **Error**, ไม่มี `#spice-results` (b) status **Error**, `NGSPICE_BIN เรียกใช้ไม่ได้`, ไม่มีตาราง/กราฟค้าง | **PASS** |
| **B8 UI** | Desktop full-page screenshot + iframe viewport กว้าง 390px วัด layout จริง | Desktop อ่านง่าย; ที่ 390px: `scrollWidth=clientWidth=390` (ไม่มี horizontal scroll), layout และ field-grid เป็น 1 column, ปุ่ม/ฟอร์มอยู่ครบ | **PASS** |

Screenshot (server-local paths):
- desktop: `~/.cache/opencode/browser-exports/.../caef601a-.../0/screenshot.png`
- 390px iframe check วัดจาก computed style (ภาพ scaled อย่างเดียวไม่ใช้หลักฐาน reflow จึงใช้การวัด DOM แทน)

## 18. Error path ที่ทดสอบเพิ่ม (unit + HTTP)

| กรณี | ผลลัพธ์ |
|---|---|
| ngspice ไม่มีใน PATH และไม่ตั้ง `NGSPICE_BIN` | `SimulationError` + ข้อความไทย + HTTP 503 ไม่มี stale success |
| `NGSPICE_BIN` ชี้ file ไม่มี | error ทันทีโดยไม่ spawn process |
| exit code ≠ 0 | 503 พร้อมท้าย log |
| log ว่าง / parse ไม่ได้ | 503 ไม่มีกราฟ |
| timeout 30 s | 503 พร้อมข้อความให้ย่น sweep |
| `.AC` gain ต่ำกว่า −3 dB ตลอด sweep | แจ้ง *"not determined in sweep range"* แทนการเดาค่า fL/fH |

## 19. ความคลาดเคลื่อน / ข้อจำกัดที่ต้องบอกตรง ๆ

- ผล SPICE ไม่เท่าผล analytical เพราะคนละโมเดล (ยืนยันในข้อ 14)
- OpenCode Browser ใช้แทน Playwright MCP; **ไม่มี截图จาก Playwright**
- ไม่ได้ใช้ Impeccable skill จริง → ปรับ UI ด้วย self-review + วัด responsive แบบ iframe แทน
- กราฟเป็น inline SVG ที่ plot จาก array ไม่มี interactive tooltip / zoom
- Public link แบบ Quick Tunnel เปลี่ยน URL ทุกครั้งที่ restart (ไม่ได้ตั้งค่าบน host ถาวร)
  ลิงก์ที่ใช้ตรวจ Lab 04: <https://tries-college-ali-certainly.trycloudflare.com>
  (GET `/`, `/health`, `/simulator` → 200; POST `/simulate` dc → `VCE 7.900 V`)

---

## 20. ปรับหน้าจอให้ตรง SCREEN TARGET (ภาพที่ 1 ในใบงาน Lab 04)

ผู้ใช้ส่ง screenshot ของภาพหน้าจอเป้าหมาย (SVG `#mockup` ใน
`Lab04_BJT_Amplifier_Simulator_2-2569.html`) แล้วขอให้ปรับ UI ให้ตรง — สิ่งที่เปลี่ยน:

| องค์ประกอบในภาพเป้าหมาย | สิ่งที่ implement จริง |
|---|---|
| แถบหัวสี `#103658` + ชื่อ “CE Amplifier Lab” + “DC Bias / AC / Transient” | `.sim-header` ใน `templates/simulator.html` |
| การ์ดซ้าย “Circuit & Parameters” + วงจร CE voltage-divider (Q1 NPN, R1/R2/RC/RE, Cin/Cout, RL, ground ร่วม) | นำ SVG วงจรจากภาพเป้าหมายมาใช้จริง (13 paths, ไม่มีค่าตัวเลขฝัง) ด้านล่างเป็นฟอร์มแก้พารามิเตอร์ + แท็บ DC/AC/Transient + ปุ่ม “Run Simulation” |
| การ์ดกลาง “Simulation & Plots” + กรอบ Bode / waveform | `.plot-frame` แสดง **กราฟจาก array ของ ngspice จริงเท่านั้น** (ไม่ใช้คำว่า illustrative และไม่มีค่าตัวอย่าง) |
| การ์ดขวา “Engineering Results” + 3 ส่วน (DC / AC / Transient) + กล่อง “Engine: ngspice / Run status + model + units” | `.result-card` แสดงผล analysis ที่รันล่าสุด; ส่วนที่ยังไม่รันแสดง `not run` (ไม่ค้างค่เก่า) |
| Theme สว่าง `#f6fafc`, การ์ดขาว, accent teal/orange | CSS ใหม่ scoped ด้วย `.sim-body` / `.sim-*` — **Lab 03 ยังใช้ theme เดิมไม่เปลี่ยน** |

### ผลตรวจหลังปรับ (OpenCode Browser จริง)

| รายการ | ผล |
|---|---|
| Layout ที่ viewport 1000 px | grid 3 คอลัมน์ **297 / 399 / 232 px** (สัดส่วนใกล้ 334 / 452 / 262 ในภาพเป้าหมาย), `scrollWidth == clientWidth == 1000` |
| Layout ที่ 390 px (iframe) | 1 คอลัมน์, `scrollWidth == clientWidth == 390`, ไม่มี element ล้ำขอบ, ฟอร์มและปุ่มครบ |
| DC | Success · VB 1.949 / VE 1.289 / VC 9.189 / VCE 7.900 V · IC 1.278 mA · analytical reference แยกต่างหาก |
| AC | Success · 4.86 dB @ 490 Hz · −179.7° · polyline 267 จุด/กราฟ · caption `Gain (dB)` / `Phase (deg)` |
| Transient | Success · 2 waveform · Vin 0.0100 V / Vout 0.017 V / 1608 samples / corr −1.0000 · legend `Vin (teal) / Vout (orange)` |
| Console error | ไม่มี |
| Automated tests | `NGSPICE_BIN=... python -m unittest discover -s tests` → **81 tests OK** (A1–A5, B1–B8 ไม่ถอยหลัง) |

**ข้อจำกัดที่ยังตรงตามใบงาน:** ไม่เพิ่ม Emitter bypass, animation หรือ circuit editor — ภาพเป้าหมายเป็น wireframe สำหรับตำแหน่งฟังก์ชัน (ใบงานระบุ *“ไม่กำหนดให้ทุกทีมทำ Layout เหมือนกัน”* และ *“แนะนำให้การอ่านวงจรและกราฟสำคัญกว่าการเพิ่ม Effects”*)

---

## 21. ทุก Analysis แสดงทั้ง 2 กราฟ (ตาม screenshot ที่ผู้ใช้ส่งเพิ่ม)

ผู้ใช้ต้องการให้กด **DC / AC / Transient** แล้วเห็น **Bode response + Input/Output waveforms พร้อมกัน** เหมือนภาพในข้อ 20 (ภาพเป้าหมายมีกรอบกราฟ 2 ช่องคงที่ และแท็บอยู่ด้านบน)

### วิธีทำที่ยังยึด "ผลจริงเท่านั้น"
- `app.py` หลัง validate จะรัน analysis ที่เลือก **แล้วรัน AC + Transient เพิ่มเสมอ** (`run_simulation` ถูกเรียก 3 ครั้งสำหรับ DC, 2 ครั้งสำหรับ AC/Transient)
- `plots` รวม SVG จากทุก result ของ **รอบเดียวกัน** — ไม่ cache, ไม่ใช้ค่าค้าง
- ถ้าการรันเสริมล้มเหลว → HTTP **503 + Error ไม่มีตาราง/กราฟ** (ทดสอบใน `test_secondary_plot_failure_has_no_stale_success`)
- ฝั่งขวา: analysis ที่เลือกแสดงตารางเต็ม (`#spice-results`) ส่วนอีก analysis แสดงสรุปแบบ inline จาก result ของรันเดียวกัน

### ผลรันจริง (OpenCode Browser)

| แท็บที่กด | กราฟที่เห็น | จุดข้อมูล | สรุปฝั่งขวา | เวลา |
|---|---|---|---|---|
| **DC** | Bode (gain+phase) + waveform ครบ | 267 / 267 / 268 | AC `4.86 dB · −179.7° · 490 Hz`, Tran `0.0100 V · 0.017 V · −1.0000` | ~151 ms |
| **AC** | Bode (gain+phase) + waveform ครบ | 267 / 267 / 268 | Tran `0.0100 V · 0.017 V · −1.0000` | ~115 ms |
| **Transient** | Bode (gain+phase) + waveform ครบ | 267 / 267 / 268 | AC `4.86 dB · −179.7° · 490 Hz` | ~109 ms |

- ทุกเคส `run-status = Success` และ `Engine: ngspice` ปรากฏ
- 390 px: 3 กราฟอยู่ครบ, `scrollWidth == clientWidth == 390`, ไม่มี element ล้ำขอบ
- Automated tests: **85 tests OK** (เพิ่มจาก 81 → 85: 4 tests ใหม่สำหรับ "ทั้ง 2 กราฟทุกแท็บ" + error path ของการรันเสริม)
