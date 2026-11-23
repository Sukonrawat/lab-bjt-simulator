# Implementation Plan — Lab 03

1. สร้าง `dc_bias.py`: MODES/MODE_FIELDS/defaults, parse_form, calculate_divider/fixed/emitter,
   region detection (cutoff/saturation/near-sat), display converters
2. สร้าง `app.py`: GET `/` (mode query), POST `/calculate`, GET `/health`, 400 on invalid input
3. สร้าง `templates/index.html` + `static/style.css`: mode switch, per-mode form, results table
4. เขียน `tests/test_dc_bias.py` (25) และ `tests/test_web.py` (23) → 48 OK
5. รัน venv + ติดตั้ง Flask, start server แบบไม่ใช้ debug บน port 5001
6. เปิด Cloudflare Quick Tunnel → ทุกคนเข้าลิงก์ได้
7. ตรวจรับ A1–A5 ด้วย test client + browser + curl บน public URL
