# Dashboard setup and usage

From the project root, activate the virtual environment, install dependencies,
and launch:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py --server.address 127.0.0.1
```

Open http://localhost:8501. Keep the terminal running and use Control+C to stop.
If first launch asks for an email, press Enter to skip the optional field.

## Pricing & Greeks

Choose the contract, annual rate/volatility, tree size, simulation payoff count
and seed. Click Calculate prices. The four cards compare Black–Scholes, CRR,
plain Monte Carlo and antithetic Monte Carlo. Displayed simulation intervals
describe sampling uncertainty within the model. Greek cards show delta, gamma
and vega per one volatility percentage point. Download the complete settings
and estimates as CSV.

At default call inputs, the Black–Scholes price is 10.450584. Increasing annual
volatility from 20% to 40% produces 18.022951, displayed as $18.0230.

## Hedge simulator

Path volatility generates a simulated stock path and determines fair entry
pricing. Hedge volatility determines delta decisions. Select the adjustment
interval, proportional costs and seed, then Run hedge. The output includes
terminal P&L, fees, a matched no-fee comparison, stock/holding curves, and the
full cash ledger. Results are per underlying unit, not per 100-share contract.

The default call path, seed 42, 252 observations and 5 bps costs gives terminal
P&L about 0.094495 and nominal fees about 0.246768. Final shares and outstanding
option liability are zero. Download the ledger to inspect each cash movement.

## Research results

Saved experiments read the CSV summaries already in results/. Their recorded
inputs are shown, including lists when settings vary across rows. Missing data
produces a command to regenerate the selected study.

The frequency-study tab runs a new common-path call experiment with S=K=100,
T=1, rate=5%, 252 intervals and a fixed fair entry premium. Change path count,
path/hedge volatility, costs and seed. Results remain in the session with CSV
downloads; existing saved experiments are preserved.

To test the complete interface automatically:

```bash
python check_dashboard.py
```

The four methods check volatility changes, put pricing, a hedge, saved research
navigation and a new study. They complement the numerical tests rather than
replacing visual inspection. Five pure adapter tests check units and delegation.

For an import error, first confirm the environment is active, requirements are
installed, and this file's parent project folder contains all model modules.
Use the Streamlit launch command rather than python dashboard.py.
