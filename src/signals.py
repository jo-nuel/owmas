"""Signal functions — Methodology §3.4. YOU implement these.

Every function must be pure (no I/O, no globals) and operate on a
pandas Series of prices indexed by date. The tests in
tests/test_signals.py encode the mathematical definitions; your
implementations must pass them unmodified.

Conventions
-----------
- Window of length m at time t: (p_t, p_{t-1}, ..., p_{t-m+1}).
- OWA weights v are indexed over DESCENDING-ordered values:
  v[0] weights the largest observation in the window.
- Rows with fewer than m observations available return NaN.
"""
import numpy as np
import pandas as pd


def sma(prices: pd.Series, m: int) -> pd.Series:
    """Simple moving average."""
    raise NotImplementedError


def wma(prices: pd.Series, m: int) -> pd.Series:
    """Linearly weighted moving average.

    w_i = (m - i) / (1 + 2 + ... + m) for lag i = 0 (today) .. m-1,
    so the most recent observation has the largest weight.
    """
    raise NotImplementedError


def ema(prices: pd.Series, m: int) -> pd.Series:
    """Exponential moving average, lambda = 2 / (m + 1).

    Recursive: EMA_t = lambda * p_t + (1 - lambda) * EMA_{t-1},
    initialised with the SMA of the first m observations
    (a standard, documented choice — state it in the thesis).
    """
    raise NotImplementedError


def owa_weights(gamma: float, m: int) -> np.ndarray:
    """OWA weight vector from Yager's quantifier Q(r) = r**gamma.

    v_j = Q(j/m) - Q((j-1)/m) for j = 1..m, applied to
    descending-ordered arguments. Returns array of length m, sums to 1.
    """
    raise NotImplementedError


def orness(v: np.ndarray) -> float:
    """alpha(v) = (1/(m-1)) * sum_j (m - j) * v_j  with j = 1..m."""
    raise NotImplementedError


def owmas(prices: pd.Series, m: int, beta: float, gamma: float) -> pd.Series:
    """OWAWMA-based signal — §3.4.

    For each window: sort descending to get b_1 >= ... >= b_m; let
    sigma(j) be the original lag of the j-th largest observation, and
    w the WMA positional weights. Then

        OWMAS_t = sum_j (beta * v_j + (1 - beta) * w_sigma(j)) * b_j

    beta = 0 must reproduce wma() exactly; beta = 1, gamma = 1 must
    reproduce sma() exactly.
    """
    raise NotImplementedError
