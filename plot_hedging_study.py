"""Chart RMSE and fees from the saved hedge-frequency study."""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    folder = Path(__file__).with_name("results")
    with (folder / "hedging_study_summary.csv").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("The study summary has no rows; run hedging_study.py first")
    costs = sorted({float(row["cost_bps"]) for row in rows})
    frequencies = sorted({int(row["rebalance_every"]) for row in rows})
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), layout="constrained")

    for cost in costs:
        group = sorted((row for row in rows if float(row["cost_bps"]) == cost),
                       key=lambda row: int(row["rebalance_every"]))
        x = [int(row["rebalance_every"]) for row in group]
        label = f"{cost:g} bps stock-trading costs"
        axes[0].plot(x, [float(row["rmse_to_zero"]) for row in group], marker="o", label=label)
        axes[1].plot(x, [float(row["mean_total_trade_cost"]) for row in group], marker="o", label=label)

    axes[0].set_title("Terminal hedging outcome: RMSE to zero")
    axes[1].set_title("Average nominal stock-trading fees")
    axes[0].set_ylabel("RMSE ($ per underlying unit)")
    axes[1].set_ylabel("Fees ($ per underlying unit)")
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xticks(frequencies, labels=[str(value) for value in frequencies])
        ax.minorticks_off()
        ax.set_xlabel("Rebalance every N observations")
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=8)

    first = rows[0]
    fig.suptitle(f"Delta hedging: frequency, error and costs\n"
                 f"{first['paths']} shared {first['option_type']} paths | "
                 f"{first['steps']} observations over {float(first['time_to_expiry']):g} year(s) | "
                 f"path vol {float(first['actual_volatility']):.0%}, hedge vol {float(first['hedge_volatility']):.0%}")
    output = folder / "hedging_frequency.png"
    fig.savefig(output, dpi=200)
    plt.close(fig)
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
