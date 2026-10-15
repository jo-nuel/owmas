# CLAUDE.md: working rules for this repository

This is the code for an Honours thesis (UTS, Bachelor of Computing Science).
It implements and evaluates the OWMAS trading signal against conventional
moving averages, following a **pre-registered** methodology. The thesis is
assessed partly on the correctness and quality of this code, and the student
must be able to explain and defend every line of it.

Read these rules before making any change.

## What this project is

OWMAS is the OWAWMA operator of Merigó and Yager (2019) applied to a rolling
window of SPY prices, and evaluated as a rule-based trading signal against
SMA, WMA, EMA, and buy and hold on daily SPY data from 2005 to 2025.

The scientific claim is not "OWMAS wins". It is that the comparison is *fair
and correctly measured*. A null result is a valid, reportable outcome. Never
write code, or suggest changes, whose effect is to make OWMAS look better.

## Hard rules

1. **Do not edit `config.yaml` values.** Every parameter in it is
   pre-registered: fixed in advance of evaluation so results cannot be the
   product of searching. Changing one silently invalidates the study. If a
   value genuinely needs to change, stop and tell the user it must be
   recorded as a documented protocol deviation.

2. **Do not edit anything in `tests/`.** The validation harness is the
   independent check on the implementation. If a test fails, the
   implementation is wrong. Fix the implementation. The single exception is
   the trade-count bracket in `test_sine_wave_crossovers_known_answer`, which
   was estimated rather than computed; if a correct implementation misses it
   narrowly, say so explicitly rather than adjusting it quietly.

3. **Never hard-code a parameter** that exists in `config.yaml`. Read it from
   config. This is what makes pre-registration auditable.

4. **Do not re-download or modify the frozen dataset.** `data/spy.csv` is a
   fixed research artifact. `scripts/get_data.py` refuses to overwrite it by
   design.

5. **No look-ahead, ever.** Signals computed at time *t* apply to positions at
   *t+1*. Any change touching signal or position logic must keep
   `test_truncation_does_not_change_history` passing.

6. **The student writes the core science.** `src/signals.py`,
   `src/backtest.py`, and `src/metrics.py` are the thesis contribution and
   should be authored by the student. Assist with debugging, review,
   explanation, plotting, and documentation. If asked to write those modules
   outright, say why that is a problem first, then respect the decision.

7. **Disclosure.** All AI assistance is declared in the thesis AI use
   statement. Keep changes reviewable and explainable. Avoid clever one-liners
   the author would struggle to defend.

## Build order

Work in this sequence. Do not skip ahead to performance numbers.

1. `python scripts/get_data.py`: freeze the dataset and write the quality log.
2. Complete `src/signals.py` until `pytest tests/test_signals.py` passes.
   Implement `owmas` via the separable form of Merigó and Yager (2019) Eq. (4):
   `OWMAS = beta * OWMA + (1 - beta) * WMA`. It is simpler and less
   error-prone than tracking the sigma(j) index mapping directly.
3. Complete `src/backtest.py` and `src/metrics.py` until
   `pytest tests/test_backtest.py` passes.
4. **Signal-divergence audit:** the go or no-go gate. Count days on which each
   pair of strategies holds different positions. If OWMAS diverges from its
   nearest benchmark on fewer than 5% of days, apply the pre-registered
   escalation (`divergence_audit.escalation_beta`) and run the audit again.
   Report the result either way.
5. Complete `src/stats.py`. Validate Ledoit-Wolf against a published example
   before trusting it. Use `arch` for the stationary bootstrap rather than
   writing a resampler.
6. Run the full experiment: tables, figures, subperiods, rolling Sharpe,
   late-sample analysis, and the sensitivity grid.

**No performance metric is computed or reported before step 3 passes.**

## Conventions

- Pure functions in `src/`: no I/O, no globals, no hidden state.
- pandas Series indexed by date; return NaN during window warm-up.
- OWA weights `v` are indexed over values sorted in descending order. `v[0]`
  weights the largest observation.
- Sharpe and Sortino use excess returns over `rf_daily`; annualise with
  `periods_per_year` from config (252).
- Fix the random seed from `config.yaml` for anything stochastic.
- Data assertions stop the run. A check that prints and continues is not a
  check.

## Commands

```text
python -m pip install -r requirements.txt
python scripts/get_data.py
python -m pytest -q
python -m pytest tests/test_signals.py -q
python scripts/validate_stats.py
python scripts/validate_experiment_outputs.py
```

## Background

The methodology is in `Assessment Task 2 - Introduction and Methods` in the
thesis folder. Section 3.4 defines OWMAS, 3.5 the signal rule, 3.7 the
backtest and divergence audit, 3.9 the statistical tests, 3.10 sensitivity,
and 3.11 the validation harness. When in doubt about intent, that document
governs, not convenience.
