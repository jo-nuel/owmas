"""Check the Week 11 chapter draft against registered experiment outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DRAFT = ROOT / "evidence" / "week11" / "results_and_discussion_draft.md"


def require(text: str, snippet: str) -> None:
    assert snippet in text, f"Week 11 draft is missing or disagrees with: {snippet}"


def main() -> None:
    text = DRAFT.read_text(encoding="utf-8")
    prose = " ".join(text.split())
    performance = pd.read_csv(RESULTS / "performance_metrics.csv").set_index("strategy")
    h1 = pd.read_csv(RESULTS / "h1_sharpe_tests.csv").set_index("comparison")
    h2 = pd.read_csv(RESULTS / "h2_risk_tests.csv").set_index(["comparison", "metric"])
    rolling = pd.read_csv(RESULTS / "h3_rolling_summary.csv", index_col=0)
    h4 = pd.read_csv(RESULTS / "h4_profile_tests.csv").set_index(["comparison", "metric"])
    subperiod = pd.read_csv(RESULTS / "subperiod_metrics.csv").set_index(["period", "strategy"])
    holdout = pd.read_csv(RESULTS / "holdout_metrics.csv").set_index("strategy")
    sensitivity = pd.read_csv(RESULTS / "sensitivity_metrics.csv").set_index("specification")

    owmas = performance.loc["OWMAS"]
    require(prose, f"{owmas['cumulative_return']:.2%} cumulative return")
    require(prose, f"annualised Sharpe ratio of {owmas['sharpe']:.3f}")
    require(prose, f"maximum drawdown was {owmas['max_drawdown']:.2%}")

    for comparison in ["OWMAS - SMA", "OWMAS - WMA", "OWMAS - EMA", "OWMAS - BuyHold"]:
        row = h1.loc[comparison]
        require(prose, f"{row['p_value_two_sided']:.4f}")

    require(
        prose,
        f"p = {h2.loc[('OWMAS - SMA', 'volatility_difference'), 'p_value']:.4f}",
    )
    require(
        prose,
        f"p = {h2.loc[('OWMAS - WMA', 'volatility_difference'), 'p_value']:.4f}",
    )
    require(prose, f"median rolling 252-day Sharpe ratio of {rolling.loc['OWMAS', 'median']:.3f}")
    require(prose, f"interquartile range of {rolling.loc['OWMAS', 'iqr']:.3f}")

    for comparison in [
        "optimistic - neutral",
        "optimistic - conservative",
        "neutral - conservative",
    ]:
        p_value = h4.loc[(comparison, "volatility_difference"), "p_value"]
        require(prose, f"p = {p_value:.4f}")

    require(prose, f"OWMAS returned {subperiod.loc[('gfc', 'OWMAS'), 'cumulative_return']:.2%}")
    require(prose, f"During 2020, OWMAS returned {subperiod.loc[('covid', 'OWMAS'), 'cumulative_return']:.2%}")
    require(prose, f"OWMAS returned {subperiod.loc[('tightening', 'OWMAS'), 'cumulative_return']:.2%}")
    require(prose, f"a {holdout.loc['OWMAS', 'sharpe']:.3f} Sharpe ratio")
    require(prose, f"strongest Sharpe point estimate at {sensitivity.loc['profile_conservative', 'sharpe']:.3f}")

    required_sections = [
        "## 4. Results",
        "## 5. Discussion",
        "### 4.6 Market-subperiod results",
        "### 4.7 Holdout robustness",
        "### 4.8 One-factor sensitivity",
        "### 5.5 Limitations",
        "### 5.6 Implications and future work",
    ]
    for section in required_sections:
        require(text, section)

    assert "H1 is therefore not supported" in prose
    assert "H3 is not supported" in prose
    assert "not promoted to primary specifications" in prose
    print("PASS: Week 11 draft structure and key claims agree with registered outputs")


if __name__ == "__main__":
    main()
