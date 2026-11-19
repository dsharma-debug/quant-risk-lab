"""Repeated Monte Carlo trials: sampling spread, RMSE and interval coverage.

Run: python mc_repeated_experiment.py
Quick run: python mc_repeated_experiment.py --runs 20
"""

import argparse
import csv
import math
from pathlib import Path
import statistics

from black_scholes import black_scholes
from monte_carlo import monte_carlo_price


def summarize_trials(trials, reference):
    """Summarize repeated estimates of one price at one sample count."""
    if len(trials) < 2:
        raise ValueError("Need at least two repetitions")
    prices = [row["price"] for row in trials]
    errors = [price - reference for price in prices]
    covered = sum(row["ci_low"] <= reference <= row["ci_high"] for row in trials)
    return {
        "repetitions": len(trials),
        "reference_price": reference,
        "mean_price": statistics.mean(prices),
        "estimated_bias": statistics.mean(errors),
        "rmse": math.sqrt(statistics.mean(error**2 for error in errors)),
        "empirical_sd": statistics.stdev(prices),
        "mean_standard_error": statistics.mean(row["standard_error"] for row in trials),
        "coverage_count": covered,
        "coverage_rate": covered / len(trials),
    }


def run_experiment(sample_counts=(1000, 4000, 16000), repetitions=100, seed_start=1000):
    """Return trial and summary rows for the standard call/put example.

    Within each group, successive trials use different seeds. Seeds are reused
    across sample counts and option types, so comparisons between groups share
    random numbers; they are not independent sets of trials.
    """
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 2:
        raise ValueError("repetitions must be an integer of at least 2")
    if isinstance(seed_start, bool) or not isinstance(seed_start, int):
        raise ValueError("seed_start must be an integer")
    sample_counts = tuple(sample_counts)
    if not sample_counts or any(isinstance(n, bool) or not isinstance(n, int) or n < 2
                                for n in sample_counts):
        raise ValueError("Sample counts must be integers of at least 2")
    if len(set(sample_counts)) != len(sample_counts):
        raise ValueError("Sample counts must be distinct")

    inputs = dict(spot=100.0, strike=100.0, time_to_expiry=1.0,
                  rate=0.05, volatility=0.20)
    all_trials = []
    summaries = []

    for kind in ("call", "put"):
        reference = black_scholes(**inputs, option_type=kind)
        for samples in sample_counts:
            group = []
            for repetition in range(repetitions):
                seed = seed_start + repetition
                result = monte_carlo_price(
                    **inputs, option_type=kind, samples=samples, seed=seed
                )
                row = dict(option_type=kind, **inputs, repetition=repetition + 1,
                           reference_price=reference, **result)
                row["covered"] = int(result["ci_low"] <= reference <= result["ci_high"])
                group.append(row)

            all_trials.extend(group)
            summaries.append(dict(option_type=kind, **inputs, samples=samples,
                                  seed_start=seed_start,
                                  **summarize_trials(group, reference)))

    return all_trials, summaries


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--samples", type=int, nargs="+", default=[1000, 4000, 16000])
    parser.add_argument("--seed-start", type=int, default=1000)
    args = parser.parse_args()

    print(f"Running {args.runs} repetitions for each option/sample-count group...")
    trials, summaries = run_experiment(args.samples, args.runs, args.seed_start)

    print(f"{'Option':>6} {'Samples':>9} {'Est. bias':>11} {'RMSE':>10} "
          f"{'Emp. SD':>10} {'Mean SE':>10} {'Coverage':>10}")
    for row in summaries:
        print(f"{row['option_type']:>6} {row['samples']:9,d} "
              f"{row['estimated_bias']:11.6f} {row['rmse']:10.6f} "
              f"{row['empirical_sd']:10.6f} {row['mean_standard_error']:10.6f} "
              f"{row['coverage_rate']:9.1%}")

    output_dir = Path(__file__).with_name("results")
    output_dir.mkdir(exist_ok=True)
    write_csv(output_dir / "mc_trials.csv", trials)
    write_csv(output_dir / "mc_summary.csv", summaries)
    print("\nSaved results/mc_trials.csv and results/mc_summary.csv")
    print("Coverage is measured over repeated trials; it need not equal exactly 95%.")


if __name__ == "__main__":
    main()
