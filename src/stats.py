"""Statistical inference — Methodology §3.9. YOU implement these.

Do NOT hand-roll Ledoit-Wolf from scratch. Port a maintained
implementation and validate it against a published example first:
  - Ledoit & Wolf (2008), J. Empirical Finance 15(5) — original paper;
    authors' code (MATLAB/R) at Michael Wolf's University of Zurich page.
  - R package `PeerPerformance` (sharpeTesting) is a reference
    implementation to validate numbers against.
Stationary bootstrap: Politis & Romano (1994); available in the
`arch` package (arch.bootstrap.StationaryBootstrap) — use it rather
than writing your own resampler.
Seed comes from config (stats.seed); never call these without it.
"""
import numpy as np
import pandas as pd


def ledoit_wolf_sharpe_test(ret_a: pd.Series, ret_b: pd.Series,
                            rf_daily: pd.Series, reps: int,
                            seed: int) -> dict:
    """Two-sided test of H0: Sharpe(a) == Sharpe(b).

    Studentised circular block bootstrap per Ledoit & Wolf (2008).
    Returns {"sharpe_a", "sharpe_b", "diff", "p_value", "ci_low", "ci_high"}.
    Validate against a published example before first use.
    """
    raise NotImplementedError


def stationary_bootstrap_ci(returns: pd.DataFrame, statistic,
                            reps: int, seed: int,
                            confidence: float) -> dict:
    """CI for `statistic` (a function of the returns DataFrame),
    resampling all strategies' returns JOINTLY (same time indices)
    so cross-strategy dependence is preserved (§3.9).
    """
    raise NotImplementedError
