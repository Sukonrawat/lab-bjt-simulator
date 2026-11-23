"""Engineering unit tests -- no Flask, no HTML, just the DC bias model."""

import unittest

import dc_bias


DIVIDER_REF = {
    "VCC": 12.0,
    "R1": 100_000.0,
    "R2": 22_000.0,
    "RC": 2_200.0,
    "RE": 1_000.0,
    "beta": 100.0,
    "VBE": 0.70,
}
FIXED_REF = {"VCC": 12.0, "RB": 1_000_000.0, "RC": 2_200.0, "beta": 100.0, "VBE": 0.70}
EMITTER_REF = {
    "VCC": 12.0,
    "RB": 1_000_000.0,
    "RE": 1_000.0,
    "RC": 2_200.0,
    "beta": 100.0,
    "VBE": 0.70,
}


class DividerBiasTest(unittest.TestCase):
    def test_default_mode_is_divider(self):
        self.assertEqual(dc_bias.DEFAULT_MODE, "divider")

    def test_mode_fields_divider(self):
        self.assertEqual(
            dc_bias.mode_fields("divider"),
            ("VCC", "R1", "R2", "RC", "RE", "beta", "VBE"),
        )

    def test_parse_form_divider_accepts_valid_values(self):
        parsed = dc_bias.parse_form(dc_bias.default_values("divider"), "divider")
        self.assertEqual(parsed, DIVIDER_REF)

    def test_a1_divider_reference_ic(self):
        result = dc_bias.calculate_divider(**DIVIDER_REF)
        self.assertAlmostEqual(result.IC, 1.2298581e-3, delta=1e-9)

    def test_a1_divider_reference_vce(self):
        result = dc_bias.calculate_divider(**DIVIDER_REF)
        self.assertAlmostEqual(result.VCE, 8.0521554, delta=1e-6)

    def test_a1_divider_reference_voltages(self):
        result = dc_bias.calculate_divider(**DIVIDER_REF)
        self.assertAlmostEqual(result.VB, 1.942157, delta=1e-5)
        self.assertAlmostEqual(result.VE, 1.242157, delta=1e-5)
        self.assertAlmostEqual(result.VC, 9.294312, delta=1e-5)
        self.assertAlmostEqual(result.VTH, 12 * 22_000 / 122_000, delta=1e-9)
        self.assertAlmostEqual(result.RTH, 100_000 * 22_000 / 122_000, delta=1e-6)

    def test_divider_is_forward_active(self):
        result = dc_bias.calculate_divider(**DIVIDER_REF)
        self.assertTrue(result.is_forward_active)
        self.assertEqual(result.warnings, [])

    def test_divider_cutoff_when_vth_below_vbe(self):
        values = dict(DIVIDER_REF, VBE=3.0)
        result = dc_bias.calculate_divider(**values)
        self.assertEqual(result.region, "Cutoff")
        self.assertEqual(result.IC, 0.0)
        self.assertTrue(any("Cutoff" in w for w in result.warnings))

    def test_parse_form_divider_requires_r1(self):
        form = dc_bias.default_values("divider")
        form.pop("R1")
        with self.assertRaises(dc_bias.ValidationError):
            dc_bias.parse_form(form, "divider")

    def test_parse_form_divider_rejects_bad_number(self):
        form = dc_bias.default_values("divider")
        form["R2"] = "abc"
        with self.assertRaises(dc_bias.ValidationError) as ctx:
            dc_bias.parse_form(form, "divider")
        self.assertIn("ตัวเลข", str(ctx.exception))

    def test_divider_larger_re_lowers_ic(self):
        base = dc_bias.calculate_divider(**DIVIDER_REF)
        larger = dc_bias.calculate_divider(**dict(DIVIDER_REF, RE=2_000.0))
        self.assertLess(larger.IC, base.IC)


class FixedBiasTest(unittest.TestCase):
    def test_mode_fields_fixed(self):
        self.assertEqual(dc_bias.mode_fields("fixed"), ("VCC", "RB", "RC", "beta", "VBE"))

    def test_a2_fixed_reference_operating_point(self):
        result = dc_bias.calculate_fixed(**FIXED_REF)
        self.assertAlmostEqual(result.IC, 1.130e-3, delta=1e-9)
        self.assertAlmostEqual(result.VCE, 9.514, delta=1e-6)

    def test_fixed_ve_is_zero(self):
        result = dc_bias.calculate_fixed(**FIXED_REF)
        self.assertEqual(result.VE, 0.0)
        self.assertAlmostEqual(result.VB, 0.70, delta=1e-12)

    def test_fixed_cutoff_when_vcc_below_vbe(self):
        result = dc_bias.calculate_fixed(**dict(FIXED_REF, VBE=12.0))
        self.assertEqual(result.region, "Cutoff")
        self.assertTrue(any("Cutoff" in w for w in result.warnings))

    def test_fixed_larger_rb_lowers_ic(self):
        base = dc_bias.calculate_fixed(**FIXED_REF)
        larger = dc_bias.calculate_fixed(**dict(FIXED_REF, RB=2_000_000.0))
        self.assertLess(larger.IC, base.IC)

    def test_fixed_saturation_warning(self):
        result = dc_bias.calculate_fixed(**dict(FIXED_REF, RB=10_000.0))
        self.assertEqual(result.region, "Saturation")
        self.assertTrue(any("Saturation" in w for w in result.warnings))


class EmitterBiasTest(unittest.TestCase):
    def test_mode_fields_emitter(self):
        self.assertEqual(
            dc_bias.mode_fields("emitter"),
            ("VCC", "RB", "RE", "RC", "beta", "VBE"),
        )

    def test_a3_emitter_reference_operating_point(self):
        result = dc_bias.calculate_emitter(**EMITTER_REF)
        self.assertAlmostEqual(result.IC, 1.026e-3, delta=1e-6)
        self.assertAlmostEqual(result.VCE, 8.705, delta=1e-3)

    def test_a4_larger_re_lowers_ic(self):
        base = dc_bias.calculate_emitter(**EMITTER_REF)
        larger = dc_bias.calculate_emitter(**dict(EMITTER_REF, RE=2_000.0))
        self.assertAlmostEqual(larger.IC, 0.940e-3, delta=1e-6)
        self.assertAlmostEqual(larger.VCE, 8.033, delta=1e-3)
        self.assertLess(larger.IC, base.IC)

    def test_emitter_ie_equals_ib_times_beta_plus_one(self):
        result = dc_bias.calculate_emitter(**EMITTER_REF)
        self.assertAlmostEqual(result.IE, 101 * result.IB, delta=1e-15)

    def test_emitter_vb_equals_ve_plus_vbe(self):
        result = dc_bias.calculate_emitter(**EMITTER_REF)
        self.assertAlmostEqual(result.VB, result.VE + 0.70, delta=1e-12)

    def test_emitter_cutoff_warning(self):
        result = dc_bias.calculate_emitter(**dict(EMITTER_REF, VBE=12.0))
        self.assertEqual(result.region, "Cutoff")
        self.assertTrue(any("Cutoff" in w for w in result.warnings))


class ModeAwareValidationTest(unittest.TestCase):
    def test_parse_form_fixed_requires_rb(self):
        form = dc_bias.default_values("fixed")
        form["RB"] = "0"
        with self.assertRaises(dc_bias.ValidationError) as ctx:
            dc_bias.parse_form(form, "fixed")
        self.assertEqual(str(ctx.exception), "RB ต้องมากกว่า 0")

    def test_parse_form_emitter_requires_re(self):
        form = dc_bias.default_values("emitter")
        form.pop("RE")
        with self.assertRaises(dc_bias.ValidationError):
            dc_bias.parse_form(form, "emitter")


if __name__ == "__main__":
    unittest.main()
