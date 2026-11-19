"""Deterministic checks of sampling, accounting and standard-error estimates."""

import math
import random
import statistics
import unittest

from black_scholes import black_scholes
from monte_carlo import monte_carlo_price


class MonteCarloTests(unittest.TestCase):
    def test_reference_prices_with_fixed_seed(self):
        # A broad fixed-seed integration check. We do not require every
        # nominal 95% interval to contain the analytical reference.
        for kind in ("call", "put"):
            result = monte_carlo_price(100, 100, 1, 0.05, 0.2, kind,
                                       samples=100_000, seed=42)
            reference = black_scholes(100, 100, 1, 0.05, 0.2, kind)
            self.assertGreater(result["standard_error"], 0)
            self.assertLess(abs(result["price"] - reference),
                            5 * result["standard_error"])

    def test_online_statistics_against_stored_sample(self):
        # Independent statistics implementation: statistics.mean/stdev on
        # explicitly stored payoffs, compared with the streaming accumulator.
        rng = random.Random(17)
        payoffs = []
        for _ in range(8):
            terminal = 110 * math.exp(0.03 + 0.2 * rng.gauss(0, 1))
            payoffs.append(math.exp(-0.05) * max(terminal - 100, 0))
        result = monte_carlo_price(110, 100, 1, 0.05, 0.2, samples=8, seed=17)
        mean = statistics.mean(payoffs)
        se = statistics.stdev(payoffs) / math.sqrt(8)
        self.assertAlmostEqual(result["price"], mean, places=11)
        self.assertAlmostEqual(result["standard_error"], se, places=11)
        self.assertAlmostEqual(result["ci_low"], mean - 1.96 * se, places=11)
        self.assertAlmostEqual(result["ci_high"], mean + 1.96 * se, places=11)

    def test_expiry_payoffs(self):
        for spot in (80, 100, 120):
            for kind in ("call", "put"):
                result = monte_carlo_price(spot, 100, 0, 0.05, 0.2, kind)
                payoff = max(spot-100, 0) if kind == "call" else max(100-spot, 0)
                self.assertEqual(result["price"], payoff)
                self.assertEqual(result["standard_error"], 0)
                self.assertEqual(result["ci_low"], result["ci_high"])

    def test_zero_volatility(self):
        for rate in (-0.05, 0.05):
            for kind in ("call", "put"):
                result = monte_carlo_price(100, 100, 1, rate, 0, kind)
                reference = black_scholes(100, 100, 1, rate, 0, kind)
                self.assertAlmostEqual(result["price"], reference)
                self.assertEqual(result["standard_error"], 0)

    def test_seed_reproducibility(self):
        args = dict(spot=100, strike=100, time_to_expiry=1, rate=0.05,
                    volatility=0.2, samples=1000)
        first = monte_carlo_price(**args, seed=7)
        self.assertEqual(first, monte_carlo_price(**args, seed=7))
        self.assertNotEqual(first["price"], monte_carlo_price(**args, seed=8)["price"])

    def test_global_random_state_unchanged(self):
        before = random.getstate()
        monte_carlo_price(100, 100, 1, 0.05, 0.2, samples=10, seed=42)
        self.assertEqual(before, random.getstate())

    def test_invalid_inputs(self):
        valid = dict(spot=100, strike=100, time_to_expiry=1, rate=0.05,
                     volatility=0.2, option_type="call", samples=10, seed=42)
        invalid = [("spot", 0), ("strike", -1), ("time_to_expiry", -1),
                   ("volatility", -0.1), ("option_type", "invalid"),
                   ("samples", 1), ("samples", 0), ("samples", True),
                   ("samples", 2.5), ("seed", "42"), ("seed", True)]
        for field in ("spot", "strike", "time_to_expiry", "rate", "volatility"):
            invalid.extend((field, x) for x in (math.nan, math.inf, -math.inf))
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    monte_carlo_price(**{**valid, field: value})


if __name__ == "__main__":
    unittest.main()
