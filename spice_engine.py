"""ngspice adapter for the Lab 04 reference CE voltage-divider amplifier.

This module owns everything about the external solver: parameter validation,
netlist generation, subprocess invocation, raw-output parsing and SVG plots.
It never imports Flask and knows nothing about HTML forms.

Results returned here always originate from a real ngspice run -- no
pre-computed gain, bandwidth or waveform constants live in this file.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

BJT_MODEL: str = "QNPN"
MODEL_CARD: str = ".model QNPN NPN(IS=1E-14 BF=100 VAF=100)"
SIM_TIMEOUT_SECONDS: int = 30

ANALYSES: tuple[str, ...] = ("dc", "ac", "transient")

DEFAULT_SIM_VALUES: dict[str, str] = {
    "VCC": "12",
    "R1": "100000",
    "R2": "22000",
    "RC": "2200",
    "RE": "1000",
    "RL": "10000",
    "CIN": "10e-6",
    "COUT": "10e-6",
    "VPEAK": "0.010",
    "FREQ": "1000",
}

FIELD_LABELS: dict[str, str] = {
    "VCC": "VCC (V)",
    "R1": "R1 (Ω)",
    "R2": "R2 (Ω)",
    "RC": "RC (Ω)",
    "RE": "RE (Ω)",
    "RL": "RL (Ω)",
    "CIN": "Cin (F)",
    "COUT": "Cout (F)",
    "VPEAK": "Vin amplitude (V peak)",
    "FREQ": "Input frequency (Hz)",
}

RANGES: dict[str, tuple[float, float]] = {
    "VCC": (0.1, 100),
    "R1": (1, 10e6),
    "R2": (1, 10e6),
    "RC": (1, 1e6),
    "RE": (1e-3, 1e6),
    "RL": (1, 1e7),
    "CIN": (1e-12, 1e-2),
    "COUT": (1e-12, 1e-2),
    "VPEAK": (1e-6, 10),
    "FREQ": (1, 1e8),
}


class SimulationError(Exception):
    """Raised for any invalid input or failed/unusable ngspice run."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.details = details


@dataclass
class SimulationResult:
    """One successful ngspice run, with provenance attached."""

    analysis: str
    model: str = BJT_MODEL
    engine: str = "ngspice"
    engine_version: str = ""
    status: str = "Success"
    values: dict[str, float] = field(default_factory=dict)
    series: dict[str, list[float]] = field(default_factory=dict)
    log_excerpt: str = ""
    netlist: str = ""
    sweep_note: str = ""


def resolve_ngspice() -> str:
    """Find the ngspice executable. Env override wins; never use a shell."""
    configured = os.environ.get("NGSPICE_BIN", "").strip()
    if configured:
        if not Path(configured).is_file() or not os.access(configured, os.X_OK):
            raise SimulationError(f"NGSPICE_BIN เรียกใช้ไม่ได้: {configured}")
        return configured
    found = shutil.which("ngspice")
    if found:
        return found
    raise SimulationError(
        "ไม่พบ ngspice ใน PATH — ติดตั้ง ngspice หรือตั้ง NGSPICE_BIN ให้ชี้ไปยัง executable"
    )


def engine_version(binary: str | None = None) -> str:
    """Return the engine version string, or an empty string if unavailable."""
    try:
        exe = binary or resolve_ngspice()
        completed = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        text = (completed.stdout + completed.stderr).strip()
        return text.splitlines()[0] if text else ""
    except (SimulationError, OSError, subprocess.SubprocessError):
        return ""


def validate_params(form: Mapping[str, Any]) -> dict[str, float]:
    """Validate every CE parameter before it can reach the netlist."""
    if not isinstance(form, Mapping):
        raise SimulationError("ข้อมูลวงจรไม่ถูกต้อง")

    parsed: dict[str, float] = {}
    for name, (low, high) in RANGES.items():
        raw = form.get(name)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            raise SimulationError(f"กรอก {FIELD_LABELS[name]} ให้ครบ")
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise SimulationError(f"{FIELD_LABELS[name]} ต้องเป็นตัวเลข") from exc
        if not math.isfinite(value):
            raise SimulationError(f"{FIELD_LABELS[name]} ต้องเป็นจำนวนจำกัด")
        if not low <= value <= high:
            raise SimulationError(
                f"{FIELD_LABELS[name]} ต้องอยู่ระหว่าง {low:g} ถึง {high:g}"
            )
        parsed[name] = value
    return parsed


def _fmt(value: float) -> str:
    """A validated number formatted safely for a SPICE deck."""
    return f"{value:.10g}"


def build_netlist(p: dict[str, float], analysis: str) -> str:
    """Create a CE voltage-divider deck for exactly one analysis.

    Nodes: vcc (supply), in (source before Cin), b (base), c (collector),
    e (emitter), out (across RL after Cout). All nets share ground node 0.
    """
    if analysis not in ANALYSES:
        raise SimulationError(f"โหมดวิเคราะห์ไม่รองรับ: {analysis}")

    lines = [
        "* CE Voltage Divider Amplifier - ENG29 2121 Lab 04",
        "* Generated by spice_engine.py from validated form values",
        f"VCC vcc 0 DC {_fmt(p['VCC'])}",
        f"VIN in 0 DC 0 AC {_fmt(p['VPEAK'])} SIN(0 {_fmt(p['VPEAK'])} {_fmt(p['FREQ'])})",
        f"R1 vcc b {_fmt(p['R1'])}",
        f"R2 b 0 {_fmt(p['R2'])}",
        f"RC vcc c {_fmt(p['RC'])}",
        f"RE e 0 {_fmt(p['RE'])}",
        f"CIN in b {_fmt(p['CIN'])}",
        f"COUT c out {_fmt(p['COUT'])}",
        f"RL out 0 {_fmt(p['RL'])}",
        f"Q1 c b e {BJT_MODEL}",
        MODEL_CARD,
    ]

    if analysis == "dc":
        lines += [
            ".OP",
            ".PRINT OP V(b) V(e) V(c) V(out) I(VCC)",
        ]
    elif analysis == "ac":
        lines += [
            ".AC DEC 100 1 100MEG",
            ".PRINT AC VDB(in) VP(in) VDB(out) VP(out)",
        ]
    else:
        period = 1.0 / p["FREQ"]
        stop = 4.0 * period
        step = period / 400.0
        lines += [
            f".TRAN {_fmt(step)} {_fmt(stop)}",
            ".PRINT TRAN V(in) V(out)",
        ]

    lines.append(".END")
    return "\n".join(lines) + "\n"


_NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def _sections(log: str) -> list[tuple[str, list[list[float]]]]:
    """Split ngspice .PRINT output into blocks keyed by their header.

    ngspice paginates long tables and repeats the `Index ...` header every
    ~57 rows, so a single analysis can produce many blocks per variable.
    """
    number_re = re.compile(_NUMBER)
    sections: list[tuple[str, list[list[float]]]] = []
    header: str | None = None
    rows: list[list[float]] = []
    for line in log.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("index "):
            if header is not None:
                sections.append((header, rows))
            header = stripped.lower()
            rows = []
            continue
        if header is None:
            continue
        values = [float(m.group()) for m in number_re.finditer(stripped)]
        if len(values) == len(header.split()):
            rows.append(values)
        elif not values and rows:
            sections.append((header, rows))
            header, rows = None, []
    if header is not None and rows:
        sections.append((header, rows))
    return sections


def _section_rows(log: str, marker: str) -> list[list[float]]:
    rows: list[list[float]] = []
    for header, block in _sections(log):
        if all(token in header for token in marker.split()):
            rows.extend(block)
    if not rows:
        raise SimulationError(
            "ngspice ไม่ได้ส่งข้อมูลที่อ่านได้ (กราฟ/ตารางว่าง) — ดู log ที่แนบมา",
            log[-1500:],
        )
    return rows


def parse_dc(log: str, params: dict[str, float]) -> dict[str, float]:
    """Read the .OP table: V(b), V(e), V(c) from one block and I(VCC) from another."""
    node_rows = _section_rows(log, "v(b) v(e) v(c)")
    supply_rows = _section_rows(log, "vcc#branch")
    vb, ve, vc, _vout = node_rows[-1][1:]
    ivcc = supply_rows[-1][1]
    return {
        "VB": vb,
        "VE": ve,
        "VC": vc,
        "VCE": vc - ve,
        # I(VCC) also feeds the R1/R2 divider, so IC comes from RC's drop.
        "IC": (params["VCC"] - vc) / params["RC"],
        "IE": ve / params["RE"],
        "I_SUPPLY": -ivcc,
    }


def parse_ac(log: str) -> dict[str, list[float]]:
    """Read .AC tables and compute gain/phase against the Vin reference node.

    Measured with ngspice-47 in this environment: ``VP()`` prints **radians**
    even though many manuals say degrees (a simple RC at 1 Hz prints
    -6.28310e-03 for -0.36 deg). Convert explicitly so the UI can label deg.
    """
    vin_rows = _section_rows(log, "frequency vdb(in)")
    vout_rows = _section_rows(log, "frequency vdb(out)")
    freq = [r[1] for r in vin_rows]
    gain = [out[2] - inp[2] for inp, out in zip(vin_rows, vout_rows)]
    rad_to_deg = 180.0 / math.pi
    phase = [
        (out[3] - inp[3]) * rad_to_deg
        for inp, out in zip(vin_rows, vout_rows)
    ]
    return {"freq": freq, "gain_db": gain, "phase_deg": phase}


def parse_transient(log: str) -> dict[str, list[float]]:
    """Read .TRAN table: index, time, v(in), v(out)."""
    rows = _section_rows(log, "time v(in) v(out)")
    return {
        "time": [r[1] for r in rows],
        "vin": [r[2] for r in rows],
        "vout": [r[3] for r in rows],
    }


def _excerpt(log: str, limit: int = 1400) -> str:
    text = log.strip()
    return text[-limit:] if len(text) > limit else text


def _correlation(xs: list[float], ys: list[float]) -> float:
    """Pearson r between two arrays from the same ngspice .tran run."""
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    var_x = sum((x - mx) ** 2 for x in xs)
    var_y = sum((y - my) ** 2 for y in ys)
    return cov / math.sqrt(var_x * var_y) if var_x and var_y else 0.0


def run_simulation(params: dict[str, float], analysis: str) -> SimulationResult:
    """Run one real ngspice batch simulation and parse its output."""
    if analysis not in ANALYSES:
        raise SimulationError(f"โหมดวิเคราะห์ไม่รองรับ: {analysis}")
    binary = resolve_ngspice()
    netlist = build_netlist(params, analysis)

    with tempfile.TemporaryDirectory(prefix="lab04-ngspice-") as workdir:
        deck = Path(workdir) / "circuit.cir"
        log_path = Path(workdir) / "run.log"
        deck.write_text(netlist, encoding="utf-8")

        try:
            # No -r here: ngspice ignores .PRINT cards when a raw file is
            # requested, and we want the human-readable .PRINT table.
            completed = subprocess.run(
                [
                    binary,
                    "-b",
                    "-o",
                    str(log_path),
                    str(deck),
                ],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=SIM_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SimulationError(
                f"ngspice หมดเวลา ({SIM_TIMEOUT_SECONDS} วินาที) — ย่นช่วง sweep หรือลดความถี่",
                _excerpt(exc.stdout or ""),
            ) from exc
        except OSError as exc:
            raise SimulationError(f"เรียก ngspice ไม่ได้: {exc}") from exc

        log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        log = log + "\n" + (completed.stderr or "")

        if completed.returncode != 0:
            raise SimulationError(
                f"ngspice run ล้มเหลว (exit code {completed.returncode})",
                _excerpt(log),
            )
        if not log.strip():
            raise SimulationError("ngspice ไม่เขียนผลลัพธ์เลย (log ว่าง)")

        if analysis == "dc":
            values = parse_dc(log, params)
            series: dict[str, list[float]] = {}
        elif analysis == "ac":
            series = parse_ac(log)
            values = {}
            if series["gain_db"]:
                imax = max(range(len(series["gain_db"])), key=series["gain_db"].__getitem__)
                values["MAX_GAIN_DB"] = series["gain_db"][imax]
                values["GAIN_FREQ_HZ"] = series["freq"][imax]
                values["PHASE_AT_MAX_DEG"] = series["phase_deg"][imax]
        else:
            series = parse_transient(log)
            vin, vout = series["vin"], series["vout"]
            mean_in = sum(vin) / len(vin)
            mean_out = sum(vout) / len(vout)
            values = {
                "VIN_PEAK": max(abs(v - mean_in) for v in vin),
                "VOUT_PEAK": max(abs(v - mean_out) for v in vout),
                # Evidence for the CE inversion claim, computed from the run.
                "INVERSION_CORR": _correlation(vin, vout),
            }

        return SimulationResult(
            analysis=analysis,
            engine_version=engine_version(binary),
            values=values,
            series=series,
            log_excerpt=_excerpt(log),
            netlist=netlist,
            sweep_note=(
                "หาจุดตัด -3 dB ไม่พบในช่วง sweep นี้ (not determined in sweep range)"
                if analysis == "ac" and series.get("gain_db") and max(series["gain_db"]) < -3
                else ""
            ),
        )


# ---------------------------------------------------------------------------
# Plot generation -- SVG built from the arrays returned by ngspice.
# ---------------------------------------------------------------------------


def _polyline(
    xs: list[float],
    ys: list[float],
    x_scale: str = "linear",
    y_min: float | None = None,
    y_max: float | None = None,
) -> str:
    """Map real ngspice arrays into the 860x280 SVG viewport."""
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if x_scale == "log":
        pairs = [(x, y) for x, y in pairs if x > 0]
    if len(pairs) < 2:
        return ""

    if x_scale == "log":
        lx0, lx1 = math.log10(pairs[0][0]), math.log10(pairs[-1][0])
        x_of = lambda x: 58 + (math.log10(x) - lx0) / (lx1 - lx0 or 1) * 760
    else:
        x0, x1 = pairs[0][0], pairs[-1][0]
        x_of = lambda x: 58 + (x - x0) / (x1 - x0 or 1) * 760

    lo = y_min if y_min is not None else min(y for _, y in pairs)
    hi = y_max if y_max is not None else max(y for _, y in pairs)
    span = hi - lo or 1.0
    step = max(1, len(pairs) // 240)
    points = [
        f"{x_of(x):.1f},{238 - (y - lo) / span * 212:.1f}"
        for x, y in pairs[::step]
    ]
    return " ".join(points)


def _svg_frame(
    title: str,
    inner: str,
    x_label: str,
    y_label: str,
    legend: str = "",
    y_ticks: tuple[float, float] | None = None,
    x_ticks: tuple[float, float] | None = None,
) -> str:
    """Frame an SVG; optional numeric ticks come from the actual data range."""
    ticks = ""
    if y_ticks:
        ticks += (
            f'<text x="62" y="30" font-size="10" fill="#486275">{y_ticks[1]:.4g}</text>'
            f'<text x="62" y="234" font-size="10" fill="#486275">{y_ticks[0]:.4g}</text>'
        )
    if x_ticks:
        ticks += (
            f'<text x="60" y="252" font-size="10" fill="#486275">{x_ticks[0]:.4g}</text>'
            f'<text x="735" y="252" font-size="10" fill="#486275">{x_ticks[1]:.4g}</text>'
        )
    return (
        f'<svg viewBox="0 0 860 280" role="img" aria-label="{title}" '
        'style="width:100%;height:auto;background:#fff">'
        '<rect width="860" height="280" fill="#fff"/>'
        f'<text x="14" y="16" font-size="13" fill="#264c6f">{title}</text>'
        '<line x1="58" y1="22" x2="58" y2="238" stroke="#9cb2c2"/>'
        '<line x1="58" y1="238" x2="818" y2="238" stroke="#9cb2c2"/>'
        f'{inner}'
        f'{ticks}'
        f'<text x="60" y="270" font-size="11" fill="#486275">{x_label}</text>'
        f'<text x="60" y="32" font-size="11" fill="#486275">{y_label}</text>'
        f'<text x="600" y="32" font-size="11" fill="#486275">{legend}</text>'
        "</svg>"
    )


def build_plots(result: SimulationResult) -> dict[str, str]:
    """Create inline SVG strings from parsed ngspice arrays."""
    plots: dict[str, str] = {}
    if result.analysis == "ac":
        s = result.series
        gain_line = _polyline(s["freq"], s["gain_db"], "log") if "gain_db" in s else ""
        phase_line = _polyline(s["freq"], s["phase_deg"], "log") if "phase_deg" in s else ""
        if gain_line:
            plots["gain"] = _svg_frame(
                "AC gain |Vout/Vin| (dB)",
                f'<polyline points="{gain_line}" fill="none" stroke="#167e93" stroke-width="2"/>',
                "Frequency (Hz, log scale)",
                "Gain (dB)",
                y_ticks=(min(s["gain_db"]), max(s["gain_db"])),
                x_ticks=(s["freq"][0], s["freq"][-1]),
            )
        if phase_line:
            plots["phase"] = _svg_frame(
                "AC phase Vout - Vin (degrees)",
                f'<polyline points="{phase_line}" fill="none" stroke="#c77a35" stroke-width="2"/>',
                "Frequency (Hz, log scale)",
                "Phase (deg)",
                y_ticks=(min(s["phase_deg"]), max(s["phase_deg"])),
                x_ticks=(s["freq"][0], s["freq"][-1]),
            )
    elif result.analysis == "transient":
        s = result.series
        if "vin" in s and "vout" in s:
            vin_line = _polyline(s["time"], s["vin"])
            vout_line = _polyline(s["time"], s["vout"])
            if vin_line and vout_line:
                levels = s["vin"] + s["vout"]
                plots["waveform"] = _svg_frame(
                    "Transient Vin / Vout (V vs s)",
                    f'<polyline points="{vin_line}" fill="none" stroke="#0c8e83" stroke-width="2"/>'
                    f'<polyline points="{vout_line}" fill="none" stroke="#c77a35" stroke-width="2"/>',
                    "Time (s)",
                    "Voltage (V)",
                    y_ticks=(min(levels), max(levels)),
                    x_ticks=(s["time"][0], s["time"][-1]),
                )
    return plots
