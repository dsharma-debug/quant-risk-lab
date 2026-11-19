"""Check analytical sensitivities using price-based numerical derivatives."""

import math
import unittest

from black_scholes import black_scholes
from greeks import black_scholes_greeks, normal_pdf


def cases():
    for spot in (80, 100, 120):
        for expiry in (0.25, 1.0):
            for volatility in (0.15, 0.30):
                for rate in (-0.01, 0.05):
                    for kind in ("call", "put"):
                        yield dict(spot=spot, strike=100, time_to_expiry=expiry,
                                   volatility=volatility, rate=rate, option_type=kind)


class GreeksTests(unittest.TestCase):
    def test_delta_against_price_derivative(self):
        for inputs in cases():
            with self.subTest(inputs=inputs):
                h = 0.01
                up = black_scholes(**{**inputs, "spot": inputs["spot"] + h})
                down = black_scholes(**{**inputs, "spot": inputs["spot"] - h})
                numerical = (up-down)/(2*h)
                self.assertAlmostEqual(black_scholes_greeks(**inputs)["delta"], numerical,
                                       delta=2e-7)

    def test_gamma_against_second_price_derivative(self):
        for inputs in cases():
            with self.subTest(inputs=inputs):
                h = 0.01
                up = black_scholes(**{**inputs, "spot": inputs["spot"] + h})
                base = black_scholes(**inputs)
                down = black_scholes(**{**inputs, "spot": inputs["spot"] - h})
                numerical = (up-2*base+down)/h**2
                self.assertAlmostEqual(black_scholes_greeks(**inputs)["gamma"], numerical,
                                       delta=2e-7)

    def test_vega_against_volatility_derivative(self):
        for inputs in cases():
            with self.subTest(inputs=inputs):
                h = 0.00001
                up = black_scholes(**{**inputs, "volatility": inputs["volatility"] + h})
                down = black_scholes(**{**inputs, "volatility": inputs["volatility"] - h})
                numerical = (up-down)/(2*h)
                self.assertAlmostEqual(black_scholes_greeks(**inputs)["vega"], numerical,
                                       delta=2e-6)

    def test_call_put_relations_and_units(self):
        call = black_scholes_greeks(100, 100, 1, 0.05, 0.2)
        put = black_scholes_greeks(100, 100, 1, 0.05, 0.2, "put")
        self.assertAlmostEqual(call["delta"] - put["delta"], 1)
        self.assertEqual(call["gamma"], put["gamma"])
        self.assertEqual(call["vega"], put["vega"])
        self.assertGreater(call["gamma"], 0)
        self.assertGreater(call["vega"], 0)
        self.assertAlmostEqual(call["vega_per_1pct"], call["vega"] * 0.01)

    def test_normal_density(self):
        self.assertAlmostEqual(normal_pdf(0), 1/math.sqrt(2*math.pi))
        self.assertEqual(normal_pdf(-1), normal_pdf(1))

    def test_invalid_inputs(self):
        valid = dict(spot=100, strike=100, time_to_expiry=1,
                     rate=0.05, volatility=0.2, option_type="call")
        invalid = [("spot", 0), ("strike", -1), ("time_to_expiry", 0),
                   ("time_to_expiry", -1), ("volatility", 0),
                   ("volatility", -0.1), ("option_type", "invalid")]
        for field in ("spot", "strike", "time_to_expiry", "rate", "volatility"):
            invalid.extend((field, x) for x in (math.nan, math.inf, -math.inf))
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    black_scholes_greeks(**{**valid, field: value})


if __name__ == "__main__":
    unittest.main()
