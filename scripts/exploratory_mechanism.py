"""Pure calculations for the exploratory trend mechanism analysis."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.signals import owa_weights


def mechanism_daily(prices: pd.Series, profiles: dict[str, float],
                    windows: list[int], beta: float) -> pd.DataFrame:
    """Measure the chronological position of rank-based weights."""
    rows = []
    for window_length in windows:
        time_position = np.arange(1, window_length + 1, dtype=float)
        centred_time = time_position - time_position.mean()
        slope_denominator = float(np.dot(centred_time, centred_time))
        recency_weights = time_position / time_position.sum()
        neutral_recency = float(time_position.mean())

        for end_location in range(window_length - 1, len(prices)):
            sample = prices.iloc[end_location - window_length + 1:end_location + 1]
            values = sample.to_numpy()
            centred_prices = values - values.mean()
            slope = float(np.dot(centred_time, centred_prices) / slope_denominator)
            regime = "rising" if slope > 0.0 else "falling" if slope < 0.0 else "flat"
            sorted_locations = np.argsort(-values, kind="stable")
            sorted_values = values[sorted_locations]
            weighted_average = float(np.dot(values, recency_weights))

            profile_values = {}
            for profile, gamma in profiles.items():
                rank_weights = owa_weights(float(gamma), window_length)
                chronological_weights = np.empty(window_length)
                chronological_weights[sorted_locations] = rank_weights
                ordered_average = float(np.dot(sorted_values, rank_weights))
                combined_signal = (
                    beta * ordered_average + (1.0 - beta) * weighted_average
                )
                profile_values[profile] = {
                    "gamma": float(gamma),
                    "effective_recency_position": float(
                        np.dot(time_position, chronological_weights)
                    ),
                    "owma": ordered_average,
                    "owmas": combined_signal,
                }

            neutral_signal = profile_values["neutral"]["owmas"]
            for profile, values_by_profile in profile_values.items():
                recency_shift = (
                    values_by_profile["effective_recency_position"]
                    - neutral_recency
                )
                expected_sign = {
                    ("rising", "optimistic"): 1,
                    ("rising", "conservative"): -1,
                    ("falling", "optimistic"): -1,
                    ("falling", "conservative"): 1,
                }.get((regime, profile), 0)
                if expected_sign == 0:
                    matches = bool(np.isclose(recency_shift, 0.0))
                else:
                    matches = bool(expected_sign * recency_shift > 0.0)
                rows.append({
                    "date": sample.index[-1],
                    "window_length": window_length,
                    "trend_regime": regime,
                    "trend_slope_fraction_per_observation": slope / values.mean(),
                    "price_change": float(values[-1] / values[0] - 1.0),
                    "profile": profile,
                    "gamma": values_by_profile["gamma"],
                    "effective_recency_position": values_by_profile[
                        "effective_recency_position"
                    ],
                    "recency_shift_from_neutral": recency_shift,
                    "owma": values_by_profile["owma"],
                    "owmas": values_by_profile["owmas"],
                    "owmas_relative_to_neutral": (
                        values_by_profile["owmas"] / neutral_signal - 1.0
                    ),
                    "matches_expected_direction": matches,
                })
    return pd.DataFrame(rows).set_index(
        ["date", "window_length", "trend_regime", "profile"]
    )


def mechanism_summary(daily: pd.DataFrame) -> pd.DataFrame:
    """Summarise effective recency by window, regime, and profile."""
    grouped = daily.reset_index().groupby(
        ["window_length", "trend_regime", "profile"], observed=True
    )
    return grouped.agg(
        n_windows=("date", "size"),
        mean_recency_shift=("recency_shift_from_neutral", "mean"),
        median_recency_shift=("recency_shift_from_neutral", "median"),
        mean_owmas_relative_difference=("owmas_relative_to_neutral", "mean"),
        fraction_matching_expected=("matches_expected_direction", "mean"),
    )


def mechanism_windows(daily: pd.DataFrame) -> pd.DataFrame:
    """Put the profile results on one auditable row per price window."""
    frame = daily.reset_index()
    common = [
        "date",
        "window_length",
        "trend_regime",
        "trend_slope_fraction_per_observation",
        "price_change",
    ]
    values = [
        "recency_shift_from_neutral",
        "owmas_relative_to_neutral",
        "matches_expected_direction",
    ]
    wide = frame.pivot(index=common, columns="profile", values=values)
    wide.columns = [f"{profile}_{metric}" for metric, profile in wide.columns]
    return wide.reset_index().set_index(["date", "window_length"])


def save_mechanism_chart(summary: pd.DataFrame, output: Path) -> None:
    """Plot the average shift toward newer or older observations."""
    display = summary.reset_index()
    profiles = ["optimistic", "conservative"]
    styles = {"optimistic": "#2F5597", "conservative": "#808080"}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True)
    for ax, window_length in zip(axes, [20, 50]):
        frame = display[display["window_length"] == window_length]
        x = np.arange(2)
        width = 0.34
        for offset, profile in enumerate(profiles):
            values = []
            for regime in ["rising", "falling"]:
                row = frame[
                    (frame["trend_regime"] == regime)
                    & (frame["profile"] == profile)
                ]
                values.append(float(row["mean_recency_shift"].iloc[0]))
            ax.bar(
                x + (offset - 0.5) * width,
                values,
                width=width,
                color=styles[profile],
                label=profile.title(),
            )
        ax.axhline(0.0, color="#222222", linewidth=0.8)
        ax.set_title(f"{window_length}-price window")
        ax.set_xlabel("Fitted window direction")
        ax.set_xticks(x, ["Rising", "Falling"])
        ax.grid(axis="y", color="#D9D9D9", linewidth=0.7)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Mean position shift from neutral\n(positive means more recent)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center", ncol=2)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    fig.savefig(output, dpi=180)
    plt.close(fig)
