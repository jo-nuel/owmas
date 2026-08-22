# Week 6 data verification

Date: 22 August 2026

## Result

The frozen Yahoo SPY file is retained unchanged. Its Stooq cross-check covers
5,244 rows, or 99.28% of the frozen series. The mean absolute relative
difference is 0.0066% and the 99.9th percentile is 0.0963%.

Three Stooq close values differ by more than 0.5%:

- 16 July 2009: Yahoo 93.11, Stooq 94.1519
- 12 March 2015: Yahoo 207.10, Stooq 205.2089
- 13 March 2015: Yahoo 205.83, Stooq 208.0755

These are sparse provider-level exceptions, 0.0572% of overlapping rows, not a
systematic disagreement. The verifier now halts on coverage, mean difference,
99.9th-percentile difference, and the fraction of large exceptions. It still
prints every largest difference for manual review.

## Manual review

The 2015 Yahoo closes match the official closing values reproduced in a US SEC
exchange exhibit: 207.10 on 12 March and 205.83 on 13 March. On all three
exception dates, open, high, low, and volume agree closely between providers,
so the disagreement is isolated to the close field. The 2009 exception remains
unresolved and does not provide enough evidence to overwrite the registered
source.

Source: https://www.sec.gov/rules/sro/miax/2015/34-75448-ex3a.pdf

## Decision

Data verification passes. No frozen price, risk-free observation, signal
parameter, or backtest parameter was changed.
