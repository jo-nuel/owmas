"""Run the complete pre-registered OWMAS experiment.

Outputs are written to ``results/`` and can be reproduced from the frozen
data and ``config.yaml``. This script never changes data or configuration.
"""
from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.backtest import (  # noqa: E402
    buy_and_hold_returns,
    crossover_positions,
    strategy_returns,
)
from src.metrics import (  # noqa: E402
    cagr,
    cumulative_return,
    exposure,
    max_drawdown,
    rolling_sharpe,
    sharpe,
    sortino,
    volatility,
)
from src.signals import ema, owmas, sma, wma  # noqa: E402
from src.stats import ledoit_wolf_sharpe_test, stationary_bootstrap_ci  # noqa: E402

RESULTS = ROOT / "results"
STRATEGIES = ["OWMAS", "SMA", "WMA", "EMA", "BuyHold"]


def _load_inputs() -> tuple[dict, pd.Series, pd.Series]:
    with open(ROOT / "config.yaml", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    spy = pd.read_csv(ROOT / "data" / "spy.csv", index_col="date", parse_dates=True)
    rf = pd.read_csv(ROOT / "data" / "rf.csv", index_col="date", parse_dates=True)
    prices = spy[config["data"]["price_field"]].astype(float)
    rf_daily = rf["rf_daily"].astype(float)
    prices, rf_daily = prices.align(rf_daily, join="inner")
    if prices.empty or prices.isna().any() or rf_daily.isna().any():
        raise ValueError("frozen price and risk-free series must align without gaps")
    return config, prices, rf_daily


def _build_strategies(prices: pd.Series, rf_daily: pd.Series, *, short: int,
                      long: int, beta: float, gamma: float,
                      cost: float) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    builders = {
        "SMA": lambda p, m: sma(p, m),
        "WMA": lambda p, m: wma(p, m),
        "EMA": lambda p, m: ema(p, m),
        "OWMAS": lambda p, m: owmas(p, m, beta, gamma),
    }
    positions: dict[str, pd.Series] = {}
    returns: dict[str, pd.Series] = {}
    for name, builder in builders.items():
        position = crossover_positions(builder(prices, short), builder(prices, long))
        positions[name] = position
        returns[name] = strategy_returns(position, prices, rf_daily, cost)
    positions["BuyHold"] = pd.Series(1.0, index=prices.index, name="position")
    returns["BuyHold"] = buy_and_hold_returns(prices, cost)
    return positions, returns


def _metrics(returns: dict[str, pd.Series], positions: dict[str, pd.Series],
             rf_daily: pd.Series, periods_per_year: int) -> pd.DataFrame:
    rows = []
    for name in STRATEGIES:
        ret = returns[name]
        pos = positions[name]
        rows.append({
            "strategy": name,
            "cumulative_return": cumulative_return(ret),
            "cagr": cagr(ret, periods_per_year),
            "sharpe": sharpe(ret, rf_daily, periods_per_year),
            "sortino": sortino(ret, rf_daily, periods_per_year),
            "max_drawdown": max_drawdown(ret),
            "volatility": volatility(ret, periods_per_year),
            "exposure": exposure(pos),
            "trades": int(pos.diff().abs().fillna(pos.abs()).sum()),
            "n_days": len(ret),
        })
    return pd.DataFrame(rows).set_index("strategy")


def _period_metrics(returns: dict[str, pd.Series], positions: dict[str, pd.Series],
                    rf_daily: pd.Series, periods_per_year: int,
                    periods: dict[str, list[str]]) -> pd.DataFrame:
    frames = []
    for period, (start, end) in periods.items():
        period_returns = {name: value.loc[start:end] for name, value in returns.items()}
        period_positions = {name: value.loc[start:end] for name, value in positions.items()}
        period_rf = rf_daily.loc[start:end]
        table = _metrics(period_returns, period_positions, period_rf, periods_per_year)
        table.insert(0, "period", period)
        table.insert(1, "start", period_rf.index.min().date().isoformat())
        table.insert(2, "end", period_rf.index.max().date().isoformat())
        frames.append(table.reset_index())
    return pd.concat(frames, ignore_index=True).set_index(["period", "strategy"])


def _vector(value) -> np.ndarray:
    return np.atleast_1d(np.asarray(value, dtype=float))


def _inference_rows(names: list[str], result: dict, comparison: str,
                    directions: list[str]) -> list[dict]:
    estimate = _vector(result["estimate"])
    low = _vector(result["ci_low"])
    high = _vector(result["ci_high"])
    p_value = _vector(result["p_value"])
    return [{
        "comparison": comparison,
        "metric": name,
        "estimate": estimate[i],
        "ci_low": low[i],
        "ci_high": high[i],
        "p_value": p_value[i],
        "favourable_direction": directions[i],
        "block_size": result["block_size"],
    } for i, name in enumerate(names)]


def _h1_tests(returns: dict[str, pd.Series], rf_daily: pd.Series,
              config: dict) -> pd.DataFrame:
    rows = []
    scale = np.sqrt(config["backtest"]["periods_per_year"])
    stats_config = config["stats"]
    for benchmark in STRATEGIES[1:]:
        result = ledoit_wolf_sharpe_test(
            returns["OWMAS"], returns[benchmark], rf_daily,
            stats_config["bootstrap_reps"], stats_config["seed"],
        )
        rows.append({
            "comparison": f"OWMAS - {benchmark}",
            "sharpe_owmas": result["sharpe_a"] * scale,
            "sharpe_benchmark": result["sharpe_b"] * scale,
            "difference": result["diff"] * scale,
            "ci_low": result["ci_low"] * scale,
            "ci_high": result["ci_high"] * scale,
            "p_value_two_sided": result["p_value"],
            "block_size": result["block_size"],
        })
    return pd.DataFrame(rows).set_index("comparison")


def _h2_tests(returns: dict[str, pd.Series], config: dict) -> pd.DataFrame:
    rows = []
    ppy = config["backtest"]["periods_per_year"]
    stats_config = config["stats"]
    for benchmark in STRATEGIES[1:]:
        pair = pd.concat({"OWMAS": returns["OWMAS"], benchmark: returns[benchmark]}, axis=1)

        def statistic(sample: pd.DataFrame) -> np.ndarray:
            return np.array([
                max_drawdown(sample["OWMAS"]) - max_drawdown(sample[benchmark]),
                volatility(sample["OWMAS"], ppy) - volatility(sample[benchmark], ppy),
            ])

        result = stationary_bootstrap_ci(
            pair, statistic, stats_config["bootstrap_reps"], stats_config["seed"],
            stats_config["confidence"],
        )
        rows.extend(_inference_rows(
            ["max_drawdown_difference", "volatility_difference"], result,
            f"OWMAS - {benchmark}", ["positive", "negative"],
        ))
    return pd.DataFrame(rows).set_index(["comparison", "metric"])


def _rolling_numpy(values: np.ndarray, window: int, ppy: int) -> np.ndarray:
    cumulative = np.vstack((np.zeros((1, values.shape[1])), np.cumsum(values, axis=0)))
    squares = np.vstack((np.zeros((1, values.shape[1])), np.cumsum(values ** 2, axis=0)))
    sums = cumulative[window:] - cumulative[:-window]
    sums2 = squares[window:] - squares[:-window]
    means = sums / window
    variances = np.maximum((sums2 - sums ** 2 / window) / (window - 1), 0.0)
    std = np.sqrt(variances)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratios = np.sqrt(ppy) * means / std
    ratios[~np.isfinite(ratios)] = np.nan
    return ratios


def _h3_outputs(returns: dict[str, pd.Series], rf_daily: pd.Series,
                config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    window = config["stats"]["rolling_sharpe_window"]
    ppy = config["backtest"]["periods_per_year"]
    rolling = pd.concat({
        name: rolling_sharpe(value, rf_daily, window, ppy)
        for name, value in returns.items()
    }, axis=1)
    summary = pd.DataFrame({
        "median": rolling.median(),
        "iqr": rolling.quantile(0.75) - rolling.quantile(0.25),
        "q25": rolling.quantile(0.25),
        "q75": rolling.quantile(0.75),
        "n_windows": rolling.count(),
    })

    rows = []
    stats_config = config["stats"]
    for benchmark in STRATEGIES[1:]:
        frame = pd.concat({
            "OWMAS": returns["OWMAS"], benchmark: returns[benchmark], "rf": rf_daily,
        }, axis=1)

        def statistic(sample: pd.DataFrame) -> np.ndarray:
            excess = sample[["OWMAS", benchmark]].to_numpy() - sample[["rf"]].to_numpy()
            ratios = _rolling_numpy(excess, window, ppy)
            medians = np.nanmedian(ratios, axis=0)
            iqrs = np.nanquantile(ratios, 0.75, axis=0) - np.nanquantile(ratios, 0.25, axis=0)
            return np.array([medians[0] - medians[1], iqrs[0] - iqrs[1]])

        result = stationary_bootstrap_ci(
            frame, statistic, stats_config["bootstrap_reps"], stats_config["seed"],
            stats_config["confidence"],
        )
        rows.extend(_inference_rows(
            ["rolling_sharpe_median_difference", "rolling_sharpe_iqr_difference"],
            result, f"OWMAS - {benchmark}", ["positive", "negative"],
        ))
    inference = pd.DataFrame(rows).set_index(["comparison", "metric"])
    return rolling, summary, inference


def _sensitivity(prices: pd.Series, rf_daily: pd.Series, config: dict
                 ) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    primary_short = config["signal"]["short_window"]
    primary_long = config["signal"]["long_window"]
    primary_beta = config["owmas"]["beta_primary"]
    profiles = config["owmas"]["gamma_profiles"]
    primary_profile = config["owmas"]["primary_profile"]
    cost = config["backtest"]["transaction_cost"]
    ppy = config["backtest"]["periods_per_year"]
    specifications = []
    for profile, gamma in profiles.items():
        specifications.append((f"profile_{profile}", primary_short, primary_long,
                               primary_beta, gamma, "gamma_profile"))
    for beta in config["robustness"]["sensitivity"]["beta"]:
        specifications.append((f"beta_{beta:.2f}", primary_short, primary_long,
                               beta, profiles[primary_profile], "beta"))
    alt_short, alt_long = config["robustness"]["sensitivity"]["windows_alt"]
    specifications.append((f"windows_{alt_short}_{alt_long}", alt_short, alt_long,
                           primary_beta, profiles[primary_profile], "windows"))

    rows = []
    profile_returns: dict[str, pd.Series] = {}
    for name, short, long, beta, gamma, varied in specifications:
        positions, returns = _build_strategies(
            prices, rf_daily, short=short, long=long, beta=beta, gamma=gamma, cost=cost,
        )
        ret = returns["OWMAS"]
        pos = positions["OWMAS"]
        rows.append({
            "specification": name,
            "varied_element": varied,
            "short_window": short,
            "long_window": long,
            "beta": beta,
            "gamma": gamma,
            "cumulative_return": cumulative_return(ret),
            "cagr": cagr(ret, ppy),
            "sharpe": sharpe(ret, rf_daily, ppy),
            "sortino": sortino(ret, rf_daily, ppy),
            "max_drawdown": max_drawdown(ret),
            "volatility": volatility(ret, ppy),
            "exposure": exposure(pos),
            "trades": int(pos.diff().abs().fillna(pos.abs()).sum()),
        })
        if varied == "gamma_profile":
            profile_returns[name.removeprefix("profile_")] = ret
    return pd.DataFrame(rows).set_index("specification"), profile_returns


def _h4_tests(profile_returns: dict[str, pd.Series], rf_daily: pd.Series,
              config: dict) -> pd.DataFrame:
    profiles = list(config["owmas"]["gamma_profiles"])
    pairs = list(combinations(profiles, 2))
    frame = pd.concat({**profile_returns, "rf": rf_daily}, axis=1)
    ppy = config["backtest"]["periods_per_year"]

    def statistic(sample: pd.DataFrame) -> np.ndarray:
        values = []
        for first, second in pairs:
            values.extend([
                sharpe(sample[first], sample["rf"], ppy) -
                sharpe(sample[second], sample["rf"], ppy),
                max_drawdown(sample[first]) - max_drawdown(sample[second]),
                volatility(sample[first], ppy) - volatility(sample[second], ppy),
            ])
        return np.asarray(values)

    stats_config = config["stats"]
    result = stationary_bootstrap_ci(
        frame, statistic, stats_config["bootstrap_reps"], stats_config["seed"],
        stats_config["confidence"],
    )
    names = []
    directions = []
    comparisons = []
    for first, second in pairs:
        names.extend(["sharpe_difference", "max_drawdown_difference", "volatility_difference"])
        directions.extend(["either", "either", "either"])
        comparisons.extend([f"{first} - {second}"] * 3)
    base_rows = _inference_rows(names, result, "", directions)
    for row, comparison in zip(base_rows, comparisons):
        row["comparison"] = comparison
    return pd.DataFrame(base_rows).set_index(["comparison", "metric"])


def _save_figures(returns: dict[str, pd.Series], rolling: pd.DataFrame) -> None:
    colors = {"OWMAS": "#1f77b4", "SMA": "#333333", "WMA": "#777777",
              "EMA": "#999999", "BuyHold": "#b05a2b"}
    return_frame = pd.concat(returns, axis=1)[STRATEGIES]
    equity = (1.0 + return_frame).cumprod()
    # Measure losses from the initial dollar as well as later peaks.
    drawdown = equity.div(equity.cummax().clip(lower=1.0)).sub(1.0)
    equity.to_csv(RESULTS / "equity_curves.csv")
    drawdown.to_csv(RESULTS / "drawdowns.csv")
    rolling[STRATEGIES].to_csv(RESULTS / "rolling_sharpe.csv")

    for filename, frame, ylabel, baseline in [
        ("equity_curves.png", equity, "Growth of $1", None),
        ("drawdowns.png", drawdown, "Drawdown", 0.0),
        ("rolling_sharpe.png", rolling[STRATEGIES], "Rolling 252-day Sharpe", 0.0),
    ]:
        fig, ax = plt.subplots(figsize=(11, 6))
        for name in STRATEGIES:
            ax.plot(frame.index, frame[name], label=name, color=colors[name],
                    linewidth=2.0 if name == "OWMAS" else 1.15)
        if baseline is not None:
            ax.axhline(baseline, color="#222222", linewidth=0.7)
        ax.set_xlabel("Date")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.2)
        ax.legend(ncol=5, frameon=False, loc="best")
        fig.tight_layout()
        fig.savefig(RESULTS / filename, dpi=180)
        plt.close(fig)


def _sha256(path: Path, *, text: bool = False) -> str:
    payload = path.read_bytes()
    if text:
        # Git may use different line endings on different operating systems.
        payload = payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(payload).hexdigest()


def _write_summary(metrics: pd.DataFrame, h1: pd.DataFrame, h2: pd.DataFrame,
                   h3_summary: pd.DataFrame, h3_tests: pd.DataFrame,
                   h4: pd.DataFrame) -> None:
    def markdown_table(frame: pd.DataFrame) -> str:
        display = frame.reset_index()
        headers = [str(column).replace("|", "\\|") for column in display.columns]
        rows = ["| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] * len(headers)) + " |"]
        for values in display.itertuples(index=False, name=None):
            formatted = []
            for value in values:
                if isinstance(value, (float, np.floating)):
                    cell = f"{value:.4f}"
                else:
                    cell = str(value)
                formatted.append(cell.replace("|", "\\|").replace("\n", " "))
            rows.append("| " + " | ".join(formatted) + " |")
        return "\n".join(rows)

    lines = [
        "# Registered OWMAS experiment summary",
        "",
        "This file is generated by `scripts/run_experiment.py`.",
        "",
        "## Headline metrics",
        "",
        markdown_table(metrics),
        "",
        "## H1: Sharpe effectiveness",
        "",
        markdown_table(h1),
        "",
        "## H2: risk reduction",
        "",
        markdown_table(h2),
        "",
        "## H3: rolling Sharpe consistency",
        "",
        markdown_table(h3_summary),
        "",
        markdown_table(h3_tests),
        "",
        "## H4: weighting-profile activity",
        "",
        markdown_table(h4),
        "",
        "Two-sided p-values and 95% confidence intervals are reported. Pairwise",
        "results should be interpreted with the registered direction and the",
        "study's multiplicity limitation, not from point estimates alone.",
    ]
    (RESULTS / "experiment_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    config, prices, rf_daily = _load_inputs()
    RESULTS.mkdir(exist_ok=True)
    primary_gamma = config["owmas"]["gamma_profiles"][config["owmas"]["primary_profile"]]
    positions, returns = _build_strategies(
        prices, rf_daily,
        short=config["signal"]["short_window"],
        long=config["signal"]["long_window"],
        beta=config["owmas"]["beta_primary"],
        gamma=primary_gamma,
        cost=config["backtest"]["transaction_cost"],
    )
    ppy = config["backtest"]["periods_per_year"]
    metrics = _metrics(returns, positions, rf_daily, ppy)
    h1 = _h1_tests(returns, rf_daily, config)
    h2 = _h2_tests(returns, config)
    rolling, h3_summary, h3_tests = _h3_outputs(returns, rf_daily, config)
    sensitivity, profile_returns = _sensitivity(prices, rf_daily, config)
    h4 = _h4_tests(profile_returns, rf_daily, config)

    subperiods = _period_metrics(
        returns, positions, rf_daily, ppy, config["robustness"]["subperiods"]
    )
    holdout = _period_metrics(
        returns, positions, rf_daily, ppy,
        {"holdout": config["robustness"]["holdout"]},
    )

    tables = {
        "performance_metrics.csv": metrics,
        "h1_sharpe_tests.csv": h1,
        "h2_risk_tests.csv": h2,
        "h3_rolling_summary.csv": h3_summary,
        "h3_rolling_tests.csv": h3_tests,
        "h4_profile_tests.csv": h4,
        "subperiod_metrics.csv": subperiods,
        "holdout_metrics.csv": holdout,
        "sensitivity_metrics.csv": sensitivity,
    }
    for filename, table in tables.items():
        table.to_csv(RESULTS / filename)
    _save_figures(returns, rolling)
    _write_summary(metrics, h1, h2, h3_summary, h3_tests, h4)

    code_paths = [
        "scripts/run_experiment.py",
        "src/signals.py",
        "src/backtest.py",
        "src/metrics.py",
        "src/stats.py",
    ]
    output_paths = [*tables, "equity_curves.csv", "drawdowns.csv",
                    "rolling_sharpe.csv", "equity_curves.png", "drawdowns.png",
                    "rolling_sharpe.png", "experiment_summary.md"]
    metadata = {
        "hash_policy": {
            "algorithm": "sha256",
            "text_line_endings": "lf",
            "binary_and_frozen_data": "raw",
        },
        "config_sha256": _sha256(ROOT / "config.yaml", text=True),
        "spy_sha256": _sha256(ROOT / "data" / "spy.csv"),
        "rf_sha256": _sha256(ROOT / "data" / "rf.csv"),
        "start": prices.index.min().date().isoformat(),
        "end": prices.index.max().date().isoformat(),
        "observations": len(prices),
        "bootstrap_reps": config["stats"]["bootstrap_reps"],
        "seed": config["stats"]["seed"],
        "confidence": config["stats"]["confidence"],
        "code_sha256": {
            name: _sha256(ROOT / name, text=True) for name in code_paths
        },
        "output_sha256": {
            name: _sha256(RESULTS / name, text=not name.endswith(".png"))
            for name in output_paths
        },
    }
    (RESULTS / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"PASS: full registered experiment completed; outputs={len(tables) + 8}")
    print(metrics.round(4).to_string())


if __name__ == "__main__":
    main()
