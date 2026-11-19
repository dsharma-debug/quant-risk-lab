"""Check separation of premium assumptions, hedge decisions and shared paths."""

import math
import unittest

from black_scholes import black_scholes, black_scholes_delta
from hedging import hedge_on_path
from hedging_study import run_study
from volatility_study import run_volatility_study


class VolatilityStudyTests(unittest.TestCase):
    def test_valuation_volatility_is_separate_from_delta(self):
        result = hedge_on_path([100, 105, 98, 110], 100, 1, 0.05, 0.15,
                               valuation_volatility=0.20)
        self.assertEqual(result["summary"]["premium_received"], black_scholes(100, 100, 1, 0.05, 0.20))
        self.assertEqual(result["summary"]["initial_delta"], black_scholes_delta(100, 100, 1, 0.05, 0.15))
        row = result["ledger"][1]
        self.assertAlmostEqual(row["option_value"], black_scholes(105, 100, 2/3, 0.05, 0.20))

    def test_changed_premium_only_shifts_financed_cash(self):
        args = ([100, 105, 98, 110], 100, 1, 0.05, 0.15)
        first = hedge_on_path(*args, cost_bps=5, valuation_volatility=0.20)
        second = hedge_on_path(*args, cost_bps=5, valuation_volatility=0.25)
        premium_difference = second["summary"]["premium_received"] - first["summary"]["premium_received"]
        for a, b in zip(first["ledger"], second["ledger"]):
            self.assertEqual(a["trade_shares"], b["trade_shares"])
            self.assertEqual(a["trade_cost"], b["trade_cost"])
            self.assertAlmostEqual(b["cash"]-a["cash"],
                                   premium_difference*math.exp(0.05*a["time"]), places=10)

    def test_default_valuation_preserves_previous_behavior(self):
        args = ([100, 105, 98, 110], 100, 1, 0.05, 0.20)
        self.assertEqual(hedge_on_path(*args), hedge_on_path(*args, valuation_volatility=0.20))

    def test_fixed_premium_and_common_paths(self):
        trials, summaries = run_volatility_study(paths=3, hedge_volatilities=(0.15, 0.2),
                     frequencies=(1, 3), cost_levels=(0, 5), steps=12)
        self.assertEqual(len(trials), 24)
        self.assertEqual(len(summaries), 8)
        self.assertEqual(len({row["premium_received"] for row in trials}), 1)
        for seed in (1000, 1001, 1002):
            group = [row for row in trials if row["seed"] == seed]
            self.assertEqual(len({row["terminal_spot"] for row in group}), 1)
            self.assertEqual(len({row["option_payoff"] for row in group}), 1)
        self.assertTrue(all(row["no_cost_mean_benchmark"] == 0 for row in summaries))

    def test_matching_volatility_reproduces_previous_study(self):
        previous, _ = run_study(paths=3, frequencies=(1, 3), cost_levels=(0, 5), steps=12)
        current, _ = run_volatility_study(paths=3, hedge_volatilities=(0.2,),
                      frequencies=(1, 3), cost_levels=(0, 5), steps=12)
        key = lambda row: (row["seed"], row["rebalance_every"], row["cost_bps"])
        previous = {key(row): row for row in previous}
        for row in current:
            self.assertEqual(row["terminal_pnl"], previous[key(row)]["terminal_pnl"])
            self.assertEqual(row["total_trade_cost"], previous[key(row)]["total_trade_cost"])

    def test_alternative_premium_protocol_has_exact_funding_shift(self):
        args = dict(paths=3, hedge_volatilities=(0.15, 0.25), frequencies=(1,),
                    cost_levels=(0, 5), steps=12)
        fixed, _ = run_volatility_study(**args)
        changed, summaries = run_volatility_study(**args, premium_mode="hedge_model")
        for a, b in zip(fixed, changed):
            expected = (b["premium_received"]-a["premium_received"])*math.exp(0.05)
            self.assertAlmostEqual(b["terminal_pnl"]-a["terminal_pnl"], expected, places=10)
            self.assertEqual(a["total_trade_cost"], b["total_trade_cost"])
        self.assertLess(summaries[0]["no_cost_mean_benchmark"], 0)
        self.assertGreater(summaries[-1]["no_cost_mean_benchmark"], 0)

    def test_invalid_inputs(self):
        invalid = [dict(paths=1), dict(paths=True), dict(steps=0), dict(steps=True),
                   dict(hedge_volatilities=()), dict(hedge_volatilities=(0,)),
                   dict(hedge_volatilities=(0.2, 0.2)), dict(actual_volatility=-1),
                   dict(frequencies=(0,)), dict(frequencies=(1, 1)), dict(frequencies=(253,)),
                   dict(cost_levels=(-1,)), dict(cost_levels=(0, 0)),
                   dict(seed_start="1"), dict(premium_mode="invalid")]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    run_volatility_study(**kwargs)
        for value in (-1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                hedge_on_path([100, 105], 100, 1, 0.05, 0.20, valuation_volatility=value)


if __name__ == "__main__":
    unittest.main()
