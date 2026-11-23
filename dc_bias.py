"""Independent engineering calculations for NPN common-emitter DC bias.

This module knows nothing about Flask, HTML, or HTTP. It accepts plain
Python values (SI units internally), validates them per bias mode, and
returns a :class:`BiasResult` describing the DC operating point.

Assumption: Forward-Active Approximation -- beta and VBE are constant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

MODES: tuple[str, ...] = ("divider", "fixed", "emitter")
DEFAULT_MODE: str = "divider"

MODE_FIELDS: dict[str, tuple[str, ...]] = {
    "divider": ("VCC", "R1", "R2", "RC", "RE", "beta", "VBE"),
    "fixed": ("VCC", "RB", "RC", "beta", "VBE"),
    "emitter": ("VCC", "RB", "RE", "RC", "beta", "VBE"),
}

MODE_LABELS: dict[str, str] = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

FIELD_LABELS: dict[str, str] = {
    "VCC": "VCC (V)",
    "R1": "R1 (Ω)",
    "R2": "R2 (Ω)",
    "RB": "RB (Ω)",
    "RC": "RC (Ω)",
    "RE": "RE (Ω)",
    "beta": "β (beta)",
    "VBE": "VBE (V)",
}

# Values pre-filled in the browser form (taken from the lab sheet).
DEFAULT_VALUES: dict[str, dict[str, str]] = {
    "divider": {
        "VCC": "12",
        "R1": "100000",
        "R2": "22000",
        "RC": "2200",
        "RE": "1000",
        "beta": "100",
        "VBE": "0.70",
    },
    "fixed": {
        "VCC": "12",
        "RB": "1000000",
        "RC": "2200",
        "beta": "100",
        "VBE": "0.70",
    },
    "emitter": {
        "VCC": "12",
        "RB": "1000000",
        "RE": "1000",
        "RC": "2200",
        "beta": "100",
        "VBE": "0.70",
    },
}

VCE_SAT: float = 0.20
VCE_NEAR_SAT: float = 0.50


class ValidationError(ValueError):
    """Raised when user-supplied input is missing or physically invalid."""

    def __init__(self, message: str, field_name: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field_name = field_name


@dataclass
class BiasResult:
    """DC operating point in SI units plus region diagnostics."""

    mode: str
    values: dict[str, float]
    VTH: float | None = None
    RTH: float | None = None
    IB: float = 0.0
    IC: float = 0.0
    IE: float = 0.0
    VB: float = 0.0
    VE: float = 0.0
    VC: float = 0.0
    VCE: float = 0.0
    region: str = "Forward-Active"
    warnings: list[str] = field(default_factory=list)

    @property
    def is_forward_active(self) -> bool:
        return self.region == "Forward-Active"

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)


def is_valid_mode(mode: Any) -> bool:
    """Return True only for one of the three supported bias modes."""
    return isinstance(mode, str) and mode in MODES


def mode_fields(mode: str) -> tuple[str, ...]:
    """Return the field names used by *mode*."""
    if not is_valid_mode(mode):
        raise ValidationError("โหมดไบอัสไม่ถูกต้อง")
    return MODE_FIELDS[mode]


def default_values(mode: str) -> dict[str, str]:
    """Return a fresh copy of the lab reference values for *mode*."""
    if not is_valid_mode(mode):
        raise ValidationError("โหมดไบอัสไม่ถูกต้อง")
    return dict(DEFAULT_VALUES[mode])


_MESSAGE_NAMES: dict[str, str] = {"beta": "β"}


def _as_float(raw: Any, name: str) -> float:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise ValidationError(f"กรอก {name} ให้ครบ", name)
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} ต้องเป็นตัวเลข", name) from exc


def parse_form(form: Mapping[str, Any], mode: str) -> dict[str, float]:
    """Validate and convert the fields required by *mode* into floats.

    Extra keys (for example a hidden ``mode`` field) are ignored, which is
    what makes the same function reusable from Flask request.form and from
    unit tests with a plain dict.
    """
    if not is_valid_mode(mode):
        raise ValidationError("โหมดไบอัสไม่ถูกต้อง")

    parsed: dict[str, float] = {}
    for name in mode_fields(mode):
        value = _as_float(form.get(name), _MESSAGE_NAMES.get(name, name))
        parsed[name] = value

    vcc = parsed["VCC"]
    vbe = parsed["VBE"]
    beta = parsed["beta"]

    if vcc <= 0:
        raise ValidationError("VCC ต้องมากกว่า 0", "VCC")
    if vbe <= 0:
        raise ValidationError("VBE ต้องมากกว่า 0", "VBE")
    if beta <= 0:
        raise ValidationError("β ต้องมากกว่า 0", "beta")

    positive_fields = ("R1", "R2", "RB", "RC")
    for name in positive_fields:
        if name in parsed and parsed[name] <= 0:
            raise ValidationError(f"{name} ต้องมากกว่า 0", name)
    if "RE" in parsed and parsed["RE"] < 0:
        raise ValidationError("RE ต้องไม่ติดลบ", "RE")

    return parsed


def _finish(
    mode: str,
    values: dict[str, float],
    ib: float,
    vth: float | None,
    rth: float | None,
    cutoff_message: str,
) -> BiasResult:
    """Apply the common IC/IE/VE/VB/VC/VCE equations and region checks."""
    beta = values["beta"]
    vcc = values["VCC"]
    vbe = values["VBE"]
    rc = values["RC"]
    re = values.get("RE", 0.0)

    result = BiasResult(mode=mode, values=dict(values), VTH=vth, RTH=rth)

    if ib <= 0:
        # Cutoff: no base current, so there is no drop across RB/RTH.
        result.IB = 0.0
        result.IC = 0.0
        result.IE = 0.0
        result.VE = 0.0
        result.VB = vth if vth is not None else vcc
        result.VC = vcc
        result.VCE = vcc
        result.region = "Cutoff"
        result.warnings.append(cutoff_message)
        return result

    result.IB = ib
    result.IC = beta * ib
    result.IE = (beta + 1) * ib
    result.VE = result.IE * re
    result.VB = result.VE + vbe
    result.VC = vcc - result.IC * rc
    result.VCE = result.VC - result.VE

    if result.VCE < VCE_SAT:
        result.region = "Saturation"
        result.warnings.append(
            f"Saturation: VCE = {result.VCE:.3f} V ต่ำกว่า VCE(sat) ≈ {VCE_SAT:.2f} V "
            "สมมติฐาน Forward-Active อาจใช้ไม่ได้"
        )
    elif result.VCE < VCE_NEAR_SAT:
        result.region = "Forward-Active"
        result.warnings.append(
            f"ใกล้ขอบ saturation: VCE = {result.VCE:.3f} V ต่ำกว่า {VCE_NEAR_SAT:.2f} V"
        )
    else:
        result.region = "Forward-Active"

    return result


def calculate_divider(
    VCC: float,
    R1: float,
    R2: float,
    RC: float,
    RE: float,
    beta: float,
    VBE: float,
) -> BiasResult:
    """Voltage Divider Bias: IB = (VTH - VBE) / (RTH + (beta+1) RE)."""
    values = {
        "VCC": VCC,
        "R1": R1,
        "R2": R2,
        "RC": RC,
        "RE": RE,
        "beta": beta,
        "VBE": VBE,
    }
    vth = VCC * R2 / (R1 + R2)
    rth = R1 * R2 / (R1 + R2)
    cutoff = f"Cutoff: VTH = {vth:.3f} V ≤ VBE = {VBE:.3f} V ทรานซิสเตอร์ไม่นำกระแส"
    ib = (vth - VBE) / (rth + (beta + 1) * RE)
    return _finish("divider", values, ib, vth, rth, cutoff)


def calculate_fixed(
    VCC: float,
    RB: float,
    RC: float,
    beta: float,
    VBE: float,
) -> BiasResult:
    """Fixed Bias: IB = (VCC - VBE) / RB, emitter tied directly to ground."""
    values = {"VCC": VCC, "RB": RB, "RC": RC, "beta": beta, "VBE": VBE}
    cutoff = f"Cutoff: VCC = {VCC:.3f} V ≤ VBE = {VBE:.3f} V ทรานซิสเตอร์ไม่นำกระแส"
    ib = (VCC - VBE) / RB
    return _finish("fixed", values, ib, None, None, cutoff)


def calculate_emitter(
    VCC: float,
    RB: float,
    RE: float,
    RC: float,
    beta: float,
    VBE: float,
) -> BiasResult:
    """Emitter Bias: IB = (VCC - VBE) / (RB + (beta+1) RE)."""
    values = {
        "VCC": VCC,
        "RB": RB,
        "RE": RE,
        "RC": RC,
        "beta": beta,
        "VBE": VBE,
    }
    cutoff = f"Cutoff: VCC = {VCC:.3f} V ≤ VBE = {VBE:.3f} V ทรานซิสเตอร์ไม่นำกระแส"
    ib = (VCC - VBE) / (RB + (beta + 1) * RE)
    return _finish("emitter", values, ib, None, None, cutoff)


def calculate(mode: str, values: Mapping[str, float]) -> BiasResult:
    """Dispatch to the calculator for *mode* using an already-parsed mapping."""
    if not is_valid_mode(mode):
        raise ValidationError("โหมดไบอัสไม่ถูกต้อง")
    values = dict(values)
    if mode == "divider":
        return calculate_divider(**{name: values[name] for name in MODE_FIELDS[mode]})
    if mode == "fixed":
        return calculate_fixed(**{name: values[name] for name in MODE_FIELDS[mode]})
    return calculate_emitter(**{name: values[name] for name in MODE_FIELDS[mode]})


def solve(mode: str, form: Mapping[str, Any]) -> BiasResult:
    """Convenience helper: parse a raw form mapping and calculate in one step."""
    return calculate(mode, parse_form(form, mode))


# ---------------------------------------------------------------------------
# Display helpers -- conversion to mA/uA happens only here, never above.
# ---------------------------------------------------------------------------


def format_voltage(value: float) -> str:
    return f"{value:.3f} V"


def format_current_amperes(value: float) -> str:
    """Show IC/IE in mA and IB in uA (caller decides which)."""
    return f"{value * 1000:.3f} mA"


def format_base_current(value: float) -> str:
    return f"{value * 1_000_000:.3f} µA"


def display_results(result: BiasResult) -> dict[str, str]:
    """Return formatted strings for the template (presentation layer only)."""
    return {
        "VTH": format_voltage(result.VTH) if result.VTH is not None else "—",
        "RTH": f"{result.RTH / 1000:.3f} kΩ" if result.RTH is not None else "—",
        "IB": format_base_current(result.IB),
        "IC": format_current_amperes(result.IC),
        "IE": format_current_amperes(result.IE),
        "VB": format_voltage(result.VB),
        "VE": format_voltage(result.VE),
        "VC": format_voltage(result.VC),
        "VCE": format_voltage(result.VCE),
    }
