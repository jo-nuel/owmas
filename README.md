# OWMAS — Ordered Weighted Moving Average Signal

Honours Project, UTS 31482 — Jonathan Immanuel (14487692), Supervisor: Prof. Jose M. Merigo

Empirical evaluation of an OWAWMA-based trading signal (OWMAS) against SMA, WMA, EMA,
and buy-and-hold on daily SPY data 2005–2025, per the pre-registered methodology in
`My Writing/AT2 Introduction and Methods - REVISED.docx`.

## Structure

- `config.yaml` — every pre-registered parameter (§3.4–3.7 of the methodology). Analysis
  code must read parameters from here, never hard-code them.
- `scripts/get_data.py` — downloads SPY + 3-month T-bill data, runs halting data
  assertions, writes the frozen dataset to `data/`. Run once; never re-download silently.
- `src/signals.py` — SMA, WMA, EMA, OWA weights, orness, OWMAS. **Stubs — you implement.**
- `src/backtest.py` — crossover rule, t+1 positions, costs, cash yield, equity. **Stubs.**
- `src/metrics.py` — CAGR, Sharpe, Sortino, max drawdown, volatility, exposure. **Stubs.**
- `src/stats.py` — Ledoit–Wolf Sharpe test + stationary bootstrap. **Stubs with references.**
- `tests/` — the validation harness (§3.11). Complete. Your implementations must pass
  these unmodified. `pytest -q` runs everything.

## Workflow (build order)

1. `python scripts/get_data.py` — freeze the dataset.
2. Implement `src/signals.py` until `pytest tests/test_signals.py` passes.
3. Implement `src/backtest.py` + `src/metrics.py` until `pytest tests/test_backtest.py` passes.
4. Run the signal-divergence audit (§3.7) — go/no-go checkpoint with supervisor.
5. Implement `src/stats.py`, validate Ledoit–Wolf against a published example.
6. Full experiment.

## Reproducibility

Pinned environment (`requirements.txt`), fixed bootstrap seed (in `config.yaml`),
git-tracked from first commit. Initialise with:

    git init && git add -A && git commit -m "scaffold"
