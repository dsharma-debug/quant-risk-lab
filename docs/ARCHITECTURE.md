# Architecture and accounting

## Design

The project retains a small flat module layout. Model functions accept decimal
rates/volatilities and return values without requiring the dashboard. Drivers
run controlled experiments and write CSVs. Plotting and interface code consume
those results. This allows numerical tests to run independently of Streamlit.

| Layer | Inputs | Outputs |
| --- | --- | --- |
| Pricing models | S, K, years, annual decimal rate/volatility, option type | Price per underlying unit; Monte Carlo also returns standard error and interval |
| Greeks | The same model inputs, positive time/volatility | Delta, gamma, raw vega, vega per volatility point |
| Path simulation | Initial price, horizon, rate, path volatility, grid, seed | A sequence including the initial stock observation |
| Hedging | A path, contract, hedge and valuation volatility, costs, schedule | Terminal summary and optional cash/trading ledger |
| Studies | Seeds and policy configurations | Trial-level rows and statistical summaries |
| Dashboard adapters | Displayed percentage inputs and settings | Validated model dictionaries, results and CSV exports |

## Numerical choices

Black–Scholes uses the standard normal CDF computed through the complementary
error function. The CRR tree values terminal payoffs and works backward with
O(N) working memory and O(N²) arithmetic. Plain Monte Carlo samples the exact
risk-neutral terminal distribution for a vanilla European option; it has
sampling error but no time-grid discretization error in the terminal simulation.

Welford's running mean/variance keeps Monte Carlo working memory constant.
Antithetic sampling feeds independent pair averages into that accumulator.
The two payoffs inside each pair are not treated as independent observations.

Analytical Greeks are checked against central finite differences over several
spots, expiries, rates and volatilities. Finite differences have both truncation
and roundoff error, so reducing the step indefinitely is not an accuracy guarantee.

## Cash ledger

The hedge is short one option unit and holds stock shares plus cash. At entry:

    cash_0 = premium - delta_0 * S_0 - opening_stock_fee

At a later observation:

    interest_i = cash_(i-1) * [exp(r*dt) - 1]
    cash_i = cash_(i-1) + interest_i - trade_shares_i*S_i - fee_i - payoff_i

Positive stock purchases reduce cash; sales increase it. Negative cash is
borrowing. The same rate applies to positive and negative balances. Trade fees
apply to opening, rebalancing and final stock liquidation. Option settlement
has no separate fee in the baseline.

At maturity, stock is fully liquidated and the option payoff is paid. Final
shares and option liability are zero; remaining cash is terminal P&L. No new
external cash is injected during rebalancing. Fees affect terminal cash through
both the charge itself and financing over the remaining time.

The tests check that the difference between fee and no-fee terminal P&L equals
the sum of individual fees compounded to expiry. They also check that paths
sharing a prefix produce identical hedge decisions up to that point.

## Pricing versus hedge volatility

`hedge_volatility` determines the stock position. `valuation_volatility`
determines the received premium and intermediate option marking. The latter
defaults to the hedge volatility for compatibility with the original examples.

The main volatility study sets valuation volatility to the true simulated
volatility for every policy. This fixes entry pricing while varying hedge
decisions. Its separate `hedge_model` protocol changes both assumptions and
records the entry-price effect explicitly.

## Interface behavior

`dashboard_support.make_contract` converts displayed annual percentages to
decimals once. The dashboard calls existing model functions rather than a
second implementation of the financial mathematics. Cached pricing results
are keyed by their complete configuration. Hedge and study forms run on
submission, and displayed outputs retain their own recorded settings.

New UI studies are session results with CSV downloads. Existing reference
files are preserved. Saved studies use fixed known filenames; missing summaries
produce a regeneration instruction. The optional AppTest checks exercise
displayed prices, option selection, a hedge, research navigation and a new study.
