"""Hand-calculated statistics and common-path experiment checks."""

import math
import unittest

from hedging_study import percentile, run_study, summarize_hedges


class HedgingStudyTests(unittest.TestCase):
    def test_hand_calculated_summary(self):
        rows = [dict(terminal_pnl=pnl, total_trade_cost=fee,
                     trade_count=trades, turnover_notional=turnover)
                for pnl, fee, trades, turnover in
                [(-2, 0.1, 2, 100), (0, 0.2, 4, 200), (2, 0.3, 6, 300)]]
        result = summarize_hedges(rows)
        self.assertEqual(result["paths"], 3)
        self.assertEqual(result["mean_pnl"], 0)
        self.assertEqual(result["std_pnl"], 2)
        self.assertAlmostEqual(result["rmse_to_zero"], math.sqrt(8/3))
        self.assertAlmostEqual(result["mean_pnl_standard_error"], 2/math.sqrt(3))
        self.assertAlmostEqual(result["mean_pnl_ci_low"], -1.96*2/math.sqrt(3))
        self.assertAlmostEqual(result["mean_pnl_ci_high"], 1.96*2/math.sqrt(3))
        self.assertAlmostEqual(result["pnl_p05"], -1.8)
        self.assertAlmostEqual(result["pnl_p95"], 1.8)
        self.assertAlmostEqual(result["mean_total_trade_cost"], 0.2)
        self.assertEqual(result["mean_trade_count"], 4)
        self.assertEqual(result["mean_turnover_notional"], 200)

    def test_percentile_endpoints_and_interpolation(self):
        self.assertEqual(percentile([3, 1, 2], 0), 1)
        self.assertEqual(percentile([3, 1, 2], 1), 3)
        self.assertEqual(percentile([3, 1, 2], 0.5), 2)
        self.assertEqual(percentile([4], 0.5), 4)
        for values, p in (([], 0.5), ([1], -0.1), ([1], 1.1), ([1], math.nan)):
            with self.assertRaises(ValueError):
                percentile(values, p)

    def test_need_multiple_paths_for_summary(self):
        for rows in ([], [dict(terminal_pnl=1)]):
            with self.assertRaises(ValueError):
                summarize_hedges(rows)

    def test_same_paths_and_seeds_for_all_policies(self):
        trials, summaries = run_study(paths=3, frequencies=(1, 3), cost_levels=(0, 5),
                                      seed_start=10, steps=12)
        self.assertEqual(len(trials), 12)
        self.assertEqual(len(summaries), 4)
        for seed in (10, 11, 12):
            same_path = [row for row in trials if row["seed"] == seed]
            self.assertEqual(len(same_path), 4)
            self.assertEqual(len({row["terminal_spot"] for row in same_path}), 1)
            self.assertEqual(len({row["option_payoff"] for row in same_path}), 1)
            for frequency in (1, 3):
                plain, costly = [row for row in same_path if row["rebalance_every"] == frequency]
                self.assertEqual(plain["total_trade_cost"], 0)
                self.assertLess(costly["terminal_pnl"], plain["terminal_pnl"])
                self.assertEqual(plain["final_shares"], 0)
                self.assertEqual(costly["final_shares"], 0)
        self.assertTrue(all(row["paths"] == 3 for row in summaries))
        self.assertEqual((trials, summaries), run_study(paths=3, frequencies=(1, 3),
                         cost_levels=(0, 5), seed_start=10, steps=12))

    def test_invalid_configuration(self):
        invalid = [dict(paths=1), dict(paths=True), dict(steps=0), dict(steps=True),
                   dict(frequencies=()), dict(frequencies=(0,)), dict(frequencies=(True,)),
                   dict(frequencies=(1, 1)), dict(frequencies=(253,)),
                   dict(cost_levels=()), dict(cost_levels=(-1,)), dict(cost_levels=(math.inf,)),
                   dict(cost_levels=(0, 0)), dict(seed_start="10"),
                   dict(actual_volatility=-0.1), dict(hedge_volatility=0),
                   dict(option_type="invalid")]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    run_study(**kwargs)


if __name__ == "__main__":
    unittest.main()
