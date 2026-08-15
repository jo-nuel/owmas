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
    return prices.rolling(m).mean()


def wma(prices: pd.Series, m: int) -> pd.Series:
    """Linearly weighted moving average.

    w_i = (m - i) / (1 + 2 + ... + m) for lag i = 0 (today) .. m-1,
    so the most recent observation has the largest weight.
    """
    denom = m * (m + 1) / 2
    # weights[k] applies to the k-th element of the rolling window as
    # pandas presents it: chronological, oldest first. weights[-1]
    # (largest) lands on today, i.e. lag i = 0.
    weights = np.arange(1, m + 1) / denom
    return prices.rolling(m).apply(lambda x: np.dot(x, weights), raw=True)


def ema(prices: pd.Series, m: int) -> pd.Series:
    """Exponential moving average, lambda = 2 / (m + 1).

    Recursive: EMA_t = lambda * p_t + (1 - lambda) * EMA_{t-1},
    initialised with the SMA of the first m observations
    (a standard, documented choice — state it in the thesis).
    """
    lam = 2 / (m + 1)
    result = pd.Series(np.nan, index=prices.index)
    start = m - 1
    result.iloc[start] = prices.iloc[:m].mean()
    for i in range(start + 1, len(prices)):
        result.iloc[i] = lam * prices.iloc[i] + (1 - lam) * result.iloc[i - 1]
    return result


def owa_weights(gamma: float, m: int) -> np.ndarray:
    """OWA weight vector from Yager's quantifier Q(r) = r**gamma.

    v_j = Q(j/m) - Q((j-1)/m) for j = 1..m, applied to
    descending-ordered arguments. Returns array of length m, sums to 1.
    """
    j = np.arange(1, m + 1)
    q = lambda r: r ** gamma
    return q(j / m) - q((j - 1) / m)


def orness(v: np.ndarray) -> float:
    """alpha(v) = (1/(m-1)) * sum_j (m - j) * v_j  with j = 1..m."""
    m = len(v)
    j = np.arange(1, m + 1)
    return float(np.sum((m - j) * v) / (m - 1))


def owmas(prices: pd.Series, m: int, beta: float, gamma: float) -> pd.Series:
    """OWAWMA-based signal — §3.4.

    Uses the separable form, Merigó & Yager (2019) Eq. (4):
        OWMAS = beta * OWMA + (1 - beta) * WMA
    where OWMA applies owa_weights(gamma, m) to the window sorted
    descending. beta = 0 reproduces wma() exactly; beta = 1, gamma = 1
    reproduces sma() exactly (equal OWA weights == arithmetic mean).
    """
    v = owa_weights(gamma, m)  # v[0] weights the largest value in the window

    def _owma_window(x):
        return np.dot(np.sort(x)[::-1], v)

    owma = prices.rolling(m).apply(_owma_window, raw=True)
    return beta * owma + (1 - beta) * wma(prices, m)
