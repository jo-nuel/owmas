# Reproducing the OWMAS results

## Fixed inputs

The experiment uses the files below without downloading replacements:

- `data/spy.csv` contains 5,282 SPY observations from 3 January 2005 to 30 December 2025.
- `data/rf.csv` contains the aligned daily risk free rate.
- `config.yaml` contains the registered signal, cost, inference, and robustness settings.

`results/run_metadata.json` records SHA-256 hashes for the inputs, analysis code, and generated outputs. `scripts/validate_experiment_outputs.py` checks these hashes.

## Environment

Create a Python 3.12 virtual environment and install the pinned packages in `requirements.txt`.

```text
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

The commands use Windows paths because the project was developed on Windows 11. The Python scripts do not depend on Windows-only libraries.

## Run the experiment

```text
.venv\Scripts\python scripts\run_experiment.py
```

The registered analysis uses 10,000 bootstrap replications and may take several minutes. It writes the result tables, chart data, figures, summary, and metadata to `results/`.

## Run the checks

```text
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts\verify_data.py
.venv\Scripts\python scripts\validate_stats.py
.venv\Scripts\python scripts\validate_experiment_outputs.py
.venv\Scripts\python scripts\validate_week9_notebook.py
.venv\Scripts\python scripts\validate_week11_draft.py
```

The data verification command prints its report without changing the repository. Use `--write-log` only when a dated verification needs to be added to `data/quality_log.txt`.

## Expected conclusion

The checks confirm that the analysis ran as registered. They do not change the interpretation. OWMAS had a full-sample Sharpe ratio of 0.458, and none of the paired Sharpe differences was statistically significant. The main result is therefore a null finding for superior risk adjusted performance.

## Limits

The study covers one US equity ETF at daily frequency. The 2016 to 2025 holdout is a temporal check within the frozen dataset, not an external replication. The sensitivity settings are supporting analyses rather than replacement primary models.
