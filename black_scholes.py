"""European option prices under Black-Scholes, without dividends.

Rates and volatility are annualized decimals; time is measured in years.
Returns the price per unit of the underlying, not per option contract.
"""

import math


def normal_cdf(x: float) -> float:
    """Return P(Z <= x) for a standard normal random variable Z."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def black_scholes(
    spot: float,
    strike: float,
    time_to_expiry: float,
    rate: float,
    volatility: float,
    option_type: str = "call",
) -> float:
    """Price a European call or put on a non-dividend-paying asset.

    Assumptions: constant volatility and continuously compounded risk-free
    rate, lognormal stock prices, frictionless trading, and European exercise.
    Negative interest rates are supported. Negative time or volatility is not.
    """
    inputs = {
        "spot": spot,
        "strike": strike,
        "time_to_expiry": time_to_expiry,
        "rate": rate,
        "volatility": volatility,
    }
    for name, value in inputs.items():
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")

    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if time_to_expiry < 0 or volatility < 0:
        raise ValueError("time_to_expiry and volatility must be nonnegative")
    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'")

    # At expiry the value equals the payoff; the formula would divide by zero.
    if time_to_expiry == 0:
        if option_type == "call":
            return max(spot - strike, 0.0)
        return max(strike - spot, 0.0)

    discounted_strike = strike * math.exp(-rate * time_to_expiry)

    # With zero volatility, the discounted terminal payoff is deterministic.
    if volatility == 0:
        if option_type == "call":
            return max(spot - discounted_strike, 0.0)
        return max(discounted_strike - spot, 0.0)

    total_volatility = volatility * math.sqrt(time_to_expiry)
    d1 = (
        math.log(spot / strike)
        + (rate + 0.5 * volatility**2) * time_to_expiry
    ) / total_volatility
    d2 = d1 - total_volatility

    if option_type == "call":
        return spot * normal_cdf(d1) - discounted_strike * normal_cdf(d2)
    return discounted_strike * normal_cdf(-d2) - spot * normal_cdf(-d1)


def black_scholes_delta(
    spot, strike, time_to_expiry, rate, volatility, option_type="call"
):
    """Exact model delta for positive time and volatility, without dividends.

    Boundary cases at expiry or zero volatility are outside this function's
    initial scope; the pricing function still supports those cases.
    """
    values = (spot, strike, time_to_expiry, rate, volatility)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("All numerical inputs must be finite")
    if min(spot, strike, time_to_expiry, volatility) <= 0:
        raise ValueError("Spot, strike, time and volatility must be positive")
    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'")

    d1 = (
        math.log(spot / strike)
        + (rate + 0.5 * volatility**2) * time_to_expiry
    ) / (volatility * math.sqrt(time_to_expiry))

    if option_type == "call":
        return normal_cdf(d1)
    return -normal_cdf(-d1)
