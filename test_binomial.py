"""Independent identities and boundary checks for the European CRR tree."""

import math
import unittest

from binomial import binomial_price
from black_scholes import black_scholes


class BinomialTests(unittest.TestCase):
    def test_hand_calculated_one_step(self):
        # r=0, u=6/5, d=5/6, p=5/11. Call payoff is 20 on an up move;
        # put payoff is 50/3 on a down move. Both prices are 100/11.
        for kind in ("call", "put"):
            price = binomial_price(100, 100, 1, 0, math.log(1.2), kind, steps=1)
            self.assertAlmostEqual(price, 100 / 11, places=11)

    def test_backward_induction_against_direct_expectation(self):
        # Sum terminal binomial probabilities directly: a different algorithm
        # from working backward, with no reliance on Black-Scholes.
        n, spot, strike, expiry, rate, sigma = 5, 110, 100, 0.75, -0.01, 0.3
        dt = expiry / n
        up = math.exp(sigma * math.sqrt(dt))
        down = 1 / up
        p = (math.exp(rate * dt) - down) / (up - down)
        for kind in ("call", "put"):
            expected = 0.0
            for j in range(n + 1):
                terminal = spot * up**j * down**(n-j)
                payoff = max(terminal - strike, 0) if kind == "call" else max(strike - terminal, 0)
                expected += math.comb(n, j) * p**j * (1-p)**(n-j) * payoff
            expected *= math.exp(-rate * expiry)
            self.assertAlmostEqual(binomial_price(spot, strike, expiry, rate, sigma,
                                                 kind, steps=n), expected, places=10)

    def test_put_call_parity_and_price_bounds(self):
        for spot in (70, 100, 140):
            for rate in (-0.02, 0.05):
                with self.subTest(spot=spot, rate=rate):
                    call = binomial_price(spot, 100, 1, rate, 0.3, steps=50)
                    put = binomial_price(spot, 100, 1, rate, 0.3, "put", steps=50)
                    discounted_strike = 100 * math.exp(-rate)
                    self.assertAlmostEqual(call-put, spot-discounted_strike, places=9)
                    self.assertGreaterEqual(call + 1e-9, max(spot-discounted_strike, 0))
                    self.assertLessEqual(call, spot + 1e-9)
                    self.assertGreaterEqual(put + 1e-9, max(discounted_strike-spot, 0))
                    self.assertLessEqual(put, discounted_strike + 1e-9)

    def test_convergence_for_reference_example(self):
        # One fixed case, comparing even-step trees. Not a universal claim
        # that every increase of N reduces the error.
        for kind in ("call", "put"):
            reference = black_scholes(100, 100, 1, 0.05, 0.2, kind)
            coarse = binomial_price(100, 100, 1, 0.05, 0.2, kind, steps=10)
            fine = binomial_price(100, 100, 1, 0.05, 0.2, kind, steps=1000)
            self.assertLess(abs(fine-reference), 0.003)
            self.assertLess(abs(fine-reference), abs(coarse-reference))

    def test_expiry(self):
        for spot in (80, 100, 120):
            self.assertEqual(binomial_price(spot, 100, 0, 0.05, 0.2), max(spot-100, 0))
            self.assertEqual(binomial_price(spot, 100, 0, 0.05, 0.2, "put"), max(100-spot, 0))

    def test_zero_volatility(self):
        for rate in (-0.05, 0.05):
            discounted_strike = 100 * math.exp(-rate)
            self.assertAlmostEqual(binomial_price(100, 100, 1, rate, 0),
                                   max(100-discounted_strike, 0))
            self.assertAlmostEqual(binomial_price(100, 100, 1, rate, 0, "put"),
                                   max(discounted_strike-100, 0))

    def test_invalid_tree_can_be_refined(self):
        with self.assertRaises(ValueError):
            binomial_price(100, 100, 1, 0.5, 0.2, steps=1)
        self.assertTrue(math.isfinite(binomial_price(100, 100, 1, 0.5, 0.2, steps=100)))

    def test_invalid_inputs(self):
        valid = dict(spot=100, strike=100, time_to_expiry=1,
                     rate=0.05, volatility=0.2, option_type="call", steps=10)
        invalid = [("spot", 0), ("strike", -1), ("time_to_expiry", -1),
                   ("volatility", -0.1), ("option_type", "american"),
                   ("steps", 0), ("steps", -1), ("steps", 1.5),
                   ("steps", True), ("steps", "10")]
        for field in ("spot", "strike", "time_to_expiry", "rate", "volatility"):
            invalid.extend((field, value) for value in (math.nan, math.inf, -math.inf))
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    binomial_price(**{**valid, field: value})


if __name__ == "__main__":
    unittest.main()
