"""Compare plain and antithetic Monte Carlo at equal payoff budgets."""

import argparse
from pathlib import Path

from antithetic import antithetic_price
from black_scholes import black_scholes
from mc_repeated_experiment import summarize_trials, write_csv
from monte_carlo import monte_carlo_price


def run_comparison(samples=10_000, repetitions=100, seed_start=1000):
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 2:
        raise ValueError("repetitions must be an integer of at least 2")
    if isinstance(seed_start, bool) or not isinstance(seed_start, int):
        raise ValueError("seed_start must be an integer")
    if (isinstance(samples, bool) or not isinstance(samples, int)
            or samples < 4 or samples % 2):
        raise ValueError("samples must be an even integer of at least 4")

    inputs = dict(spot=100.0, strike=100.0, time_to_expiry=1.0,
                  rate=0.05, volatility=0.20)
    trials = []
    summaries = []

    for kind in ("call", "put"):
        reference = black_scholes(**inputs, option_type=kind)
        for method, pricer in (("plain", monte_carlo_price),
                               ("antithetic", antithetic_price)):
            group = []
            observations = samples if method == "plain" else samples // 2
            for repetition in range(repetitions):
                result = pricer(**inputs, option_type=kind, samples=samples,
                                seed=seed_start + repetition)
                # Use the same CSV fields for both methods. For antithetic,
                # independent_observations counts pairs, not individual payoffs.
                row = dict(method=method, option_type=kind, **inputs,
                           repetition=repetition + 1, samples=samples,
                           independent_observations=observations,
                           seed=result["seed"], reference_price=reference,
                           price=result["price"], standard_error=result["standard_error"],
                           ci_low=result["ci_low"], ci_high=result["ci_high"])
                row["covered"] = int(result["ci_low"] <= reference <= result["ci_high"])
                group.append(row)
            trials.extend(group)
            summaries.append(dict(method=method, option_type=kind, **inputs,
                                  samples=samples, independent_observations=observations,
                                  seed_start=seed_start,
                                  **summarize_trials(group, reference)))

    # Empirical variance ratio across repeated price estimates, per option.
    for kind in ("call", "put"):
        plain, anti = [row for row in summaries if row["option_type"] == kind]
        ratio = (plain["empirical_sd"] / anti["empirical_sd"])**2 if anti["empirical_sd"] else float("nan")
        plain["variance_reduction_factor"] = 1.0
        anti["variance_reduction_factor"] = ratio
    return trials, summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=1000)
    args = parser.parse_args()
    print(f"Each method: {args.samples:,} payoff evaluations per trial, {args.runs} trials.")
    trials, summaries = run_comparison(args.samples, args.runs, args.seed_start)

    print(f"{'Option':>6} {'Method':>11} {'RMSE':>10} {'Emp. SD':>10} "
          f"{'Mean SE':>10} {'Coverage':>10} {'Var. factor':>12}")
    for row in summaries:
        print(f"{row['option_type']:>6} {row['method']:>11} {row['rmse']:10.6f} "
              f"{row['empirical_sd']:10.6f} {row['mean_standard_error']:10.6f} "
              f"{row['coverage_rate']:9.1%} {row['variance_reduction_factor']:12.3f}")

    output_dir = Path(__file__).with_name("results")
    output_dir.mkdir(exist_ok=True)
    write_csv(output_dir / "variance_reduction_trials.csv", trials)
    write_csv(output_dir / "variance_reduction_summary.csv", summaries)
    print("\nSaved results/variance_reduction_trials.csv and results/variance_reduction_summary.csv")
    print("Variance factor > 1 indicates lower empirical variance than plain Monte Carlo.")


if __name__ == "__main__":
    main()
