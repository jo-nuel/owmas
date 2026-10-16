"""Context tables and figures derived from registered results."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def h1_effect_sizes(h1: pd.DataFrame) -> pd.DataFrame:
    """Expose the practical bounds of the registered Sharpe intervals."""
    table = h1.reset_index().copy()
    table["benchmark"] = table["comparison"].str.replace("OWMAS - ", "", regex=False)
    table["largest_gain_not_ruled_out"] = table["ci_high"]
    table["largest_loss_not_ruled_out"] = -table["ci_low"]
    columns = [
        "benchmark",
        "difference",
        "ci_low",
        "ci_high",
        "largest_gain_not_ruled_out",
        "largest_loss_not_ruled_out",
        "p_value_two_sided",
        "block_size",
    ]
    return table[columns].set_index("benchmark")


def h4_volatility_effect_sizes(h4: pd.DataFrame) -> pd.DataFrame:
    """Express annualised volatility differences in percentage points."""
    table = h4.reset_index()
    table = table[table["metric"] == "volatility_difference"].copy()
    table["difference_percentage_points"] = table["estimate"] * 100.0
    table["ci_low_percentage_points"] = table["ci_low"] * 100.0
    table["ci_high_percentage_points"] = table["ci_high"] * 100.0
    table["ci_excludes_zero"] = (
        (table["ci_low"] > 0.0) | (table["ci_high"] < 0.0)
    )
    columns = [
        "comparison",
        "difference_percentage_points",
        "ci_low_percentage_points",
        "ci_high_percentage_points",
        "p_value",
        "block_size",
        "ci_excludes_zero",
    ]
    return table[columns].set_index("comparison")


def exposure_context(metrics: pd.DataFrame) -> pd.DataFrame:
    """Report invested time for each registered strategy."""
    table = metrics[["exposure", "n_days", "sharpe", "cagr"]].copy()
    table["exposure_percentage"] = table["exposure"] * 100.0
    table["invested_days"] = np.rint(table["exposure"] * table["n_days"]).astype(int)
    owmas_exposure = float(table.loc["OWMAS", "exposure_percentage"])
    table["exposure_difference_from_owmas_pp"] = (
        table["exposure_percentage"] - owmas_exposure
    )
    return table[[
        "exposure",
        "exposure_percentage",
        "invested_days",
        "n_days",
        "exposure_difference_from_owmas_pp",
        "sharpe",
        "cagr",
    ]]


def profile_return_correlations(returns: dict[str, pd.Series]) -> pd.DataFrame:
    """Calculate paired daily-return correlations between gamma profiles."""
    return pd.concat(returns, axis=1).corr()


def spy_statistics(prices: pd.Series, periods: dict[str, list[str]],
                   periods_per_year: int) -> pd.DataFrame:
    """Describe daily SPY returns over the full sample and subperiods."""
    returns = prices.pct_change().dropna()
    samples = {
        "full_sample": (prices.index.min().date().isoformat(),
                        prices.index.max().date().isoformat()),
        **periods,
    }
    rows = []
    for name, (start, end) in samples.items():
        sample = returns.loc[start:end]
        rows.append({
            "sample": name,
            "start": sample.index.min().date().isoformat(),
            "end": sample.index.max().date().isoformat(),
            "observations": len(sample),
            "daily_mean_return": float(sample.mean()),
            "annualised_arithmetic_mean": float(sample.mean() * periods_per_year),
            "annualised_volatility": float(sample.std(ddof=1) * np.sqrt(periods_per_year)),
            "skewness": float(sample.skew()),
            "excess_kurtosis": float(sample.kurt()),
            "first_order_autocorrelation": float(sample.autocorr(lag=1)),
            "cumulative_return": float((1.0 + sample).prod() - 1.0),
        })
    return pd.DataFrame(rows).set_index("sample")


def save_spy_sample_chart(prices: pd.Series, periods: dict[str, list[str]],
                          output: Path) -> None:
    """Show the frozen SPY sample and registered subperiods."""
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.plot(prices.index, prices, color="#2F5597", linewidth=1.5,
            label="SPY adjusted close")
    shades = ["#D9D9D9", "#BFBFBF", "#A6A6A6", "#7F7F7F"]
    labels = {
        "gfc": "GFC",
        "post_gfc": "Post-GFC",
        "covid": "COVID",
        "tightening": "Tightening",
    }
    for (name, (start, end)), shade in zip(periods.items(), shades):
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=shade,
                   alpha=0.28, label=labels[name])
    ax.set_yscale("log")
    ax.set_xlabel("Date")
    ax.set_ylabel("Adjusted close, log scale (USD)")
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, ncol=3, loc="upper left")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def write_context_summary(h1: pd.DataFrame, h4: pd.DataFrame,
                          exposure: pd.DataFrame, spy: pd.DataFrame,
                          correlations: pd.DataFrame,
                          output: Path) -> None:
    """Write concise statements for the thesis and presentation."""
    lines = [
        "# Exploratory context for registered results",
        "",
        "These statements explain registered results. They are not new hypothesis tests.",
        "",
        "## H1 effect sizes",
        "",
    ]
    for benchmark, row in h1.iterrows():
        difference = row["difference"]
        if abs(difference) < 0.0005:
            difference = 0.0
        lines.append(
            f"- Against {benchmark}, the Sharpe difference was {difference:.3f} "
            f"with a 95% interval from {row['ci_low']:.3f} to {row['ci_high']:.3f}. "
            f"A gain above {row['largest_gain_not_ruled_out']:.3f} is ruled out by "
            "this interval."
        )
    lines.extend([
        "",
        "## H4 volatility differences",
        "",
    ])
    for comparison, row in h4.iterrows():
        lines.append(
            f"- {comparison}: {row['difference_percentage_points']:.2f} percentage "
            f"points a year, with a 95% interval from "
            f"{row['ci_low_percentage_points']:.2f} to "
            f"{row['ci_high_percentage_points']:.2f}."
        )
    correlation_values = correlations.to_numpy()[
        np.triu_indices_from(correlations, k=1)
    ]
    ema = exposure.loc["EMA"]
    owmas = exposure.loc["OWMAS"]
    full = spy.loc["full_sample"]
    lines.extend([
        "",
        "## Exposure",
        "",
        f"EMA was invested on {ema['exposure_percentage']:.1f}% of days, compared "
        f"with {owmas['exposure_percentage']:.1f}% for OWMAS. The "
        f"{ema['exposure_difference_from_owmas_pp']:.1f} percentage point gap "
        "provides context for EMA's higher Sharpe ratio, but it does not establish "
        "that exposure caused the difference.",
        "",
        "## SPY sample",
        "",
        f"The full sample had an annualised arithmetic mean return of "
        f"{full['annualised_arithmetic_mean']:.1%}, annualised volatility of "
        f"{full['annualised_volatility']:.1%}, skewness of {full['skewness']:.2f}, "
        f"excess kurtosis of {full['excess_kurtosis']:.2f}, and first-order "
        f"autocorrelation of {full['first_order_autocorrelation']:.3f}.",
        "",
        "## Bootstrap blocks",
        "",
        f"H1 block sizes ranged from {int(h1['block_size'].min())} to "
        f"{int(h1['block_size'].max())} trading days. H4 used "
        f"{int(h4['block_size'].iloc[0])} days. These blocks preserve longer "
        "runs of dependence and contribute to wider uncertainty intervals.",
    ])
    correlation_position = lines.index("## Exposure") - 1
    lines[correlation_position:correlation_position] = [
        "",
        f"The profile return correlations range from {correlation_values.min():.3f} "
        f"to {correlation_values.max():.3f}. Pairing these closely related returns "
        "makes small volatility differences easier to detect, but the annual "
        "differences remain only 0.16 to 0.41 percentage points.",
    ]
    # Avoid displaying negative zero after rounding.
    lines = [line.replace("skewness of -0.00", "skewness of 0.00") for line in lines]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
