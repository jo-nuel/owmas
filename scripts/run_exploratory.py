"""Describe when the registered OWMAS and SMA positions disagree.

This is a post hoc exploratory analysis. It uses the registered strategy
settings but writes only to ``results/exploratory/``. It does not change the
primary experiment or its hypothesis tests.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_experiment import _build_strategies, _load_inputs  # noqa: E402
from scripts.exploratory_mechanism import (  # noqa: E402
    mechanism_daily,
    mechanism_summary,
    mechanism_windows,
    save_mechanism_chart,
)
from src.signals import orness, owa_weights  # noqa: E402

OUTPUT = ROOT / "results" / "exploratory"


def _sha256_text(path: Path) -> str:
    payload = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(payload).hexdigest()


def _compound(values: pd.Series) -> float:
    return float((1.0 + values).prod() - 1.0)


def _start_event(previous_owmas: int, previous_sma: int,
                 owmas_position: int, sma_position: int) -> str:
    transition = (previous_owmas, previous_sma, owmas_position, sma_position)
    labels = {
        (0, 0, 1, 0): "OWMAS entered first",
        (0, 0, 0, 1): "SMA entered first",
        (1, 1, 1, 0): "SMA exited first",
        (1, 1, 0, 1): "OWMAS exited first",
    }
    return labels.get(transition, "positions crossed")


def _daily_table(prices: pd.Series, positions: dict[str, pd.Series],
                 returns: dict[str, pd.Series], short_window: int) -> pd.DataFrame:
    table = pd.DataFrame({
        "owmas_position": positions["OWMAS"].astype(int),
        "sma_position": positions["SMA"].astype(int),
        "spy_return": prices.pct_change().fillna(0.0),
        "owmas_return": returns["OWMAS"],
        "sma_return": returns["SMA"],
        "trend_20d_return": prices.pct_change(short_window),
    })
    table.index.name = "date"
    table["trend_regime"] = np.select(
        [table["trend_20d_return"] > 0.0, table["trend_20d_return"] < 0.0,
         table["trend_20d_return"] == 0.0],
        ["rising", "falling", "flat"],
        default="unavailable",
    )
    table["disagreement_type"] = np.where(
        table["owmas_position"] > table["sma_position"],
        "OWMAS invested only",
        "SMA invested only",
    )
    return table.loc[table["owmas_position"] != table["sma_position"]].copy()


def _episode_table(disagreement: pd.DataFrame,
                   all_positions: pd.DataFrame) -> pd.DataFrame:
    previous_date = disagreement.index.to_series().shift()
    previous_type = disagreement["disagreement_type"].shift()
    prior_trading_date = all_positions.index.to_series().shift()
    expected_previous = disagreement.index.to_series().map(prior_trading_date)
    new_episode = previous_date.ne(expected_previous) | previous_type.ne(
        disagreement["disagreement_type"]
    )
    episode_id = new_episode.cumsum()

    rows = []
    for number, (_, episode) in enumerate(disagreement.groupby(episode_id), start=1):
        start = episode.index[0]
        location = all_positions.index.get_loc(start)
        if location == 0:
            previous = pd.Series({"OWMAS": 0, "SMA": 0})
        else:
            previous = all_positions.iloc[location - 1]
        rows.append({
            "episode": number,
            "start": start.date().isoformat(),
            "end": episode.index[-1].date().isoformat(),
            "trading_days": len(episode),
            "disagreement_type": episode["disagreement_type"].iloc[0],
            "start_event": _start_event(
                int(previous["OWMAS"]), int(previous["SMA"]),
                int(episode["owmas_position"].iloc[0]),
                int(episode["sma_position"].iloc[0]),
            ),
            "start_regime": episode["trend_regime"].iloc[0],
            "owmas_return": _compound(episode["owmas_return"]),
            "sma_return": _compound(episode["sma_return"]),
            "return_difference": (
                _compound(episode["owmas_return"])
                - _compound(episode["sma_return"])
            ),
        })
    return pd.DataFrame(rows).set_index("episode")


def _summary(disagreement: pd.DataFrame, episodes: pd.DataFrame,
             observations: int) -> pd.DataFrame:
    owmas_only = int((disagreement["disagreement_type"] == "OWMAS invested only").sum())
    sma_only = int((disagreement["disagreement_type"] == "SMA invested only").sum())
    values = {
        "observation_days": observations,
        "disagreement_days": len(disagreement),
        "disagreement_fraction": len(disagreement) / observations,
        "owmas_invested_only_days": owmas_only,
        "sma_invested_only_days": sma_only,
        "episodes": len(episodes),
        "median_episode_days": float(episodes["trading_days"].median()),
        "owmas_compound_return_on_disagreement_days": _compound(disagreement["owmas_return"]),
        "sma_compound_return_on_disagreement_days": _compound(disagreement["sma_return"]),
    }
    return pd.DataFrame({"value": pd.Series(values)})


def _by_regime(disagreement: pd.DataFrame) -> pd.DataFrame:
    counts = disagreement.groupby(
        ["trend_regime", "disagreement_type"], observed=True
    ).size().rename("days").reset_index()
    counts["share_of_disagreement_days"] = counts["days"] / len(disagreement)
    return counts.set_index(["trend_regime", "disagreement_type"])


def _by_year(disagreement: pd.DataFrame, full_index: pd.DatetimeIndex) -> pd.DataFrame:
    observations = pd.Series(1, index=full_index).groupby(full_index.year).sum()
    differing = disagreement.groupby(disagreement.index.year).size().reindex(
        observations.index, fill_value=0
    )
    frame = pd.DataFrame({
        "observation_days": observations,
        "disagreement_days": differing,
    })
    frame["disagreement_fraction"] = (
        frame["disagreement_days"] / frame["observation_days"]
    )
    frame.index.name = "year"
    return frame


def _save_year_chart(by_year: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(by_year.index.astype(str), by_year["disagreement_fraction"] * 100,
           color="#2F5597", width=0.72)
    ax.set_xlabel("Year")
    ax.set_ylabel("Position disagreement (%)")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.7)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUTPUT / "signal_disagreement_by_year.png", dpi=180)
    plt.close(fig)


def _weight_profiles(profiles: dict[str, float], window: int) -> pd.DataFrame:
    rows = []
    for profile, gamma in profiles.items():
        weights = owa_weights(float(gamma), window)
        profile_orness = orness(weights)
        for rank, weight in enumerate(weights, start=1):
            rows.append({
                "profile": profile,
                "gamma": float(gamma),
                "rank": rank,
                "rank_meaning": "largest" if rank == 1 else (
                    "smallest" if rank == window else "ordered value"
                ),
                "weight": float(weight),
                "orness": profile_orness,
            })
    return pd.DataFrame(rows).set_index(["profile", "rank"])


def _save_weight_chart(profiles: pd.DataFrame) -> None:
    styles = {
        "optimistic": ("#2F5597", "-"),
        "neutral": ("#222222", "--"),
        "conservative": ("#808080", ":"),
    }
    fig, ax = plt.subplots(figsize=(9, 5))
    for profile, frame in profiles.reset_index().groupby("profile", sort=False):
        color, line_style = styles[profile]
        profile_orness = frame["orness"].iloc[0]
        gamma = frame["gamma"].iloc[0]
        ax.plot(
            frame["rank"], frame["weight"] * 100,
            color=color, linestyle=line_style, linewidth=2,
            marker="o", markersize=3,
            label=f"{profile.title()} (gamma={gamma:g}, orness={profile_orness:.3f})",
        )
    ax.set_xlabel("Rank after sorting prices from largest to smallest")
    ax.set_ylabel("Weight (%)")
    ax.set_xticks(range(1, 21))
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUTPUT / "owa_weight_profiles.png", dpi=180)
    plt.close(fig)


def _worked_examples(prices: pd.Series, profiles: dict[str, float],
                     beta: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    window = 5
    changes = prices.div(prices.shift(window - 1)).sub(1.0).dropna()
    selected = {
        "strongest rise": changes.idxmax(),
        "strongest fall": changes.idxmin(),
    }
    price_rows = []
    value_rows = []
    summary_rows = []
    wma_weights = np.arange(1, window + 1) / sum(range(1, window + 1))

    for label, end_date in selected.items():
        end_location = prices.index.get_loc(end_date)
        sample = prices.iloc[end_location - window + 1:end_location + 1]
        sorted_prices = np.sort(sample.to_numpy())[::-1]
        simple_average = float(sample.mean())
        weighted_average = float(np.dot(sample.to_numpy(), wma_weights))
        sample_change = float(sample.iloc[-1] / sample.iloc[0] - 1.0)
        for observation, ((date, price), weight) in enumerate(
            zip(sample.items(), wma_weights), start=1
        ):
            price_rows.append({
                "window": label,
                "observation": observation,
                "date": date.date().isoformat(),
                "price": float(price),
                "wma_weight": float(weight),
            })

        for profile, gamma in profiles.items():
            weights = owa_weights(float(gamma), window)
            ordered_average = float(np.dot(sorted_prices, weights))
            combined_signal = beta * ordered_average + (1.0 - beta) * weighted_average
            summary_rows.append({
                "window": label,
                "start": sample.index[0].date().isoformat(),
                "end": sample.index[-1].date().isoformat(),
                "price_change": sample_change,
                "profile": profile,
                "gamma": float(gamma),
                "orness": orness(weights),
                "sma": simple_average,
                "wma": weighted_average,
                "owma": ordered_average,
                "owmas_beta_0.5": combined_signal,
            })
            for rank, (price, weight) in enumerate(
                zip(sorted_prices, weights), start=1
            ):
                value_rows.append({
                    "window": label,
                    "start": sample.index[0].date().isoformat(),
                    "end": sample.index[-1].date().isoformat(),
                    "profile": profile,
                    "rank": rank,
                    "sorted_price": float(price),
                    "owa_weight": float(weight),
                    "weighted_contribution": float(price * weight),
                })

    price_table = pd.DataFrame(price_rows).set_index(["window", "observation"])
    values = pd.DataFrame(value_rows).set_index(["window", "profile", "rank"])
    summary = pd.DataFrame(summary_rows).set_index(["window", "profile"])
    return price_table, values, summary


def _save_worked_example_chart(prices: pd.DataFrame, summary: pd.DataFrame) -> None:
    display = summary.reset_index()
    styles = {
        "SMA": ("#222222", "--"),
        "WMA": ("#808080", ":"),
        "OWMAS optimistic": ("#2F5597", "-"),
        "OWMAS neutral": ("#5B9BD5", "-."),
        "OWMAS conservative": ("#17365D", (0, (5, 2))),
    }
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, label in zip(axes, ["strongest rise", "strongest fall"]):
        frame = display[display["window"] == label]
        x = np.arange(1, 6)
        source = prices.loc[label].sort_index()
        ax.plot(x, source["price"].to_numpy(), color="#222222", marker="o",
                linewidth=1.8, label="SPY adjusted close")
        fixed_lines = {"SMA": frame["sma"].iloc[0], "WMA": frame["wma"].iloc[0]}
        for name, value in fixed_lines.items():
            color, line_style = styles[name]
            ax.axhline(value, color=color, linestyle=line_style, linewidth=1.4,
                       label=name)
        for _, row in frame.iterrows():
            name = f"OWMAS {row['profile']}"
            color, line_style = styles[name]
            ax.axhline(row["owmas_beta_0.5"], color=color,
                       linestyle=line_style, linewidth=1.4, label=name)
        ax.set_title(
            f"{label.title()}\n{frame['start'].iloc[0]} to {frame['end'].iloc[0]}"
        )
        ax.set_xlabel("Observation in five-price window")
        ax.set_xticks(x)
        ax.grid(axis="y", color="#D9D9D9", linewidth=0.7)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Adjusted close (USD)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center", ncol=3)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.savefig(OUTPUT / "worked_example.png", dpi=180)
    plt.close(fig)


def main() -> None:
    config, prices, rf_daily = _load_inputs()
    primary_gamma = config["owmas"]["gamma_profiles"][config["owmas"]["primary_profile"]]
    positions, returns = _build_strategies(
        prices,
        rf_daily,
        short=config["signal"]["short_window"],
        long=config["signal"]["long_window"],
        beta=config["owmas"]["beta_primary"],
        gamma=primary_gamma,
        cost=config["backtest"]["transaction_cost"],
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)

    disagreement = _daily_table(
        prices, positions, returns, int(config["signal"]["short_window"])
    )
    all_positions = pd.concat(
        {"OWMAS": positions["OWMAS"], "SMA": positions["SMA"]}, axis=1
    ).astype(int)
    episodes = _episode_table(disagreement, all_positions)
    summary = _summary(disagreement, episodes, len(prices))
    by_regime = _by_regime(disagreement)
    by_year = _by_year(disagreement, prices.index)
    weight_profiles = _weight_profiles(
        config["owmas"]["gamma_profiles"], int(config["signal"]["short_window"])
    )
    worked_prices, worked_values, worked_summary = _worked_examples(
        prices,
        config["owmas"]["gamma_profiles"],
        float(config["owmas"]["beta_primary"]),
    )
    mechanism = mechanism_daily(
        prices,
        config["owmas"]["gamma_profiles"],
        [int(config["signal"]["short_window"]), int(config["signal"]["long_window"])],
        float(config["owmas"]["beta_primary"]),
    )
    mechanism_by_regime = mechanism_summary(mechanism)
    mechanism_by_window = mechanism_windows(mechanism)

    disagreement.to_csv(OUTPUT / "signal_disagreement_days.csv")
    episodes.to_csv(OUTPUT / "signal_disagreement_episodes.csv")
    summary.to_csv(OUTPUT / "signal_disagreement_summary.csv")
    by_regime.to_csv(OUTPUT / "signal_disagreement_by_regime.csv")
    by_year.to_csv(OUTPUT / "signal_disagreement_by_year.csv")
    weight_profiles.to_csv(OUTPUT / "owa_weight_profiles.csv")
    worked_prices.to_csv(OUTPUT / "worked_example_prices.csv")
    worked_values.to_csv(OUTPUT / "worked_example_values.csv")
    worked_summary.to_csv(OUTPUT / "worked_example_summary.csv")
    mechanism_by_window.to_csv(OUTPUT / "trend_conditional_mechanism_windows.csv")
    mechanism_by_regime.to_csv(OUTPUT / "trend_conditional_mechanism_summary.csv")
    _save_year_chart(by_year)
    _save_weight_chart(weight_profiles)
    _save_worked_example_chart(worked_prices, worked_summary)
    save_mechanism_chart(
        mechanism_by_regime, OUTPUT / "trend_conditional_mechanism.png"
    )

    metadata = {
        "analysis_type": "exploratory",
        "status": "post hoc descriptive analysis",
        "registered_results_changed": False,
        "config_sha256": _sha256_text(ROOT / "config.yaml"),
        "registered_run_metadata_sha256": _sha256_text(
            ROOT / "results" / "run_metadata.json"
        ),
        "regime_definition": (
            "Trailing 20-trading-day adjusted-close return: positive is rising, "
            "negative is falling, zero is flat, and the warm-up period is unavailable."
        ),
        "mechanism_regime_definition": (
            "A registered price window is rising when its fitted linear price "
            "slope is positive and falling when the slope is negative."
        ),
        "interpretation_limit": (
            "Returns on disagreement days and episodes are descriptive and do not "
            "support causal or confirmatory claims."
        ),
    }
    (OUTPUT / "exploratory_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "PASS: exploratory disagreement analysis completed; "
        f"days={len(disagreement)}, episodes={len(episodes)}"
    )


if __name__ == "__main__":
    main()
