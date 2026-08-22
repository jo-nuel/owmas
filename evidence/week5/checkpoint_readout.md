# Week 5 Supervisor Checkpoint Readout

## Decision requested

The registered primary OWMAS configuration does not clear the 5% signal-divergence gate. The supervisor must decide whether to revise the signal design under a documented protocol deviation or continue with the current design while explicitly treating the limited divergence as a likely constraint on statistical power.

No return, Sharpe-ratio, drawdown, or other performance result has been computed for this checkpoint.

## Decision recorded on 22 August 2026

The supervisor approved continuation and left the choice among the three proposed paths to the student. Option 1 was selected: preserve the registered beta=0.50 neutral configuration, report the 4.92% divergence from SMA as a limitation and substantive finding, and continue with the registered performance evaluation without tuning the primary signal.

No registered parameter was changed. The full decision record is in `supervisor_decision.md`.

## Implementation status

- SMA, WMA, EMA, OWA weights, orness and OWMAS are implemented.
- The t+1 crossover rule is implemented by shifting the close-of-day signal one trading day.
- Strategy accounting applies asset returns while invested, Treasury-bill yield while in cash, and 0.1% cost on each position change.
- Buy-and-hold is charged once on its initial purchase.
- Cumulative return, CAGR, annualised volatility, Sharpe, Sortino, maximum drawdown, exposure and rolling Sharpe functions are implemented.
- The divergence audit reports pairwise position-day differences and trade-event differences.

## Validation log

- Signal identities: **11 passed**.
- Backtest/accounting tests excluding the disputed timing assertion: **5 passed**.
- Frozen-data halting assertions: **passed** (ordered unique dates, no missing or non-positive prices, maximum absolute daily return 14.52% below the registered 20% threshold, risk-free series aligned and complete).
- Independent metric known-answer checks: **passed**.
- Full repository suite: **16 passed, 1 failed**.

### Disputed timing assertion

The failing test compares dates of raw-signal changes with dates of executed-position changes and assumes the two sets can never overlap. In the fixed random series, the raw signal changes on both Friday 7 May 2010 and Monday 10 May 2010. Under the registered t+1 rule, Friday's change is executed on Monday, which legitimately coincides with Monday's new close-of-day signal. The test therefore reports a false positive even though the truncation/no-look-ahead test passes.

Changing the implementation to a two-day delay would make this test pass but would violate the registered t+1 timing rule. The implementation has not been altered to accommodate the faulty assertion. The recommended resolution is to obtain supervisor approval to replace this assertion with a direct identity check: `position[t] == raw_signal[t-1]`.

## Divergence-gate result

| Configuration | Nearest benchmark | Divergent position-days | Gate |
|---|---:|---:|---:|
| beta=0.50, neutral | SMA | 4.92% | Escalate |
| beta=0.75, neutral | SMA | 2.25% | Below gate |
| beta=0.75, optimistic | SMA | 3.43% | Below gate |
| beta=0.75, conservative | SMA | 2.92% | Below gate |

The registered beta escalation moves the neutral configuration closer to SMA because gamma=1 gives equal ordered weights, making the ordered component the arithmetic mean. Increasing beta therefore increases the SMA contribution. The two registered extreme profiles also remain below the 5% gate at beta=0.75.

## Recommended supervisor discussion

1. Confirm the t+1 implementation and approve correction of the faulty test assertion.
2. Confirm that the primary divergence gate failed by a small margin (4.92% versus 5%).
3. Decide whether the study should:
   - preserve the primary design and report limited signal divergence as a substantive finding;
   - adopt a documented protocol deviation that changes the weighting profile or signal construction; or
   - revise the research question toward whether OWMAS is operationally distinguishable from conventional averages.
4. Record the decision before any performance evaluation is run.

## Evidence files

- `divergence_audit_primary.csv`
- `divergence_audit_escalated.csv`
- `divergence_audit_candidate_optimistic.csv`
- `divergence_audit_candidate_conservative.csv`
- `divergence_audit_escalation_candidates.csv`
- `divergence_audit_summary.md`
