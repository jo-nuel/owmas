# Week 7 full experiment summary

Date: 23 August 2026

## Run status

The first registered performance evaluation completed successfully on 5,282
SPY trading days from 3 January 2005 to 30 December 2025. It used 10,000
bootstrap replications, seed 14487692, 95% confidence intervals, the registered
0.1% transaction cost, and the registered primary OWMAS specification.

The frozen dataset ends one trading day before the configured 31 December 2025
boundary because the original Yahoo download treated the end argument as
exclusive. The frozen data was not changed after evaluation began. Results are
therefore reported for the exact frozen range ending 30 December 2025.

## Headline result

OWMAS produced a 274.26% cumulative return, 6.50% CAGR, 0.458 Sharpe ratio,
24.60% maximum drawdown, and 11.45% annualised volatility. Its exposure was
69.22%, with 109 position changes.

Point estimates alone were mixed. OWMAS had a higher Sharpe ratio than SMA,
was effectively equal to WMA, and had a lower Sharpe ratio than EMA and
buy-and-hold. None of the four paired Sharpe differences was statistically
significant at 5%.

## Hypothesis outcomes

### H1: effectiveness

Not supported. OWMAS did not produce a statistically significant Sharpe-ratio
improvement over SMA, WMA, EMA, or buy-and-hold. Against SMA, the annualised
Sharpe difference was 0.075 with p=0.298. Against WMA it was -0.0004 with
p=0.998.

### H2: risk reduction

Mixed and not supported as a general claim against conventional benchmarks.
OWMAS volatility was 0.26 percentage points lower than SMA, with p=0.0466, but
0.33 percentage points higher than WMA, with p=0.0212. Its volatility was not
significantly different from EMA. Relative to buy-and-hold, OWMAS had both a
significantly smaller maximum drawdown and significantly lower volatility.

### H3: consistency

Not supported. No OWMAS comparison showed a statistically significant
improvement in both the median and interquartile range of rolling 252-day
Sharpe ratios.

### H4: ordered weighting

Partly supported as an activity result, not as an effectiveness result. The
optimistic, neutral, and conservative profiles produced statistically
different volatility, but their Sharpe-ratio and maximum-drawdown differences
were not significant. All three volatility p-values also remain below a simple
0.05/9 Bonferroni threshold for the nine H4 pairwise metric tests. Ordered
weighting therefore changes the strategy's risk profile, but H1 provides no
evidence that it improves risk-adjusted performance.

## Robustness context

- During the global financial crisis, EMA was the only active strategy with a
  positive return. OWMAS lost 9.63%, compared with a 37.16% buy-and-hold loss.
- During 2010-2019, OWMAS trailed EMA and buy-and-hold on Sharpe ratio.
- During 2020, OWMAS returned 16.20%, below SMA and EMA but above WMA.
- During 2022, OWMAS lost 14.19%, less than SMA, EMA, and buy-and-hold, but its
  Sharpe ratio remained negative.
- In the 2016-2025 holdout, OWMAS had a 0.714 Sharpe ratio. This was above SMA,
  WMA, and EMA point estimates, but below buy-and-hold. The holdout figures are
  descriptive and do not replace the full-period primary tests.

## Sensitivity context

The conservative profile had the strongest OWMAS point estimate, with a 0.519
Sharpe ratio and 21.80% maximum drawdown. The registered primary neutral result
remains the headline result. The conservative profile, beta 0.25, and 10/30
windows are not promoted to primary configurations because they were designated
as sensitivity checks before evaluation.

## Reproducible outputs

Run `python scripts/run_experiment.py` to regenerate all files in `results/`,
then run `python scripts/validate_experiment_outputs.py`.
