"""HTTP tests using Flask's built-in test client."""

import unittest

import app as web_app


class WebAppTest(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_get_index_returns_200_with_divider_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('action="/calculate"', body)
        self.assertIn('id="field-R1"', body)
        self.assertIn('id="field-R2"', body)

    def test_get_index_prefills_reference_values(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('value="100000"', body)
        self.assertIn('value="22000"', body)
        self.assertIn('value="0.70"', body)

    def test_get_index_has_mode_switch(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('name="mode"', body)
        self.assertIn("เปลี่ยนโหมด", body)

    def test_index_shows_visible_circuit_svg_for_every_mode(self):
        for mode, resistor in (("divider", "R1"), ("fixed", "RB"), ("emitter", "RB")):
            with self.subTest(mode=mode):
                body = self.client.get(f"/?mode={mode}").get_data(as_text=True)
                self.assertIn('class="bias-schematic"', body)
                self.assertIn("NPN common-emitter DC bias", body)
                self.assertIn(f">{resistor}<", body)
                self.assertIn("Q1 NPN", body)
                self.assertIn("GND", body)

    def test_a2_post_calculate_returns_backend_results(self):
        # Lab 03 A2 is the divider case in the web suite (name kept from Lab 02).
        response = self.client.post(
            "/calculate",
            data={
                "mode": "divider",
                "VCC": "12",
                "R1": "100000",
                "R2": "22000",
                "RC": "2200",
                "RE": "1000",
                "beta": "100",
                "VBE": "0.70",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("1.230 mA", body)
        self.assertIn("8.052 V", body)
        self.assertIn("Forward-Active", body)

    def test_post_divider_with_explicit_mode_keeps_a1_results(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "divider",
                "VCC": "12",
                "R1": "100000",
                "R2": "22000",
                "RC": "2200",
                "RE": "1000",
                "beta": "100",
                "VBE": "0.70",
            },
        )
        body = response.get_data(as_text=True)
        self.assertIn('id="ic-value">1.230 mA', body)
        self.assertIn('id="vce-value">8.052 V', body)

    def test_post_divider_shows_region_badge(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "divider",
                "VCC": "12",
                "R1": "100000",
                "R2": "22000",
                "RC": "2200",
                "RE": "1000",
                "beta": "100",
                "VBE": "0.70",
            },
        )
        self.assertIn('id="region-badge"', response.get_data(as_text=True))

    def test_post_divider_shows_all_six_voltages_and_currents(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "divider",
                "VCC": "12",
                "R1": "100000",
                "R2": "22000",
                "RC": "2200",
                "RE": "1000",
                "beta": "100",
                "VBE": "0.70",
            },
        )
        body = response.get_data(as_text=True)
        for key in ("vb", "ve", "vc", "vce", "ic", "ib", "ie"):
            self.assertIn(f'id="{key}-value"', body)

    def test_post_divider_cutoff_shows_warning(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "divider",
                "VCC": "12",
                "R1": "100000",
                "R2": "22000",
                "RC": "2200",
                "RE": "1000",
                "beta": "100",
                "VBE": "3.0",
            },
        )
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Cutoff", body)
        self.assertIn("alert-warning", body)


class ModeSelectionWebTest(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_get_mode_fixed_hides_r1_r2_re(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn('id="field-RB"', body)
        for name in ("R1", "R2", "RE"):
            self.assertNotIn(f'id="field-{name}"', body)

    def test_get_mode_emitter_hides_r1_r2(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)
        self.assertIn('id="field-RE"', body)
        self.assertNotIn('id="field-R1"', body)
        self.assertNotIn('id="field-R2"', body)

    def test_get_invalid_mode_returns_400_without_form(self):
        response = self.client.get("/?mode=darlington")
        self.assertEqual(response.status_code, 400)
        body = response.get_data(as_text=True)
        self.assertNotIn('action="/calculate"', body)
        self.assertNotIn('id="results"', body)
        self.assertNotIn("1.230 mA", body)

    def test_post_fixed_returns_a2_results(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "fixed",
                "VCC": "12",
                "RB": "1000000",
                "RC": "2200",
                "beta": "100",
                "VBE": "0.70",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("1.130 mA", body)
        self.assertIn("9.514 V", body)

    def test_post_emitter_returns_a3_results(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "emitter",
                "VCC": "12",
                "RB": "1000000",
                "RE": "1000",
                "RC": "2200",
                "beta": "100",
                "VBE": "0.70",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("1.026 mA", body)
        self.assertIn("8.705 V", body)

    def test_post_a4_re_change_changes_ic_in_the_predicted_direction(self):
        base = self.client.post(
            "/calculate",
            data={
                "mode": "emitter",
                "VCC": "12",
                "RB": "1000000",
                "RE": "1000",
                "RC": "2200",
                "beta": "100",
                "VBE": "0.70",
            },
        ).get_data(as_text=True)
        changed = self.client.post(
            "/calculate",
            data={
                "mode": "emitter",
                "VCC": "12",
                "RB": "1000000",
                "RE": "2000",
                "RC": "2200",
                "beta": "100",
                "VBE": "0.70",
            },
        ).get_data(as_text=True)
        self.assertIn("1.026 mA", base)
        self.assertIn("0.940 mA", changed)
        self.assertIn("8.033 V", changed)

    def test_post_mode_hidden_field_is_used(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "fixed",
                "VCC": "12",
                "RB": "1000000",
                "RC": "2200",
                "beta": "100",
                "VBE": "0.70",
            },
        )
        body = response.get_data(as_text=True)
        self.assertIn('value="fixed"', body)
        self.assertNotIn('id="field-R1"', body)


class ModeAwareValidationWebTest(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_post_a5_zero_rb_shows_error_without_stale_results(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "fixed",
                "VCC": "12",
                "RB": "0",
                "RC": "2200",
                "beta": "100",
                "VBE": "0.70",
            },
        )
        self.assertEqual(response.status_code, 400)
        body = response.get_data(as_text=True)
        self.assertIn("RB ต้องมากกว่า 0", body)
        self.assertNotIn('id="results"', body)
        self.assertNotIn("1.130 mA", body)

    def test_post_negative_vcc_shows_error_400(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "fixed",
                "VCC": "-5",
                "RB": "1000000",
                "RC": "2200",
                "beta": "100",
                "VBE": "0.70",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("VCC ต้องมากกว่า 0", response.get_data(as_text=True))

    def test_post_missing_beta_shows_error(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "fixed",
                "VCC": "12",
                "RB": "1000000",
                "RC": "2200",
                "VBE": "0.70",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("β", response.get_data(as_text=True))

    def test_post_divider_zero_r1_shows_error(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "divider",
                "VCC": "12",
                "R1": "0",
                "R2": "22000",
                "RC": "2200",
                "RE": "1000",
                "beta": "100",
                "VBE": "0.70",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("R1 ต้องมากกว่า 0", response.get_data(as_text=True))

    def test_post_bad_beta_shows_error(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "fixed",
                "VCC": "12",
                "RB": "1000000",
                "RC": "2200",
                "beta": "abc",
                "VBE": "0.70",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("β ต้องเป็นตัวเลข", response.get_data(as_text=True))


class MiscWebTest(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_static_css_is_served(self):
        response = self.client.get("/static/style.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response.content_type)

    def test_no_results_table_on_first_get(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('id="results"', body)
        self.assertIn('id="results-placeholder"', body)


if __name__ == "__main__":
    unittest.main()
