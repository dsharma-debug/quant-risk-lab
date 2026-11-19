"""Small, testable adapters between the dashboard and existing model code."""

import csv
import io
import math
from pathlib import Path

from antithetic import antithetic_price
from binomial import binomial_price
from black_scholes import black_scholes
from greeks import black_scholes_greeks
from hedging import hedge_on_path, simulate_stock_path
from monte_carlo import monte_carlo_price
from volatility_study import run_volatility_study


STUDIES = {
    "Hedge frequency and costs": ("hedging_study_summary.csv", "python hedging_study.py"),
    "Volatility assumptions": ("volatility_fixed_summary.csv", "python volatility_study.py"),
    "Monte Carlo precision": ("mc_summary.csv", "python mc_repeated_experiment.py"),
    "Variance reduction": ("variance_reduction_summary.csv", "python compare_variance_reduction.py"),
}


def make_contract(spot, strike, years, rate_percent, volatility_percent, option_type):
    """Convert displayed percentages to the backend's decimal conventions."""
    contract = dict(spot=float(spot), strike=float(strike), time_to_expiry=float(years),
                    rate=float(rate_percent)/100, volatility=float(volatility_percent)/100,
                    option_type=option_type)
    # Reuse the model's validation, including positive time and volatility.
    black_scholes_greeks(**contract)
    return contract


def pricing_snapshot(contract, tree_steps=200, samples=10_000, seed=42):
    reference = black_scholes(**contract)
    greeks = black_scholes_greeks(**contract)
    settings = dict(tree_steps=tree_steps, samples=samples, seed=seed)
    rows = []

    def add(method, price, se=None, low=None, high=None, message=""):
        rows.append(dict(method=method, **contract, **settings, price=price,
                         absolute_error=None if price is None else abs(price-reference),
                         standard_error=se, ci_low=low, ci_high=high, message=message))

    add("Black-Scholes", reference)
    try:
        add("Binomial tree", binomial_price(**contract, steps=tree_steps))
    except ValueError as error:
        # A coarse CRR tree can be invalid even for valid continuous-model inputs.
        add("Binomial tree", None, message=str(error))
    for label, pricer in (("Monte Carlo", monte_carlo_price), ("Antithetic MC", antithetic_price)):
        result = pricer(**contract, samples=samples, seed=seed)
        add(label, result["price"], result["standard_error"], result["ci_low"], result["ci_high"])
    return dict(contract=dict(contract), settings=settings, rows=rows, greeks=greeks)


def hedge_snapshot(contract, actual_vol_percent=20.0, hedge_vol_percent=20.0,
                   steps=252, rebalance_every=1, cost_bps=5.0, seed=42):
    actual_vol = float(actual_vol_percent) / 100
    assumed_vol = float(hedge_vol_percent) / 100
    if not math.isfinite(actual_vol) or actual_vol < 0:
        raise ValueError("Path volatility must be nonnegative")
    prices = simulate_stock_path(contract["spot"], contract["time_to_expiry"],
                                 contract["rate"], actual_vol, steps, seed)
    common = dict(stock_prices=prices, strike=contract["strike"],
                  time_to_expiry=contract["time_to_expiry"], rate=contract["rate"],
                  hedge_volatility=assumed_vol, option_type=contract["option_type"],
                  rebalance_every=rebalance_every, valuation_volatility=actual_vol)
    with_costs = hedge_on_path(**common, cost_bps=cost_bps)
    without_costs = hedge_on_path(**common, cost_bps=0, record_ledger=False)
    return dict(contract=dict(contract), actual_volatility=actual_vol,
                hedge_volatility=assumed_vol, seed=seed, prices=prices,
                with_costs=with_costs, without_costs=without_costs)


def interactive_study(paths=250, actual_vol_percent=20.0, hedge_vol_percent=20.0,
                       cost_bps=5.0, seed_start=1000):
    """A fixed-premium frequency study, retained in the dashboard session."""
    costs = (0,) if cost_bps == 0 else (0, cost_bps)
    trials, summaries = run_volatility_study(
        paths=paths, hedge_volatilities=(hedge_vol_percent/100,),
        frequencies=(1, 5, 21, 63), cost_levels=costs,
        actual_volatility=actual_vol_percent/100, premium_mode="fixed", seed_start=seed_start,
    )
    return dict(trials=trials, summaries=summaries)


def rows_to_csv(rows):
    if not rows:
        raise ValueError("No rows to export")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def load_saved_study(name, folder=None):
    """Read only a known study filename, not an arbitrary user-supplied path."""
    filename, _ = STUDIES[name]
    folder = Path(folder) if folder is not None else Path(__file__).with_name("results")
    with (folder / filename).open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("The saved summary has no rows")
    converted = []
    for row in rows:
        new = {}
        for key, value in row.items():
            try:
                number = float(value)
                new[key] = int(number) if math.isfinite(number) and number.is_integer() else number
            except (ValueError, TypeError):
                new[key] = value
        converted.append(new)
    return converted
