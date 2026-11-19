"""Inspect one stock path, cash ledger and transaction-cost comparison."""

import csv
from pathlib import Path

from hedging import hedge_on_path, simulate_stock_path


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    spot, strike, expiry, rate = 100.0, 100.0, 1.0, 0.05
    actual_volatility = hedge_volatility = 0.20
    steps, seed = 252, 42
    prices = simulate_stock_path(spot, expiry, rate, actual_volatility, steps, seed)
    output = Path(__file__).with_name("results")
    output.mkdir(exist_ok=True)
    write_csv(output / "hedge_path.csv", [dict(step=i, time=expiry*i/steps, spot=s)
                                           for i, s in enumerate(prices)])
    summaries = []

    print("One simulated path; short one call unit; rebalance every observation.")
    print(f"Seed: {seed} | Observations after start: {steps}")
    print(f"Stock: {prices[0]:.6f} -> {prices[-1]:.6f}")
    print(f"{'Cost (bps)':>12} {'Premium':>12} {'Final payoff':>14} "
          f"{'Fees paid':>12} {'Terminal P&L':>15}")

    for cost in (0, 5):
        result = hedge_on_path(prices, strike, expiry, rate, hedge_volatility,
                               option_type="call", cost_bps=cost)
        row = dict(seed=seed, actual_volatility=actual_volatility, **result["summary"])
        summaries.append(row)
        write_csv(output / f"hedge_ledger_{cost}bps.csv", result["ledger"])
        print(f"{cost:12.1f} {row['premium_received']:12.6f} {row['option_payoff']:14.6f} "
              f"{row['total_trade_cost']:12.6f} {row['terminal_pnl']:15.6f}")
        if cost == 0:
            first = result["ledger"][0]
            print(f"  Initial stock hedge: {first['shares_after']:.6f} shares")
            print(f"  Initial cash balance: {first['cash']:.6f}")

    write_csv(output / "hedge_summary.csv", summaries)
    print("\nSaved results/hedge_path.csv, hedge_summary.csv and two hedge ledgers.")
    print("Terminal P&L is the cash left after closing the stock hedge and paying the option.")
    print("One path illustrates accounting; performance conclusions require many paths.")


if __name__ == "__main__":
    main()
