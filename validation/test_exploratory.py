"""Checks for the generated exploratory disagreement analysis."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.signals import orness, owa_weights

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "exploratory"


def test_disagreement_matches_week5_audit():
    summary = pd.read_csv(
        OUTPUT / "signal_disagreement_summary.csv", index_col=0
    )["value"]
    audit = pd.read_csv(ROOT / "evidence" / "week5" / "divergence_audit_primary.csv")
    row = audit[
        (audit["strategy_a"] == "sma")
        & (audit["strategy_b"] == "owmas_beta_0.5_neutral")
    ].iloc[0]
    assert int(summary["observation_days"]) == 5282
    assert np.isclose(summary["disagreement_fraction"], row["frac_days_differ"])


def test_daily_rows_and_episodes_are_consistent():
    days = pd.read_csv(OUTPUT / "signal_disagreement_days.csv")
    episodes = pd.read_csv(OUTPUT / "signal_disagreement_episodes.csv")
    summary = pd.read_csv(
        OUTPUT / "signal_disagreement_summary.csv", index_col=0
    )["value"]
    assert len(days) == int(summary["disagreement_days"])
    assert (days["owmas_position"] != days["sma_position"]).all()
    assert set(days["owmas_position"]) <= {0, 1}
    assert set(days["sma_position"]) <= {0, 1}
    assert episodes["trading_days"].sum() == len(days)
    assert len(episodes) == int(summary["episodes"])


def test_exploratory_label_and_outputs():
    required = [
        "signal_disagreement_days.csv",
        "signal_disagreement_episodes.csv",
        "signal_disagreement_summary.csv",
        "signal_disagreement_by_regime.csv",
        "signal_disagreement_by_year.csv",
        "signal_disagreement_by_year.png",
        "owa_weight_profiles.csv",
        "owa_weight_profiles.png",
        "worked_example_prices.csv",
        "worked_example_values.csv",
        "worked_example_summary.csv",
        "worked_example.png",
        "trend_conditional_mechanism_windows.csv",
        "trend_conditional_mechanism_summary.csv",
        "trend_conditional_mechanism.png",
        "h1_effect_size_context.csv",
        "h4_volatility_effect_sizes.csv",
        "strategy_exposure_context.csv",
        "spy_descriptive_statistics.csv",
        "profile_return_correlations.csv",
        "spy_sample_periods.png",
        "context_summary.md",
    ]
    for name in required:
        path = OUTPUT / name
        assert path.exists() and path.stat().st_size > 0, name
    metadata = json.loads((OUTPUT / "exploratory_metadata.json").read_text())
    assert metadata["analysis_type"] == "exploratory"
    assert metadata["registered_results_changed"] is False


def test_weight_profiles_match_signal_definition():
    profiles = pd.read_csv(OUTPUT / "owa_weight_profiles.csv")
    gamma_by_profile = {"optimistic": 0.5, "neutral": 1.0, "conservative": 2.0}
    for profile, gamma in gamma_by_profile.items():
        rows = profiles[profiles["profile"] == profile].sort_values("rank")
        expected = owa_weights(gamma, 20)
        assert np.allclose(rows["weight"], expected)
        assert np.isclose(rows["weight"].sum(), 1.0)
        assert np.isclose(rows["orness"].iloc[0], orness(expected))


def test_worked_examples_use_real_prices_and_show_neutral_identity():
    summary = pd.read_csv(OUTPUT / "worked_example_summary.csv")
    spy = pd.read_csv(ROOT / "data" / "spy.csv", index_col="date", parse_dates=True)
    changes = spy["adj_close"].div(spy["adj_close"].shift(4)).sub(1.0).dropna()
    expected = {
        "strongest rise": changes.max(),
        "strongest fall": changes.min(),
    }
    for label, change in expected.items():
        rows = summary[summary["window"] == label]
        assert np.allclose(rows["price_change"], change)
        neutral = rows[rows["profile"] == "neutral"].iloc[0]
        assert np.isclose(neutral["owma"], neutral["sma"])
        assert np.isclose(
            neutral["owmas_beta_0.5"],
            0.5 * neutral["sma"] + 0.5 * neutral["wma"],
        )


def test_trend_mechanism_reverses_effective_recency():
    summary = pd.read_csv(OUTPUT / "trend_conditional_mechanism_summary.csv")
    expected_sign = {
        ("rising", "optimistic"): 1,
        ("rising", "conservative"): -1,
        ("falling", "optimistic"): -1,
        ("falling", "conservative"): 1,
    }
    for window_length in [20, 50]:
        frame = summary[summary["window_length"] == window_length]
        for (regime, profile), sign in expected_sign.items():
            row = frame[
                (frame["trend_regime"] == regime)
                & (frame["profile"] == profile)
            ].iloc[0]
            assert sign * row["mean_recency_shift"] > 0.0
            assert row["fraction_matching_expected"] > 0.5


def test_neutral_profile_has_no_recency_shift():
    windows = pd.read_csv(OUTPUT / "trend_conditional_mechanism_windows.csv")
    assert np.allclose(windows["neutral_recency_shift_from_neutral"], 0.0)
    assert np.allclose(windows["neutral_owmas_relative_to_neutral"], 0.0)


def test_effect_size_context_matches_registered_results():
    context = pd.read_csv(OUTPUT / "h1_effect_size_context.csv", index_col="benchmark")
    registered = pd.read_csv(
        ROOT / "results" / "h1_sharpe_tests.csv", index_col="comparison"
    )
    for benchmark, row in context.iterrows():
        source = registered.loc[f"OWMAS - {benchmark}"]
        assert np.isclose(row["difference"], source["difference"])
        assert np.isclose(row["ci_low"], source["ci_low"])
        assert np.isclose(row["ci_high"], source["ci_high"])
        assert int(row["block_size"]) == int(source["block_size"])


def test_exposure_context_matches_registered_metrics():
    context = pd.read_csv(OUTPUT / "strategy_exposure_context.csv", index_col="strategy")
    registered = pd.read_csv(
        ROOT / "results" / "performance_metrics.csv", index_col="strategy"
    )
    assert np.allclose(context["exposure"], registered.loc[context.index, "exposure"])
    assert np.allclose(context["sharpe"], registered.loc[context.index, "sharpe"])


def test_h4_context_uses_annual_percentage_points():
    context = pd.read_csv(
        OUTPUT / "h4_volatility_effect_sizes.csv", index_col="comparison"
    )
    registered = pd.read_csv(ROOT / "results" / "h4_profile_tests.csv")
    registered = registered[registered["metric"] == "volatility_difference"].set_index(
        "comparison"
    )
    assert np.allclose(
        context["difference_percentage_points"], registered["estimate"] * 100.0
    )
    assert np.allclose(context["ci_low_percentage_points"], registered["ci_low"] * 100.0)
    assert np.allclose(context["ci_high_percentage_points"], registered["ci_high"] * 100.0)
    assert context["ci_excludes_zero"].all()


def test_profile_return_correlations_are_paired_and_high():
    correlations = pd.read_csv(
        OUTPUT / "profile_return_correlations.csv", index_col=0
    )
    assert np.allclose(correlations, correlations.T)
    assert np.allclose(np.diag(correlations), 1.0)
    off_diagonal = correlations.to_numpy()[np.triu_indices_from(correlations, k=1)]
    assert (off_diagonal > 0.95).all()


def test_spy_statistics_cover_full_sample_and_registered_subperiods():
    statistics = pd.read_csv(OUTPUT / "spy_descriptive_statistics.csv", index_col="sample")
    assert set(statistics.index) == {
        "full_sample", "gfc", "post_gfc", "covid", "tightening"
    }
    assert int(statistics.loc["full_sample", "observations"]) == 5281
    numeric = statistics.drop(columns=["start", "end"]).to_numpy(dtype=float)
    assert np.isfinite(numeric).all()
