"""Compare hedge frequency and stock-trading costs on common simulated paths."""

import argparse
import csv
import math
from pathlib import Path
import statistics

from hedging import hedge_on_path, simulate_stock_path


def percentile(values, probability):
    """Linearly interpolated empirical quantile, including both endpoints."""
    if not values or not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Need observations and a probability between zero and one")
    ordered = sorted(values)
    location = (len(ordered) - 1) * probability
    lower = math.floor(location)
    upper = math.ceil(location)
    weight = location - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize_hedges(rows):
    """Summarize terminal dollar P&L across paths for a single configuration."""
    if len(rows) < 2:
        raise ValueError("Need at least two paths")
    pnls = [row["terminal_pnl"] for row in rows]
    mean = statistics.mean(pnls)
    spread = statistics.stdev(pnls)
    mean_se = spread / math.sqrt(len(rows))
    return dict(
        paths=len(rows), mean_pnl=mean, std_pnl=spread,
        rmse_to_zero=math.sqrt(statistics.mean(pnl**2 for pnl in pnls)),
        mean_pnl_standard_error=mean_se,
        mean_pnl_ci_low=mean - 1.96 * mean_se,
        mean_pnl_ci_high=mean + 1.96 * mean_se,
        pnl_p05=percentile(pnls, 0.05), pnl_p95=percentile(pnls, 0.95),
        mean_total_trade_cost=statistics.mean(row["total_trade_cost"] for row in rows),
        mean_trade_count=statistics.mean(row["trade_count"] for row in rows),
        mean_turnover_notional=statistics.mean(row["turnover_notional"] for row in rows),
    )


def run_study(paths=500, frequencies=(1, 5, 21, 63), cost_levels=(0, 5),
              seed_start=1000, steps=252, actual_volatility=0.20,
              hedge_volatility=0.20, option_type="call"):
    """Reuse each underlying path for every frequency/cost configuration.

    Different paths use different seeded pseudorandom streams. Configurations
    on a given path are paired observations, not independent samples.
    """
    for name, value, minimum in (("paths", paths, 2), ("steps", steps, 1)):
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"{name} must be an integer of at least {minimum}")
    if isinstance(seed_start, bool) or not isinstance(seed_start, int):
        raise ValueError("seed_start must be an integer")
    frequencies = tuple(frequencies)
    cost_levels = tuple(cost_levels)
    if not frequencies or any(isinstance(f, bool) or not isinstance(f, int)
                              or not 1 <= f <= steps for f in frequencies):
        raise ValueError("Frequencies must be integer intervals from 1 through steps")
    if len(set(frequencies)) != len(frequencies):
        raise ValueError("Frequencies must be distinct")
    if not cost_levels or any(isinstance(c, bool) or not math.isfinite(c) or c < 0
                             for c in cost_levels):
        raise ValueError("Costs must be finite nonnegative basis-point values")
    if len(set(cost_levels)) != len(cost_levels):
        raise ValueError("Costs must be distinct")
    if (not math.isfinite(actual_volatility) or actual_volatility < 0
            or not math.isfinite(hedge_volatility) or hedge_volatility <= 0):
        raise ValueError("Actual volatility must be nonnegative; hedge volatility positive")
    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'")

    groups = {(f, c): [] for f in frequencies for c in cost_levels}
    trials = []
    for path_index in range(paths):
        seed = seed_start + path_index
        # Generate ONCE per seed. All policies see the same full fine-grid path.
        prices = simulate_stock_path(100, 1, 0.05, actual_volatility, steps, seed)
        for frequency in frequencies:
            for cost in cost_levels:
                result = hedge_on_path(
                    prices, 100, 1, 0.05, hedge_volatility, option_type,
                    cost_bps=cost, rebalance_every=frequency, record_ledger=False,
                )
                row = dict(seed=seed, actual_volatility=actual_volatility,
                           **result["summary"])
                trials.append(row)
                groups[(frequency, cost)].append(row)

    metadata = ("option_type", "strike", "initial_spot", "time_to_expiry", "rate",
                "hedge_volatility", "actual_volatility", "steps", "rebalance_every", "cost_bps")
    summaries = []
    for group in groups.values():
        first = group[0]
        summaries.append(dict(**{key: first[key] for key in metadata},
                              seed_start=seed_start, **summarize_hedges(group)))
    return trials, summaries


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths", type=int, default=500)
    parser.add_argument("--frequencies", type=int, nargs="+", default=[1, 5, 21, 63])
    parser.add_argument("--costs", type=float, nargs="+", default=[0, 5])
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--steps", type=int, default=252)
    parser.add_argument("--actual-vol", type=float, default=0.20)
    parser.add_argument("--hedge-vol", type=float, default=0.20)
    parser.add_argument("--option-type", choices=["call", "put"], default="call")
    args = parser.parse_args()
    print(f"Running {args.paths} shared stock paths across "
          f"{len(args.frequencies)*len(args.costs)} configurations...")
    trials, summaries = run_study(
        args.paths, args.frequencies, args.costs, args.seed_start, args.steps,
        args.actual_vol, args.hedge_vol, args.option_type,
    )

    print(f"{'Every steps':>12} {'Cost bps':>9} {'Mean P&L':>11} {'Std. P&L':>11} "
          f"{'RMSE':>10} {'P&L p05':>11} {'Mean fees':>11}")
    for row in summaries:
        print(f"{row['rebalance_every']:12d} {row['cost_bps']:9.1f} "
              f"{row['mean_pnl']:11.6f} {row['std_pnl']:11.6f} "
              f"{row['rmse_to_zero']:10.6f} {row['pnl_p05']:11.6f} "
              f"{row['mean_total_trade_cost']:11.6f}")

    output = Path(__file__).with_name("results")
    output.mkdir(exist_ok=True)
    write_csv(output / "hedging_study_trials.csv", trials)
    write_csv(output / "hedging_study_summary.csv", summaries)
    print("\nSaved results/hedging_study_trials.csv and results/hedging_study_summary.csv")
    print("P&L p05 is the empirical 5th percentile of outcomes, not a confidence interval.")


if __name__ == "__main__":
    main()
