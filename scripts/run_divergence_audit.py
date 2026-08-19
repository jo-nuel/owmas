"""Run the pre-registered Week 5 signal-divergence audit.

This script computes positions only. It deliberately does not calculate or
display performance metrics, because the divergence gate precedes performance
evaluation in the registered workflow.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backtest import crossover_positions, divergence_audit
from src.signals import ema, owmas, sma, wma


EVIDENCE = ROOT / "evidence" / "week5"


def _load_inputs() -> tuple[dict, pd.Series]:
    with (ROOT / "config.yaml").open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    prices = (
        pd.read_csv(ROOT / "data" / "spy.csv", index_col="date", parse_dates=True)
        .sort_index()[config["data"]["price_field"]]
        .astype(float)
    )
    return config, prices


def _positions(
    config: dict, prices: pd.Series, beta: float, profile: str | None = None
) -> dict[str, pd.Series]:
    short = int(config["signal"]["short_window"])
    long = int(config["signal"]["long_window"])
    gamma_profiles = config["owmas"]["gamma_profiles"]
    selected_profile = profile or config["owmas"]["primary_profile"]
    gamma = float(gamma_profiles[selected_profile])

    signal_pairs = {
        "sma": (sma(prices, short), sma(prices, long)),
        "wma": (wma(prices, short), wma(prices, long)),
        "ema": (ema(prices, short), ema(prices, long)),
        f"owmas_beta_{beta:g}_{selected_profile}": (
            owmas(prices, short, beta, gamma),
            owmas(prices, long, beta, gamma),
        ),
    }
    return {
        name: crossover_positions(short_signal, long_signal)
        for name, (short_signal, long_signal) in signal_pairs.items()
    }


def _nearest_benchmark(audit: pd.DataFrame, owmas_name: str) -> pd.Series:
    rows = audit.reset_index()
    relevant = rows[(rows["strategy_a"] == owmas_name) | (rows["strategy_b"] == owmas_name)].copy()
    relevant["benchmark"] = relevant.apply(
        lambda row: row["strategy_b"] if row["strategy_a"] == owmas_name else row["strategy_a"],
        axis=1,
    )
    return relevant.sort_values("frac_days_differ").iloc[0]


def main() -> None:
    config, prices = _load_inputs()
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    beta_primary = float(config["owmas"]["beta_primary"])
    beta_escalated = float(config["divergence_audit"]["escalation_beta"])
    minimum = float(config["divergence_audit"]["min_divergent_days_frac"])
    profile = config["owmas"]["primary_profile"]

    primary_positions = _positions(config, prices, beta_primary)
    primary_name = f"owmas_beta_{beta_primary:g}_{profile}"
    primary_audit = divergence_audit(primary_positions)
    primary_audit.to_csv(EVIDENCE / "divergence_audit_primary.csv")
    nearest_primary = _nearest_benchmark(primary_audit, primary_name)

    escalated_audit = None
    nearest_escalated = None
    candidate_results = []
    if float(nearest_primary["frac_days_differ"]) < minimum:
        escalated_positions = _positions(config, prices, beta_escalated)
        escalated_name = f"owmas_beta_{beta_escalated:g}_{profile}"
        escalated_audit = divergence_audit(escalated_positions)
        escalated_audit.to_csv(EVIDENCE / "divergence_audit_escalated.csv")
        nearest_escalated = _nearest_benchmark(escalated_audit, escalated_name)
        if float(nearest_escalated["frac_days_differ"]) < minimum:
            for candidate_profile in config["owmas"]["gamma_profiles"]:
                if candidate_profile == profile:
                    continue
                candidate_positions = _positions(
                    config, prices, beta_escalated, profile=candidate_profile
                )
                candidate_name = f"owmas_beta_{beta_escalated:g}_{candidate_profile}"
                candidate_audit = divergence_audit(candidate_positions)
                candidate_audit.to_csv(
                    EVIDENCE / f"divergence_audit_candidate_{candidate_profile}.csv"
                )
                nearest_candidate = _nearest_benchmark(candidate_audit, candidate_name)
                candidate_results.append(
                    {
                        "profile": candidate_profile,
                        "beta": beta_escalated,
                        "nearest_benchmark": nearest_candidate["benchmark"],
                        "frac_days_differ": nearest_candidate["frac_days_differ"],
                        "n_differing_trades": nearest_candidate["n_differing_trades"],
                    }
                )
            pd.DataFrame(candidate_results).to_csv(
                EVIDENCE / "divergence_audit_escalation_candidates.csv", index=False
            )

    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Week 5 Signal-Divergence Audit",
        "",
        f"Generated: {now}",
        f"Frozen sample: {prices.index.min().date()} to {prices.index.max().date()} ({len(prices):,} rows)",
        f"Registered gate: at least {minimum:.1%} divergent position-days from the nearest benchmark.",
        "",
        "## Primary configuration",
        "",
        f"- OWMAS configuration: beta={beta_primary:g}, profile={profile}",
        f"- Nearest benchmark: {nearest_primary['benchmark']}",
        f"- Divergent position-days: {nearest_primary['frac_days_differ']:.2%}",
        f"- OWMAS trades: {int(nearest_primary['n_trades_a'] if nearest_primary['strategy_a'] == primary_name else nearest_primary['n_trades_b'])}",
        f"- Differing trade dates: {int(nearest_primary['n_differing_trades'])}",
    ]
    if escalated_audit is None:
        lines.extend(["- Gate result: GO - the primary configuration meets the registered threshold."])
    else:
        lines.extend(
            [
                "- Gate result: ESCALATE - the primary configuration is below the registered threshold.",
                "",
                "## Pre-registered escalation",
                "",
                f"- OWMAS configuration: beta={beta_escalated:g}, profile={profile}",
                f"- Nearest benchmark: {nearest_escalated['benchmark']}",
                f"- Divergent position-days: {nearest_escalated['frac_days_differ']:.2%}",
                f"- Differing trade dates: {int(nearest_escalated['n_differing_trades'])}",
                "- Gate result: "
                + ("GO" if float(nearest_escalated["frac_days_differ"]) >= minimum else "NO-GO / supervisor decision required"),
            ]
        )
        if candidate_results:
            lines.extend(["", "## Pre-registered profile candidates", ""])
            for candidate in candidate_results:
                result = "MEETS GATE" if candidate["frac_days_differ"] >= minimum else "BELOW GATE"
                lines.append(
                    f"- beta={candidate['beta']:g}, profile={candidate['profile']}: "
                    f"{candidate['frac_days_differ']:.2%} from nearest benchmark "
                    f"({candidate['nearest_benchmark']}); {result}."
                )
            lines.append(
                "- These are already registered gamma profiles, but selecting one as the new primary configuration requires the supervisor's documented approval before performance evaluation."
            )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "This audit measures whether the experiment can discriminate among position series. It does not report returns, risk-adjusted performance, or hypothesis results.",
        ]
    )
    summary = "\n".join(lines) + "\n"
    (EVIDENCE / "divergence_audit_summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
