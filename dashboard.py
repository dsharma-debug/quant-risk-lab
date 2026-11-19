"""Local dashboard: python -m streamlit run dashboard.py --server.address 127.0.0.1"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from black_scholes import black_scholes, black_scholes_delta
from dashboard_support import (STUDIES, hedge_snapshot, interactive_study,
                               load_saved_study, make_contract, pricing_snapshot, rows_to_csv)


st.set_page_config(page_title="Quant Risk Lab", page_icon="📈", layout="wide")


@st.cache_data(show_spinner=False)
def cached_prices(contract, tree_steps, samples, seed):
    return pricing_snapshot(contract, tree_steps, samples, seed)


def show_figure(fig):
    st.pyplot(fig)
    plt.close(fig)


def show_frequency_chart(rows):
    frame = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), layout="constrained")
    intervals = sorted(frame["rebalance_every"].unique())
    for cost, group in frame.groupby("cost_bps", sort=True):
        group = group.sort_values("rebalance_every")
        label = f"{cost:g} bps costs"
        axes[0].plot(group["rebalance_every"], group["rmse_to_zero"], marker="o", label=label)
        axes[1].plot(group["rebalance_every"], group["mean_total_trade_cost"], marker="o", label=label)
    for ax, title, ylabel in zip(axes, ("Residual outcome RMSE", "Average trading fees"),
                                 ("RMSE ($ per unit)", "Nominal fees ($ per unit)")):
        ax.set_title(title)
        ax.set_xscale("log")
        ax.set_xticks(intervals, labels=[str(v) for v in intervals])
        ax.minorticks_off()
        ax.set_xlabel("Rebalance every N observations")
        ax.set_ylabel(ylabel)
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.25)
        ax.legend(frameon=False, fontsize=8)
    show_figure(fig)


def show_study_chart(name, rows):
    if name == "Hedge frequency and costs":
        show_frequency_chart(rows)
        return
    frame = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5), layout="constrained")
    if name == "Volatility assumptions":
        cost = frame["cost_bps"].min()
        for frequency, group in frame[frame["cost_bps"] == cost].groupby("rebalance_every"):
            group = group.sort_values("hedge_volatility")
            axes[0].plot(100*group["hedge_volatility"], group["rmse_to_zero"],
                         marker="o", label=f"Every {frequency:g} observations")
        frequency = frame["rebalance_every"].min()
        for cost, group in frame[frame["rebalance_every"] == frequency].groupby("cost_bps"):
            group = group.sort_values("hedge_volatility")
            axes[1].errorbar(100*group["hedge_volatility"], group["mean_pnl"],
                             yerr=1.96*group["mean_pnl_standard_error"], capsize=4,
                             marker="o", label=f"{cost:g} bps costs")
        axes[0].set_title("RMSE at the lowest saved fee level")
        axes[1].set_title("Mean P&L at the finest saved hedge schedule")
        axes[0].set_ylabel("RMSE ($ per unit)")
        axes[1].set_ylabel("Mean P&L ($ per unit)")
        axes[1].axhline(0, color="gray", linestyle="--", linewidth=1)
        for ax in axes:
            ax.set_xlabel("Assumed hedge volatility (%)")
            ax.axvline(100*float(rows[0]["actual_volatility"]), color="gray", linestyle=":")
    elif name == "Monte Carlo precision":
        for kind, group in frame.groupby("option_type"):
            group = group.sort_values("samples")
            axes[0].loglog(group["samples"], group["empirical_sd"], marker="o", label=f"{kind}: observed SD")
            axes[0].loglog(group["samples"], group["mean_standard_error"], linestyle="--", label=f"{kind}: mean SE")
            axes[1].semilogx(group["samples"], 100*group["coverage_rate"], marker="o", label=kind)
        axes[0].set_title("Observed and estimated sampling spread")
        axes[0].set_ylabel("Spread ($ per unit)")
        axes[1].set_title("Interval coverage across repetitions")
        axes[1].set_ylabel("Coverage (%)")
        axes[1].axhline(95, color="gray", linestyle="--", label="95% reference")
        for ax in axes:
            ax.set_xlabel("Samples per repetition")
    else:
        frame.pivot(index="option_type", columns="method", values="rmse").plot.bar(ax=axes[0], rot=0)
        anti = frame[frame["method"] == "antithetic"]
        axes[1].bar(anti["option_type"], anti["variance_reduction_factor"], color="#227c9d")
        axes[1].axhline(1, color="gray", linestyle="--", label="Plain MC reference")
        axes[0].set_title("RMSE at equal payoff budgets")
        axes[0].set_ylabel("RMSE ($ per unit)")
        axes[1].set_title("Empirical variance reduction factor")
        axes[1].set_ylabel("Plain variance / antithetic variance")
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(frameon=False, fontsize=8)
    show_figure(fig)


def pricing_view():
    st.header("Pricing & Greeks")
    st.caption("European options without dividends. Values are per underlying unit.")
    with st.form("pricing_form"):
        a, b, c, d = st.columns(4)
        spot = a.number_input("Stock price ($)", min_value=1.0, max_value=10000.0, value=100.0, key="p_spot")
        strike = b.number_input("Strike ($)", min_value=1.0, max_value=10000.0, value=100.0, key="p_strike")
        years = c.number_input("Time to expiry (years)", min_value=0.00274, max_value=5.0, value=1.0, key="p_years")
        kind = d.selectbox("Option type", ["call", "put"], key="p_kind")
        a, b, c, d = st.columns(4)
        rate = a.number_input("Annual cash rate (%)", min_value=-10.0, max_value=20.0, value=5.0, key="p_rate")
        vol = b.number_input("Annual volatility (%)", min_value=1.0, max_value=100.0, value=20.0, key="p_vol")
        steps = c.number_input("Tree steps", min_value=10, max_value=1000, value=200, step=10, key="p_steps")
        samples = d.number_input("MC payoff evaluations (even)", min_value=1000, max_value=200000, value=10000, step=1000, key="p_samples")
        seed = st.number_input("Simulation seed", min_value=0, max_value=2147483647, value=42, key="p_seed")
        submitted = st.form_submit_button("Calculate prices")

    if submitted or "pricing_result" not in st.session_state:
        try:
            with st.spinner("Calculating prices and sensitivities..."):
                contract = make_contract(spot, strike, years, rate, vol, kind)
                st.session_state["pricing_result"] = cached_prices(contract, int(steps), int(samples), int(seed))
        except (ValueError, OverflowError) as error:
            st.session_state.pop("pricing_result", None)
            st.error(str(error))
    result = st.session_state.get("pricing_result")
    if result is None:
        return
    contract = result["contract"]
    st.caption(f"Displayed results: {contract['option_type']} | S=${contract['spot']:g}, K=${contract['strike']:g} "
               f"| T={contract['time_to_expiry']:g} years | volatility={contract['volatility']:.1%}")
    for column, row in zip(st.columns(4), result["rows"]):
        column.metric(row["method"], "Unavailable" if row["price"] is None else f"${row['price']:,.4f}")
        if row["message"]:
            st.warning(f"{row['method']}: {row['message']}")
    a, b, c = st.columns(3)
    a.metric("Delta", f"{result['greeks']['delta']:.6f}")
    b.metric("Gamma", f"{result['greeks']['gamma']:.6f}")
    c.metric("Vega per 1 volatility point", f"${result['greeks']['vega_per_1pct']:.6f}")

    curve_x = [contract["spot"]*(0.5+i/60) for i in range(61)]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3), layout="constrained")
    axes[0].plot(curve_x, [black_scholes(**{**contract, "spot": x}) for x in curve_x], color="#1768ac")
    axes[1].plot(curve_x, [black_scholes_delta(**{**contract, "spot": x}) for x in curve_x], color="#cb591b")
    for ax, title, ylabel in zip(axes, ("Option value across stock prices", "Delta across stock prices"),
                                 ("Option price ($)", "Delta")):
        ax.set_title(title)
        ax.set_xlabel("Stock price ($)")
        ax.set_ylabel(ylabel)
        ax.axvline(contract["spot"], color="gray", linestyle=":")
        ax.grid(alpha=0.25)
    show_figure(fig)
    columns = ["method", "price", "absolute_error", "standard_error", "ci_low", "ci_high"]
    st.dataframe(pd.DataFrame(result["rows"])[columns], hide_index=True)
    st.caption("Absolute errors use Black-Scholes as the reference. MC intervals describe sampling uncertainty within the model.")
    st.download_button("Download pricing CSV", rows_to_csv(result["rows"]), "pricing_snapshot.csv", "text/csv")
    with st.expander("Units and assumptions"):
        st.write("Volatility and interest inputs are annual percentages; the model uses decimal values. "
                 "One volatility point means, for example, 20% to 21%. Rates are continuously compounded. "
                 "Antithetic standard errors use independent pair averages. Contract multipliers have not been applied.")


def hedge_view():
    st.header("Hedge simulator")
    st.caption("Sell one option unit, adjust the stock hedge, then close and cash-settle at expiry.")
    with st.form("hedge_form"):
        a, b, c, d = st.columns(4)
        spot = a.number_input("Initial stock price ($)", min_value=1.0, max_value=10000.0, value=100.0, key="h_spot")
        strike = b.number_input("Strike ($)", min_value=1.0, max_value=10000.0, value=100.0, key="h_strike")
        years = c.number_input("Horizon (years)", min_value=0.00274, max_value=5.0, value=1.0, key="h_years")
        kind = d.selectbox("Option type", ["call", "put"], key="h_kind")
        a, b, c = st.columns(3)
        actual = a.number_input("Path volatility (%)", min_value=0.0, max_value=100.0, value=20.0, key="h_actual")
        assumed = b.number_input("Hedge volatility (%)", min_value=1.0, max_value=100.0, value=20.0, key="h_assumed")
        rate = c.number_input("Annual cash rate (%)", min_value=-10.0, max_value=20.0, value=5.0, key="h_rate")
        a, b, c, d = st.columns(4)
        steps = a.selectbox("Observations after start", [52, 126, 252, 504], index=2, key="h_steps")
        frequency = b.number_input("Rebalance every N observations", min_value=1, max_value=504, value=1, key="h_frequency")
        cost = c.number_input("Stock-trading cost (bps)", min_value=0.0, max_value=100.0, value=5.0, key="h_cost")
        seed = d.number_input("Seed", min_value=0, max_value=2147483647, value=42, key="h_seed")
        submitted = st.form_submit_button("Run hedge")
    st.caption("Entry pricing and liability marking use path volatility. Hedge volatility controls stock positions. "
               "If the rebalance interval reaches the horizon, only opening and closing stock trades occur.")

    if submitted:
        try:
            contract = make_contract(spot, strike, years, rate, assumed, kind)
            st.session_state["hedge_result"] = hedge_snapshot(
                contract, actual, assumed, int(steps), int(frequency), cost, int(seed)
            )
        except (ValueError, OverflowError) as error:
            st.session_state.pop("hedge_result", None)
            st.error(str(error))
    result = st.session_state.get("hedge_result")
    if result is None:
        st.info("Choose your scenario and select Run hedge.")
        return
    summary = result["with_costs"]["summary"]
    ledger = result["with_costs"]["ledger"]
    st.caption(f"Displayed run: seed {result['seed']} | {summary['option_type']} | "
               f"path vol {result['actual_volatility']:.1%}, hedge vol {result['hedge_volatility']:.1%} "
               f"| every {summary['rebalance_every']} observations | {summary['cost_bps']:g} bps costs")
    a, b, c, d = st.columns(4)
    a.metric("Terminal P&L", f"${summary['terminal_pnl']:.6f}")
    b.metric("Fees paid", f"${summary['total_trade_cost']:.6f}")
    c.metric("Entry premium", f"${summary['premium_received']:.6f}")
    d.metric("Final stock price", f"${summary['terminal_spot']:.6f}")
    baseline = result["without_costs"]["summary"]["terminal_pnl"]
    st.caption(f"Same-path P&L without stock-trading fees: ${baseline:.6f}. "
               f"Fee and financing impact: ${baseline-summary['terminal_pnl']:.6f}.")
    frame = pd.DataFrame(ledger)
    fig, axes = plt.subplots(2, 1, figsize=(10, 4), sharex=True, layout="constrained")
    axes[0].plot(frame["time"], frame["spot"], color="#1768ac")
    axes[0].set_ylabel("Stock price ($)")
    axes[1].step(frame["time"], frame["shares_after"], where="post", color="#cb591b")
    axes[1].set_ylabel("Shares held")
    axes[1].set_xlabel("Time (years)")
    for ax in axes:
        ax.grid(alpha=0.25)
    show_figure(fig)
    st.subheader("Cash and trading ledger")
    st.dataframe(frame, hide_index=True)
    a, b = st.columns(2)
    a.download_button("Download hedge ledger", rows_to_csv(ledger), "hedge_ledger.csv", "text/csv")
    b.download_button("Download hedge summary", rows_to_csv([summary]), "hedge_summary.csv", "text/csv")
    st.caption("Terminal cash is measured after liquidating stock and paying the option. "
               "A single path illustrates accounting; use repeated paths to assess the outcome distribution.")


def research_view():
    st.header("Research results")
    saved_tab, live_tab = st.tabs(["Saved experiments", "Run a frequency study"])
    with saved_tab:
        name = st.selectbox("Experiment", list(STUDIES), key="saved_study")
        try:
            rows = load_saved_study(name)
        except FileNotFoundError:
            st.info(f"Generate this saved experiment first: `{STUDIES[name][1]}`")
        except ValueError as error:
            st.error(str(error))
        else:
            st.caption("These results use the inputs recorded in their saved configuration.")
            show_study_chart(name, rows)
            st.dataframe(pd.DataFrame(rows), hide_index=True)
            st.download_button("Download saved summary", rows_to_csv(rows), STUDIES[name][0], "text/csv")
            with st.expander("Recorded configuration"):
                keys = ("initial_spot", "strike", "time_to_expiry", "rate", "actual_volatility",
                        "hedge_volatility", "premium_mode", "steps", "paths", "repetitions", "seed_start")
                configuration = {}
                for key in keys:
                    values = list(dict.fromkeys(row[key] for row in rows if key in row))
                    if values:
                        configuration[key] = values[0] if len(values) == 1 else values
                st.json(configuration)
    with live_tab:
        st.caption("Call option: S=K=$100, horizon=1 year, cash rate=5%, 252 observations. "
                   "Entry premium stays fair under path volatility. Compare intervals 1, 5, 21 and 63.")
        with st.form("live_study_form"):
            a, b, c = st.columns(3)
            paths = a.number_input("Stock paths", min_value=50, max_value=2000, value=250, step=50, key="study_paths")
            actual = b.number_input("Path volatility (%)", min_value=1.0, max_value=100.0, value=20.0, key="study_actual")
            assumed = c.number_input("Hedge volatility (%)", min_value=1.0, max_value=100.0, value=20.0, key="study_assumed")
            a, b = st.columns(2)
            cost = a.number_input("Stock-trading cost (bps)", min_value=0.0, max_value=100.0, value=5.0, key="study_cost")
            seed = b.number_input("Starting seed", min_value=0, max_value=2147483647, value=1000, key="study_seed")
            submitted = st.form_submit_button("Run frequency study")
        if submitted:
            try:
                with st.spinner("Comparing policies on common stock paths..."):
                    st.session_state["live_study"] = interactive_study(int(paths), actual, assumed, cost, int(seed))
            except (ValueError, OverflowError) as error:
                st.session_state.pop("live_study", None)
                st.error(str(error))
        result = st.session_state.get("live_study")
        if result is not None:
            first = result["summaries"][0]
            st.caption(f"Displayed study: {first['paths']} shared paths | "
                       f"path vol {first['actual_volatility']:.1%}, hedge vol {first['hedge_volatility']:.1%}")
            show_frequency_chart(result["summaries"])
            st.dataframe(pd.DataFrame(result["summaries"]), hide_index=True)
            a, b = st.columns(2)
            a.download_button("Download new study summary", rows_to_csv(result["summaries"]), "interactive_study_summary.csv", "text/csv")
            b.download_button("Download all path outcomes", rows_to_csv(result["trials"]), "interactive_study_trials.csv", "text/csv")
            st.caption("Download the CSVs to retain this configuration. Existing saved experiment files are preserved.")


def main():
    st.title("Quant Risk Lab")
    st.caption("Option pricing, risk sensitivities and reproducible hedging research.")
    with st.sidebar:
        st.markdown("### Workspace")
        workspace = st.radio("Choose a view", ["Pricing & Greeks", "Hedge simulator", "Research results"], key="workspace")
        st.markdown("---")
        st.caption("European options · No dividends · Per underlying unit\n\nControlled model simulations")
    if workspace == "Pricing & Greeks":
        pricing_view()
    elif workspace == "Hedge simulator":
        hedge_view()
    else:
        research_view()


if __name__ == "__main__":
    main()
