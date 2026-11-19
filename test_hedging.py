"""Accounting invariants and information timing for the hedge simulator."""

import math
import random
import unittest

from hedging import hedge_on_path, simulate_stock_path


class HedgingTests(unittest.TestCase):
    def test_one_step_manual_cash_flow(self):
        # At r=0, S=K=100, sigma=.2, T=1: premium=7.9655674554,
        # initial delta=.5398278373. No intermediate trades, S_T=110.
        result = hedge_on_path([100, 110], 100, 1, 0, 0.2)
        expected = 7.965567455405804 + 0.539827837277029 * 10 - 10
        self.assertAlmostEqual(result["summary"]["terminal_pnl"], expected, places=10)
        self.assertEqual(result["summary"]["final_shares"], 0)

    def test_constant_spot_does_not_create_trading_wealth(self):
        for cost in (0, 5):
            result = hedge_on_path([100] * 13, 100, 1, 0, 0.2, cost_bps=cost)
            summary = result["summary"]
            self.assertAlmostEqual(summary["terminal_pnl"],
                                   summary["premium_received"] - summary["total_trade_cost"],
                                   places=10)

    def test_ledger_cash_recurrence_and_final_settlement(self):
        result = hedge_on_path([100, 104, 97, 110], 100, 1, 0.05, 0.2, cost_bps=5)
        rows = result["ledger"]
        summary = result["summary"]
        first = rows[0]
        self.assertAlmostEqual(first["cash"], summary["premium_received"]
                               - first["trade_shares"] * first["spot"] - first["trade_cost"])
        self.assertAlmostEqual(first["hedged_equity"], -first["trade_cost"])
        for previous, row in zip(rows, rows[1:]):
            expected_cash = (previous["cash"] + row["interest"]
                             - row["trade_shares"] * row["spot"]
                             - row["trade_cost"] - row["option_payoff"])
            self.assertAlmostEqual(row["cash"], expected_cash, places=11)
            self.assertAlmostEqual(row["shares_after"],
                                   previous["shares_after"] + row["trade_shares"])
            self.assertAlmostEqual(row["hedged_equity"], row["cash"]
                                   + row["shares_after"] * row["spot"] - row["option_value"])
        self.assertEqual(rows[-1]["option_value"], 0)
        self.assertEqual(rows[-1]["shares_after"], 0)
        self.assertEqual(rows[-1]["option_payoff"], 10)
        self.assertEqual(rows[-1]["cash"], summary["terminal_pnl"])

    def test_fee_drag_includes_financing(self):
        for rate in (-0.02, 0.05):
            plain = hedge_on_path([100, 101, 98, 106, 104], 100, 1, rate, 0.2)
            costly = hedge_on_path([100, 101, 98, 106, 104], 100, 1, rate, 0.2, cost_bps=5)
            expected_drag = sum(row["trade_cost"] * math.exp(rate * (1-row["time"]))
                                for row in costly["ledger"])
            actual_drag = plain["summary"]["terminal_pnl"] - costly["summary"]["terminal_pnl"]
            self.assertAlmostEqual(actual_drag, expected_drag, places=10)

    def test_decisions_do_not_use_future_prices(self):
        first = hedge_on_path([100, 101, 99, 110, 120], 100, 1, 0.05, 0.2)
        second = hedge_on_path([100, 101, 99, 80, 70], 100, 1, 0.05, 0.2)
        self.assertEqual(first["ledger"][:3], second["ledger"][:3])

    def test_call_put_hedging_error_parity_without_fees(self):
        path = [100, 105, 98, 110, 90, 115]
        call = hedge_on_path(path, 100, 1, 0.05, 0.2, "call", rebalance_every=2)
        put = hedge_on_path(path, 100, 1, 0.05, 0.2, "put", rebalance_every=2)
        self.assertAlmostEqual(call["summary"]["terminal_pnl"],
                               put["summary"]["terminal_pnl"], places=10)

    def test_simulator_reproducibility_and_zero_volatility(self):
        before = random.getstate()
        first = simulate_stock_path(100, 1, 0.05, 0.2, steps=8, seed=7)
        self.assertEqual(first, simulate_stock_path(100, 1, 0.05, 0.2, steps=8, seed=7))
        self.assertEqual(before, random.getstate())
        self.assertEqual(len(first), 9)
        self.assertTrue(all(s > 0 for s in first))
        deterministic = simulate_stock_path(100, 1, 0.05, 0, steps=8, seed=7)
        for i, price in enumerate(deterministic):
            self.assertAlmostEqual(price, 100*math.exp(0.05*i/8), places=10)

    def test_rebalance_schedule(self):
        result = hedge_on_path([100, 101, 99, 103, 100, 110], 100, 1, 0.05, 0.2,
                               rebalance_every=2)
        self.assertEqual([r["event"] for r in result["ledger"]],
                         ["initial", "hold", "rebalance", "hold", "rebalance", "settlement"])
        for row in result["ledger"]:
            if row["event"] == "hold":
                self.assertEqual(row["trade_shares"], 0)

    def test_optional_ledger_does_not_change_results(self):
        args = ([100, 104, 98, 110], 100, 1, 0.05, 0.2)
        full = hedge_on_path(*args, cost_bps=5)
        compact = hedge_on_path(*args, cost_bps=5, record_ledger=False)
        self.assertEqual(full["summary"], compact["summary"])
        self.assertEqual(compact["ledger"], [])

    def test_invalid_inputs(self):
        base = dict(stock_prices=[100, 101], strike=100, time_to_expiry=1,
                    rate=0.05, hedge_volatility=0.2)
        invalid = [dict(stock_prices=[100]), dict(stock_prices=[100, 0]),
                   dict(stock_prices=[100, math.nan]), dict(strike=0),
                   dict(time_to_expiry=0), dict(hedge_volatility=0),
                   dict(rate=math.inf), dict(cost_bps=-1),
                   dict(rebalance_every=0), dict(rebalance_every=True),
                   dict(option_type="invalid"), dict(record_ledger="yes")]
        for changes in invalid:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    hedge_on_path(**{**base, **changes})
        sim = dict(spot=100, time_to_expiry=1, rate=0.05, volatility=0.2)
        for changes in (dict(spot=0), dict(time_to_expiry=0), dict(volatility=-1),
                        dict(rate=math.nan), dict(steps=True), dict(steps=0), dict(seed="42")):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    simulate_stock_path(**{**sim, **changes})


if __name__ == "__main__":
    unittest.main()
