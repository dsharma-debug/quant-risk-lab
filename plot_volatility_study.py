"""Plot residual risk and mean P&L under different hedge-volatility assumptions."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--premium-mode", choices=["fixed", "hedge_model"], default="fixed")
    args = parser.parse_args()
    folder = Path(__file__).with_name("results")
    prefix = f"volatility_{args.premium_mode}"
    with (folder / f"{prefix}_summary.csv").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("No summary rows; run volatility_study.py first")
    frequencies = sorted({int(row["rebalance_every"]) for row in rows})
    costs = sorted({float(row["cost_bps"]) for row in rows})
    vols = sorted({float(row["hedge_volatility"]) for row in rows})
    first = rows[0]
    actual = 100 * float(first["actual_volatility"])
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), layout="constrained")

    for frequency in frequencies:
        group = sorted((row for row in rows if int(row["rebalance_every"]) == frequency
                        and float(row["cost_bps"]) == costs[0]),
                       key=lambda row: float(row["hedge_volatility"]))
        axes[0].plot([100*float(row["hedge_volatility"]) for row in group],
                     [float(row["rmse_to_zero"]) for row in group], marker="o",
                     label=f"Every {frequency} observation" + ("s" if frequency != 1 else ""))

    for cost in costs:
        group = sorted((row for row in rows if int(row["rebalance_every"]) == frequencies[0]
                        and float(row["cost_bps"]) == cost),
                       key=lambda row: float(row["hedge_volatility"]))
        axes[1].errorbar([100*float(row["hedge_volatility"]) for row in group],
                         [float(row["mean_pnl"]) for row in group],
                         yerr=[1.96*float(row["mean_pnl_standard_error"]) for row in group],
                         marker="o", capsize=4, label=f"{cost:g} bps stock costs")

    axes[0].set_title(f"Residual outcome RMSE ({costs[0]:g} bps costs)")
    axes[0].set_ylabel("RMSE ($ per underlying unit)")
    axes[0].set_ylim(bottom=0)
    interval_label = f"every {frequencies[0]} observation" + ("s" if frequencies[0] != 1 else "")
    axes[1].set_title(f"Mean P&L: {interval_label}\nBars: approximate 95% intervals for the mean")
    axes[1].set_ylabel("Mean terminal P&L ($ per underlying unit)")
    axes[1].axhline(0, color="gray", linewidth=1, linestyle="--")
    for ax in axes:
        ax.axvline(actual, color="gray", linewidth=1, linestyle=":")
        ax.set_xticks([100*v for v in vols], labels=[f"{v:.0%}" for v in vols])
        ax.set_xlabel("Volatility assumed for delta hedging")
        ax.grid(alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=8)

    protocol = "Fixed fair entry premium" if args.premium_mode == "fixed" else "Entry pricing also uses hedge volatility"
    fig.suptitle(f"Volatility-assumption study: {protocol}\n"
                 f"{first['paths']} shared call paths | actual volatility {actual:g}% | "
                 f"{first['steps']} observations/year")
    output = folder / f"{prefix}.png"
    fig.savefig(output, dpi=200)
    plt.close(fig)
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
