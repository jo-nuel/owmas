# Exploratory signal disagreement

This folder describes when the registered OWMAS and SMA positions differ. The analysis is post hoc and descriptive. It does not change the registered configuration, primary results, or hypothesis tests.

The market regime uses the trailing 20-trading-day adjusted-close return because 20 days is the registered short signal window. A positive return is labelled rising, a negative return is falling, and the initial warm-up period is unavailable.

Run the analysis with:

```text
python scripts/run_exploratory.py
```

The daily file lists each disagreement date. The episode file groups consecutive disagreement dates when the same strategy remains invested. The regime and annual tables show where the differences occur. Returns in these files are descriptive and should not be read as new hypothesis tests.

`owa_weight_profiles.csv` and its chart show how the three registered gamma profiles distribute weight across a 20-price window. Rank 1 is the largest price, not the most recent price.

The worked example uses the strongest rising and falling five-price windows in the frozen SPY sample. This transparent selection makes the ordering mechanism easy to see. It is an illustration and not evidence of typical performance. The prices file records the original dates, prices, and recency weights. The values file shows every sorted price, OWA weight, and contribution. The summary compares OWMA and OWMAS with SMA and WMA.

The trend-conditional mechanism analysis covers every complete registered 20 and 50 price window. A window is rising when its fitted linear price slope is positive and falling when it is negative. Effective recency is the average chronological position receiving the OWA weights. A positive shift means a profile places more weight on recent observations than the neutral profile. The chart tests whether this shift reverses between rising and falling windows. This is a descriptive mechanism check, not a trading performance test.

The monotonicity analysis measures each window as `1 - abs(Kendall tau)` between time and price. A value of zero describes a strictly rising or falling window. It compares each non-neutral OWMAS profile with the fixed linear filter implied by a monotone window. The gap from that linear reference increased strongly with non-monotonicity, while the optimistic-to-conservative signal gap became smaller. The analysis is exploratory and does not change the registered tests.

The context tables restate the registered H1 confidence intervals as effect-size bounds, convert H4 volatility differences to annual percentage points, compare profile return correlations and strategy exposure, and describe SPY returns over the full sample and registered subperiods. `context_summary.md` contains short interpretations that can be checked directly against those tables. The sample chart uses a log scale and marks the registered subperiods.
