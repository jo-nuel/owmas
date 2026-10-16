"""Build the rendered results demonstration notebook without Jupyter."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
NOTEBOOK = ROOT / "notebooks" / "owmas_results_demo.ipynb"


def _lines(text: str) -> list[str]:
    parts = text.splitlines(keepends=True)
    if parts and not parts[-1].endswith("\n"):
        return parts
    return parts


def _markdown(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def _code(source: str, count: int, outputs: list[dict]) -> dict:
    return {
        "cell_type": "code",
        "execution_count": count,
        "metadata": {},
        "outputs": outputs,
        "source": _lines(source),
    }


def _stream(text: str) -> dict:
    return {"name": "stdout", "output_type": "stream", "text": _lines(text)}


def _table_output(table: pd.DataFrame, count: int) -> dict:
    return {
        "data": {
            "text/html": _lines(table.to_html(border=0)),
            "text/plain": _lines(table.to_string()),
        },
        "execution_count": count,
        "metadata": {},
        "output_type": "execute_result",
    }


def _image_output(path: Path) -> dict:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "data": {"image/png": encoded},
        "metadata": {},
        "output_type": "display_data",
    }


def _performance_table() -> pd.DataFrame:
    performance = pd.read_csv(RESULTS / "performance_metrics.csv", index_col="strategy")
    table = performance.rename(columns={
        "cumulative_return": "Cumulative return",
        "cagr": "CAGR",
        "sharpe": "Sharpe",
        "sortino": "Sortino",
        "max_drawdown": "Max drawdown",
        "volatility": "Volatility",
        "exposure": "Exposure",
        "trades": "Trades",
    })[[
        "Cumulative return", "CAGR", "Sharpe", "Sortino",
        "Max drawdown", "Volatility", "Exposure", "Trades",
    ]]
    display = table.copy().astype(object)
    for column in [
        "Cumulative return", "CAGR", "Max drawdown", "Volatility", "Exposure"
    ]:
        display[column] = table[column].map(lambda value: f"{value:.2%}")
    for column in ["Sharpe", "Sortino"]:
        display[column] = table[column].map(lambda value: f"{value:.3f}")
    display["Trades"] = table["Trades"].map(lambda value: f"{int(value)}")
    return display


def _sharpe_table() -> pd.DataFrame:
    tests = pd.read_csv(RESULTS / "h1_sharpe_tests.csv")
    table = tests.rename(columns={
        "comparison": "Comparison",
        "difference": "Difference",
        "ci_low": "95% CI low",
        "ci_high": "95% CI high",
        "p_value_two_sided": "p-value",
        "block_size": "Block size",
    })[[
        "Comparison", "Difference", "95% CI low", "95% CI high",
        "p-value", "Block size",
    ]]
    display = table.copy().astype(object)
    for column in ["Difference", "95% CI low", "95% CI high", "p-value"]:
        display[column] = table[column].map(lambda value: f"{value:.4f}")
    display["Block size"] = table["Block size"].map(lambda value: f"{int(value)}")
    return display.set_index("Comparison")


def main() -> None:
    performance = _performance_table()
    sharpe = _sharpe_table()
    setup_code = """from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path.cwd()
if not (ROOT / 'results').is_dir():
    ROOT = ROOT.parent
RESULTS = ROOT / 'results'
print(f'Reading committed results from: {RESULTS.resolve()}')"""
    table1_code = """performance = pd.read_csv(RESULTS / 'performance_metrics.csv', index_col='strategy')
table1 = performance.rename(columns={
    'cumulative_return': 'Cumulative return', 'cagr': 'CAGR',
    'sharpe': 'Sharpe', 'sortino': 'Sortino',
    'max_drawdown': 'Max drawdown', 'volatility': 'Volatility',
    'exposure': 'Exposure', 'trades': 'Trades',
})[['Cumulative return', 'CAGR', 'Sharpe', 'Sortino',
    'Max drawdown', 'Volatility', 'Exposure', 'Trades']]
table1"""
    table2_code = """table2 = pd.read_csv(RESULTS / 'h1_sharpe_tests.csv').rename(columns={
    'comparison': 'Comparison', 'difference': 'Difference',
    'ci_low': '95% CI low', 'ci_high': '95% CI high',
    'p_value_two_sided': 'p-value', 'block_size': 'Block size',
})[['Comparison', 'Difference', '95% CI low', '95% CI high', 'p-value', 'Block size']]
table2.set_index('Comparison')"""
    figure_code = {
        1: """equity = pd.read_csv(RESULTS / 'equity_curves.csv', parse_dates=['date']).set_index('date')
ax = equity.plot(figsize=(11, 6), color=['#1f77b4', '#333333', '#777777', '#999999', '#b05a2b'])
ax.set_xlabel('Date'); ax.set_ylabel('Growth of $1'); ax.grid(True, alpha=0.2)
plt.tight_layout(); plt.show()""",
        2: """drawdowns = pd.read_csv(RESULTS / 'drawdowns.csv', parse_dates=['date']).set_index('date')
ax = drawdowns.plot(figsize=(11, 6), color=['#1f77b4', '#333333', '#777777', '#999999', '#b05a2b'])
ax.axhline(0.0, color='#222222', linewidth=0.7)
ax.set_xlabel('Date'); ax.set_ylabel('Drawdown'); ax.grid(True, alpha=0.2)
plt.tight_layout(); plt.show()""",
        3: """rolling = pd.read_csv(RESULTS / 'rolling_sharpe.csv', parse_dates=['date']).set_index('date')
ax = rolling.plot(figsize=(11, 6), color=['#1f77b4', '#333333', '#777777', '#999999', '#b05a2b'])
ax.axhline(0.0, color='#222222', linewidth=0.7)
ax.set_xlabel('Date'); ax.set_ylabel('Rolling 252-day Sharpe'); ax.grid(True, alpha=0.2)
plt.tight_layout(); plt.show()""",
    }
    cells = [
        _markdown(
            "# OWMAS results demonstration\n\n"
            "This notebook rebuilds the two main tables and three registered figures "
            "from the committed result files. It does not change the experiment, data, "
            "or registered settings.\n"
        ),
        _code(setup_code, 1, [_stream("Reading committed results from: results\n")]),
        _markdown(
            "## Table 1. Full-sample performance\n\n"
            "Returns, risk, and exposure are percentages. Sharpe and Sortino ratios "
            "are annualised.\n"
        ),
        _code(table1_code, 2, [_table_output(performance, 2)]),
        _markdown(
            "## Table 2. Paired Sharpe-ratio tests\n\n"
            "The 95% intervals include zero for all comparisons, so the registered "
            "results do not support a Sharpe improvement.\n"
        ),
        _code(table2_code, 3, [_table_output(sharpe, 3)]),
        _markdown("## Figure 1. Growth of one dollar\n"),
        _code(figure_code[1], 4, [_image_output(RESULTS / "equity_curves.png")]),
        _markdown("## Figure 2. Full-sample drawdowns\n"),
        _code(figure_code[2], 5, [_image_output(RESULTS / "drawdowns.png")]),
        _markdown("## Figure 3. Rolling 252-day Sharpe ratios\n"),
        _code(figure_code[3], 6, [_image_output(RESULTS / "rolling_sharpe.png")]),
        _markdown(
            "## Reading the result\n\n"
            "OWMAS had a higher full-sample Sharpe estimate than SMA, was effectively "
            "tied with WMA, and was below EMA. None of those differences was "
            "statistically significant at the 5% level. The main result is therefore "
            "a transparent null finding rather than evidence of consistent "
            "outperformance.\n"
        ),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
            "owmas_demo": {
                "rendered": True,
                "source_files": [
                    "results/performance_metrics.csv",
                    "results/h1_sharpe_tests.csv",
                    "results/equity_curves.csv",
                    "results/drawdowns.csv",
                    "results/rolling_sharpe.csv",
                ],
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
    print(f"PASS: rendered notebook written to {NOTEBOOK.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
