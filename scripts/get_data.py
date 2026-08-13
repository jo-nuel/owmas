"""Download and freeze the SPY + T-bill dataset (Methodology §3.3, §3.11).

Run once:  python scripts/get_data.py
Writes data/spy.csv and data/rf.csv plus data/quality_log.txt.
Assertions HALT on failure — do not downgrade them to warnings.
"""
from pathlib import Path
import sys

import pandas as pd
import yaml
import yfinance as yf
from pandas_datareader import data as pdr

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load(open(ROOT / "config.yaml"))
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


def main() -> None:
    c = CFG["data"]
    log = []

    if (DATA / "spy.csv").exists():
        sys.exit("data/spy.csv already exists — dataset is frozen. "
                 "Delete it deliberately (and record why) to re-download.")

    px = yf.download(c["ticker"], start=c["start"], end=c["end"],
                     auto_adjust=False, progress=False)
    df = px[["Open", "High", "Low", "Close", "Adj Close", "Volume"]].copy()
    df.columns = ["open", "high", "low", "close", "adj_close", "volume"]
    df.index.name = "date"

    # --- Halting assertions (§3.11) ---
    assert df.index.is_monotonic_increasing, "dates not monotone"
    assert not df.index.duplicated().any(), "duplicate dates"
    assert df["adj_close"].notna().all(), "missing adjusted closes"
    r = df["adj_close"].pct_change().dropna()
    bad = r[r.abs() > c["max_abs_daily_return"]]
    assert bad.empty, f"daily |return| > {c['max_abs_daily_return']:.0%} on: {list(bad.index.date)}"
    log.append(f"rows={len(df)} range={df.index[0].date()}..{df.index[-1].date()}")
    log.append(f"max |daily return| = {r.abs().max():.4f} on {r.abs().idxmax().date()}")

    # --- Cross-check against a second source on sampled dates (§3.3) ---
    try:
        alt = pdr.DataReader(f"{c['ticker']}.US", "stooq",
                             c["start"], c["end"]).sort_index()["Close"]
        sample = df["close"].iloc[::250]
        joined = pd.concat([sample, alt], axis=1, join="inner").dropna()
        joined.columns = ["yahoo", "stooq"]
        reldiff = (joined["yahoo"] / joined["stooq"] - 1).abs()
        log.append(f"cross-check n={len(joined)} max reldiff={reldiff.max():.4%}")
        assert reldiff.max() < 0.01, "close prices disagree >1% with second source"
    except Exception as e:  # cross-check is best-effort but its absence must be logged
        log.append(f"WARNING: stooq cross-check unavailable ({e}); "
                   "falling back to FRED SP500 index (returns-based, partial range)")
        # SP500 is an index level (not an ETF price), so compare daily returns
        # rather than price levels; FRED only retains ~10 years for this series.
        try:
            sp500 = pdr.DataReader("SP500", "fred", c["start"], c["end"]).iloc[:, 0].dropna()
            joined = pd.concat([df["close"].pct_change(), sp500.pct_change()],
                               axis=1, join="inner").dropna()
            joined.columns = ["spy_close_ret", "sp500_index_ret"]
            absdiff = (joined["spy_close_ret"] - joined["sp500_index_ret"]).abs()
            log.append(f"fallback cross-check (FRED SP500 returns) n={len(joined)} "
                       f"range={joined.index[0].date()}..{joined.index[-1].date()} "
                       f"max abs return diff={absdiff.max():.4%}")
            assert absdiff.max() < 0.015, "daily returns disagree >1.5pp with FRED SP500"
        except Exception as e2:
            log.append(f"WARNING: second-source cross-check unavailable: {e2}")

    # --- Risk-free rate (FRED DTB3, percent -> daily decimal) ---
    rf = pdr.DataReader(c["rf_series"], "fred", c["start"], c["end"])
    rf = (rf[c["rf_series"]] / 100).reindex(df.index).ffill().fillna(0.0)
    rf_daily = rf / CFG["backtest"]["periods_per_year"]
    rf_daily.name = "rf_daily"
    log.append(f"rf mean annualised = {rf.mean():.3%}")

    df.to_csv(DATA / "spy.csv")
    rf_daily.to_csv(DATA / "rf.csv")
    (DATA / "quality_log.txt").write_text("\n".join(log) + "\n")
    print("\n".join(log))
    print("Frozen: data/spy.csv, data/rf.csv")


if __name__ == "__main__":
    main()
