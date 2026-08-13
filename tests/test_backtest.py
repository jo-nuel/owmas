"""Validation harness parts 2–4 — look-ahead, assertions, known-answer (§3.11).
COMPLETE — do not modify. Run: pytest tests/test_backtest.py -q
"""
import numpy as np
import pandas as pd
import pytest

from src.signals import sma
from src.backtest import crossover_positions, strategy_returns, buy_and_hold_returns

RNG = np.random.default_rng(7)
IDX = pd.bdate_range("2010-01-01", periods=600)
PRICES = pd.Series(100 * np.exp(np.cumsum(RNG.normal(0.0003, 0.01, 600))),
                   index=IDX, name="adj_close")
RF = pd.Series(0.0001, index=IDX, name="rf_daily")


def _positions(prices, s=20, l=50):
    return crossover_positions(sma(prices, s), sma(prices, l))


# ---------- look-ahead test (§3.11 second class) ----------

def test_truncation_does_not_change_history():
    full = _positions(PRICES)
    for cut in (300, 450, 599):
        trunc = _positions(PRICES.iloc[:cut])
        pd.testing.assert_series_equal(full.iloc[:cut - 1], trunc.iloc[:-1],
                                       check_names=False)


def test_position_is_shifted_at_least_one_day():
    # A signal flip on day t must not affect the return earned on day t.
    pos = _positions(PRICES)
    raw = (sma(PRICES, 20) > sma(PRICES, 50)).astype(float)
    changes = raw.diff().abs() > 0
    same_day = (pos.diff().abs() > 0) & changes
    assert not same_day.any(), "position changes on the same day as its signal"


# ---------- known-answer test on synthetic data (§3.11 fourth class) ----------

def test_sine_wave_crossovers_known_answer():
    # Slow sine + linear trend: crossover dates computable by construction.
    n = 400
    idx = pd.bdate_range("2018-01-01", periods=n)
    t = np.arange(n)
    prices = pd.Series(100 + 10 * np.sin(2 * np.pi * t / 100), index=idx)
    pos = crossover_positions(sma(prices, 5), sma(prices, 30))
    assert pos.isin([0.0, 1.0]).all()
    n_trades = int(pos.diff().abs().sum())
    # ~4 cycles -> in [6, 10] entry/exit events after warmup; exact count
    # depends only on warmup handling, brackets catch off-by-window bugs.
    assert 6 <= n_trades <= 10, f"unexpected trade count {n_trades}"
    # While price is falling through its trough, must be out of market.
    trough_zone = idx[(t % 100 > 60) & (t % 100 < 90) & (t > 40)]
    assert pos.loc[trough_zone].mean() < 0.2


# ---------- accounting tests ----------

def test_costs_charged_on_changes_only():
    pos = pd.Series([0, 0, 1, 1, 1, 0, 0, 1, 1, 1.0],
                    index=pd.bdate_range("2020-01-01", periods=10))
    prices = pd.Series(np.full(10, 100.0), index=pos.index)  # zero asset returns
    rf = pd.Series(0.0, index=pos.index)
    ret = strategy_returns(pos, prices, rf, cost=0.001)
    # 3 position changes -> total cost exactly 0.003
    assert float(ret.sum()) == pytest.approx(-0.003, abs=1e-12)


def test_cash_earns_rf():
    pos = pd.Series(0.0, index=IDX)  # never invested
    ret = strategy_returns(pos, PRICES, RF, cost=0.001)
    assert float(ret.iloc[10]) == pytest.approx(0.0001, abs=1e-12)


def test_buy_and_hold_cost_once():
    ret = buy_and_hold_returns(PRICES, cost=0.001)
    asset = PRICES.pct_change().fillna(0.0)
    # After day 0, B&H return equals asset return exactly.
    pd.testing.assert_series_equal(ret.iloc[1:], asset.iloc[1:],
                                   check_names=False, atol=1e-12)
    assert float(ret.iloc[0]) == pytest.approx(-0.001, abs=1e-12)
