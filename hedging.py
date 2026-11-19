"""Single-asset, self-financing discrete delta hedging of one short option unit.

Uniformly spaced observations, no dividends, fractional shares and identical
borrowing/lending rates. Costs apply to initial, rebalancing and closing trades.
"""

import math
import random

from black_scholes import black_scholes, black_scholes_delta


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def simulate_stock_path(spot, time_to_expiry, rate, volatility, steps=252, seed=42):
    """Generate a risk-neutral GBM path including its initial observation.

    volatility is the path-generating volatility, which may later differ from
    the hedge model's assumed volatility. This is a model simulation, not a
    forecast of stock returns.
    """
    if not all(math.isfinite(v) for v in (spot, time_to_expiry, rate, volatility)):
        raise ValueError("All numerical inputs must be finite")
    if spot <= 0 or time_to_expiry <= 0 or volatility < 0:
        raise ValueError("Spot/time must be positive and volatility nonnegative")
    _positive_integer(steps, "steps")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer or None")

    rng = random.Random(seed)
    dt = time_to_expiry / steps
    drift = (rate - 0.5 * volatility**2) * dt
    diffusion = volatility * math.sqrt(dt)
    prices = [spot]
    for _ in range(steps):
        prices.append(prices[-1] * math.exp(drift + diffusion * rng.gauss(0, 1)))
    return prices


def hedge_on_path(
    stock_prices, strike, time_to_expiry, rate, hedge_volatility,
    option_type="call", cost_bps=0.0, rebalance_every=1, record_ledger=True,
    valuation_volatility=None,
):
    """Sell one option unit, delta hedge it, then close and cash-settle at expiry.

    Return a summary and an optional transaction ledger. No external funding
    is injected: initial premium, stock trades, cash interest and fees are
    booked explicitly. Negative cash represents borrowing at the same rate.
    valuation_volatility prices the entry premium and marks the option; when
    omitted it defaults to hedge_volatility, preserving the original behavior.
    Time/hedge volatility must be positive. Prices are observed on a uniform
    time grid. No future path values are used when choosing today's hedge.
    """
    prices = list(stock_prices)
    if len(prices) < 2 or any(not math.isfinite(s) or s <= 0 for s in prices):
        raise ValueError("Need at least two finite, positive stock prices")
    if valuation_volatility is None:
        valuation_volatility = hedge_volatility
    if not all(math.isfinite(v) for v in (strike, time_to_expiry, rate, hedge_volatility,
                                         cost_bps, valuation_volatility)):
        raise ValueError("All numerical inputs must be finite")
    if strike <= 0 or time_to_expiry <= 0 or hedge_volatility <= 0 or cost_bps < 0:
        raise ValueError("Strike/time/hedge volatility must be positive; costs nonnegative")
    if valuation_volatility < 0:
        raise ValueError("Valuation volatility must be nonnegative")
    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'")
    _positive_integer(rebalance_every, "rebalance_every")
    if not isinstance(record_ledger, bool):
        raise ValueError("record_ledger must be a boolean")

    steps = len(prices) - 1
    dt = time_to_expiry / steps
    interest_factor = math.expm1(rate * dt)
    fee_rate = cost_bps / 10_000
    premium = black_scholes(prices[0], strike, time_to_expiry, rate,
                            valuation_volatility, option_type)
    initial_delta = black_scholes_delta(prices[0], strike, time_to_expiry, rate,
                                        hedge_volatility, option_type)
    shares = initial_delta
    turnover = abs(shares) * prices[0]
    initial_cost = turnover * fee_rate
    total_cost = initial_cost
    cash = premium - shares * prices[0] - initial_cost
    trade_count = int(shares != 0)
    ledger = []

    if record_ledger:
        ledger.append(dict(step=0, time=0.0, spot=prices[0], event="initial",
                           shares_before=0.0, trade_shares=shares, shares_after=shares,
                           interest=0.0, trade_cost=initial_cost, option_payoff=0.0,
                           cash=cash, option_value=premium, hedged_equity=-initial_cost))

    payoff = 0.0
    for i in range(1, steps + 1):
        spot = prices[i]
        time = time_to_expiry * i / steps
        remaining = time_to_expiry * (steps - i) / steps
        interest = cash * interest_factor
        cash += interest
        shares_before = shares

        if i == steps:
            target_shares = 0.0  # Close the stock hedge; no expiry delta needed.
            event = "settlement"
        elif i % rebalance_every == 0:
            target_shares = black_scholes_delta(
                spot, strike, remaining, rate, hedge_volatility, option_type
            )
            event = "rebalance"
        else:
            target_shares = shares
            event = "hold"

        trade_shares = target_shares - shares
        traded_notional = abs(trade_shares) * spot
        trade_cost = traded_notional * fee_rate
        cash -= trade_shares * spot + trade_cost
        shares = target_shares
        turnover += traded_notional
        total_cost += trade_cost
        trade_count += int(trade_shares != 0)

        payoff_paid = 0.0
        if i == steps:
            payoff = (max(spot - strike, 0.0) if option_type == "call"
                      else max(strike - spot, 0.0))
            payoff_paid = payoff
            cash -= payoff_paid

        if record_ledger:
            option_value = (0.0 if i == steps else black_scholes(
                spot, strike, remaining, rate, valuation_volatility, option_type
            ))
            ledger.append(dict(step=i, time=time, spot=spot, event=event,
                               shares_before=shares_before, trade_shares=trade_shares,
                               shares_after=shares, interest=interest,
                               trade_cost=trade_cost, option_payoff=payoff_paid,
                               cash=cash, option_value=option_value,
                               hedged_equity=cash + shares * spot - option_value))

    summary = dict(option_type=option_type, strike=strike, initial_spot=prices[0],
                   time_to_expiry=time_to_expiry, rate=rate,
                   hedge_volatility=hedge_volatility, steps=steps,
                   valuation_volatility=valuation_volatility,
                   rebalance_every=rebalance_every, cost_bps=cost_bps,
                   premium_received=premium, initial_delta=initial_delta,
                   terminal_spot=prices[-1], option_payoff=payoff,
                   terminal_pnl=cash, discounted_pnl=cash * math.exp(-rate * time_to_expiry),
                   total_trade_cost=total_cost, turnover_notional=turnover,
                   trade_count=trade_count, final_shares=shares)
    return dict(summary=summary, ledger=ledger)
