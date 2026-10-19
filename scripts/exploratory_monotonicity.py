"""Explore how non-monotone price windows affect ordered weighting.

This post hoc analysis does not change the registered hypotheses. It compares
each OWMAS profile with the fixed linear filter that would apply if price rank
followed time perfectly within a rising or falling window.
"""
from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "exploratory"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.signals import owa_weights


def non_monotonicity(values: np.ndarray) -> float:
    """Return 1 - absolute Kendall tau between time and price."""
    time = np.arange(len(values), dtype=float)
    tau = float(kendalltau(time, values).statistic)
    if np.isnan(tau):
        return 0.0
    return 1.0 - abs(tau)


def fitted_direction(values: np.ndarray) -> str:
    """Classify a window by the sign of its fitted linear price slope."""
    time = np.arange(len(values), dtype=float)
    slope = float(np.polyfit(time, values, 1)[0])
    return "rising" if slope > 0.0 else "falling" if slope < 0.0 else "flat"


def profile_values(values: np.ndarray, beta: float, gamma: float,
                   direction: str) -> tuple[float, float]:
    """Return actual OWMAS and its monotone-window linear reference."""
    window = len(values)
    rank_weights = owa_weights(gamma, window)
    recency_weights = np.arange(1, window + 1, dtype=float)
    recency_weights /= recency_weights.sum()
    weighted_average = float(np.dot(values, recency_weights))
    ordered_average = float(np.dot(np.sort(values)[::-1], rank_weights))

    if direction == "rising":
        chronological_rank_weights = rank_weights[::-1]
    elif direction == "falling":
        chronological_rank_weights = rank_weights
    else:
        chronological_rank_weights = np.full(window, 1.0 / window)

    linear_ordered_average = float(np.dot(values, chronological_rank_weights))
    actual = beta * ordered_average + (1.0 - beta) * weighted_average
    reference = beta * linear_ordered_average + (1.0 - beta) * weighted_average
    return actual, reference


def analyse_windows(prices: pd.Series, windows: list[int], beta: float,
                    profiles: dict[str, float]) -> pd.DataFrame:
    """Calculate profile and linear-reference gaps for every complete window."""
    rows: list[dict[str, float | int | str | pd.Timestamp]] = []
    for window in windows:
        for end in range(window - 1, len(prices)):
            sample = prices.iloc[end - window + 1:end + 1]
            values = sample.to_numpy(dtype=float)
            direction = fitted_direction(values)
            if direction == "flat":
                continue
            scale = float(values.mean())
            window_range = float(np.ptp(values))
            window_std = float(np.std(values, ddof=0))
            actual: dict[str, float] = {}
            reference_gaps: dict[str, float] = {}
            for name in ("optimistic", "conservative"):
                value, reference = profile_values(
                    values, beta, float(profiles[name]), direction
                )
                actual[name] = value
                reference_gaps[name] = abs(value - reference) / scale
            profile_gap = abs(actual["optimistic"] - actual["conservative"])
            rows.append({
                "date": sample.index[-1],
                "window_length": window,
                "direction": direction,
                "non_monotonicity": non_monotonicity(values),
                "profile_gap_fraction": profile_gap / scale,
                "profile_gap_range_fraction": (
                    profile_gap / window_range if window_range > 0.0 else 0.0
                ),
                "profile_gap_std_fraction": (
                    profile_gap / window_std if window_std > 0.0 else 0.0
                ),
                "optimistic_linear_gap_fraction": reference_gaps["optimistic"],
                "conservative_linear_gap_fraction": reference_gaps["conservative"],
                "mean_linear_gap_fraction": float(np.mean(list(reference_gaps.values()))),
            })
    return pd.DataFrame(rows).set_index(["date", "window_length"])


def summarise(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarise gaps by non-monotonicity decile and window length."""
    data = frame.reset_index()
    data["non_monotonicity_decile"] = pd.cut(
        data["non_monotonicity"],
        bins=np.linspace(0.0, 1.0, 11),
        labels=False,
        include_lowest=True,
    )
    grouped = data.groupby(
        ["window_length", "non_monotonicity_decile"], observed=True
    )
    return grouped.agg(
        n_windows=("date", "size"),
        mean_non_monotonicity=("non_monotonicity", "mean"),
        mean_profile_gap_fraction=("profile_gap_fraction", "mean"),
        mean_profile_gap_range_fraction=("profile_gap_range_fraction", "mean"),
        mean_profile_gap_std_fraction=("profile_gap_std_fraction", "mean"),
        mean_linear_gap_fraction=("mean_linear_gap_fraction", "mean"),
    )


def correlations(frame: pd.DataFrame) -> pd.DataFrame:
    """Report Spearman associations between non-monotonicity and each gap."""
    rows = []
    data = frame.reset_index()
    for window, group in data.groupby("window_length"):
        for measure in [
            "profile_gap_fraction",
            "profile_gap_range_fraction",
            "profile_gap_std_fraction",
            "mean_linear_gap_fraction",
        ]:
            result = spearmanr(group["non_monotonicity"], group[measure])
            rows.append({
                "window_length": int(window),
                "measure": measure,
                "spearman_rho": float(result.statistic),
                "p_value": float(result.pvalue),
                "n_windows": int(len(group)),
            })
    return pd.DataFrame(rows).set_index(["window_length", "measure"])


def save_chart(summary: pd.DataFrame, output: Path) -> None:
    """Plot mean profile and linear-reference gaps by non-monotonicity."""
    data = summary.reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True)
    for axis, window in zip(axes, [20, 50]):
        subset = data[data["window_length"] == window]
        x = subset["mean_non_monotonicity"]
        axis.plot(
            x,
            subset["mean_profile_gap_fraction"] * 100,
            color="#2F5597",
            linewidth=2,
            marker="o",
            label="Optimistic to conservative gap",
        )
        axis.plot(
            x,
            subset["mean_linear_gap_fraction"] * 100,
            color="#666666",
            linewidth=2,
            marker="s",
            label="Gap from monotone linear filter",
        )
        axis.set_title(f"{window}-price window")
        axis.set_xlabel("Non-monotonicity  1 - |Kendall tau|")
        axis.grid(color="#D9D9D9", linewidth=0.7)
        axis.set_axisbelow(True)
    axes[0].set_ylabel("Mean signal gap as percentage of price")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center", ncol=2)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main() -> None:
    with (ROOT / "config.yaml").open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    prices = pd.read_csv(ROOT / "data" / "spy.csv", parse_dates=["date"])
    prices = prices.set_index("date")[config["data"]["price_field"]]
    windows = [
        int(config["signal"]["short_window"]),
        int(config["signal"]["long_window"]),
    ]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    detail = analyse_windows(
        prices,
        windows,
        float(config["owmas"]["beta_primary"]),
        config["owmas"]["gamma_profiles"],
    )
    summary = summarise(detail)
    association = correlations(detail)
    detail.to_csv(OUTPUT / "monotonicity_windows.csv")
    summary.to_csv(OUTPUT / "monotonicity_summary.csv")
    association.to_csv(OUTPUT / "monotonicity_correlations.csv")
    save_chart(summary, OUTPUT / "monotonicity_profile_gap.png")
    print(association.to_string())


if __name__ == "__main__":
    main()
