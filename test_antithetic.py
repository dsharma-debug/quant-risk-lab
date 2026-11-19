"""Checks of pair accounting, standard errors and matched-budget experiments."""

import math
import random
import statistics
import unittest

from antithetic import antithetic_price
from black_scholes import black_scholes
from compare_variance_reduction import run_comparison


class AntitheticTests(unittest.TestCase):
    def test_pair_mean_and_standard_error_against_stored_pairs(self):
        rng = random.Random(17)
        pair_averages = []
        for _ in range(4):
            z = rng.gauss(0, 1)
            terminals = [110 * math.exp(0.03 + 0.2 * shock) for shock in (z, -z)]
            payoffs = [math.exp(-0.05) * max(terminal - 100, 0) for terminal in terminals]
            pair_averages.append(statistics.mean(payoffs))
        result = antithetic_price(110, 100, 1, 0.05, 0.2, samples=8, seed=17)
        mean = statistics.mean(pair_averages)
        se = statistics.stdev(pair_averages) / math.sqrt(4)
        self.assertEqual(result["samples"], 8)
        self.assertEqual(result["pairs"], 4)
        self.assertAlmostEqual(result["price"], mean, places=11)
        self.assertAlmostEqual(result["standard_error"], se, places=11)
        self.assertAlmostEqual(result["ci_low"], mean - 1.96 * se, places=11)
        self.assertAlmostEqual(result["ci_high"], mean + 1.96 * se, places=11)

    def test_reference_prices_fixed_seed(self):
        for kind in ("call", "put"):
            result = antithetic_price(100, 100, 1, 0.05, 0.2, kind,
                                      samples=20_000, seed=42)
            reference = black_scholes(100, 100, 1, 0.05, 0.2, kind)
            self.assertGreater(result["standard_error"], 0)
            self.assertLess(abs(result["price"] - reference), 5 * result["standard_error"])

    def test_deterministic_boundaries(self):
        for expiry, sigma in ((0, 0.2), (1, 0)):
            for rate in (-0.05, 0.05):
                for kind in ("call", "put"):
                    result = antithetic_price(110, 100, expiry, rate, sigma, kind)
                    reference = black_scholes(110, 100, expiry, rate, sigma, kind)
                    self.assertAlmostEqual(result["price"], reference)
                    self.assertEqual(result["standard_error"], 0)

    def test_reproducibility_and_global_random_state(self):
        before = random.getstate()
        first = antithetic_price(100, 100, 1, 0.05, 0.2, samples=100, seed=7)
        second = antithetic_price(100, 100, 1, 0.05, 0.2, samples=100, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(before, random.getstate())

    def test_invalid_pricer_inputs(self):
        valid = dict(spot=100, strike=100, time_to_expiry=1, rate=0.05,
                     volatility=0.2, samples=10, seed=42, option_type="call")
        invalid = [("spot", 0), ("strike", -1), ("time_to_expiry", -1),
                   ("volatility", -0.1), ("samples", 2), ("samples", 5),
                   ("samples", 4.5), ("samples", True), ("seed", "42"),
                   ("seed", True), ("option_type", "invalid")]
        for field in ("spot", "strike", "time_to_expiry", "rate", "volatility"):
            invalid.extend((field, x) for x in (math.nan, math.inf, -math.inf))
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    antithetic_price(**{**valid, field: value})

    def test_matched_budget_experiment(self):
        trials, summaries = run_comparison(samples=20, repetitions=3, seed_start=10)
        self.assertEqual(len(trials), 12)
        self.assertEqual(len(summaries), 4)
        for kind in ("call", "put"):
            for method in ("plain", "antithetic"):
                group = [row for row in trials if row["option_type"] == kind and row["method"] == method]
                self.assertEqual([row["seed"] for row in group], [10, 11, 12])
                self.assertTrue(all(row["samples"] == 20 for row in group))
                expected = 20 if method == "plain" else 10
                self.assertTrue(all(row["independent_observations"] == expected for row in group))

    def test_invalid_experiment_inputs(self):
        for kwargs in (dict(samples=3), dict(samples=True), dict(repetitions=1),
                       dict(repetitions=True), dict(seed_start="10")):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    run_comparison(**kwargs)


if __name__ == "__main__":
    unittest.main()
