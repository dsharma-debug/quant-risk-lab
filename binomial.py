"""Cox-Ross-Rubinstein pricing for European options without dividends.

Uses O(N) working memory and O(N^2) time for N steps.
Input units match black_scholes.py. No analytical pricer is called here.
"""

import math


def binomial_price(
    spot, strike, time_to_expiry, rate, volatility,
    option_type="call", steps=100,
):
    """Return the European option price per underlying unit.

    This first tree supports European exercise only. Very extreme parameters
    can exceed floating-point range; validation targets ordinary equity inputs.
    """
    for value in (spot, strike, time_to_expiry, rate, volatility):
        if not math.isfinite(value):
            raise ValueError("All numerical inputs must be finite")
    if spot <= 0 or strike <= 0:
        raise ValueError("Spot and strike must be positive")
    if time_to_expiry < 0 or volatility < 0:
        raise ValueError("Time and volatility must be nonnegative")
    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be a positive integer")

    # Treat deterministic boundary cases before building a tree.
    if time_to_expiry == 0:
        if option_type == "call":
            return max(spot - strike, 0.0)
        return max(strike - spot, 0.0)
    if volatility == 0:
        discounted_strike = strike * math.exp(-rate * time_to_expiry)
        if option_type == "call":
            return max(spot - discounted_strike, 0.0)
        return max(discounted_strike - spot, 0.0)

    # 1. Define one time step and the up/down stock multipliers.
    dt = time_to_expiry / steps
    move = volatility * math.sqrt(dt)
    up = math.exp(move)
    down = 1.0 / up
    growth = math.exp(rate * dt)
    discount = math.exp(-rate * dt)

    # Strict no-arbitrage condition: down < growth < up.
    if not down < growth < up:
        raise ValueError("Invalid tree probabilities; increase steps")

    # 2. Risk-neutral pricing probability, NOT a market forecast.
    probability_up = (growth - down) / (up - down)

    # 3. At expiry, j upward moves and (steps-j) downward moves
    #    lead to S * up**j * down**(steps-j).
    values = []
    for j in range(steps + 1):
        terminal_spot = spot * math.exp((2 * j - steps) * move)
        if option_type == "call":
            payoff = max(terminal_spot - strike, 0.0)
        else:
            payoff = max(strike - terminal_spot, 0.0)
        values.append(payoff)

    # 4. Work backward: discounted risk-neutral expected value.
    # Ascending j keeps values[j+1] from the previous time layer intact
    # until it has been used. The list shrinks by one node each layer.
    for level in range(steps - 1, -1, -1):
        for j in range(level + 1):
            values[j] = discount * (
                probability_up * values[j + 1]
                + (1.0 - probability_up) * values[j]
            )
        values.pop()

    return values[0]
