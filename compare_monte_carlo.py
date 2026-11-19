"""Study Monte Carlo price estimates and their sampling uncertainty."""

import argparse

from black_scholes import black_scholes
from monte_carlo import monte_carlo_price


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--samples", nargs="+", type=int, default=[10_000, 40_000, 160_000])
    args = parser.parse_args()
    inputs = dict(spot=100.0, strike=100.0, time_to_expiry=1.0,
                  rate=0.05, volatility=0.20)
    seed = args.seed
    print(f"Random seed: {seed}")

    for option_type in ("call", "put"):
        reference = black_scholes(**inputs, option_type=option_type)
        print(f"\n{option_type.upper()} - Black-Scholes: {reference:.6f}")
        print(f"{'Samples':>10} {'MC price':>12} {'Abs. error':>12} "
              f"{'Std. error':>12} {'Approx. 95% interval':>25}")

        for samples in args.samples:
            result = monte_carlo_price(
                **inputs, option_type=option_type, samples=samples, seed=seed
            )
            interval = f"[{result['ci_low']:.6f}, {result['ci_high']:.6f}]"
            print(f"{samples:10,d} {result['price']:12.6f} "
                  f"{abs(result['price']-reference):12.6f} "
                  f"{result['standard_error']:12.6f} {interval:>25}")

    print("\nStandard error measures sampling uncertainty; it is not the actual error.")


if __name__ == "__main__":
    main()
