# Week 6 statistical validation

Date: 22 August 2026

## Result

`src/stats.py` now provides:

- a paired, studentized circular-block bootstrap test for a difference in
  Sharpe ratios
- joint stationary-bootstrap confidence intervals using `arch`
- fixed-seed reproducibility and automatic block-length selection

The reference fixture contains the 120 monthly mutual-fund return pairs used
by Ledoit and Wolf. Its means, standard deviations, and Sharpe ratios match
Table 2 of the paper. With the paper's calibrated block size of four and 4,999
replications, the Python implementation returns a two-sided p-value of 6.62%.
The authors' current R/Parzen reference reports 7.0%; the small difference is
within bootstrap Monte Carlo variation from the random seed.

`scripts/validate_stats.py` also confirms that repeated calls with seed
14487692 are identical and that stationary resampling preserves the paired
time indices across strategies.

Sources:

- Paper and official code: https://www.econ.uzh.ch/en/people/faculty/wolf/publications.html
- `arch` stationary bootstrap: https://arch.readthedocs.io/en/stable/bootstrap/generated/arch.bootstrap.StationaryBootstrap.html

## Decision

The Week 6 inference functions are ready for the full experiment. No
performance result was generated during validation.
