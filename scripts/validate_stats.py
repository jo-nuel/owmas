"""Deterministic Week 6 validation for the statistical inference module."""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.stats as stats  # noqa: E402

SEED = 14_487_692
FIXTURE = ROOT / "evidence" / "week6" / "ledoit_wolf_mutual_funds.csv"


def main() -> None:
    returns = pd.read_csv(FIXTURE)
    means = returns.mean()
    std = returns.std(ddof=1)
    sharpes = means / std
    np.testing.assert_allclose(means, [0.511, 0.098], atol=0.0006)
    np.testing.assert_allclose(std, [4.760, 9.161], atol=0.0006)
    np.testing.assert_allclose(sharpes, [0.108, 0.011], atol=0.0006)

    original_block_selector = stats._automatic_block_size
    stats._automatic_block_size = lambda values, kind: 4
    try:
        zero_rf = pd.Series(0.0, index=returns.index)
        result = stats.ledoit_wolf_sharpe_test(
            returns["fund_a"], returns["fund_b"], zero_rf,
            reps=4_999, seed=SEED,
        )
    finally:
        stats._automatic_block_size = original_block_selector
    assert abs(result["p_value"] - 0.070) <= 0.01

    rng = np.random.default_rng(42)
    common = rng.normal(0.0, 0.01, 180)
    a = pd.Series(common + rng.normal(0.0004, 0.002, 180))
    b = pd.Series(common + rng.normal(0.0, 0.002, 180))
    rf = pd.Series(0.0001, index=a.index)
    first = stats.ledoit_wolf_sharpe_test(a, b, rf, 199, SEED)
    second = stats.ledoit_wolf_sharpe_test(a, b, rf, 199, SEED)
    assert first == second

    joint = pd.DataFrame({"a": np.arange(80.0), "b": 2.0 * np.arange(80.0)})
    slope = lambda frame: np.array([frame["b"].sum() / frame["a"].sum()])
    interval = stats.stationary_bootstrap_ci(joint, slope, 199, SEED, 0.95)
    assert np.isclose(interval["estimate"], 2.0)
    assert np.isclose(interval["ci_low"], 2.0)
    assert np.isclose(interval["ci_high"], 2.0)

    print(
        "PASS: published Ledoit-Wolf example, registered-seed determinism, "
        "and joint stationary resampling"
    )
    print(f"reference p-value={result['p_value']:.4f} (authors' R result=0.0700)")


if __name__ == "__main__":
    main()
