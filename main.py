"""Run the first pricing example: python3 main.py."""

from black_scholes import black_scholes, black_scholes_delta


def main() -> None:
    # Edit these inputs, save, and run again to explore the model.
    spot = 100.0
    strike = 100.0
    time_to_expiry = 1.0
    rate = 0.05
    volatility = 0.20

    print("Quant Risk Lab - Black-Scholes example")
    print(f"Stock price: ${spot:.2f} | Strike: ${strike:.2f}")
    print(f"Time: {time_to_expiry:g} year(s)")
    print(f"Annual rate: {rate:.1%} | Annual volatility: {volatility:.1%}")

    for option_type in ("call", "put"):
        price = black_scholes(
            spot, strike, time_to_expiry, rate, volatility, option_type
        )
        print(f"{option_type.capitalize()} price per underlying unit: ${price:.4f}")

    # Central finite difference, compared with the exact model derivative.
    h = 0.01
    for option_type in ("call", "put"):
        price_up = black_scholes(
            spot + h, strike, time_to_expiry, rate, volatility, option_type
        )
        price_down = black_scholes(
            spot - h, strike, time_to_expiry, rate, volatility, option_type
        )
        delta = (price_up - price_down) / (2 * h)
        exact_delta = black_scholes_delta(
            spot, strike, time_to_expiry, rate, volatility, option_type
        )
        print(f"{option_type.capitalize()} delta: {delta:.4f}")
        print(f"Exact delta: {exact_delta:.4f}")
        print(f"Absolute difference: {abs(delta - exact_delta):.10f}")


if __name__ == "__main__":
    main()
