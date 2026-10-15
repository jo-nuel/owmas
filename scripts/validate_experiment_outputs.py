"""Deterministic checks for generated full-experiment outputs."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.metrics import max_drawdown  # noqa: E402

RESULTS = ROOT / "results"
STRATEGIES = {"OWMAS", "SMA", "WMA", "EMA", "BuyHold"}


def sha256(path: Path, *, text: bool = False) -> str:
    payload = path.read_bytes()
    if text:
        payload = payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    with open(ROOT / "config.yaml", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    with open(RESULTS / "run_metadata.json", encoding="utf-8") as handle:
        metadata = json.load(handle)

    assert metadata["bootstrap_reps"] == config["stats"]["bootstrap_reps"]
    assert metadata["seed"] == config["stats"]["seed"]
    assert metadata["confidence"] == config["stats"]["confidence"]
    assert metadata["start"] == "2005-01-03"
    assert metadata["end"] == "2025-12-30"
    assert metadata["hash_policy"] == {
        "algorithm": "sha256",
        "text_line_endings": "lf",
        "binary_and_frozen_data": "raw",
    }
    assert metadata["config_sha256"] == sha256(ROOT / "config.yaml", text=True)
    assert metadata["spy_sha256"] == sha256(ROOT / "data" / "spy.csv")
    assert metadata["rf_sha256"] == sha256(ROOT / "data" / "rf.csv")
    for name, expected in metadata["code_sha256"].items():
        assert sha256(ROOT / name, text=True) == expected, name
    for name, expected in metadata["output_sha256"].items():
        actual = sha256(RESULTS / name, text=not name.endswith(".png"))
        assert actual == expected, name

    # A first-day loss is measured from the starting capital of one dollar.
    assert np.isclose(max_drawdown(pd.Series([-0.10, 0.20])), -0.10)

    metrics = pd.read_csv(RESULTS / "performance_metrics.csv", index_col="strategy")
    assert set(metrics.index) == STRATEGIES
    assert np.isfinite(metrics.to_numpy(dtype=float)).all()
    assert (metrics["exposure"].between(0.0, 1.0)).all()
    assert (metrics["max_drawdown"] <= 0.0).all()

    h1 = pd.read_csv(RESULTS / "h1_sharpe_tests.csv", index_col="comparison")
    assert len(h1) == 4
    assert (h1["p_value_two_sided"].between(0.0, 1.0)).all()
    assert (h1["ci_low"] <= h1["difference"]).all()
    assert (h1["difference"] <= h1["ci_high"]).all()
    for comparison, row in h1.iterrows():
        benchmark = comparison.removeprefix("OWMAS - ")
        assert np.isclose(row["sharpe_owmas"], metrics.loc["OWMAS", "sharpe"])
        assert np.isclose(row["sharpe_benchmark"], metrics.loc[benchmark, "sharpe"])

    subperiod = pd.read_csv(RESULTS / "subperiod_metrics.csv")
    assert set(subperiod["period"]) == set(config["robustness"]["subperiods"])
    assert set(subperiod["strategy"]) == STRATEGIES
    assert len(subperiod) == 20

    holdout = pd.read_csv(RESULTS / "holdout_metrics.csv")
    assert set(holdout["strategy"]) == STRATEGIES
    assert len(holdout) == 5

    sensitivity = pd.read_csv(RESULTS / "sensitivity_metrics.csv")
    assert set(sensitivity["varied_element"]) == {"gamma_profile", "beta", "windows"}
    assert len(sensitivity) == 6

    required = [
        "experiment_summary.md", "equity_curves.png", "drawdowns.png",
        "rolling_sharpe.png", "h2_risk_tests.csv", "h3_rolling_tests.csv",
        "h4_profile_tests.csv",
    ]
    for filename in required:
        path = RESULTS / filename
        assert path.exists() and path.stat().st_size > 0, filename

    print("PASS: experiment schemas, registered parameters, metrics, and outputs")


if __name__ == "__main__":
    main()
