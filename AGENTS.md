# AGENTS.md — AI coding conventions

## Layout
- `dc_bias.py` owns every physics equation and all per-mode input validation. It must not import Flask.
- `app.py` only translates HTTP ↔ Python. No numeric constants from the circuit belong here.
- `templates/index.html` renders values passed by Flask. No hard-coded results or equations.
- `static/style.css` presentation only — no numbers, no units.

## Modes
Supported modes are exactly `divider`, `fixed`, `emitter`. Any other value must produce HTTP 400
with no form and no result table. Field sets come from `dc_bias.MODE_FIELDS`.

## Units
Internally SI (V, Ω, A). Convert to mA / µA only in `display_results()`.

## Tests
Run `python -m unittest discover -s tests -v`. Expected: 48 tests OK.
When adding a mode or changing an equation, add both an engineering test and an HTTP test.

## Public link
The Flask server runs with `--host 0.0.0.0 --port 5001` (port 5000 is taken by AirPlay Receiver on
this Mac). A Cloudflare Quick Tunnel forwards to 127.0.0.1:5001. Do not enable Flask `--debug`
while the tunnel is active.
