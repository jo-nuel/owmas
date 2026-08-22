"""Dependence-robust statistical inference for strategy returns.

The Sharpe comparison follows Ledoit and Wolf (2008) and the maintained
PeerPerformance implementation: paired returns are resampled jointly with a
circular block bootstrap and every replicate is studentized with its own
block-based standard error. General confidence intervals use ``arch``'s
implementation of the Politis-Romano stationary bootstrap.
"""
from collections.abc import Callable

import numpy as np
import pandas as pd
from arch.bootstrap import (
    CircularBlockBootstrap,
    StationaryBootstrap,
    optimal_block_length,
)


def _validate_resampling(reps: int, seed: int) -> None:
    if not isinstance(reps, int) or reps < 1:
        raise ValueError("reps must be a positive integer")
    if not isinstance(seed, (int, np.integer)):
        raise ValueError("seed must be an integer")


def _as_output(value: np.ndarray):
    flat = np.asarray(value, dtype=float).squeeze()
    return float(flat) if flat.ndim == 0 else flat


def _automatic_block_size(values: np.ndarray, kind: str) -> int:
    """Estimate a conservative joint block size from squared observations."""
    table = optimal_block_length(values ** 2)
    estimates = table[kind].to_numpy(dtype=float)
    finite = estimates[np.isfinite(estimates)]
    if finite.size == 0:
        return 1
    return max(1, min(len(values), int(np.ceil(finite.max()))))


def _sharpe_pair(values: np.ndarray) -> tuple[float, float, float]:
    means = values.mean(axis=0)
    std = values.std(axis=0, ddof=1)
    scale = np.maximum(np.abs(values).max(axis=0), 1.0)
    if np.any(std <= np.finfo(float).eps * scale) or not np.isfinite(std).all():
        raise ValueError("both excess-return series must have positive variance")
    sharpes = means / std
    return float(sharpes[0]), float(sharpes[1]), float(sharpes[0] - sharpes[1])


def _sharpe_gradient(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    means = values.mean(axis=0)
    second = np.square(values).mean(axis=0)
    variances = second - np.square(means)
    if np.any(variances <= 0):
        raise ValueError("both excess-return series must have positive variance")

    denom = np.power(variances, 1.5)
    gradient = np.array([
        second[0] / denom[0],
        -second[1] / denom[1],
        -0.5 * means[0] / denom[0],
        0.5 * means[1] / denom[1],
    ])
    moments = np.column_stack((values[:, 0], values[:, 1],
                               values[:, 0] ** 2, values[:, 1] ** 2))
    return gradient, moments - moments.mean(axis=0)


def _block_standard_error(values: np.ndarray, block_size: int) -> float:
    """Natural circular-block standard error used by PeerPerformance."""
    n = len(values)
    block_count = n // block_size
    if block_count < 1:
        raise ValueError("block size must not exceed the sample length")
    gradient, centred_moments = _sharpe_gradient(values)
    complete = centred_moments[:block_count * block_size]
    blocks = complete.reshape(block_count, block_size, 4)
    zeta = np.sqrt(block_size) * blocks.mean(axis=1)
    psi = np.einsum("bi,bj->ij", zeta, zeta) / block_count
    variance = float(gradient @ psi @ gradient / n)
    if not np.isfinite(variance) or variance <= 0:
        raise ValueError("could not estimate a positive Sharpe-difference variance")
    return float(np.sqrt(variance))


def ledoit_wolf_sharpe_test(ret_a: pd.Series, ret_b: pd.Series,
                            rf_daily: pd.Series, reps: int,
                            seed: int) -> dict:
    """Two-sided test of H0 that two unannualised Sharpe ratios are equal.

    The fixed-block circular bootstrap is studentized as in Ledoit and Wolf
    (2008, equations 6-9). A data-driven block length is estimated jointly
    from the squared excess returns. The same sampled time indices are used
    for both strategies, preserving their dependence.
    """
    _validate_resampling(reps, seed)
    frame = pd.concat({"a": ret_a, "b": ret_b, "rf": rf_daily}, axis=1,
                      join="inner").dropna()
    if len(frame) < 8:
        raise ValueError("at least eight finite overlapping observations are required")
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("returns and rf_daily must be finite")

    excess = frame[["a", "b"]].sub(frame["rf"], axis=0).to_numpy(dtype=float)
    sharpe_a, sharpe_b, difference = _sharpe_pair(excess)
    block_size = _automatic_block_size(excess, "circular")
    observed_se = _block_standard_error(excess, block_size)
    observed_t = abs(difference) / observed_se

    bootstrap = CircularBlockBootstrap(block_size, excess, seed=int(seed))
    studentized = np.empty(reps, dtype=float)
    for index, (positional, _) in enumerate(bootstrap.bootstrap(reps)):
        sample = np.asarray(positional[0], dtype=float)
        _, _, sample_difference = _sharpe_pair(sample)
        sample_se = _block_standard_error(sample, block_size)
        studentized[index] = abs(sample_difference - difference) / sample_se

    p_value = (np.count_nonzero(studentized >= observed_t) + 1) / (reps + 1)
    critical = float(np.quantile(studentized, 0.95))
    half_width = critical * observed_se
    return {
        "sharpe_a": sharpe_a,
        "sharpe_b": sharpe_b,
        "diff": difference,
        "p_value": float(p_value),
        "ci_low": float(difference - half_width),
        "ci_high": float(difference + half_width),
        "block_size": block_size,
    }


def stationary_bootstrap_ci(returns: pd.DataFrame, statistic: Callable,
                            reps: int, seed: int,
                            confidence: float) -> dict:
    """Basic CI for a statistic using joint stationary-bootstrap resampling."""
    _validate_resampling(reps, seed)
    if not isinstance(returns, pd.DataFrame) or returns.empty:
        raise ValueError("returns must be a non-empty DataFrame")
    if returns.isna().any().any() or not np.isfinite(returns.to_numpy(dtype=float)).all():
        raise ValueError("returns must contain only finite observations")
    if not callable(statistic):
        raise ValueError("statistic must be callable")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between zero and one")

    values = returns.astype(float)
    block_size = _automatic_block_size(values.to_numpy(), "stationary")
    bootstrap = StationaryBootstrap(block_size, values, seed=int(seed))

    def wrapped(sample: pd.DataFrame) -> np.ndarray:
        result = np.asarray(statistic(sample), dtype=float)
        if not np.isfinite(result).all():
            raise ValueError("statistic must return finite values")
        return np.atleast_1d(result)

    estimate = wrapped(values)
    samples = np.asarray(bootstrap.apply(wrapped, reps=reps), dtype=float)
    alpha = (1.0 - confidence) / 2.0
    interval = np.vstack((
        2.0 * estimate - np.quantile(samples, 1.0 - alpha, axis=0),
        2.0 * estimate - np.quantile(samples, alpha, axis=0),
    ))
    centred = samples - estimate
    p_value = (
        np.count_nonzero(np.abs(centred) >= np.abs(estimate), axis=0) + 1
    ) / (reps + 1)
    return {
        "estimate": _as_output(estimate),
        "ci_low": _as_output(interval[0]),
        "ci_high": _as_output(interval[1]),
        "p_value": _as_output(p_value),
        "block_size": block_size,
    }
