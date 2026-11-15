"""Exercise metadata inputs and partial-total presentation with artificial ET0."""

from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from agrinova.analysis.water import validate_eto
from agrinova.rotation.compare import evaluate_rotation, assess_comparability

APP = Path(__file__).resolve().parents[2] / "app.py"
SOURCE = "Artificial arithmetic test, not a crop reference"


def test_complete_metadata_flow_reaches_calculation_without_independent_validation(monkeypatch):
    monkeypatch.setattr(st, "file_uploader", lambda *a, **k: BytesIO(b"date,eto_mm\n2025-01-01,1\n2025-01-02,2\n"))
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    next(w for w in app.text_input if w.label.startswith("Source ET₀")).set_value(SOURCE)
    next(w for w in app.text_input if w.label == "Méthode de calcul de l’ET₀").set_value("Artificial method")
    for label, value in [("Unité de la série ET₀", "mm/day"), ("Surface de référence ET₀", "short_grass"),
                         ("Standard temporel de la série ET₀", "UTC")]:
        next(w for w in app.selectbox if w.label == label).select(value)
    next(w for w in app.number_input if w.label.startswith("Latitude représentée")).set_value(32.34)
    next(w for w in app.number_input if w.label.startswith("Longitude représentée")).set_value(-6.36)
    next(w for w in app.checkbox if w.label.startswith("Je confirme les références")).check()
    app.run(timeout=30)
    for i in range(3):
        app.session_state[f"stages_{i}"] = {"edited_rows": {0: {
            "crop": f"Artificial crop {i}", "start": "2025-01-01", "end": "2025-01-02", "kc": 1.,
            "kc_source": SOURCE, "validated": True, "growth_stage": "Artificial stage",
            "regional_applicability": SOURCE, "kc_reference_surface": "short_grass"}},
            "added_rows": [], "deleted_rows": []}
    next(w for w in app.date_input if w.label == "Début de l’horizon commun").set_value(date(2025, 1, 1))
    next(w for w in app.date_input if w.label == "Fin de l’horizon commun").set_value(date(2025, 1, 2))
    next(b for b in app.button if b.label == "Comparer les trois rotations").click().run(timeout=30)
    assert not app.exception
    saved = app.session_state["comparison"]
    assert saved["comparability"]["quantitative_comparison_allowed"]
    assert saved["eto_metadata"]["fao56_compliance"] == "not_verified"
    assert all(r["water"]["etc_mm"] == 3. for r in saved["results"])
    assert all(r["statuses"]["agronomic_validation"] == "not_performed" for r in saved["results"])


def test_partial_total_is_available_in_details_but_withheld_from_comparison(eto_metadata):
    eto = validate_eto(pd.DataFrame({"date": ["2025-01-01", "2025-01-02"], "eto_mm": [1., 2.]}), SOURCE, True, eto_metadata)
    results = []
    for i in range(3):
        rows = [{"crop": f"Artificial {i}", "start": "2025-01-01", "end": "2025-01-01" if i else "2025-01-02",
                 "kc": 1., "kc_source": SOURCE, "validated": True, "growth_stage": "Artificial stage",
                 "regional_applicability": SOURCE, "kc_reference_surface": "short_grass"}]
        results.append(evaluate_rotation(f"Artificial {i}", rows, {}, "2025-01-01", "2025-01-02", eto=eto))
    app = AppTest.from_file(str(APP))
    app.session_state["comparison"] = {"results": results, "comparability": assess_comparability(results),
        "mode": "farmer_input", "farm": {"priorités": []}, "calculated_at_utc": "Artificial test instant"}
    app.run(timeout=30)
    assert not app.exception
    table = next(d.value for d in app.dataframe if "Stratégie" in d.value.columns)
    assert table["ETc des stades saisis (mm)"].isna().all()
    assert results[1]["water"]["etc_mm"] == 1.
    assert any("ne peuvent pas être comparés" in w.value for w in app.warning)
    coverage = next(d.value for d in app.dataframe if "Couverture ETc (%)" in d.value.columns)
    assert coverage["Couverture ETc (%)"].tolist() == [100., 50., 50.]


def test_existing_manual_tables_survive_metadata_schema_upgrade():
    old = pd.DataFrame({"crop": ["Previously submitted artificial crop"],
        "start": pd.to_datetime(["2025-01-01"]), "end": pd.to_datetime(["2025-01-02"]),
        "kc": [None], "kc_source": [""], "validated": [False]})
    app = AppTest.from_file(str(APP))
    app.session_state["manual_rotation_snapshot"] = {"stages_0": old}
    app.run(timeout=30)
    assert not app.exception
    next(b for b in app.button if b.label == "Comparer les trois rotations").click().run(timeout=30)
    assert not app.exception
    row = app.session_state["comparison"]["results"][0]["declared_stages"][0]
    assert row["crop"] == "Previously submitted artificial crop"
    assert row["kc"] is None
    assert row["growth_stage"] == ""
    assert row["regional_applicability"] == ""
