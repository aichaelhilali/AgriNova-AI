from pathlib import Path

import requests
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[2] / "app.py"


def test_app_starts_without_network_or_fabricated_data():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    assert len(app.tabs) == 3
    assert "climate" not in app.session_state
    assert len(app.get("plotly_chart")) == 0
    assert next(n for n in app.number_input if n.label.startswith("Surface")).value is None


def test_empty_comparison_reports_all_three_rotations():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    next(b for b in app.button if b.label == "Comparer les trois rotations").click().run(timeout=30)
    assert not app.exception
    saved = app.session_state["comparison"]
    assert [r["name"] for r in saved["results"]] == ["Rotation actuelle", "Alternative 1", "Alternative 2"]
    assert all(r["water"] is None for r in saved["results"])
    assert all(not r["stages"] for r in saved["results"])


def test_failed_fetch_removes_stale_data_and_comparison(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.Timeout("Artificial network failure for test")
    monkeypatch.setattr(requests, "get", fail)
    app = AppTest.from_file(str(APP)).run(timeout=30)
    app.session_state["climate"] = object()  # sentinel, not climate observations
    app.session_state["comparison"] = object()
    next(b for b in app.button if b.label == "Charger les données NASA").click().run(timeout=30)
    assert not app.exception
    assert "climate" not in app.session_state
    assert "comparison" not in app.session_state
    assert "Timeout" in app.session_state["climate_error"]
    assert len(app.get("plotly_chart")) == 0


def test_farmer_can_enter_three_distinct_rotations():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    for i in range(3):
        # Explicit artificial UI test labels, not agronomic crop proposals.
        app.session_state[f"stages_{i}"] = {"edited_rows": {0: {"crop": f"Artificial UI test crop {i}",
                    "start": "2025-01-01", "end": "2025-12-31"}},
                                                 "added_rows": [], "deleted_rows": []}
    next(b for b in app.button if b.label == "Comparer les trois rotations").click().run(timeout=30)
    assert not app.exception
    results = app.session_state["comparison"]["results"]
    assert [r["stages"][0]["crop"] for r in results] == [f"Artificial UI test crop {i}" for i in range(3)]
    assert all(r["water"] is None for r in results)
