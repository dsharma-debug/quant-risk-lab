"""Financial identities and boundary checks: python3 -m unittest -v."""

import math
import unittest

from black_scholes import black_scholes, black_scholes_delta, normal_cdf


class BlackScholesTests(unittest.TestCase):
    def test_delta_against_finite_differences(self):
        for spot in (70, 100, 140):
            for rate in (-0.02, 0.05):
                for kind in ("call", "put"):
                    with self.subTest(spot=spot, rate=rate, kind=kind):
                        h = 0.001
                        up = black_scholes(spot + h, 100, 0.75, rate, 0.3, kind)
                        down = black_scholes(spot - h, 100, 0.75, rate, 0.3, kind)
                        exact = black_scholes_delta(spot, 100, 0.75, rate, 0.3, kind)
                        self.assertAlmostEqual((up - down) / (2 * h), exact,
                                               delta=1e-8)

    def test_delta_parity_and_bounds(self):
        for spot in (50, 100, 200):
            call = black_scholes_delta(spot, 100, 1, 0.05, 0.2)
            put = black_scholes_delta(spot, 100, 1, 0.05, 0.2, "put")
            self.assertAlmostEqual(call - put, 1.0)
            self.assertTrue(0 <= call <= 1)
            self.assertTrue(-1 <= put <= 0)

    def test_delta_invalid_inputs(self):
        valid = dict(spot=100, strike=100, time_to_expiry=1,
                     rate=0.05, volatility=0.2, option_type="call")
        invalid = [("spot", 0), ("strike", -1), ("time_to_expiry", 0),
                   ("time_to_expiry", -1), ("volatility", 0),
                   ("volatility", -0.1), ("option_type", "invalid")]
        for field in ("spot", "strike", "time_to_expiry", "rate", "volatility"):
            invalid.extend((field, value) for value in (math.nan, math.inf, -math.inf))
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    black_scholes_delta(**{**valid, field: value})

    def test_reference_prices(self):
        # Standard example: S=K=100, T=1, r=5%, sigma=20%, no dividends.
        self.assertAlmostEqual(black_scholes(100, 100, 1, 0.05, 0.20),
                               10.450583572185565, places=10)
        self.assertAlmostEqual(black_scholes(100, 100, 1, 0.05, 0.20, "put"),
                               5.573526022256971, places=10)

    def test_put_call_parity(self):
        for spot in (70, 100, 140):
            for rate in (-0.02, 0, 0.05):
                with self.subTest(spot=spot, rate=rate):
                    call = black_scholes(spot, 100, 0.75, rate, 0.3)
                    put = black_scholes(spot, 100, 0.75, rate, 0.3, "put")
                    self.assertAlmostEqual(call - put,
                                           spot - 100 * math.exp(-rate * 0.75),
                                           places=10)

    def test_expiry_payoffs(self):
        for spot in (80, 100, 120):
            self.assertEqual(black_scholes(spot, 100, 0, 0.05, 0.2),
                             max(spot - 100, 0))
            self.assertEqual(black_scholes(spot, 100, 0, 0.05, 0.2, "put"),
                             max(100 - spot, 0))

    def test_zero_volatility(self):
        discounted_strike = 100 * math.exp(-0.05)
        self.assertAlmostEqual(black_scholes(100, 100, 1, 0.05, 0),
                               100 - discounted_strike)
        self.assertEqual(black_scholes(100, 100, 1, 0.05, 0, "put"), 0)

    def test_no_arbitrage_bounds(self):
        for spot in (50, 100, 150):
            for rate in (-0.02, 0.05):
                with self.subTest(spot=spot, rate=rate):
                    discounted_strike = 100 * math.exp(-rate)
                    call = black_scholes(spot, 100, 1, rate, 0.2)
                    put = black_scholes(spot, 100, 1, rate, 0.2, "put")
                    self.assertGreaterEqual(call + 1e-10,
                                            max(spot - discounted_strike, 0))
                    self.assertLessEqual(call, spot + 1e-10)
                    self.assertGreaterEqual(put + 1e-10,
                                            max(discounted_strike - spot, 0))
                    self.assertLessEqual(put, discounted_strike + 1e-10)

    def test_more_volatility_increases_option_values(self):
        for kind in ("call", "put"):
            self.assertGreater(black_scholes(100, 100, 1, 0.05, 0.4, kind),
                               black_scholes(100, 100, 1, 0.05, 0.2, kind))

    def test_invalid_inputs(self):
        valid = dict(spot=100, strike=100, time_to_expiry=1,
                     rate=0.05, volatility=0.2, option_type="call")
        invalid = [("spot", 0), ("strike", -1), ("time_to_expiry", -1),
                   ("volatility", -0.1), ("option_type", "invalid")]
        for field in ("spot", "strike", "time_to_expiry", "rate", "volatility"):
            invalid.extend((field, value) for value in (math.nan, math.inf, -math.inf))
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    black_scholes(**{**valid, field: value})

    def test_normal_distribution(self):
        self.assertEqual(normal_cdf(0), 0.5)
        self.assertAlmostEqual(normal_cdf(1.96), 0.9750021048517795)
        self.assertAlmostEqual(normal_cdf(-1.96), 1 - normal_cdf(1.96))


if __name__ == "__main__":
    unittest.main()
