import numpy as np
import pandas as pd

from scripts.exploratory_monotonicity import (
    analyse_windows,
    non_monotonicity,
    profile_values,
)


def test_non_monotonicity_is_zero_for_monotone_windows():
    assert non_monotonicity(np.array([1.0, 2.0, 3.0, 4.0])) == 0.0
    assert non_monotonicity(np.array([4.0, 3.0, 2.0, 1.0])) == 0.0


def test_monotone_reference_matches_actual_ordered_weighting():
    rising = np.array([1.0, 2.0, 3.0, 4.0])
    falling = rising[::-1]
    for values, direction in [(rising, "rising"), (falling, "falling")]:
        actual, reference = profile_values(values, 0.5, 0.5, direction)
        assert np.isclose(actual, reference)


def test_analysis_reports_positive_gap_for_mixed_window():
    prices = pd.Series(
        [1.0, 4.0, 2.0, 5.0],
        index=pd.date_range("2026-01-01", periods=4),
    )
    result = analyse_windows(
        prices,
        [4],
        0.5,
        {"optimistic": 0.5, "neutral": 1.0, "conservative": 2.0},
    )
    row = result.iloc[0]
    assert row["non_monotonicity"] > 0.0
    assert row["mean_linear_gap_fraction"] > 0.0
    assert row["profile_gap_range_fraction"] > 0.0
    assert row["profile_gap_std_fraction"] > 0.0
