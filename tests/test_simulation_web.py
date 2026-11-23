"""HTTP tests for the Lab 04 simulator route (engine calls are mocked)."""

from __future__ import annotations

import unittest
from unittest import mock

import app as web_app
import spice_engine as se


DEFAULT_FORM = {
    "analysis": "dc",
    **se.DEFAULT_SIM_VALUES,
}


def _by_analysis(params, analysis):
    """Mock side effect matching run_simulation(params, analysis)."""
    return _result(analysis)


def _result(analysis: str) -> se.SimulationResult:
    if analysis == "dc":
        return se.SimulationResult(
            analysis="dc",
            values={"VB": 1.9, "VE": 1.2, "VC": 9.1, "VCE": 7.9, "IC": 0.00127},
            log_excerpt="fake .op log",
            netlist="fake deck",
        )
    if analysis == "ac":
        return se.SimulationResult(
            analysis="ac",
            values={"MAX_GAIN_DB": 12.5, "GAIN_FREQ_HZ": 1000.0, "PHASE_AT_MAX_DEG": -179.0},
            series={
                "freq": [1.0, 1000.0, 1e5],
                "gain_db": [0.0, 12.5, -3.0],
                "phase_deg": [0.0, -179.0, -190.0],
            },
            log_excerpt="fake .ac log",
            netlist="fake deck",
        )
    return se.SimulationResult(
        analysis="transient",
        values={"VIN_PEAK": 0.01, "VOUT_PEAK": 0.08, "INVERSION_CORR": -0.999},
        series={
            "time": [0.0, 1e-4, 2e-4],
            "vin": [0.0, 0.01, 0.0],
            "vout": [7.0, 6.8, 7.2],
        },
        log_excerpt="fake .tran log",
        netlist="fake deck",
    )


class SimulatorPageTest(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_get_simulator_returns_form_with_idle_status(self):
        response = self.client.get("/simulator")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('action="/simulate"', body)
        self.assertIn('id="run-status">Idle', body)
        self.assertNotIn("Engine: ngspice", body)  # badge appears only after a run
        self.assertIn('value="100000"', body)

    def test_get_simulator_selects_ac_from_query(self):
        body = self.client.get("/simulator?analysis=ac").get_data(as_text=True)
        self.assertIn('value="ac" checked', body)

    def test_get_simulator_unknown_analysis_falls_back_to_dc(self):
        body = self.client.get("/simulator?analysis=foo").get_data(as_text=True)
        self.assertIn('value="dc" checked', body)

    def test_index_links_to_simulator(self):
        self.assertIn("/simulator", self.client.get("/").get_data(as_text=True))


class SimulateRouteTest(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_unknown_analysis_returns_400_without_results(self):
        response = self.client.post("/simulate", data=dict(DEFAULT_FORM, analysis="foo"))
        self.assertEqual(response.status_code, 400)
        body = response.get_data(as_text=True)
        self.assertIn("โหมดวิเคราะห์ไม่ถูกต้อง", body)
        self.assertNotIn('id="run-status">Success', body)

    def test_invalid_re_returns_400_without_results(self):
        response = self.client.post("/simulate", data=dict(DEFAULT_FORM, RE="0"))
        self.assertEqual(response.status_code, 400)
        body = response.get_data(as_text=True)
        self.assertIn("RE", body)
        self.assertIn('id="run-status">Error', body)
        self.assertNotIn('id="run-status">Success', body)
        self.assertNotIn("fake .op log", body)

    def test_engine_failure_returns_503_and_no_stale_success(self):
        failure = se.SimulationError("ngspice ล้มเหลว", "fake tail")
        with mock.patch.object(web_app.spice_engine, "run_simulation", side_effect=failure):
            response = self.client.post("/simulate", data=DEFAULT_FORM)
        self.assertEqual(response.status_code, 503)
        body = response.get_data(as_text=True)
        self.assertIn("ngspice ล้มเหลว", body)
        self.assertIn('id="run-status">Error', body)
        self.assertNotIn('id="run-status">Success', body)
        self.assertNotIn('id="spice-results"', body)

    def test_dc_success_shows_spice_values_and_separate_reference(self):
        with mock.patch.object(
            web_app.spice_engine, "run_simulation", return_value=_result("dc")
        ) as run:
            response = self.client.post("/simulate", data=DEFAULT_FORM)
        self.assertEqual(response.status_code, 200)
        # DC is the selected analysis, but AC + transient must also run so
        # that both target-screen plots come from this request.
        self.assertEqual(
            [call.args[1] for call in run.call_args_list], ["dc", "ac", "transient"]
        )
        body = response.get_data(as_text=True)
        self.assertIn('id="run-status">Success', body)
        self.assertIn("Engine: ngspice", body)
        self.assertIn('id="dc-vce">7.900 V', body)
        self.assertIn('id="dc-ic">1.270 mA', body)
        self.assertIn('id="analytical-reference"', body)
        self.assertIn("ngspice .op", body)

    def test_ac_success_renders_bode_plots(self):
        with mock.patch.object(
            web_app.spice_engine, "run_simulation", return_value=_result("ac")
        ):
            response = self.client.post("/simulate", data=dict(DEFAULT_FORM, analysis="ac"))
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('id="plot-gain"', body)
        self.assertIn('id="plot-phase"', body)
        self.assertIn("<polyline", body)
        self.assertIn('id="ac-gain">12.50 dB', body)

    def test_transient_success_renders_waveform(self):
        with mock.patch.object(
            web_app.spice_engine, "run_simulation", return_value=_result("transient")
        ):
            response = self.client.post(
                "/simulate", data=dict(DEFAULT_FORM, analysis="transient")
            )
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('id="plot-waveform"', body)
        self.assertIn('id="tran-samples">3', body)
        self.assertIn('id="tran-correlation">-0.9990', body)
        self.assertIn('id="inversion-note"', body)
        self.assertIn("Vin (teal)", body)

    def test_dc_run_renders_both_target_plots(self):
        with mock.patch.object(
            web_app.spice_engine, "run_simulation", side_effect=_by_analysis
        ):
            response = self.client.post("/simulate", data=DEFAULT_FORM)
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        for plot_id in ("plot-gain", "plot-phase", "plot-waveform"):
            self.assertIn(f'id="{plot_id}"', body)

    def test_ac_run_renders_bode_and_waveform(self):
        with mock.patch.object(
            web_app.spice_engine, "run_simulation", side_effect=_by_analysis
        ) as run:
            response = self.client.post("/simulate", data=dict(DEFAULT_FORM, analysis="ac"))
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([call.args[1] for call in run.call_args_list], ["ac", "transient"])
        for plot_id in ("plot-gain", "plot-phase", "plot-waveform"):
            self.assertIn(f'id="{plot_id}"', body)
        self.assertIn("-0.9990", body)  # transient summary of the same run

    def test_transient_run_renders_bode_and_waveform(self):
        with mock.patch.object(
            web_app.spice_engine, "run_simulation", side_effect=_by_analysis
        ) as run:
            response = self.client.post(
                "/simulate", data=dict(DEFAULT_FORM, analysis="transient")
            )
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([call.args[1] for call in run.call_args_list], ["transient", "ac"])
        for plot_id in ("plot-gain", "plot-phase", "plot-waveform"):
            self.assertIn(f'id="{plot_id}"', body)
        self.assertIn("12.50 dB", body)  # AC summary of the same run

    def test_secondary_plot_failure_has_no_stale_success(self):
        def fail_secondary(params, analysis):
            if analysis == "dc":
                return _result("dc")
            raise se.SimulationError("AC ล้มเหลว", "fake tail")

        with mock.patch.object(
            web_app.spice_engine, "run_simulation", side_effect=fail_secondary
        ):
            response = self.client.post("/simulate", data=DEFAULT_FORM)
        self.assertEqual(response.status_code, 503)
        body = response.get_data(as_text=True)
        self.assertIn("AC ล้มเหลว", body)
        self.assertNotIn('id="run-status">Success', body)
        self.assertNotIn('id="spice-results"', body)
        self.assertNotIn('id="plot-gain"', body)

    def test_lab03_routes_still_work(self):
        self.assertEqual(self.client.get("/health").json, {"status": "ok"})
        self.assertEqual(self.client.get("/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
