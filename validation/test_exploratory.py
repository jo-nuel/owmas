"""Checks for the generated exploratory disagreement analysis."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

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
    ]
    for name in required:
        path = OUTPUT / name
        assert path.exists() and path.stat().st_size > 0, name
    metadata = json.loads((OUTPUT / "exploratory_metadata.json").read_text())
    assert metadata["analysis_type"] == "exploratory"
    assert metadata["registered_results_changed"] is False
