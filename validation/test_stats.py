"""Pytest checks for the statistical methods used in the experiment."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import src.stats as stats


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "evidence" / "week6" / "ledoit_wolf_mutual_funds.csv"
SEED = 14_487_692


def test_ledoit_wolf_matches_the_published_example(monkeypatch):
    returns = pd.read_csv(FIXTURE)
    risk_free = pd.Series(0.0, index=returns.index)

    # The reference implementation uses a four-observation block.
    monkeypatch.setattr(stats, "_automatic_block_size", lambda values, kind: 4)
    result = stats.ledoit_wolf_sharpe_test(
        returns["fund_a"],
        returns["fund_b"],
        risk_free,
        reps=4_999,
        seed=SEED,
    )

    assert result["sharpe_a"] == pytest.approx(0.108, abs=0.001)
    assert result["sharpe_b"] == pytest.approx(0.011, abs=0.001)
    assert result["p_value"] == pytest.approx(0.070, abs=0.01)
    assert result["block_size"] == 4


def test_ledoit_wolf_is_repeatable_with_the_registered_seed():
    rng = np.random.default_rng(42)
    common = rng.normal(0.0, 0.01, 180)
    first = pd.Series(common + rng.normal(0.0004, 0.002, 180))
    second = pd.Series(common + rng.normal(0.0, 0.002, 180))
    risk_free = pd.Series(0.0001, index=first.index)

    result_a = stats.ledoit_wolf_sharpe_test(first, second, risk_free, 199, SEED)
    result_b = stats.ledoit_wolf_sharpe_test(first, second, risk_free, 199, SEED)

    assert result_a == result_b


def test_stationary_bootstrap_keeps_paired_columns_together():
    values = np.arange(1.0, 81.0)
    returns = pd.DataFrame({"a": values, "b": 2.0 * values})

    def slope(frame):
        return np.array([frame["b"].sum() / frame["a"].sum()])

    result = stats.stationary_bootstrap_ci(
        returns,
        slope,
        reps=199,
        seed=SEED,
        confidence=0.95,
    )

    assert result["estimate"] == pytest.approx(2.0)
    assert result["ci_low"] == pytest.approx(2.0)
    assert result["ci_high"] == pytest.approx(2.0)


@pytest.mark.parametrize("reps", [0, -1, 1.5])
def test_bootstrap_rejects_invalid_replication_counts(reps):
    returns = pd.DataFrame({"a": [0.01, 0.02], "b": [0.02, 0.01]})

    with pytest.raises(ValueError):
        stats.stationary_bootstrap_ci(returns, np.mean, reps, SEED, 0.95)


@pytest.mark.parametrize("confidence", [0.0, 1.0, -0.1, 1.1])
def test_stationary_bootstrap_rejects_invalid_confidence(confidence):
    returns = pd.DataFrame({"a": [0.01, 0.02], "b": [0.02, 0.01]})

    with pytest.raises(ValueError):
        stats.stationary_bootstrap_ci(returns, np.mean, 9, SEED, confidence)


def test_ledoit_wolf_rejects_too_few_overlapping_dates():
    first = pd.Series(np.linspace(0.00, 0.07, 7))
    second = pd.Series(np.linspace(0.01, 0.08, 7))
    risk_free = pd.Series(0.0, index=first.index)

    with pytest.raises(ValueError, match="at least eight"):
        stats.ledoit_wolf_sharpe_test(first, second, risk_free, 99, SEED)
