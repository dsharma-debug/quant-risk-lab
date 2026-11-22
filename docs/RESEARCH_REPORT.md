# Option Pricing and Discrete Delta Hedging

Author: Deewash Sharma
Project: Quant Risk Lab

## Introduction

This project investigates numerical methods for pricing European
options and the practical limitations of discrete delta hedging.

Black-Scholes prices provide a benchmark for evaluating binomial
trees and Monte Carlo estimates. Repeated simulation experiments
measure sampling uncertainty and examine whether antithetic
sampling improves precision at a fixed payoff evaluation budget.

The hedging experiments investigate how rebalancing frequency,
transaction costs, and volatility assumptions affect the terminal
profit and loss of a hedged short option position.

## Research Questions

1. How do binomial and Monte Carlo prices approach the
   Black-Scholes benchmark as computational effort increases?

2. How much does antithetic sampling reduce Monte Carlo variance
   at an equal payoff evaluation budget?

3. How does rebalancing frequency affect hedging error and
   transaction costs?

4. How do incorrect hedge volatility assumptions affect outcomes
   when the option's initial premium is held fixed?

## Scope

The experiments use simulated stock prices and European options.
The results describe behavior within the chosen models and
simulation settings. They do not establish profitability in
real markets.

## Methods

### Reference Configuration

The baseline European options use the following inputs:

| Parameter | Value |
| --- | --- |
| Initial stock price | $100 |
| Strike price | $100 |
| Time to expiry | 1 year |
| Annual continuously compounded interest rate | 5% |
| Annual volatility | 20% |
| Dividends | None |

Option prices and hedging outcomes are reported per underlying
unit. Stock holdings may include fractional shares.

### Option Pricing

Black-Scholes provides the analytical reference price.

The Cox-Ross-Rubinstein binomial model calculates terminal
payoffs and works backward through the tree using risk-neutral
probabilities and discounting. Prices are compared with the
reference as the number of steps increases.

Plain Monte Carlo samples the exact risk-neutral terminal stock
distribution and averages discounted option payoffs. It therefore
has sampling error but no stock time-grid discretization error.

### Monte Carlo Experiments

The repeated experiment uses 100 trials at each sample count:
1,000, 4,000, and 16,000. Results include estimated bias, root
mean squared error (RMSE), empirical standard deviation, mean
reported standard error, and approximate 95% interval coverage.

Coverage is the fraction of trial intervals containing the
Black-Scholes reference price. It need not equal exactly 95%
in a finite experiment.

Plain and antithetic Monte Carlo are also compared using 10,000
payoff evaluations per trial and 100 trials. Antithetic sampling
pairs each normal shock with its negative. Its standard error
is calculated from 5,000 pair averages.

The variance reduction factor is the empirical variance of
plain estimates divided by that of antithetic estimates.
This comparison matches payoff counts, not measured runtime.

### Greek Validation

Analytical delta, gamma, and vega are compared with central
finite difference estimates obtained by perturbing the relevant
input. Absolute differences measure numerical agreement.

### Discrete Hedging

The hedging study simulates 500 stock paths with 252 equal time
intervals over one year. Stock dynamics use constant 20%
volatility and risk-neutral drift equal to the interest rate;
these paths are model scenarios, not market forecasts.

Each strategy sells one call unit and trades stock according
to its Black-Scholes delta. Cash earns or incurs interest at
the same rate. Transaction fees apply to initial, rebalancing,
and closing stock trades.

Rebalancing intervals are 1, 5, 21, and 63 observations.
Trading costs are either zero or 5 basis points of traded
stock value. At expiry, the stock hedge is closed and the
option payoff is paid. Remaining cash is terminal P&L.

Every configuration uses the same 500 paths, with seeds
1000 through 1499. Comparisons across configurations are paired.

### Volatility Assumptions

The volatility study keeps actual simulated volatility at 20%
while using hedge volatilities of 15%, 20%, and 25%.

The reported fixed-premium experiment holds the entry premium
at the Black-Scholes value calculated using 20% volatility.
It changes hedge decisions while holding initial pricing fixed.

The study uses the same paths across configurations, rebalancing
intervals of 1, 5, and 21 observations, and costs of zero or
5 basis points.

Hedging outcomes are summarized using mean P&L, sample standard
deviation, RMSE relative to zero, empirical percentiles, and
mean fees. The fifth percentile describes the lower tail of
outcomes; it is not a confidence interval for the mean.

## Results

### Pricing Benchmark and Binomial Convergence

For the reference configuration, Black-Scholes gives a call
price of $10.450584 and a put price of $5.573526.

With 1,000 steps, the binomial prices are $10.448584 for the
call and $5.571527 for the put. Both absolute errors are
approximately $0.002.

The convergence experiment also shows oscillation between
odd and even step counts. Increasing the number of steps
does not guarantee that every successive price estimate
has a smaller error.

### Repeated Monte Carlo Experiment

The following results use 100 trials per option and sample count.
RMSE is measured against the Black-Scholes reference price.

| Option | Samples per trial | RMSE | Mean standard error | Coverage |
| --- | ---: | ---: | ---: | ---: |
| Call | 1,000 | 0.500810 | 0.467163 | 91% |
| Call | 4,000 | 0.232977 | 0.232514 | 94% |
| Call | 16,000 | 0.105866 | 0.116478 | 97% |
| Put | 1,000 | 0.275019 | 0.274771 | 95% |
| Put | 4,000 | 0.127778 | 0.137075 | 96% |
| Put | 16,000 | 0.060950 | 0.068502 | 99% |

RMSE decreases as the sample count increases in this experiment.
Multiplying the sample count by four roughly halves the
reported standard error.

Standard error estimates sampling uncertainty; it is not the
realized difference from the reference price. An individual
trial can become less accurate even when its sample count
increases.

Coverage ranges from 91% to 99%. With only 100 trials per group,
these percentages give a limited assessment of interval
calibration.

Source: results/mc_summary.csv.

### Antithetic Variance Reduction

Both methods use 10,000 payoff evaluations per trial and
100 trials per option.

| Option | Method | RMSE | Variance reduction factor |
| --- | --- | ---: | ---: |
| Call | Plain | 0.141188 | 1.000 |
| Call | Antithetic | 0.101667 | 1.912 |
| Put | Plain | 0.083961 | 1.000 |
| Put | Antithetic | 0.065756 | 1.607 |

Antithetic sampling produces lower empirical variance and
lower RMSE for both options in this experiment.

The improvement depends on the payoff and configuration.
These results establish a benefit at equal payoff counts;
they do not establish a runtime improvement.

Source: results/variance_reduction_summary.csv.

### Greek Validation

The call option's analytical Greeks agree closely with
central finite difference estimates.

| Greek | Analytical value | Absolute difference |
| --- | ---: | ---: |
| Delta | 0.63683065 | 8.599e-09 |
| Gamma | 0.01876202 | 2.681e-10 |
| Vega | 37.52403469 | 3.045e-07 |

Vega is expressed per unit change in volatility. Dividing
by 100 gives approximately $0.375240 per one percentage
point change in volatility.

The put delta is approximately -0.36316935. Its gamma and
vega match the call values for the same configuration.

This agreement supports the implementation at the tested
inputs. It does not validate the model against market data.

Source: results/greeks_validation.csv.

### Rebalancing Frequency and Transaction Costs

The following results use 500 shared stock paths and
a correctly specified hedge volatility of 20%.

All monetary values are dollars per option unit.
"Every" is the number of observations between rebalances.

| Every | Cost (bps) | Mean P&L | P&L standard deviation | RMSE | Mean fees |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | 0.033331 | 0.444348 | 0.445153 | 0.000000 |
| 1 | 5 | -0.281339 | 0.453603 | 0.533382 | 0.306943 |
| 5 | 0 | 0.069951 | 0.964252 | 0.965824 | 0.000000 |
| 5 | 5 | -0.107384 | 0.971201 | 0.976154 | 0.173035 |
| 21 | 0 | -0.049002 | 1.896236 | 1.894973 | 0.000000 |
| 21 | 5 | -0.166600 | 1.901201 | 1.906591 | 0.114711 |
| 63 | 0 | -0.192550 | 3.293845 | 3.296179 | 0.000000 |
| 63 | 5 | -0.284246 | 3.298175 | 3.307113 | 0.089451 |

Without transaction costs, more frequent rebalancing produces
lower P&L dispersion and lower RMSE in the tested configurations.
Rebalancing every observation reduces RMSE from approximately
$3.296 for the 63-observation interval to $0.445.

The estimated mean P&L varies across configurations. However,
the approximate 95% confidence interval for each no-cost mean
includes zero. These sample means do not establish a systematic
profit opportunity.

With costs, more frequent trading incurs higher average fees.
At 5 basis points, rebalancing every observation generates
approximately $0.307 in average fees, compared with $0.089
for the 63-observation interval.

The reduction in terminal P&L includes both fees and their
financing effect. It therefore differs from the sum of fees.

Rebalancing every observation still has the lowest RMSE among
the tested intervals at both cost levels. This experiment does
not identify an optimal interval across all possible strategies
or transaction cost levels.

Source: results/hedging_study_summary.csv.

### Incorrect Hedge Volatility

The table below shows rebalancing every observation.
Actual simulated volatility remains 20%, and every strategy
receives the same initial premium of $10.450584.

| Hedge volatility | Cost (bps) | Mean P&L | P&L standard deviation | RMSE |
| ---: | ---: | ---: | ---: | ---: |
| 15% | 0 | 0.048059 | 0.935630 | 0.935929 |
| 20% | 0 | 0.033331 | 0.444348 | 0.445153 |
| 25% | 0 | 0.024585 | 0.806734 | 0.806302 |
| 15% | 5 | -0.299749 | 1.039684 | 1.081032 |
| 20% | 5 | -0.281339 | 0.453603 | 0.533382 |
| 25% | 5 | -0.263566 | 0.756028 | 0.799939 |

Using the correct 20% hedge volatility produces the lowest
RMSE among these settings at both cost levels. Both lower
and higher hedge volatility increase residual risk relative
to the correctly specified hedge.

The effect is asymmetric: using 15% volatility produces
greater RMSE than using 25% in this experiment.

Because the premium is fixed, changing hedge volatility
does not introduce a different entry price. Under the
simulated risk-neutral dynamics, changing delta alone
does not imply a nonzero expected P&L before costs.

Costs lower terminal P&L on each matched path, but they
need not increase its standard deviation. For example,
the 25% hedge volatility configuration has lower dispersion
with costs than without costs. This does not mean that
fees improve its profitability.

Source: results/volatility_fixed_summary.csv.

## Limitations

### Model Assumptions

Stock prices follow geometric Brownian motion with constant
volatility and interest rates. The simulations exclude jumps,
stochastic volatility, dividends, and changing market conditions.

The hedging paths use risk-neutral drift. Their outcomes
describe the chosen model rather than forecasts of real-world
investment returns.

### Trading Assumptions

The hedge permits fractional shares and uses the same interest
rate for borrowing and lending. Transaction costs are a fixed
proportion of traded stock value.

The experiments exclude bid-ask spreads beyond this simplified
fee, market impact, execution delays, funding constraints,
and stock borrowing restrictions.

### Statistical Uncertainty

The pricing experiments use 100 trials per configuration,
and the hedging studies use 500 paths. Estimated errors,
coverage rates, and tail percentiles remain subject to
sampling variability.

Confidence intervals use normal approximations. A larger
experiment would provide a more precise assessment of coverage
and extreme outcomes.

Configurations share random seeds or stock paths. Comparisons
between configurations are therefore paired, and their results
should not be treated as independent samples.

### Scope of Validation

Most reported experiments use one at-the-money option
configuration. The findings cannot automatically be extended
to other strikes, maturities, volatility levels, or payoffs.

Agreement with Black-Scholes and finite differences supports
numerical consistency within the tested settings. It does
not establish that the model accurately describes market prices.

Antithetic sampling is compared at equal payoff evaluation
counts. Runtime and memory performance are not benchmarked.

## Conclusion

This project connects option pricing, numerical validation,
and discrete hedging in a reproducible simulation framework.

Binomial prices approach the Black-Scholes reference as the
tree is refined, although odd-even oscillations prevent
strictly monotonic convergence. Repeated Monte Carlo trials
show decreasing RMSE as sample counts increase.

At equal payoff evaluation budgets, antithetic sampling
reduces empirical estimator variance by factors of approximately
1.91 for calls and 1.61 for puts in the tested configuration.

The hedging experiments demonstrate that accurate option
pricing does not eliminate residual risk when trading occurs
at discrete times. More frequent rebalancing reduces hedging
error in the tested settings but incurs higher transaction fees.

Using hedge volatility different from the simulated volatility
increases RMSE in the reported comparisons. Holding the entry
premium fixed separates this effect from differences in
initial option pricing.

The main contribution is an implementation that makes these
relationships measurable and inspectable through repeated
experiments, saved results, accounting ledgers, and tests.

Possible extensions include a broader parameter study,
more simulation paths, runtime benchmarks, and stock models
with jumps or changing volatility. These extensions would
test how far the present findings generalize.
