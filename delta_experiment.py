"""Compare finite-difference step sizes and save reproducible results."""

import csv
from pathlib import Path

from black_scholes import black_scholes, black_scholes_delta


def main():
    inputs = dict(
        spot=100.0,
        strike=100.0,
        time_to_expiry=1.0,
        rate=0.05,
        volatility=0.20,
    )
    step_sizes = [1.0, 0.1, 0.01, 0.001, 0.0001,
                  0.00001, 0.000001, 0.0000001, 0.00000001]
    rows = []

    for option_type in ("call", "put"):
        exact = black_scholes_delta(**inputs, option_type=option_type)
        print(f"\n{option_type.upper()} - analytical delta: {exact:.12f}")
        print(f"{'h':>12} {'Estimated delta':>18} {'Absolute error':>18}")

        for h in step_sizes:
            up = {**inputs, "spot": inputs["spot"] + h}
            down = {**inputs, "spot": inputs["spot"] - h}
            price_up = black_scholes(**up, option_type=option_type)
            price_down = black_scholes(**down, option_type=option_type)
            estimate = (price_up - price_down) / (2 * h)
            error = abs(estimate - exact)

            print(f"{h:12.1e} {estimate:18.12f} {error:18.3e}")
            rows.append(dict(
                option_type=option_type, **inputs, h=h,
                estimated_delta=estimate, analytical_delta=exact,
                absolute_error=error,
            ))

    output_folder = Path(__file__).with_name("results")
    output_folder.mkdir(exist_ok=True)
    output = output_folder / "delta_convergence.csv"
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved results to {output.name}")


if __name__ == "__main__":
    main()
