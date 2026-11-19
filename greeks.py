"""Analytical delta, gamma and vega under no-dividend Black-Scholes."""

import math

from black_scholes import black_scholes_delta


def normal_pdf(x):
    """Standard normal probability DENSITY, distinct from normal_cdf."""
    return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)


def black_scholes_greeks(
    spot, strike, time_to_expiry, rate, volatility, option_type="call"
):
    """Return sensitivities per underlying unit, for positive time/volatility.

    vega is dV/dsigma with sigma in decimal units. vega_per_1pct is the
    approximate price change for a one-percentage-point volatility increase.
    All sensitivities hold the other model inputs fixed.
    """
    # The existing delta function also validates all inputs and option_type.
    delta = black_scholes_delta(
        spot, strike, time_to_expiry, rate, volatility, option_type
    )
    sqrt_time = math.sqrt(time_to_expiry)
    d1 = (
        math.log(spot / strike)
        + (rate + 0.5 * volatility**2) * time_to_expiry
    ) / (volatility * sqrt_time)
    density = normal_pdf(d1)

    gamma = density / (spot * volatility * sqrt_time)
    vega = spot * density * sqrt_time
    return dict(delta=delta, gamma=gamma, vega=vega,
                vega_per_1pct=0.01 * vega)
