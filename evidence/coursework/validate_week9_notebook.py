"""Execute and validate the Week 9 preliminary-results notebook."""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "week9_preliminary_results.ipynb"


def main() -> None:
    os.environ.setdefault("MPLBACKEND", "Agg")
    warnings.filterwarnings(
        "ignore",
        message="FigureCanvasAgg is non-interactive, and thus cannot be shown",
        category=UserWarning,
    )
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))

    assert notebook["nbformat"] == 4
    cells = notebook["cells"]
    assert cells, "Notebook contains no cells"

    full_text = "\n".join("".join(cell.get("source", [])) for cell in cells)
    required_markers = [
        "Main performance table",
        "Sharpe-ratio significance tests",
        "Full-sample equity curves",
        "Full-sample drawdowns",
        "performance_metrics.csv",
        "h1_sharpe_tests.csv",
        "equity_curves.csv",
        "drawdowns.csv",
    ]
    missing = [marker for marker in required_markers if marker not in full_text]
    assert not missing, f"Notebook is missing required Week 9 content: {missing}"

    namespace: dict[str, object] = {"__name__": "__notebook__"}
    original_cwd = Path.cwd()
    try:
        os.chdir(ROOT)
        for index, cell in enumerate(cells):
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell.get("source", []))
            try:
                exec(compile(source, f"{NOTEBOOK.name}:cell-{index}", "exec"), namespace)
            except Exception as exc:
                raise AssertionError(f"Notebook code cell {index} failed") from exc
    finally:
        os.chdir(original_cwd)

    performance = namespace["performance"]
    sharpe_tests = namespace["sharpe_tests"]
    assert len(performance) == 5
    assert abs(float(performance.loc["OWMAS", "sharpe"]) - 0.4582901949430193) < 1e-12
    assert len(sharpe_tests) == 4
    registered = sharpe_tests[sharpe_tests["comparison"].isin(
        ["OWMAS - SMA", "OWMAS - WMA", "OWMAS - EMA"]
    )]
    assert not (registered["p_value_two_sided"] < 0.05).any()
    assert not (sharpe_tests["p_value_two_sided"] < 0.05).any()
    assert "three registered moving-average comparisons" in full_text

    print("PASS: Week 9 notebook contains all required sections and every code cell executes")


if __name__ == "__main__":
    main()
