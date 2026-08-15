"""Standalone cross-check: data/spy.csv (frozen) vs a manually downloaded
second source, data/spy_stooq.csv (§3.3). Read-only — does not modify
data/spy.csv, config.yaml, or tests/.

Compares the `close` column only (not adj_close: dividend-adjustment
conventions differ between providers and would produce false alarms).

Run: python scripts/verify_data.py
Exits non-zero if the maximum relative difference exceeds 0.5%.
"""
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MAX_RELDIFF = 0.005


def _load_close(path: Path) -> pd.Series:
    df = pd.read_csv(path, index_col=0, parse_dates=True).sort_index()
    df.index.name = "date"
    close_col = next(c for c in df.columns if c.lower() == "close")
    return df[close_col].astype(float).rename("close")


def main() -> None:
    spy = _load_close(DATA / "spy.csv")
    stooq = _load_close(DATA / "spy_stooq.csv")

    joined = pd.concat([spy, stooq], axis=1, join="inner").dropna()
    joined.columns = ["spy_close", "stooq_close"]

    total_rows = len(spy)
    n = len(joined)
    reldiff = (joined["spy_close"] / joined["stooq_close"] - 1).abs()

    lines = [f"[{datetime.now(timezone.utc).isoformat()}] verify_data.py — spy.csv vs spy_stooq.csv (close, §3.3)"]
    lines.append(f"overlap n={n} coverage={n / total_rows:.2%} of {total_rows} frozen rows")

    if n == 0:
        lines.append("no overlapping dates — cannot compare")
    else:
        lines.append(f"overlap range={joined.index[0].date()}..{joined.index[-1].date()}")
        lines.append(
            f"abs reldiff: mean={reldiff.mean():.4%} "
            f"p99.9={reldiff.quantile(0.999):.4%} max={reldiff.max():.4%}"
        )
        lines.append("largest differences:")
        for date, val in reldiff.sort_values(ascending=False).head(10).items():
            row = joined.loc[date]
            lines.append(
                f"  {date.date()}  spy_close={row['spy_close']:.4f}  "
                f"stooq_close={row['stooq_close']:.4f}  reldiff={val:.4%}"
            )

    report = "\n".join(lines)
    print(report)

    with open(DATA / "quality_log.txt", "a", encoding="utf-8") as f:
        f.write("\n" + report + "\n")

    if n == 0 or reldiff.max() > MAX_RELDIFF:
        detail = "no overlap" if n == 0 else f"max relative difference {reldiff.max():.4%} exceeds {MAX_RELDIFF:.2%}"
        sys.exit(f"FAIL: {detail}")


if __name__ == "__main__":
    main()
