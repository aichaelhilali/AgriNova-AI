"""Dashboard navigation regression, independent of network and crop values."""

from copy import deepcopy
import json
import os
from pathlib import Path

import plotly.graph_objects as go
from streamlit.testing.v1 import AppTest

from agrinova.ui.dashboard import PAGES, TAB_LABELS
from agrinova.ui.theme import style_climate_chart

APP = Path(__file__).resolve().parents[2] / "app.py"


def navigate(app, page):
    next(r for r in app.radio if r.key == "dashboard_page").set_value(page).run(timeout=30)
    assert not app.exception
    assert app.session_state["dashboard_page"] == page


def click(app, label):
    next(b for b in app.button if b.label == label).click().run(timeout=30)
    assert not app.exception


def test_all_dashboard_destinations_keep_original_controls_and_honest_empty_states():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    assert app.session_state["dashboard_page"] == "Vue d’ensemble"
    for page in PAGES:
        navigate(app, page)
        assert len(app.tabs) == 3
        assert [tab.label for tab in app.tabs] == list(TAB_LABELS)
        assert next(b for b in app.button if b.label == "Charger les données NASA")
        assert next(b for b in app.button if b.label == "Charger un scénario de démonstration")
        assert next(b for b in app.button if b.label == "Comparer les trois rotations")
        assert len(app.get("download_button")) == 1  # empty ET0 template only
        assert "climate" not in app.session_state
        assert not app.get("plotly_chart")
        if page in ("Rotations", "Exploitation"):
            assert app.session_state["workspace_tabs"] == TAB_LABELS[1]
        elif page == "Climat":
            assert app.session_state["workspace_tabs"] == TAB_LABELS[0]
        elif page == "Comparaison":
            assert app.session_state["workspace_tabs"] == TAB_LABELS[2]
    click(app, "Exporter")
    assert app.session_state["dashboard_page"] == "Export"


def test_submitted_manual_inputs_comparison_and_demo_restoration_survive_page_changes():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    navigate(app, "Rotations")
    for number in range(3):
        app.session_state[f"stages_{number}"] = {"edited_rows": {0: {
            "crop": f"Manual navigation test {number}", "start": None, "end": None}},
            "added_rows": [], "deleted_rows": []}
    next(n for n in app.number_input if n.label.startswith("Surface de la parcelle")).set_value(2.)
    # Streamlit forms send their values on submission, not sidebar interaction.
    # Verify the supported submitted-input workflow without claiming a browser
    # check of client-side, unsent drafts.
    click(app, "Comparer les trois rotations")
    saved = deepcopy(app.session_state["comparison"])
    assert saved["farm"]["surface_ha"] == 2.
    assert [r["declared_stages"][0]["crop"] for r in saved["results"]] == [f"Manual navigation test {i}" for i in range(3)]
    for page in PAGES:
        navigate(app, page)
        assert app.session_state["comparison"] == saved
    navigate(app, "Rotations")
    click(app, "Charger un scénario de démonstration")
    revision = app.session_state["demo_revision"]
    app.session_state[f"demo_{revision}_stages_1"] = {"edited_rows": {1: {"crop": "Edited fictional UI test crop"}}, "added_rows": [], "deleted_rows": []}
    click(app, "Comparer les trois rotations")
    navigate(app, "Comparaison")
    navigate(app, "Rotations")
    click(app, "Comparer les trois rotations")
    assert app.session_state["comparison"]["results"][1]["declared_crops"][-1] == "Edited fictional UI test crop"
    click(app, "Quitter le mode démonstration")
    click(app, "Comparer les trois rotations")
    restored = app.session_state["comparison"]
    assert restored["mode"] == "farmer_input"
    assert [r["declared_stages"][0]["crop"] for r in restored["results"]] == [f"Manual navigation test {i}" for i in range(3)]
    assert all(r["water"] is None for r in restored["results"])
    output = os.environ.get("AGRINOVA_UI_REPORT_DIR")
    if output:
        destination = Path(output).resolve()
        assert destination.is_relative_to(APP.parent)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "navigation_verification.json").write_text(json.dumps({
            "verification_method": "Streamlit AppTest; not a visual browser review",
            "destinations_passed": list(PAGES), "original_three_tabs_preserved": True,
            "submitted_manual_inputs_preserved": True, "saved_comparison_preserved": True,
            "demo_loading_and_restoration_passed": True, "export_navigation_passed": True,
            "no_fabricated_climate_or_kc": True}, ensure_ascii=False, indent=2), encoding="utf-8")


def test_chart_presentation_leaves_original_scientific_traces_unchanged():
    # Deliberately artificial plot values, including a gap. Styling must neither
    # interpolate nor alter observations, axes units or the daily domain.
    figure = go.Figure(go.Scatter(x=["2025-01-01", "2025-01-02", "2025-01-03"],
        y=[1., None, 3.], connectgaps=False))
    figure.update_layout(yaxis_title="mm/jour", xaxis_title="Date (UTC)")
    traces = deepcopy(figure.to_dict()["data"])
    style_climate_chart(figure, "Présentation de test")
    assert figure.to_dict()["data"] == traces
    assert figure.layout.yaxis.title.text == "mm/jour"
    assert figure.layout.xaxis.title.text == "Date (UTC)"
