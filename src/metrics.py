"""Performance metrics — Methodology §3.8. YOU implement these.

All annualisation uses periods_per_year from config (252 for daily).
Sharpe/Sortino use EXCESS returns over rf_daily.
"""
import pandas as pd


def cumulative_return(returns: pd.Series) -> float:
    raise NotImplementedError


def cagr(returns: pd.Series, periods_per_year: int) -> float:
    raise NotImplementedError


def volatility(returns: pd.Series, periods_per_year: int) -> float:
    raise NotImplementedError


def sharpe(returns: pd.Series, rf_daily: pd.Series, periods_per_year: int) -> float:
    raise NotImplementedError


def sortino(returns: pd.Series, rf_daily: pd.Series, periods_per_year: int) -> float:
    raise NotImplementedError


def max_drawdown(returns: pd.Series) -> float:
    """Most negative peak-to-trough decline of the equity curve (<= 0)."""
    raise NotImplementedError


def exposure(positions: pd.Series) -> float:
    """Fraction of days invested (§3.7 requires reporting this)."""
    raise NotImplementedError


def rolling_sharpe(returns: pd.Series, rf_daily: pd.Series,
                   window: int, periods_per_year: int) -> pd.Series:
    """Rolling Sharpe for H3 (window = 252 per config)."""
    raise NotImplementedError
