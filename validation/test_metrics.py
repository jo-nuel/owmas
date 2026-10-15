"""Extra checks for the performance metrics used in the thesis."""

import numpy as np
import pandas as pd
import pytest

from src.metrics import (
    cagr,
    cumulative_return,
    exposure,
    max_drawdown,
    rolling_sharpe,
    sharpe,
    sortino,
    volatility,
)


def test_return_and_risk_metrics_match_small_known_examples():
    returns = pd.Series([0.10, -0.10])

    assert cumulative_return(returns) == pytest.approx(-0.01)
    assert cagr(returns, periods_per_year=2) == pytest.approx(-0.01)
    assert volatility(returns, periods_per_year=2) == pytest.approx(0.20)


def test_sharpe_and_sortino_use_excess_returns():
    returns = pd.Series([0.03, -0.01, 0.02, -0.02])
    risk_free = pd.Series(0.001, index=returns.index)
    excess = returns - risk_free

    expected_sharpe = 2.0 * excess.mean() / excess.std(ddof=1)
    downside = np.minimum(excess.to_numpy(), 0.0)
    expected_sortino = 2.0 * excess.mean() / np.sqrt(np.mean(downside ** 2))

    assert sharpe(returns, risk_free, periods_per_year=4) == pytest.approx(expected_sharpe)
    assert sortino(returns, risk_free, periods_per_year=4) == pytest.approx(expected_sortino)


def test_sharpe_aligns_returns_and_risk_free_dates():
    returns = pd.Series([0.01, 0.02, -0.01], index=[1, 2, 3])
    risk_free = pd.Series([0.001, 0.002, 0.003], index=[2, 3, 4])
    overlap = pd.Series([0.019, -0.012])
    expected = np.sqrt(252) * overlap.mean() / overlap.std(ddof=1)

    assert sharpe(returns, risk_free, periods_per_year=252) == pytest.approx(expected)


def test_max_drawdown_includes_the_starting_capital():
    returns = pd.Series([-0.10, 0.20, -0.25])

    assert max_drawdown(returns) == pytest.approx(-0.25)


def test_exposure_is_the_fraction_of_invested_days():
    positions = pd.Series([0.0, 1.0, 1.0, 0.0])

    assert exposure(positions) == pytest.approx(0.5)


def test_rolling_sharpe_keeps_the_warmup_period_empty():
    returns = pd.Series([0.01, 0.02, -0.01, 0.03])
    risk_free = pd.Series(0.0, index=returns.index)

    result = rolling_sharpe(returns, risk_free, window=3, periods_per_year=252)

    assert result.name == "rolling_sharpe"
    assert result.iloc[:2].isna().all()
    assert result.iloc[2:].notna().all()


@pytest.mark.parametrize(
    "returns",
    [
        pd.Series(dtype=float),
        pd.Series([0.01, np.inf]),
        pd.Series([0.01, -1.0]),
    ],
)
def test_return_metrics_reject_invalid_observations(returns):
    with pytest.raises(ValueError):
        cumulative_return(returns)


@pytest.mark.parametrize("periods_per_year", [0, -252])
def test_annual_metrics_reject_invalid_frequency(periods_per_year):
    returns = pd.Series([0.01, -0.01])
    risk_free = pd.Series(0.0, index=returns.index)

    with pytest.raises(ValueError):
        cagr(returns, periods_per_year)
    with pytest.raises(ValueError):
        volatility(returns, periods_per_year)
    with pytest.raises(ValueError):
        sharpe(returns, risk_free, periods_per_year)
    with pytest.raises(ValueError):
        sortino(returns, risk_free, periods_per_year)


def test_undefined_ratios_return_nan():
    constant = pd.Series([0.01, 0.01, 0.01])
    risk_free = pd.Series(0.0, index=constant.index)

    assert np.isnan(sharpe(constant, risk_free, periods_per_year=252))
    assert np.isnan(sortino(constant, risk_free, periods_per_year=252))


@pytest.mark.parametrize(
    "positions",
    [pd.Series(dtype=float), pd.Series([0.0, 0.5, 1.0])],
)
def test_exposure_rejects_invalid_positions(positions):
    with pytest.raises(ValueError):
        exposure(positions)
