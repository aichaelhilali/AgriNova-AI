"""UI integration with explicitly artificial schedules, no crop parameters."""

import json
from datetime import date
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[2] / "app.py"


def click(app, label):
    next(button for button in app.button if button.label == label).click().run(timeout=30)
    assert not app.exception


def test_three_fictional_demo_rotations_have_referenced_qualitative_analysis():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    click(app, "Charger un scénario de démonstration")
    click(app, "Comparer les trois rotations")
    saved = app.session_state["comparison"]
    assert len(saved["results"]) == 3
    reference, alternative1, alternative2 = saved["results"]
    assert reference["agronomy"]["sequence"][0]["same_crop"] is True
    assert alternative1["agronomy"]["cycles"][1]["taxon"] == "Vicia faba"
    assert alternative2["agronomy"]["cycles"][1]["taxon"] == "Cicer arietinum"
    for result in saved["results"]:
        assert result["is_demo"]
        assert result["agronomy"]["references"]
        assert result["agronomy"]["calendar"]["potential_bare_soil_periods"] == []
        assert result["agronomy"]["calendar"]["boundary_status"] == "unknown"
        assert not result["calculation_availability"]["etc"]
        assert result["water"] is None
        assert result["missing_information"]
    assert saved["comparability"]["ranking"] is None
    assert not saved["comparability"]["quantitative_comparison_allowed"]
    assert len(app.tabs) == 3
    encoded = json.dumps(saved, default=str, allow_nan=False)
    assert "nitrogen_fixation" in encoded
    assert len(app.get("download_button")) == 2  # empty ET0 template + comparison, no NASA loaded
    # Editing a fictional crop removes its inferred family and legume status.
    revision = app.session_state["demo_revision"]
    app.session_state[f"demo_{revision}_stages_1"] = {"edited_rows": {1: {"crop": "Unverified edited crop"}}, "added_rows": [], "deleted_rows": []}
    click(app, "Comparer les trois rotations")
    identity = app.session_state["comparison"]["results"][1]["agronomy"]["cycles"][1]
    assert identity["family"] is None and identity["legume"] is None


def artificial_frame(second_crop):
    data = pd.DataFrame({"crop": ["Blé", second_crop], "start": ["2025-01-01", "2025-01-06"],
        "end": ["2025-01-02", "2025-01-08"], "planting_date": ["2025-01-01", "2025-01-06"],
        "harvest_date": ["2025-01-02", "2025-01-08"], "crop_cycle": ["test_cycle1", "test_cycle2"],
        "kc": [float("nan"), float("nan")], "kc_source": ["", ""], "validated": [False, False],
        "growth_stage": ["", ""], "regional_applicability": ["", ""], "kc_reference_surface": ["", ""]})
    for field in ("start", "end", "planting_date", "harvest_date"):
        data[field] = pd.to_datetime(data[field])
    return data


def test_manual_boundaries_survive_demo_restore_and_are_exported_with_uncertainty():
    app = AppTest.from_file(str(APP))
    app.session_state["manual_rotation_seed"] = {f"stages_{i}": artificial_frame(crop)
        for i, crop in enumerate(["Blé", "Féverole", "Pois chiche"])}
    app.run(timeout=30)
    next(d for d in app.date_input if d.label == "Début de l’horizon commun").set_value(date(2025, 1, 1))
    next(d for d in app.date_input if d.label == "Fin de l’horizon commun").set_value(date(2025, 1, 10))
    click(app, "Comparer les trois rotations")
    saved = app.session_state["comparison"]
    for result in saved["results"]:
        gap, = result["agronomy"]["calendar"]["potential_bare_soil_periods"]
        assert gap["days"] == 3
        assert gap["actual_soil_cover"] == "unknown"
        assert result["issues"] == []
        assert result["agronomy"]["calendar"]["local_agronomic_compatibility"] == "not_verified"
    click(app, "Charger un scénario de démonstration")
    click(app, "Quitter le mode démonstration")
    click(app, "Comparer les trois rotations")
    restored = app.session_state["comparison"]
    assert [r["agronomy"]["calendar"] for r in restored["results"]] == [r["agronomy"]["calendar"] for r in saved["results"]]
    assert restored["mode"] == "farmer_input"
    json.dumps(restored, default=str, allow_nan=False)
