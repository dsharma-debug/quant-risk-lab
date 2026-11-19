"""Separate hedge-volatility errors from entry-premium assumptions."""

import argparse
import math
from pathlib import Path

from black_scholes import black_scholes
from hedging import hedge_on_path, simulate_stock_path
from hedging_study import summarize_hedges, write_csv


def run_volatility_study(paths=500, hedge_volatilities=(0.15, 0.20, 0.25),
                         frequencies=(1, 5, 21), cost_levels=(0, 5),
                         actual_volatility=0.20, premium_mode="fixed",
                         seed_start=1000, steps=252):
    """Hold true dynamics fixed and vary the volatility used for delta hedging.

    fixed: all policies receive the fair premium under actual_volatility.
    hedge_model: entry premium also uses each policy's hedge volatility.
    In either mode, all configurations share each exact simulated stock path.
    """
    for name, value, minimum in (("paths", paths, 2), ("steps", steps, 1)):
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"{name} must be an integer of at least {minimum}")
    if isinstance(seed_start, bool) or not isinstance(seed_start, int):
        raise ValueError("seed_start must be an integer")
    hedge_volatilities = tuple(hedge_volatilities)
    frequencies = tuple(frequencies)
    cost_levels = tuple(cost_levels)
    if (not hedge_volatilities or any(not math.isfinite(v) or v <= 0 for v in hedge_volatilities)
            or len(set(hedge_volatilities)) != len(hedge_volatilities)):
        raise ValueError("Hedge volatilities must be distinct positive finite values")
    if (not frequencies or any(isinstance(f, bool) or not isinstance(f, int)
                              or not 1 <= f <= steps for f in frequencies)
            or len(set(frequencies)) != len(frequencies)):
        raise ValueError("Frequencies must be distinct integer intervals from 1 through steps")
    if (not cost_levels or any(isinstance(c, bool) or not math.isfinite(c) or c < 0 for c in cost_levels)
            or len(set(cost_levels)) != len(cost_levels)):
        raise ValueError("Costs must be distinct finite nonnegative basis-point values")
    if not math.isfinite(actual_volatility) or actual_volatility < 0:
        raise ValueError("Actual volatility must be nonnegative and finite")
    if premium_mode not in ("fixed", "hedge_model"):
        raise ValueError("premium_mode must be 'fixed' or 'hedge_model'")

    fair_reference_premium = black_scholes(100, 100, 1, 0.05, actual_volatility)
    groups = {(v, f, c): [] for v in hedge_volatilities for f in frequencies for c in cost_levels}
    trials = []
    for path_index in range(paths):
        seed = seed_start + path_index
        prices = simulate_stock_path(100, 1, 0.05, actual_volatility, steps, seed)
        for volatility in hedge_volatilities:
            valuation_volatility = actual_volatility if premium_mode == "fixed" else volatility
            for frequency in frequencies:
                for cost in cost_levels:
                    result = hedge_on_path(
                        prices, 100, 1, 0.05, volatility, cost_bps=cost,
                        rebalance_every=frequency, record_ledger=False,
                        valuation_volatility=valuation_volatility,
                    )
                    row = dict(premium_mode=premium_mode, seed=seed,
                               actual_volatility=actual_volatility,
                               fair_reference_premium=fair_reference_premium,
                               **result["summary"])
                    trials.append(row)
                    groups[(volatility, frequency, cost)].append(row)

    fields = ("premium_mode", "actual_volatility", "hedge_volatility", "valuation_volatility",
              "option_type", "strike", "initial_spot", "time_to_expiry", "rate", "steps",
              "rebalance_every", "cost_bps", "premium_received", "fair_reference_premium")
    summaries = []
    for group in groups.values():
        first = group[0]
        summary = dict(**{key: first[key] for key in fields}, seed_start=seed_start,
                       **summarize_hedges(group))
        # Under risk-neutral dynamics, any admissible self-financing hedge has
        # this expected terminal P&L before fees. A different premium shifts
        # expected P&L; changing delta alone need not do so.
        summary["no_cost_mean_benchmark"] = (
            first["premium_received"] - fair_reference_premium
        ) * math.exp(0.05)
        summaries.append(summary)
    return trials, summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths", type=int, default=500)
    parser.add_argument("--hedge-vols", type=float, nargs="+", default=[0.15, 0.20, 0.25])
    parser.add_argument("--frequencies", type=int, nargs="+", default=[1, 5, 21])
    parser.add_argument("--costs", type=float, nargs="+", default=[0, 5])
    parser.add_argument("--actual-vol", type=float, default=0.20)
    parser.add_argument("--premium-mode", choices=["fixed", "hedge_model"], default="fixed")
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--steps", type=int, default=252)
    args = parser.parse_args()
    print(f"Running {args.paths} common paths | actual volatility {args.actual_vol:.0%} "
          f"| premium mode: {args.premium_mode}")
    trials, summaries = run_volatility_study(
        args.paths, args.hedge_vols, args.frequencies, args.costs,
        args.actual_vol, args.premium_mode, args.seed_start, args.steps,
    )
    print(f"{'Hedge vol':>10} {'Every':>7} {'Cost bps':>9} {'Premium':>11} "
          f"{'Mean P&L':>11} {'Std. P&L':>11} {'RMSE':>11}")
    for row in summaries:
        print(f"{row['hedge_volatility']:9.0%} {row['rebalance_every']:7d} "
              f"{row['cost_bps']:9.1f} {row['premium_received']:11.6f} "
              f"{row['mean_pnl']:11.6f} {row['std_pnl']:11.6f} {row['rmse_to_zero']:11.6f}")

    folder = Path(__file__).with_name("results")
    folder.mkdir(exist_ok=True)
    prefix = f"volatility_{args.premium_mode}"
    write_csv(folder / f"{prefix}_trials.csv", trials)
    write_csv(folder / f"{prefix}_summary.csv", summaries)
    print(f"\nSaved results/{prefix}_trials.csv and results/{prefix}_summary.csv")
    print("Fixed-premium mode changes hedge decisions while holding entry pricing fixed.")


if __name__ == "__main__":
    main()
