"""Compare the independent tree implementation with Black-Scholes."""

import argparse

from binomial import binomial_price
from black_scholes import black_scholes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", nargs="+", type=int,
                        default=[10, 11, 12, 13, 50, 51, 52, 53, 100, 500, 1000])
    args = parser.parse_args()
    inputs = dict(spot=100.0, strike=100.0, time_to_expiry=1.0,
                  rate=0.05, volatility=0.20)

    for option_type in ("call", "put"):
        reference = black_scholes(**inputs, option_type=option_type)
        print(f"\n{option_type.upper()} - Black-Scholes: {reference:.6f}")
        print(f"{'Steps':>8} {'Tree price':>14} {'Absolute error':>16}")
        for steps in args.steps:
            price = binomial_price(**inputs, option_type=option_type, steps=steps)
            print(f"{steps:8d} {price:14.6f} {abs(price - reference):16.6f}")


if __name__ == "__main__":
    main()
