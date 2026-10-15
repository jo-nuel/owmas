"""Backtest engine from Methodology sections 3.5 and 3.7.

Three explicitly separated stages (§3.7): signals -> positions -> returns.
tests/test_backtest.py contains the look-ahead and known-answer tests.
"""
from itertools import combinations

import pandas as pd


def crossover_positions(short_sig: pd.Series, long_sig: pd.Series) -> pd.Series:
    """Crossover rule + t+1 timing (§3.5).

    Raw signal: 1 where short > long, else 0 (NaN while either window
    is warming up -> 0). Position = raw signal shifted by ONE day.
    Returns a Series of {0, 1}.
    """
    if not short_sig.index.equals(long_sig.index):
        raise ValueError("short_sig and long_sig must have identical indexes")

    valid = short_sig.notna() & long_sig.notna()
    raw_signal = ((short_sig > long_sig) & valid).astype(float)
    # A signal observed after the close on t can first be held on t+1.
    return raw_signal.shift(1, fill_value=0.0).rename("position")


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
    if not positions.index.equals(prices.index):
        raise ValueError("positions and prices must have identical indexes")
    if not rf_daily.index.equals(prices.index):
        raise ValueError("rf_daily and prices must have identical indexes")
    if prices.isna().any() or rf_daily.isna().any() or positions.isna().any():
        raise ValueError("positions, prices, and rf_daily must not contain missing values")
    if not positions.isin([0.0, 1.0]).all():
        raise ValueError("positions must contain only 0 (cash) and 1 (invested)")
    if cost < 0:
        raise ValueError("cost must be non-negative")

    position = positions.astype(float)
    asset_return = prices.astype(float).pct_change(fill_method=None).fillna(0.0)
    gross_return = position * asset_return + (1.0 - position) * rf_daily.astype(float)

    turnover = position.diff().abs()
    turnover.iloc[0] = abs(position.iloc[0])  # charge an initial entry, if present
    return (gross_return - cost * turnover).rename("strategy_return")


def buy_and_hold_returns(prices: pd.Series, cost: float) -> pd.Series:
    """Always invested; cost charged once on the first day."""
    if prices.isna().any():
        raise ValueError("prices must not contain missing values")
    if cost < 0:
        raise ValueError("cost must be non-negative")

    returns = prices.astype(float).pct_change(fill_method=None).fillna(0.0)
    if len(returns):
        returns.iloc[0] -= cost
    return returns.rename("buy_and_hold_return")


def divergence_audit(positions: dict[str, pd.Series]) -> pd.DataFrame:
    """§3.7 go/no-go audit. For each pair of strategies report:
    frac_days_differ, n_trades_a, n_trades_b, n_differing_trades.
    Run and review with supervisor BEFORE any performance evaluation.
    """
    if len(positions) < 2:
        raise ValueError("positions must contain at least two strategies")

    rows = []
    for name_a, name_b in combinations(positions, 2):
        a, b = positions[name_a].align(positions[name_b], join="inner")
        if a.empty:
            raise ValueError(f"{name_a} and {name_b} have no overlapping dates")
        if a.isna().any() or b.isna().any():
            raise ValueError(f"{name_a} and {name_b} contain missing positions")
        if not a.isin([0.0, 1.0]).all() or not b.isin([0.0, 1.0]).all():
            raise ValueError("all position series must contain only 0 and 1")

        a = a.astype(float)
        b = b.astype(float)
        trade_a = a.diff().abs().fillna(a.abs())
        trade_b = b.diff().abs().fillna(b.abs())
        rows.append(
            {
                "strategy_a": name_a,
                "strategy_b": name_b,
                "frac_days_differ": float((a != b).mean()),
                "n_trades_a": int(trade_a.sum()),
                "n_trades_b": int(trade_b.sum()),
                # A differing trade is a date on which only one strategy changes
                # position. Simultaneous entries/exits are the same trade event.
                "n_differing_trades": int((trade_a != trade_b).sum()),
            }
        )

    return pd.DataFrame(rows).set_index(["strategy_a", "strategy_b"])
