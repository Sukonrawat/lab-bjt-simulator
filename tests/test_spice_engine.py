"""Engineering tests for the ngspice adapter (no Flask, no real solver needed)."""

from __future__ import annotations

import os
import unittest
from unittest import mock

import spice_engine as se


# Minimal tables in the exact format ngspice -b -o writes (index first).
DC_LOG = """
Circuit: test
Index   v(b)            v(e)            v(c)            v(out)
0       1.949112e+00    1.289454e+00    9.189410e+00    0.000000e+00

Index   vcc#branch
0       -1.500000e-02
"""

AC_LOG_IN = """
Index   frequency       vdb(in)         vp(in)
0       1.000000e+00    -4.000000e+01   0.000000e+00
1       1.000000e+03    -4.000000e+01   0.000000e+00
2       1.000000e+05    -4.000000e+01   0.000000e+00
"""
# ngspice-47 in this environment writes VP() in radians (verified with an RC).
AC_LOG_OUT = """
Index   frequency       vdb(out)        vp(out)
0       1.000000e+00    -3.900000e+01   -1.745329e+00
1       1.000000e+03    -3.500000e+01   -2.967060e+00
2       1.000000e+05    -4.500000e+01   -1.745330e-01
"""

TRAN_LOG = """
Index   time            v(in)           v(out)
0       0.000000e+00    0.000000e+00    7.000000e+00
1       1.000000e-04    1.000000e-02    6.900000e+00
2       2.000000e-04    0.000000e+00    7.100000e+00
3       3.000000e-04    -1.000000e-02   7.200000e+00
"""


class ValidationTest(unittest.TestCase):
    def test_default_values_are_valid(self):
        params = se.validate_params(se.DEFAULT_SIM_VALUES)
        self.assertEqual(params["VCC"], 12.0)
        self.assertEqual(params["FREQ"], 1000.0)

    def test_missing_field_is_rejected(self):
        raw = dict(se.DEFAULT_SIM_VALUES)
        del raw["RE"]
        with self.assertRaises(se.SimulationError) as ctx:
            se.validate_params(raw)
        self.assertIn("RE", str(ctx.exception))

    def test_non_numeric_value_is_rejected(self):
        raw = dict(se.DEFAULT_SIM_VALUES, RC="abc")
        with self.assertRaises(se.SimulationError):
            se.validate_params(raw)

    def test_spice_metacharacters_are_rejected_before_netlist(self):
        raw = dict(se.DEFAULT_SIM_VALUES, VCC="12; rm -rf /")
        with self.assertRaises(se.SimulationError):
            se.validate_params(raw)

    def test_zero_re_is_rejected(self):
        raw = dict(se.DEFAULT_SIM_VALUES, RE="0")
        with self.assertRaises(se.SimulationError):
            se.validate_params(raw)

    def test_out_of_range_frequency_is_rejected(self):
        raw = dict(se.DEFAULT_SIM_VALUES, FREQ="-1")
        with self.assertRaises(se.SimulationError):
            se.validate_params(raw)


class NetlistTest(unittest.TestCase):
    def setUp(self):
        self.params = se.validate_params(se.DEFAULT_SIM_VALUES)

    def test_all_analyses_include_the_circuit_and_model(self):
        for analysis in se.ANALYSES:
            netlist = se.build_netlist(self.params, analysis)
            self.assertIn("VCC vcc 0 DC 12", netlist)
            self.assertIn("Q1 c b e QNPN", netlist)
            self.assertIn(se.MODEL_CARD, netlist)
            self.assertTrue(netlist.rstrip().endswith(".END"))

    def test_dc_netlist_uses_op(self):
        self.assertIn(".OP", se.build_netlist(self.params, "dc"))

    def test_ac_netlist_sweeps_and_prints_both_nodes(self):
        netlist = se.build_netlist(self.params, "ac")
        self.assertIn(".AC DEC 100 1 100MEG", netlist)
        self.assertIn("VDB(in)", netlist)
        self.assertIn("VDB(out)", netlist)

    def test_transient_stop_is_four_periods(self):
        params = dict(self.params, FREQ=1000.0)
        netlist = se.build_netlist(params, "transient")
        self.assertIn(".TRAN 2.5e-06 0.004", netlist)

    def test_unknown_analysis_is_rejected(self):
        with self.assertRaises(se.SimulationError):
            se.build_netlist(self.params, "foo")


class ParserTest(unittest.TestCase):
    def test_parse_dc_reads_supply_current_separately(self):
        values = se.parse_dc(DC_LOG, se.validate_params(se.DEFAULT_SIM_VALUES))
        self.assertAlmostEqual(values["VB"], 1.949112, places=6)
        self.assertAlmostEqual(values["VCE"], 9.189410 - 1.289454, places=6)
        # IC comes from RC's voltage drop, not VCC's branch current.
        self.assertAlmostEqual(values["IC"], (12 - 9.189410) / 2200, places=8)
        self.assertAlmostEqual(values["I_SUPPLY"], 0.015, places=8)

    def test_parse_ac_computes_gain_and_phase_from_two_tables(self):
        series = se.parse_ac(AC_LOG_IN + AC_LOG_OUT)
        self.assertEqual(series["freq"], [1.0, 1000.0, 100000.0])
        self.assertEqual(series["gain_db"], [1.0, 5.0, -5.0])
        for actual, expected in zip(series["phase_deg"], [-100.0, -170.0, -10.0]):
            self.assertAlmostEqual(actual, expected, places=3)

    def test_parse_transient_keeps_time_and_voltages(self):
        series = se.parse_transient(TRAN_LOG)
        self.assertEqual(series["time"], [0.0, 1e-4, 2e-4, 3e-4])
        self.assertEqual(series["vin"][2], 0.0)
        self.assertEqual(series["vout"][3], 7.2)

    def test_empty_log_raises_useful_error(self):
        with self.assertRaises(se.SimulationError) as ctx:
            se.parse_transient("no tables here")
        self.assertIn("ไม่ได้ส่งข้อมูล", str(ctx.exception))


class EngineLookupTest(unittest.TestCase):
    def test_missing_engine_is_reported(self):
        env = {"NGSPICE_BIN": ""}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch(
            "shutil.which", return_value=None
        ):
            with self.assertRaises(se.SimulationError) as ctx:
                se.resolve_ngspice()
        self.assertIn("ไม่พบ ngspice", str(ctx.exception))

    def test_bad_env_override_is_reported(self):
        with mock.patch.dict(os.environ, {"NGSPICE_BIN": "/no/such/ngspice"}):
            with self.assertRaises(se.SimulationError):
                se.resolve_ngspice()

    def test_engine_version_never_raises(self):
        with mock.patch.dict(os.environ, {"NGSPICE_BIN": ""}, clear=True), mock.patch(
            "shutil.which", return_value=None
        ):
            self.assertEqual(se.engine_version(), "")


class PlotTest(unittest.TestCase):
    def test_ac_plots_come_from_series(self):
        result = se.SimulationResult(analysis="ac", series=se.parse_ac(AC_LOG_IN + AC_LOG_OUT))
        plots = se.build_plots(result)
        self.assertIn("gain", plots)
        self.assertIn("phase", plots)
        self.assertIn("<polyline", plots["gain"])
        self.assertIn("Frequency (Hz, log scale)", plots["gain"])

    def test_transient_plot_shows_both_waveforms(self):
        result = se.SimulationResult(
            analysis="transient", series=se.parse_transient(TRAN_LOG)
        )
        svg = se.build_plots(result)["waveform"]
        self.assertEqual(svg.count("<polyline"), 2)

    def test_empty_series_produces_no_plot(self):
        result = se.SimulationResult(
            analysis="ac", series={"freq": [], "gain_db": [], "phase_deg": []}
        )
        self.assertEqual(se.build_plots(result), {})


@unittest.skipUnless(os.environ.get("NGSPICE_BIN"), "set NGSPICE_BIN to run the real solver test")
class RealEngineTest(unittest.TestCase):
    def test_all_three_analyses_run(self):
        params = se.validate_params(se.DEFAULT_SIM_VALUES)
        for analysis in se.ANALYSES:
            result = se.run_simulation(params, analysis)
            self.assertEqual(result.engine, "ngspice")
            self.assertTrue(result.values or result.series)


if __name__ == "__main__":
    unittest.main()
