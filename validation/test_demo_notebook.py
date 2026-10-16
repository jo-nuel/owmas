"""Checks for the rendered results demonstration notebook."""
import base64
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "owmas_results_demo.ipynb"
RESULTS = ROOT / "results"


def _load() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def test_demo_notebook_is_rendered_without_errors():
    notebook = _load()
    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["owmas_demo"]["rendered"] is True
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert [cell["execution_count"] for cell in code_cells] == list(range(1, 7))
    assert all(cell["outputs"] for cell in code_cells)
    assert not any(
        output["output_type"] == "error"
        for cell in code_cells
        for output in cell["outputs"]
    )


def test_demo_tables_contain_registered_values():
    notebook = _load()
    outputs = [
        output
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
        for output in cell["outputs"]
        if output["output_type"] == "execute_result"
    ]
    rendered = "\n".join("".join(output["data"]["text/plain"]) for output in outputs)
    metrics = pd.read_csv(RESULTS / "performance_metrics.csv", index_col="strategy")
    h1 = pd.read_csv(RESULTS / "h1_sharpe_tests.csv", index_col="comparison")
    assert f"{metrics.loc['OWMAS', 'sharpe']:.3f}" in rendered
    assert f"{metrics.loc['OWMAS', 'max_drawdown']:.2%}" in rendered
    assert f"{h1.loc['OWMAS - SMA', 'difference']:.4f}" in rendered
    assert f"{h1.loc['OWMAS - SMA', 'ci_high']:.4f}" in rendered


def test_demo_figures_match_registered_png_files():
    notebook = _load()
    images = [
        base64.b64decode(output["data"]["image/png"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
        for output in cell["outputs"]
        if "image/png" in output.get("data", {})
    ]
    expected = [
        (RESULTS / "equity_curves.png").read_bytes(),
        (RESULTS / "drawdowns.png").read_bytes(),
        (RESULTS / "rolling_sharpe.png").read_bytes(),
    ]
    assert len(images) == len(expected)
    assert [hashlib.sha256(value).digest() for value in images] == [
        hashlib.sha256(value).digest() for value in expected
    ]


def test_demo_code_rebuilds_each_display_from_csv():
    notebook = _load()
    code = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    for filename in [
        "performance_metrics.csv",
        "h1_sharpe_tests.csv",
        "equity_curves.csv",
        "drawdowns.csv",
        "rolling_sharpe.csv",
    ]:
        assert filename in code


def test_demo_code_runs_in_sequence():
    import warnings

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    notebook = _load()
    namespace = {"__name__": "__main__"}
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="FigureCanvasAgg is non-interactive")
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                source = "".join(cell["source"])
                exec(compile(source, "owmas_results_demo.ipynb", "exec"), namespace)
    plt.close("all")
