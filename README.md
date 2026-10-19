# Design and Evaluation of an Ordered Weighted Moving Average Signal for Risk-Aware Equity Trading Decision Making

[![Tests](https://github.com/jo-nuel/owmas/actions/workflows/tests.yml/badge.svg)](https://github.com/jo-nuel/owmas/actions/workflows/tests.yml)

This repository contains the code and evidence for Jonathan Immanuel's UTS Honours research project, supervised by Professor José M. Merigó.

Repository: https://github.com/jo-nuel/owmas

The study tests whether an Ordered Weighted Moving Average Signal (OWMAS) improves risk adjusted performance compared with SMA, WMA, EMA, and buy and hold. All active strategies use the same SPY data, 20 and 50 day crossover rule, next day execution, transaction costs, and cash return.

## Main result

The registered OWMAS did not produce a statistically significant Sharpe ratio improvement over the benchmarks. It reduced risk compared with buy and hold and showed useful downside control in some periods, but the results do not support a claim of consistent outperformance.

| Strategy | CAGR | Sharpe | Volatility | Maximum drawdown |
| --- | ---: | ---: | ---: | ---: |
| OWMAS | 6.50% | 0.458 | 11.45% | -24.60% |
| SMA | 5.66% | 0.383 | 11.71% | -28.36% |
| WMA | 6.38% | 0.459 | 11.12% | -22.07% |
| EMA | 8.53% | 0.627 | 11.37% | -25.35% |
| Buy and hold | 10.69% | 0.539 | 19.05% | -55.19% |

The complete registered tables, figures, and run metadata are in [`results/`](results/). These are the outputs used in the thesis and presentation. Post hoc descriptions of signal disagreement are kept separately in [`results/exploratory/`](results/exploratory/) and are not part of the registered hypothesis tests.

## Repository structure

- `config.yaml` contains the registered settings used by the experiment.
- `data/` contains the frozen SPY and risk free datasets and the independent price cross-check.
- `src/` contains the signal, backtest, metric, and statistical functions.
- `scripts/` contains the research pipeline and its validation commands.
- `tests/` checks the signal definitions, execution timing, costs, and accounting rules.
- `validation/` adds pytest coverage for statistics and performance metric edge cases.
- `notebooks/owmas_results_demo.ipynb` is a rendered demonstration of the main tables and figures. The Week 9 checkpoint notebook is retained alongside it as coursework evidence.
- `evidence/` contains checkpoint records, coursework checks, and the Results and Discussion draft.
- `docs/decisions/` records the decision to retain the registered strategy after the divergence audit.
- `docs/CLAUDE.md` records the project working rules and disclosure requirement.

## Reproduce the results

Python 3.12 is recommended. On Windows PowerShell:

```text
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\run_experiment.py
```

On macOS or Linux:

```text
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/run_experiment.py
```

The experiment reads only the frozen datasets and `config.yaml`. It writes 17 files to `results/`. A repeated run with the registered seed produces the same values. CSV files can contain machine-level rounding differences, and PNG file bytes can vary between systems even when the plotted data are unchanged.

Run the research checks on Windows PowerShell:

```text
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts\verify_data.py
.venv\Scripts\python scripts\validate_stats.py
.venv\Scripts\python scripts\validate_experiment_outputs.py
.venv\Scripts\python scripts\run_exploratory.py
.venv\Scripts\python scripts\exploratory_monotonicity.py
.venv\Scripts\python scripts\build_demo_notebook.py
```

On macOS or Linux:

```text
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_data.py
.venv/bin/python scripts/validate_stats.py
.venv/bin/python scripts/validate_experiment_outputs.py
.venv/bin/python scripts/run_exploratory.py
.venv/bin/python scripts/exploratory_monotonicity.py
.venv/bin/python scripts/build_demo_notebook.py
```

See [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) for the frozen inputs, output checks, and interpretation limits.

I used OpenAI Codex and Anthropic Claude for coding support and debugging, documentation, thesis drafting, and formatting. I made the research decisions and checked the assisted work against the registered design, source code, 63-test suite, reference statistical result, complete experiment rerun, frozen outputs, cited papers, and supervisor feedback. The working rules are recorded in [`docs/CLAUDE.md`](docs/CLAUDE.md).

## Research safeguards

- The registered values in `config.yaml` are not changed after results are observed.
- A signal calculated at the close of day `t` is first used on day `t+1`.
- All strategy comparisons use paired dates and common trading assumptions.
- The neutral OWMAS profile remains the primary result. Sensitivity results are not promoted after inspection.
- The 2016 to 2025 late-sample subperiod is part of the same frozen dataset and is not described as an independent replication.
