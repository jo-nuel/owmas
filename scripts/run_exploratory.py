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

    disagreement.to_csv(OUTPUT / "signal_disagreement_days.csv")
    episodes.to_csv(OUTPUT / "signal_disagreement_episodes.csv")
    summary.to_csv(OUTPUT / "signal_disagreement_summary.csv")
    by_regime.to_csv(OUTPUT / "signal_disagreement_by_regime.csv")
    by_year.to_csv(OUTPUT / "signal_disagreement_by_year.csv")
    _save_year_chart(by_year)

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
