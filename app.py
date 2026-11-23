"""Flask HTTP layer for the BJT DC Bias web app.

Responsibilities: read the mode, parse the incoming request, call dc_bias,
and render the Jinja template. No physics equations live in this file.
"""

from __future__ import annotations

from typing import Any

import dc_bias
import spice_engine

from flask import Flask, render_template, request

app = Flask(__name__)


def _template_context(
    mode: str,
    values: dict[str, str] | None = None,
    *,
    result: dc_bias.BiasResult | None = None,
    error: str | None = None,
    invalid_mode: bool = False,
) -> dict[str, Any]:
    fields = dc_bias.mode_fields(mode) if dc_bias.is_valid_mode(mode) else ()
    if values is None:
        values = dc_bias.default_values(mode) if dc_bias.is_valid_mode(mode) else {}
    return {
        "mode": mode,
        "modes": dc_bias.MODES,
        "mode_labels": dc_bias.MODE_LABELS,
        "mode_label": dc_bias.MODE_LABELS.get(mode, mode),
        "fields": fields,
        "field_labels": dc_bias.FIELD_LABELS,
        "values": {name: values.get(name, "") for name in fields},
        "result": result,
        "display": dc_bias.display_results(result) if result is not None else None,
        "error": error,
        "invalid_mode": invalid_mode,
    }


@app.get("/")
def index() -> tuple[str, int] | str:
    """Render the form for the requested mode (GET query parameter)."""
    mode = request.args.get("mode", dc_bias.DEFAULT_MODE)
    if not dc_bias.is_valid_mode(mode):
        return (
            render_template("index.html", **_template_context(mode, invalid_mode=True)),
            400,
        )
    return render_template("index.html", **_template_context(mode))


@app.post("/calculate")
def calculate() -> tuple[str, int] | str:
    """Calculate the DC operating point from a submitted form."""
    mode = request.form.get("mode", dc_bias.DEFAULT_MODE)
    if not dc_bias.is_valid_mode(mode):
        return (
            render_template("index.html", **_template_context(mode, invalid_mode=True)),
            400,
        )

    raw_values = {
        name: request.form.get(name) for name in dc_bias.mode_fields(mode)
    }

    try:
        parsed = dc_bias.parse_form(raw_values, mode)
    except dc_bias.ValidationError as exc:
        return (
            render_template(
                "index.html",
                **_template_context(mode, raw_values, error=exc.message),
            ),
            400,
        )

    result = dc_bias.calculate(mode, parsed)
    return render_template("index.html", **_template_context(mode, raw_values, result=result))


def _simulator_context(
    analysis: str,
    values: dict[str, str] | None = None,
    *,
    result: spice_engine.SimulationResult | None = None,
    ac_result: spice_engine.SimulationResult | None = None,
    tran_result: spice_engine.SimulationResult | None = None,
    plots: dict[str, str] | None = None,
    error: spice_engine.SimulationError | None = None,
) -> dict[str, Any]:
    """Build template context for the CE simulator page."""
    if values is None:
        values = dict(spice_engine.DEFAULT_SIM_VALUES)
    reference = None
    if result is not None and analysis == "dc":
        reference = dc_bias.calculate_divider(
            VCC=float(values["VCC"]),
            R1=float(values["R1"]),
            R2=float(values["R2"]),
            RC=float(values["RC"]),
            RE=float(values["RE"]),
            beta=100.0,
            VBE=0.70,
        )
    return {
        "analysis": analysis,
        "analyses": spice_engine.ANALYSES,
        "values": {name: values.get(name, "") for name in spice_engine.RANGES},
        "field_labels": spice_engine.FIELD_LABELS,
        "model": spice_engine.BJT_MODEL,
        "model_card": spice_engine.MODEL_CARD,
        "result": result,
        # Both plots are always on screen; each comes from its own real run.
        "ac_result": ac_result,
        "tran_result": tran_result,
        "plots": plots or {},
        "error": error,
        "reference": reference,
        "reference_display": dc_bias.display_results(reference) if reference else None,
        "engine_version": spice_engine.engine_version() if result is not None else "",
    }


@app.get("/simulator")
def simulator() -> tuple[str, int] | str:
    """CE voltage-divider simulator page (Lab 04)."""
    analysis = request.args.get("analysis", "dc")
    if analysis not in spice_engine.ANALYSES:
        analysis = "dc"
    return render_template("simulator.html", **_simulator_context(analysis))


@app.post("/simulate")
def simulate() -> tuple[str, int] | str:
    """Run a real ngspice analysis (DC / AC / transient)."""
    analysis = request.form.get("analysis", "dc")
    if analysis not in spice_engine.ANALYSES:
        return render_template(
            "simulator.html",
            **_simulator_context(
                "dc",
                error=spice_engine.SimulationError("โหมดวิเคราะห์ไม่ถูกต้อง"),
            ),
        ), 400

    raw = {name: request.form.get(name) for name in spice_engine.RANGES}
    try:
        params = spice_engine.validate_params(raw)
    except spice_engine.SimulationError as exc:
        return (
            render_template("simulator.html", **_simulator_context(analysis, raw, error=exc)),
            400,
        )

    # The target screen shows BOTH the Bode response and the waveform no
    # matter which tab is selected. Run the analyses needed for those plots;
    # any failure fails the whole request so no stale plot can survive.
    try:
        results = {analysis: spice_engine.run_simulation(params, analysis)}
        for needed in ("ac", "transient"):
            if needed not in results:
                results[needed] = spice_engine.run_simulation(params, needed)
    except spice_engine.SimulationError as exc:
        return (
            render_template("simulator.html", **_simulator_context(analysis, raw, error=exc)),
            503,
        )

    plots: dict[str, str] = {}
    for run in results.values():
        plots.update(spice_engine.build_plots(run))
    return render_template(
        "simulator.html",
        **_simulator_context(
            analysis,
            raw,
            result=results[analysis],
            ac_result=results.get("ac"),
            tran_result=results.get("transient"),
            plots=plots,
        ),
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Small liveness endpoint used by the public-link setup."""
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
