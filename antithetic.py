"""Antithetic Monte Carlo for European calls/puts without dividends.

samples counts terminal payoff evaluations, so samples/2 independent shock
pairs are generated. Standard error is computed from pair averages.
"""

import math
import random


def antithetic_price(
    spot, strike, time_to_expiry, rate, volatility,
    option_type="call", samples=10_000, seed=42,
):
    """Return a price estimate and approximate 95% sampling interval.

    samples must be even and at least four, giving at least two independent
    pairs for estimating variance. The interval has the same large-sample
    limitations as plain Monte Carlo, especially for rare-event payoffs.
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
    if (isinstance(samples, bool) or not isinstance(samples, int)
            or samples < 4 or samples % 2 != 0):
        raise ValueError("samples must be an even integer of at least 4")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer or None")

    pairs = samples // 2
    discount = math.exp(-rate * time_to_expiry)
    if time_to_expiry == 0 or volatility == 0:
        discounted_strike = strike * discount
        mean = (max(spot - discounted_strike, 0.0) if option_type == "call"
                else max(discounted_strike - spot, 0.0))
        standard_error = 0.0
    else:
        rng = random.Random(seed)
        drift = (rate - 0.5 * volatility**2) * time_to_expiry
        diffusion = volatility * math.sqrt(time_to_expiry)
        mean = 0.0
        m2 = 0.0

        for count in range(1, pairs + 1):
            z = rng.gauss(0.0, 1.0)
            terminal_plus = spot * math.exp(drift + diffusion * z)
            terminal_minus = spot * math.exp(drift - diffusion * z)

            if option_type == "call":
                payoff_plus = max(terminal_plus - strike, 0.0)
                payoff_minus = max(terminal_minus - strike, 0.0)
            else:
                payoff_plus = max(strike - terminal_plus, 0.0)
                payoff_minus = max(strike - terminal_minus, 0.0)

            # The two payoffs are dependent: one PAIR AVERAGE is an
            # independent observation for the mean/variance calculation.
            pair_average = discount * (payoff_plus + payoff_minus) / 2
            difference = pair_average - mean
            mean += difference / count
            m2 += difference * (pair_average - mean)

        pair_variance = m2 / (pairs - 1)
        standard_error = math.sqrt(pair_variance / pairs)

    return dict(price=mean, standard_error=standard_error,
                ci_low=mean - 1.96 * standard_error,
                ci_high=mean + 1.96 * standard_error,
                samples=samples, pairs=pairs, seed=seed)
