"""Plot experiment CSV errors on logarithmic axes.

Run after delta_experiment.py: python plot_delta_convergence.py
Or choose a CSV: python plot_delta_convergence.py path/to/results.csv
"""

import argparse
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Save a figure without needing a desktop plot window.
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", nargs="?", type=Path,
                        default=Path(__file__).with_name("results") / "delta_convergence.csv")
    args = parser.parse_args()

    data = {"call": [], "put": []}
    zero_count = 0
    with args.csv_path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            h = float(row["h"])
            error = float(row["absolute_error"])
            if not math.isfinite(h) or not math.isfinite(error) or h <= 0 or error < 0:
                raise ValueError("Step sizes must be positive and errors nonnegative and finite")
            kind = row["option_type"]
            if kind not in data:
                raise ValueError(f"Unknown option type: {kind}")
            if error == 0:
                zero_count += 1
                continue  # Zero has no finite logarithm; do not invent an error floor.
            data[kind].append((h, error))

    if any(not points for points in data.values()):
        raise ValueError("Need at least one positive error for both call and put")

    fig, ax = plt.subplots(figsize=(8, 5.2), layout="constrained")
    for kind, color, marker in (("call", "#1768AC", "o"), ("put", "#CB591B", "s")):
        points = sorted(data[kind])
        steps, errors = zip(*points)
        ax.loglog(steps, errors, marker=marker, color=color,
                  linewidth=1.7, markersize=6, markerfacecolor="white",
                  label=kind.capitalize())

    ax.set_title("Delta approximation: step size versus error", pad=14)
    ax.set_xlabel("Stock-price step size h (log scale)")
    ax.set_ylabel("Absolute difference from analytical delta (log scale)")
    ax.grid(True, which="major", alpha=0.3)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)

    output = args.csv_path.with_name("delta_convergence.png")
    fig.savefig(output, dpi=200)
    plt.close(fig)
    print(f"Saved chart to {output}")
    if zero_count:
        print(f"Omitted {zero_count} zero-error rows because log(0) is undefined")


if __name__ == "__main__":
    main()
