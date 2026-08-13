"""Validation harness part 1 — identity tests (§3.11). COMPLETE — do not modify.

Your src/signals.py implementations must pass these unmodified.
Run: pytest tests/test_signals.py -q
"""
import numpy as np
import pandas as pd
import pytest

from src.signals import sma, wma, ema, owa_weights, orness, owmas

RNG = np.random.default_rng(14487692)
PRICES = pd.Series(
    100 * np.exp(np.cumsum(RNG.normal(0.0003, 0.01, 500))),
    index=pd.bdate_range("2015-01-01", periods=500), name="adj_close",
)
M = 20


# ---------- basic definitions ----------

def test_sma_matches_pandas():
    expected = PRICES.rolling(M).mean()
    pd.testing.assert_series_equal(sma(PRICES, M), expected,
                                   check_names=False, atol=1e-12)


def test_wma_hand_computed_window():
    window = PRICES.iloc[:M].to_numpy()          # p_{t-m+1} .. p_t
    lags = window[::-1]                          # p_t, p_{t-1}, ...
    w = (M - np.arange(M)) / (M * (M + 1) / 2)   # w_0 largest (most recent)
    expected = float(np.sum(w * lags))
    got = wma(PRICES, M).iloc[M - 1]
    assert got == pytest.approx(expected, abs=1e-12)


def test_wma_weights_sum_and_recency():
    const = pd.Series(np.full(100, 42.0), index=pd.RangeIndex(100))
    assert np.allclose(wma(const, M).dropna(), 42.0)   # weights sum to 1
    # rising prices: WMA must exceed SMA (recency weighting)
    rising = pd.Series(np.arange(1.0, 101.0))
    assert (wma(rising, M).dropna() > sma(rising, M).dropna()).all()


def test_ema_recursion():
    lam = 2 / (M + 1)
    e = ema(PRICES, M).dropna()
    t = e.index[5]
    prev = e.shift(1).loc[t]
    assert e.loc[t] == pytest.approx(lam * PRICES.loc[t] + (1 - lam) * prev, rel=1e-10)


# ---------- OWA weights and orness ----------

def test_owa_weights_sum_to_one():
    for g in (0.5, 1.0, 2.0):
        v = owa_weights(g, M)
        assert v.shape == (M,)
        assert np.all(v >= 0)
        assert np.sum(v) == pytest.approx(1.0, abs=1e-12)


def test_orness_analytic_values():
    # gamma=1 -> equal weights -> orness exactly 0.5
    assert orness(owa_weights(1.0, M)) == pytest.approx(0.5, abs=1e-12)
    # gamma<1 tilts to larger (descending-ordered) values -> orness > 0.5
    assert orness(owa_weights(0.5, M)) > 0.5
    assert orness(owa_weights(2.0, M)) < 0.5
    # extreme cases on small m
    assert orness(np.array([1.0, 0, 0, 0])) == pytest.approx(1.0)
    assert orness(np.array([0, 0, 0, 1.0])) == pytest.approx(0.0)


# ---------- OWMAS identities (§3.11 first test class) ----------

def test_owmas_beta0_equals_wma():
    pd.testing.assert_series_equal(
        owmas(PRICES, M, beta=0.0, gamma=2.0), wma(PRICES, M),
        check_names=False, atol=1e-10)


def test_owmas_beta1_gamma1_equals_sma():
    pd.testing.assert_series_equal(
        owmas(PRICES, M, beta=1.0, gamma=1.0), sma(PRICES, M),
        check_names=False, atol=1e-10)


def test_owmas_weights_are_convex_combination():
    # On a constant series every average equals the constant.
    const = pd.Series(np.full(100, 7.0), index=pd.RangeIndex(100))
    for beta in (0.25, 0.5, 0.75):
        for g in (0.5, 1.0, 2.0):
            assert np.allclose(owmas(const, M, beta, g).dropna(), 7.0)


def test_owmas_separable_form():
    # Merigó & Yager (2019), Eq. (4): OWAWMA = beta*OWMA + (1-beta)*WMA.
    # OWMA is OWMAS with beta=1. Must hold for every beta and profile.
    for beta in (0.25, 0.5, 0.75):
        for g in (0.5, 1.0, 2.0):
            direct = owmas(PRICES, M, beta, g)
            separable = beta * owmas(PRICES, M, 1.0, g) + (1 - beta) * wma(PRICES, M)
            pd.testing.assert_series_equal(direct, separable,
                                           check_names=False, atol=1e-10)


def test_owmas_attitude_ordering():
    # For beta=1: optimistic (gamma<1) weights larger values more,
    # so optimistic >= neutral >= conservative pointwise.
    opt = owmas(PRICES, M, 1.0, 0.5).dropna()
    neu = owmas(PRICES, M, 1.0, 1.0).dropna()
    con = owmas(PRICES, M, 1.0, 2.0).dropna()
    assert (opt >= neu - 1e-12).all()
    assert (neu >= con - 1e-12).all()
