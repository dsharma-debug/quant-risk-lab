"""Optional headless UI checks: python check_dashboard.py (requires Streamlit)."""

from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


class DashboardUITests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).with_name("dashboard.py")), default_timeout=20).run()

    def assert_clean(self, app):
        self.assertFalse(app.exception, [error.message for error in app.exception])

    def test_pricing_inputs_change_prices(self):
        app = self.app()
        self.assert_clean(app)
        self.assertEqual(app.metric[0].value, "$10.4506")
        app.number_input(key="p_vol").set_value(40.0)
        app.button[0].click().run()
        self.assert_clean(app)
        self.assertEqual(app.metric[0].value, "$18.0230")

    def test_put_option_is_displayed(self):
        app = self.app()
        app.selectbox(key="p_kind").select("put")
        app.button[0].click().run()
        self.assert_clean(app)
        self.assertEqual(app.metric[0].value, "$5.5735")

    def test_single_path_hedge(self):
        app = self.app()
        app.radio(key="workspace").set_value("Hedge simulator").run()
        app.button[0].click().run()
        self.assert_clean(app)
        result = app.session_state["hedge_result"]["with_costs"]["summary"]
        self.assertAlmostEqual(result["terminal_pnl"], 0.094495, places=6)
        self.assertEqual(result["final_shares"], 0)

    def test_saved_views_and_new_study(self):
        app = self.app()
        app.radio(key="workspace").set_value("Research results").run()
        for name in ("Hedge frequency and costs", "Volatility assumptions", "Monte Carlo precision", "Variance reduction"):
            app.selectbox(key="saved_study").select(name).run()
            self.assert_clean(app)
        app.number_input(key="study_paths").set_value(50)
        app.button[0].click().run()
        self.assert_clean(app)
        self.assertEqual(len(app.session_state["live_study"]["summaries"]), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
