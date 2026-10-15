# Exploratory signal disagreement

This folder describes when the registered OWMAS and SMA positions differ. The analysis is post hoc and descriptive. It does not change the registered configuration, primary results, or hypothesis tests.

The market regime uses the trailing 20-trading-day adjusted-close return because 20 days is the registered short signal window. A positive return is labelled rising, a negative return is falling, and the initial warm-up period is unavailable.

Run the analysis with:

```text
python scripts/run_exploratory.py
```

The daily file lists each disagreement date. The episode file groups consecutive disagreement dates when the same strategy remains invested. The regime and annual tables show where the differences occur. Returns in these files are descriptive and should not be read as new hypothesis tests.
