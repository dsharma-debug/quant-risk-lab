"""Validate dashboard units, backend delegation, and safe result loading."""

import csv
import io
from pathlib import Path
import tempfile
import unittest

from black_scholes import black_scholes
from dashboard_support import (hedge_snapshot, interactive_study, load_saved_study,
                               make_contract, pricing_snapshot, rows_to_csv)


class DashboardSupportTests(unittest.TestCase):
    def test_percentage_conversion_and_pricing(self):
        contract = make_contract(100, 100, 1, 5, 20, "call")
        self.assertEqual(contract["rate"], 0.05)
        self.assertEqual(contract["volatility"], 0.20)
        result = pricing_snapshot(contract, tree_steps=20, samples=100, seed=7)
        self.assertEqual(len(result["rows"]), 4)
        self.assertEqual(result["rows"][0]["price"], black_scholes(**contract))
        self.assertEqual(result["rows"][0]["absolute_error"], 0)

    def test_invalid_coarse_tree_preserves_other_methods(self):
        contract = make_contract(100, 100, 1, 20, 1, "call")
        result = pricing_snapshot(contract, tree_steps=10, samples=100, seed=7)
        self.assertIsNone(result["rows"][1]["price"])
        self.assertTrue(result["rows"][1]["message"])
        self.assertTrue(all(row["price"] is not None for row in result["rows"] if row["method"] != "Binomial tree"))

    def test_hedge_adapter_holds_valuation_separate(self):
        contract = make_contract(100, 100, 1, 5, 15, "call")
        result = hedge_snapshot(contract, actual_vol_percent=20, hedge_vol_percent=15, steps=12)
        summary = result["with_costs"]["summary"]
        self.assertEqual(summary["valuation_volatility"], 0.20)
        self.assertEqual(summary["hedge_volatility"], 0.15)
        self.assertEqual(summary["premium_received"], black_scholes(100, 100, 1, 0.05, 0.20))
        self.assertEqual(summary["final_shares"], 0)
        self.assertLess(summary["terminal_pnl"], result["without_costs"]["summary"]["terminal_pnl"])

    def test_interactive_study_and_csv_export(self):
        result = interactive_study(paths=3, actual_vol_percent=20, hedge_vol_percent=15, cost_bps=0)
        self.assertEqual(len(result["summaries"]), 4)
        self.assertEqual(len(result["trials"]), 12)
        self.assertEqual(len({row["premium_received"] for row in result["trials"]}), 1)
        text = rows_to_csv(result["summaries"])
        parsed = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual(len(parsed), 4)

    def test_known_saved_study_loading_and_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                load_saved_study("Hedge frequency and costs", folder)
            path = Path(folder) / "hedging_study_summary.csv"
            path.write_text("option_type,paths,mean_pnl\ncall,500,0.125\n", encoding="utf-8")
            result = load_saved_study("Hedge frequency and costs", folder)
            self.assertEqual(result, [dict(option_type="call", paths=500, mean_pnl=0.125)])
            with self.assertRaises(KeyError):
                load_saved_study("../../other-file", folder)


if __name__ == "__main__":
    unittest.main()
