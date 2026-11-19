"""Validate analytical Greeks against price perturbations and save the results."""

import csv
from pathlib import Path

from black_scholes import black_scholes
from greeks import black_scholes_greeks


def main():
    inputs = dict(spot=100.0, strike=100.0, time_to_expiry=1.0,
                  rate=0.05, volatility=0.20)
    spot_step = 0.01
    volatility_step = 0.0001
    rows = []

    for kind in ("call", "put"):
        exact = black_scholes_greeks(**inputs, option_type=kind)
        base = black_scholes(**inputs, option_type=kind)
        up = black_scholes(**{**inputs, "spot": inputs["spot"] + spot_step}, option_type=kind)
        down = black_scholes(**{**inputs, "spot": inputs["spot"] - spot_step}, option_type=kind)
        vol_up = black_scholes(**{**inputs, "volatility": inputs["volatility"] + volatility_step}, option_type=kind)
        vol_down = black_scholes(**{**inputs, "volatility": inputs["volatility"] - volatility_step}, option_type=kind)
        numerical = dict(delta=(up-down)/(2*spot_step),
                         gamma=(up-2*base+down)/spot_step**2,
                         vega=(vol_up-vol_down)/(2*volatility_step))

        print(f"\n{kind.upper()} - price: {base:.6f}")
        print(f"{'Greek':>8} {'Analytical':>14} {'Numerical':>14} {'Abs. difference':>18}")
        for greek in ("delta", "gamma", "vega"):
            difference = abs(numerical[greek] - exact[greek])
            print(f"{greek:>8} {exact[greek]:14.8f} {numerical[greek]:14.8f} {difference:18.3e}")
            rows.append(dict(option_type=kind, **inputs, greek=greek,
                             step_size=volatility_step if greek == "vega" else spot_step,
                             analytical=exact[greek], numerical=numerical[greek],
                             absolute_difference=difference))

        print(f"Vega per 1 percentage point of volatility: {exact['vega_per_1pct']:.6f}")

        # A separate illustrative scenario: only the stock price changes by $1.
        stock_move = 1.0
        moved_price = black_scholes(**{**inputs, "spot": inputs["spot"] + stock_move}, option_type=kind)
        linear_prediction = exact["delta"] * stock_move
        quadratic_prediction = linear_prediction + 0.5 * exact["gamma"] * stock_move**2
        print("For a $1 stock-price increase, with other inputs fixed:")
        print(f"  Delta-only price-change prediction:  {linear_prediction:.6f}")
        print(f"  Delta-gamma price-change prediction: {quadratic_prediction:.6f}")
        print(f"  Actual model price change:          {moved_price-base:.6f}")

    output_dir = Path(__file__).with_name("results")
    output_dir.mkdir(exist_ok=True)
    output = output_dir / "greeks_validation.csv"
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("\nSaved results/greeks_validation.csv")


if __name__ == "__main__":
    main()
