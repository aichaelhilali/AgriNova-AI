"""Artificial meteorology for UI wiring, never application demo/NASA data."""

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from agrinova.analysis.eto import REQUIRED_POWER_UNITS
from agrinova.data.power import ClimateData

APP = Path(__file__).resolve().parents[2] / "app.py"


def fixture_climate():
    daily = pd.DataFrame({"T2M": [16.9, 16.9], "T2M_MIN": [12.3, 12.3], "T2M_MAX": [21.5, 21.5],
        "RH2M": [73.5, 73.5], "WS2M": [2.078, 2.078], "ALLSKY_SFC_SW_DWN": [22.07, 22.07],
        "PS": [100.1, 100.1], "PRECTOTCORR": [0., 0.]}, index=pd.date_range("2025-07-06", periods=2))
    units = {**REQUIRED_POWER_UNITS, "PRECTOTCORR": "mm/day"}
    return ClimateData(daily, {"units": units, "time_standard": "UTC", "grid_elevation_m": 100.,
        "grid_elevation_source": "Artificial software fixture, not a measurement",
        "requested_coordinates": {"latitude": 50.8, "longitude": 4.4},
        "start": "2025-07-06", "end": "2025-07-07", "url": "https://example.invalid/eto-ui-test",
        "retrieved_at_utc": "Artificial fixture", "payload_sha256": "artificial-fixture"}, {})


def click(app, label):
    next(b for b in app.button if b.label == label).click().run(timeout=30)
    assert not app.exception


def test_nasa_eto_can_feed_existing_services_only_with_explicit_choice():
    app = AppTest.from_file(str(APP))
    app.session_state["climate"] = fixture_climate()
    app.run(timeout=30)
    click(app, "Calculer l’ET₀ FAO-56 avec NASA POWER")
    assert app.session_state["nasa_eto_result"].complete
    assert len(app.get("download_button")) == 6  # 3 climate + template + 2 ET0; no comparison yet
    checkbox = next(c for c in app.checkbox if c.label == "Utiliser cette ET₀ calculée pour les rotations")
    assert checkbox.value is False
    checkbox.check().run(timeout=30)
    click(app, "Charger un scénario de démonstration")
    click(app, "Comparer les trois rotations")
    saved = app.session_state["comparison"]
    assert saved["eto_derivation"]["method"] == "FAO-56 Penman-Monteith daily eq.6"
    assert all(r["water"] is None for r in saved["results"])  # no demo dates or Kc invented
    assert len(app.get("plotly_chart")) == 2
    assert len(app.get("download_button")) == 7


def test_incomplete_eto_disables_use_without_hiding_climate_charts():
    climate = fixture_climate()
    climate.daily.loc[climate.daily.index[0], "WS2M"] = float("nan")
    app = AppTest.from_file(str(APP))
    app.session_state["climate"] = climate
    app.run(timeout=30)
    click(app, "Calculer l’ET₀ FAO-56 avec NASA POWER")
    assert not app.session_state["nasa_eto_result"].complete
    checkbox = next(c for c in app.checkbox if c.label == "Utiliser cette ET₀ calculée pour les rotations")
    assert checkbox.disabled
    assert len(app.get("plotly_chart")) == 2
    assert any("ET₀ indisponible sur la période complète" in w.value for w in app.warning)


def test_sparse_nasa_eto_is_usable_for_complete_selected_crop_season():
    import json
    from datetime import date

    climate = fixture_climate()
    climate.daily.loc[climate.daily.index[0], "WS2M"] = float("nan")
    app = AppTest.from_file(str(APP))
    app.session_state["climate"] = climate
    app.run(timeout=30)
    click(app, "Calculer l’ET₀ FAO-56 avec NASA POWER")
    next(c for c in app.checkbox if c.label == "Utiliser les jours ET₀ disponibles, avec contrôle de chaque saison").check().run(timeout=30)
    next(d for d in app.date_input if d.label == "Début de l’horizon commun").set_value(date(2025, 7, 7))
    next(d for d in app.date_input if d.label == "Fin de l’horizon commun").set_value(date(2025, 7, 7))
    for index, crop in enumerate(["Blé", "Féverole", "Pois chiche"]):
        app.session_state[f"stages_{index}"] = {"edited_rows": {0: {
            "crop": crop, "start": "2025-07-07", "end": "2025-07-07", "kc": .5,
            "growth_stage": "Artificial test only", "validated": True,
            "kc_source": "Artificial UI arithmetic, not agricultural guidance",
            "regional_applicability": "Not locally validated; software test only",
            "kc_reference_surface": "short_grass"}}, "added_rows": [], "deleted_rows": []}
    click(app, "Comparer les trois rotations")
    saved = app.session_state["comparison"]
    assert saved["comparability"]["quantitative_comparison_allowed"]
    assert all(r["water"] is not None for r in saved["results"])
    assert all(r["crop_results"][0]["coverage"]["eto_fraction"] == 1 for r in saved["results"])
    assert saved["eto_derivation"]["unavailable_dates"] == ["2025-07-06"]
    assert len(app.get("plotly_chart")) == 2
    assert len(app.get("download_button")) == 7
    json.dumps(saved, default=str, allow_nan=False)
    # Manual inputs survive the existing demo/restore workflow.
    click(app, "Charger un scénario de démonstration")
    click(app, "Quitter le mode démonstration")
    click(app, "Comparer les trois rotations")
    assert [r["stages"][0]["crop"] for r in app.session_state["comparison"]["results"]] == ["Blé", "Féverole", "Pois chiche"]
