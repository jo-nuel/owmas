"""Backtest engine — Methodology §3.5, §3.7. YOU implement these.

Three explicitly separated stages (§3.7): signals -> positions -> returns.
tests/test_backtest.py contains the look-ahead and known-answer tests.
"""
import pandas as pd


def crossover_positions(short_sig: pd.Series, long_sig: pd.Series) -> pd.Series:
    """Crossover rule + t+1 timing (§3.5).

    Raw signal: 1 where short > long, else 0 (NaN while either window
    is warming up -> 0). Position = raw signal shifted by ONE day.
    Returns a Series of {0, 1}.
    """
    raise NotImplementedError


def strategy_returns(positions: pd.Series,
                     prices: pd.Series,
                     rf_daily: pd.Series,
                     cost: float) -> pd.Series:
    """Daily net returns (§3.7).

    - Invested days: asset return from adj_close pct change.
    - Cash days: rf_daily (cash earns the T-bill rate).
    - Cost: `cost` fraction charged on every position CHANGE
      (|position_t - position_{t-1}|), including the initial entry.
    """
    raise NotImplementedError


def buy_and_hold_returns(prices: pd.Series, cost: float) -> pd.Series:
    """Always invested; cost charged once on the first day."""
    raise NotImplementedError


def divergence_audit(positions: dict[str, pd.Series]) -> pd.DataFrame:
    """§3.7 go/no-go audit. For each pair of strategies report:
    frac_days_differ, n_trades_a, n_trades_b, n_differing_trades.
    Run and review with supervisor BEFORE any performance evaluation.
    """
    raise NotImplementedError
