"""Performance metrics — Methodology §3.8. YOU implement these.

All annualisation uses periods_per_year from config (252 for daily).
Sharpe/Sortino use EXCESS returns over rf_daily.
"""
import numpy as np
import pandas as pd


def _clean_returns(returns: pd.Series) -> pd.Series:
    clean = returns.astype(float).dropna()
    if clean.empty:
        raise ValueError("returns must contain at least one finite observation")
    if not np.isfinite(clean).all():
        raise ValueError("returns must be finite")
    if (clean <= -1.0).any():
        raise ValueError("returns must be greater than -100%")
    return clean


def _aligned_excess(returns: pd.Series, rf_daily: pd.Series) -> pd.Series:
    ret, rf = returns.astype(float).align(rf_daily.astype(float), join="inner")
    excess = (ret - rf).dropna()
    if excess.empty or not np.isfinite(excess).all():
        raise ValueError("returns and rf_daily must have finite overlapping observations")
    return excess


def cumulative_return(returns: pd.Series) -> float:
    clean = _clean_returns(returns)
    return float((1.0 + clean).prod() - 1.0)


def cagr(returns: pd.Series, periods_per_year: int) -> float:
    clean = _clean_returns(returns)
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    growth = float((1.0 + clean).prod())
    return float(growth ** (periods_per_year / len(clean)) - 1.0)


def volatility(returns: pd.Series, periods_per_year: int) -> float:
    clean = _clean_returns(returns)
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    return float(clean.std(ddof=1) * np.sqrt(periods_per_year))


def sharpe(returns: pd.Series, rf_daily: pd.Series, periods_per_year: int) -> float:
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    excess = _aligned_excess(returns, rf_daily)
    denominator = excess.std(ddof=1)
    if denominator == 0 or np.isnan(denominator):
        return float("nan")
    return float(np.sqrt(periods_per_year) * excess.mean() / denominator)


def sortino(returns: pd.Series, rf_daily: pd.Series, periods_per_year: int) -> float:
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    excess = _aligned_excess(returns, rf_daily)
    downside = np.minimum(excess.to_numpy(), 0.0)
    downside_deviation = float(np.sqrt(np.mean(np.square(downside))))
    if downside_deviation == 0:
        return float("nan")
    return float(np.sqrt(periods_per_year) * excess.mean() / downside_deviation)


def max_drawdown(returns: pd.Series) -> float:
    """Most negative peak-to-trough decline of the equity curve (<= 0)."""
    clean = _clean_returns(returns)
    equity = (1.0 + clean).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min())


def exposure(positions: pd.Series) -> float:
    """Fraction of days invested (§3.7 requires reporting this)."""
    clean = positions.astype(float).dropna()
    if clean.empty or not clean.isin([0.0, 1.0]).all():
        raise ValueError("positions must contain at least one observation and only 0 or 1")
    return float(clean.mean())


def rolling_sharpe(returns: pd.Series, rf_daily: pd.Series,
                   window: int, periods_per_year: int) -> pd.Series:
    """Rolling Sharpe for H3 (window = 252 per config)."""
    if window <= 1 or periods_per_year <= 0:
        raise ValueError("window must exceed one and periods_per_year must be positive")
    ret, rf = returns.astype(float).align(rf_daily.astype(float), join="inner")
    excess = ret - rf
    mean = excess.rolling(window, min_periods=window).mean()
    std = excess.rolling(window, min_periods=window).std(ddof=1)
    result = np.sqrt(periods_per_year) * mean / std.replace(0.0, np.nan)
    return result.rename("rolling_sharpe")
