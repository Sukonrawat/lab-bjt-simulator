# BJT Web Lab — ENG29 2121 · Lab 03 + Lab 04

โปรเจกต์ต่อเนื่องเดียวกัน two labs:

- **Lab 03** — BJT DC Bias Calculator: NPN Common-Emitter 3 โหมด (Divider / Fixed / Emitter)
  จาก `dc_bias.py` (สมการ analytic, β และ VBE คงที่)
- **Lab 04** — CE Amplifier Simulator: ต่อยอดเว็บเดิมด้วย `spice_engine.py` เรียก **ngspice จริง**
  เพื่อรัน `.op` / `.ac` / `.tran` ของวงจร Voltage Divider CE อ้างอิง แล้วแสดงตัวเลขและกราฟ
  จากผลรันเท่านั้น

Lab 03 ทั้ง 3 โหมดยังใช้ได้เหมือนเดิม (48 tests เดิมผ่านทุกตัว)

> ### ✅ ฉันเชื่อม ngspice แล้ว
> `spice_engine.py` เรียก **ngspice-47 จริง** ผ่านตัวแปร `NGSPICE_BIN` แบบ `subprocess` (`--version` / `-b -o run.log`)
> เพื่อรัน `.op` / `.ac` / `.tran` ของวงจร Voltage Divider CE แล้วอ่านตาราง `.PRINT` มาแสดงเป็นตัวเลขและกราฟ
> **ไม่มี mock data ไม่มีค่า cache และถ้า solver ล้มเหลวจะตอบ 503 โดยไม่โชว์ผลเก่า**
> หลักฐาน: `docs/validation.md` ข้อ 23–24 · screenshot ใน `docs/screenshots/` · `ngspice-47 : Circuit level simulation program`

---

## 🔗 Public Link & Source

**👉 Live app: <https://heel-represent-reservation-avon.trycloudflare.com>** (ตรวจแล้ว: GET `/`, `/health`, `/simulator` → 200 และ POST `/simulate` → `Success`, `VCE 7.900 V`, `IC 1.278 mA`)

**👉 Source code: <https://github.com/Sukonrawat/lab-bjt-simulator>** (public repo, branch `main`)

**Lab 04 commit (ระบุสำหรับการตรวจรับ):** `23d21c5` — รวม ngspice DC/AC/Transient เข้ากับ Lab 03 เดิม · `1658481` — hardening การเชื่อม ngspice (version/provenance/transient frequency)

> ลิงก์ Quick Tunnel **เปลี่ยนทุกครั้งที่ restart** — ต้องรัน Flask + cloudflared ค้างไว้
> path ของ `cloudflared` และ `NGSPICE_BIN` ด้านล่างเป็นของเครื่องนี้ — บนเครื่องอื่นให้เปลี่ยนตามตำแหน่งจริง

```bash
# Terminal 1 — port 5001 (5000 ถูก AirPlay Receiver ใช้บน macOS เครื่องนี้)
NGSPICE_BIN=/Users/sukonrawatsukkeaw/.local/ngspice-47/bin/ngspice \
  .venv/bin/python -m flask --app app run --host 0.0.0.0 --port 5001

# Terminal 2
/private/var/folders/nv/_p76k6hs3vvfr0py55_zncm40000gn/T/opencode/cloudflared \
  tunnel --no-autoupdate --url http://127.0.0.1:5001
```

cloudflared จะพิมพ์ URL แบบ `https://<random>.trycloudflare.com` ออกมา — นำ URL นั้นไปแจกได้ทันที
**ห้ามเปิด `--debug` ขณะ tunnel ทำงาน**

---

## 1 · ติดตั้ง

### Python

ต้องการ **Python 3.10+**

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### ngspice (โปรแกรมภายนอก ไม่ใช่ pip package)

macOS เครื่องนี้ไม่มี Homebrew และ ngspice ไม่มี binary สำเร็จรูปจากทางการ → build จาก source 47:

```bash
curl -fsSLO https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/ngspice-47.tar.gz
tar -xzf ngspice-47.tar.gz && cd ngspice-47
./configure --prefix=$HOME/.local/ngspice-47 \
  --without-x --disable-debug --disable-openmp --with-readline=no
make -j4 && make install
$HOME/.local/ngspice-47/bin/ngspice --version
```

`--disable-openmp` และ `--with-readline=no` จำเป็นบน macOS Command Line Tools เครื่องนี้
(ถ้าไม่ใส่จะ error ตอน compile `signal_handler.c` / OpenMP)

ถ้าติดตั้ง ngspice ไว้ที่อื่น ให้ตั้ง env ก่อนรัน Flask:

```bash
export NGSPICE_BIN=/path/to/ngspice     # ไม่ตั้งก็ได้ ถ้าอยู่ใน PATH แล้ว
```

### รันเซิร์ฟเวอร์

```bash
NGSPICE_BIN=$HOME/.local/ngspice-47/bin/ngspice \
  python -m flask --app app run --host 0.0.0.0 --port 5001
```

- Lab 03: <http://127.0.0.1:5001/>
- Lab 04 simulator: <http://127.0.0.1:5001/simulator>
- Health: <http://127.0.0.1:5001/health>

---

## 2 · สิ่งที่เพิ่มใน Lab 04

| ไฟล์ | หน้าที่ |
|---|---|
| `spice_engine.py` | validate → build netlist → `subprocess.run([...], timeout=30)` → parse `.PRINT` log → สร้าง SVG จาก array จริง; ไม่ import Flask |
| `app.py` | `GET /simulator`, `POST /simulate` (dc/ac/transient), แยกป้าย **SPICE result** กับ **Analytical reference** |
| `templates/simulator.html` | หน้าจอตาม SCREEN TARGET ของใบงาน: แถบหัว “CE Amplifier Lab” + 3 การ์ด (Circuit & Parameters / Simulation & Plots / Engineering Results), ฟอร์ม CE, radio DC/AC/Transient, badge `Engine: ngspice`, สถานะ Idle/Success/Error, Bode + waveform inline SVG พร้อมแกน/หน่วย/ตัวเลข |
| `static/style.css` | theme สว่างสำหรับ Lab 04 (แยก scope จาก Lab 03), responsive layout (desktop 3 column + 390 px), ไม่มีตัวเลขหรือหน่วยฝังอยู่ |
| `tests/test_spice_engine.py` | validation, netlist, parser, engine lookup, plot, real-engine test (skip ถ้าไม่ตั้ง `NGSPICE_BIN`) |
| `tests/test_simulation_web.py` | route test แบบ mock engine รวม error path (400/503, ไม่มี stale success) |
| `docs/validation.md` | ตาราง B1–B8 + ผลรันจริง + ข้อจำกัดเครื่องมือ |

### วงจรอ้างอิง (netlist ที่สร้างจริง)

```
VCC vcc 0 DC 12
VIN in 0 DC 0 AC 0.01 SIN(0 0.01 1000)
R1 vcc b 100k   R2 b 0 22k   RC vcc c 2.2k   RE e 0 1k
CIN in b 10u    COUT c out 10u   RL out 0 10k
Q1 c b e QNPN
.model QNPN NPN(IS=1E-14 BF=100 VAF=100)
```

- `.op` → `VB, VE, VC, VCE, IC` (IC คำนวณจากแรงดันตกบน RC เพราะ I(VCC) รวมกระแส divider ด้วย)
- `.ac DEC 100 1 100MEG` → freq / gain(dB) / phase(deg) วัดที่ `in` กับ `out`
- `.tran` → time / vin / vout (4 periods, 400 steps/period) + correlation เพื่อยืนยันการกลับเฟส
- **ทุกครั้งที่กด Run** (DC/AC/Transient) จะรัน AC + Transient ด้วยเสมอ → แสดง **Bode + waveform ทั้ง 2 กราฟ** จากผลรอบเดียวกัน (ถ้ารันเสริมล้มเหลว → 503 ไม่มีกราฟค้าง)

**หมายเหตุหน่วย phase:** ngspice-47 ในเครื่องนี้เขียน `VP()` ออกมาเป็น **radian** แม้หลายคู่มือบอก degree
(ทดสอบด้วย RC ธรรมดา: ที่ 1 Hz ได้ `-6.28310e-03`) → `parse_ac()` คูณ `180/π` ก่อนแสดงผล

**ห้าม stale success:** ถ้า ngspice หาย / exit ≠ 0 / log ว่าง / parse ไม่ได้ / timeout → HTTP 503 หรือ 400
แสดง Error และ **ไม่ส่งตารางหรือกราฟเก่ามาด้วย**

---

## 3 · Automated Tests

```bash
python -m unittest discover -s tests -v
# → Ran 91 tests OK (49 Lab 03 + 42 Lab 04; 1 real-engine test ข้ามถ้าไม่ตั้ง NGSPICE_BIN)
NGSPICE_BIN=$HOME/.local/ngspice-47/bin/ngspice python -m unittest discover -s tests
# → Ran 91 tests OK (ไม่มี skip)
```

---

## 4 · โครงสร้าง

```
.
├── app.py                     # Flask HTTP layer เท่านั้น
├── dc_bias.py                 # Lab 03 analytic engine (ห้าม import Flask)
├── spice_engine.py            # Lab 04 ngspice adapter (ห้าม import Flask)
├── templates/
│   ├── index.html             # Lab 03 calculator + visible mode-specific circuit SVG
│   └── simulator.html         # Lab 04 simulator + plots
├── static/style.css           # presentation only
├── tests/
│   ├── test_dc_bias.py        # 25 engineering tests
│   ├── test_web.py            # 24 Lab 03 HTTP tests (รวม circuit SVG)
│   ├── test_spice_engine.py   # netlist/parser/error/plot tests
│   └── test_simulation_web.py # Lab 04 HTTP tests (mock engine)
├── docs/
│   ├── validation.md          # A1–A5 + B1–B8 + ngspice evidence
│   ├── design-note.md
│   ├── reflection.md
│   ├── test-log.txt
│   └── screenshots/
├── requirements.txt
└── AGENTS.md
```

---

## 5 · Lab 03 acceptance (ยังต้องผ่านอยู่)

| # | เกณฑ์ | ผล |
|---|---|---|
| A1 | Divider ค่าเริ่มต้น | IC 1.230 mA, VCE 8.052 V |
| A2 | Fixed RB=1M | IC 1.130 mA, VCE 9.514 V |
| A3 | Emitter RE=1k | IC 1.026 mA, VCE 8.705 V |
| A4 | Emitter RE=2k | IC 0.940 mA, VCE 8.033 V |
| A5 | Fixed RB=0 | HTTP 400 + "RB ต้องมากกว่า 0" |

## 6 · Lab 04 acceptance (B1–B8)

ดูตารางผลจริงพร้อมหลักฐาน log/screenshot ได้ใน **`docs/validation.md`**

---

## 7 · ข้อจำกัดและเครื่องมือตรวจรับ

- **Playwright MCP ไม่พร้อมใช้** (ไม่มี node/npx ในเครื่อง) → ใช้ **OpenCode Browser** แทน
- **ImpeccableSkill ไม่มีอยู่ในสภาพแวดล้อมนี้** → ใช้ self-review (ทบทวน contrast, sizing, error states)
  และบันทึกตรงไปตรงมาใน `docs/validation.md` แทนการอ้างว่าใช้ skill
- กราฟสร้างจาก array ที่ parse จาก ngspice log ด้วย inline SVG — ไม่มี chart library เพิ่ม
- ไม่มี Emitter bypass, animated overlay หรือวงจรอื่นนอกเหนือจาก CE Voltage Divider v1

---

ENG29 2121 · COMPUTER PROGRAMMING FOR ELECTRICAL ENGINEERS · 2/2569 · Lab 03 → Lab 04
