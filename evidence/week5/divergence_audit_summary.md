# Week 5 Signal-Divergence Audit

Generated: 2026-08-19T13:18:50.419705+00:00
Frozen sample: 2005-01-03 to 2025-12-30 (5,282 rows)
Registered gate: at least 5.0% divergent position-days from the nearest benchmark.

## Primary configuration

- OWMAS configuration: beta=0.5, profile=neutral
- Nearest benchmark: sma
- Divergent position-days: 4.92%
- OWMAS trades: 109
- Differing trade dates: 194
- Gate result: ESCALATE - the primary configuration is below the registered threshold.

## Pre-registered escalation

- OWMAS configuration: beta=0.75, profile=neutral
- Nearest benchmark: sma
- Divergent position-days: 2.25%
- Differing trade dates: 178
- Gate result: NO-GO / supervisor decision required

## Pre-registered profile candidates

- beta=0.75, profile=optimistic: 3.43% from nearest benchmark (sma); BELOW GATE.
- beta=0.75, profile=conservative: 2.92% from nearest benchmark (sma); BELOW GATE.
- These are already registered gamma profiles, but selecting one as the new primary configuration requires the supervisor's documented approval before performance evaluation.

## Interpretation boundary

This audit measures whether the experiment can discriminate among position series. It does not report returns, risk-adjusted performance, or hypothesis results.
