"""Plain Monte Carlo for European options under Black-Scholes assumptions.

Samples the exact risk-neutral terminal distribution, so there is no time-grid
discretization error. O(samples) time and O(1) working memory. No dividends.
"""

import math
import random


def monte_carlo_price(
    spot, strike, time_to_expiry, rate, volatility,
    option_type="call", samples=100_000, seed=42,
):
    """Return a price estimate, standard error and approximate 95% interval.

    The interval describes simulation sampling uncertainty within the assumed
    model. It does not measure uncertainty about real market prices or whether
    the model is correct. Normal-approximation intervals need sufficient samples
    and can be unreliable for rare-event payoffs.
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
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 2:
        raise ValueError("samples must be an integer of at least 2")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer or None")

    discount = math.exp(-rate * time_to_expiry)

    # Deterministic boundary cases have zero sampling uncertainty.
    if time_to_expiry == 0 or volatility == 0:
        discounted_strike = strike * discount
        if option_type == "call":
            mean = max(spot - discounted_strike, 0.0)
        else:
            mean = max(discounted_strike - spot, 0.0)
        standard_error = 0.0
    else:
        # A private generator avoids changing the global random stream.
        rng = random.Random(seed)
        drift = (rate - 0.5 * volatility**2) * time_to_expiry
        diffusion = volatility * math.sqrt(time_to_expiry)
        mean = 0.0
        m2 = 0.0

        for count in range(1, samples + 1):
            z = rng.gauss(0.0, 1.0)
            terminal_spot = spot * math.exp(drift + diffusion * z)
            if option_type == "call":
                payoff = max(terminal_spot - strike, 0.0)
            else:
                payoff = max(strike - terminal_spot, 0.0)
            discounted_payoff = discount * payoff

            # Welford's online mean and sample-variance accumulator.
            # This avoids storing every simulated payoff.
            difference = discounted_payoff - mean
            mean += difference / count
            m2 += difference * (discounted_payoff - mean)

        sample_variance = m2 / (samples - 1)
        standard_error = math.sqrt(sample_variance / samples)

    return {
        "price": mean,
        "standard_error": standard_error,
        "ci_low": mean - 1.96 * standard_error,
        "ci_high": mean + 1.96 * standard_error,
        "samples": samples,
        "seed": seed,
    }
