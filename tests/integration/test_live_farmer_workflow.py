"""Live manual workflow. No real farmer history, crop calendar or Kc supplied.

The dated phase uses explicitly technical climate-analysis windows only. Neither
planting/harvest dates nor a genuine phenological stage are asserted. Real NASA
values are never mocked. Optional exports are actual download payloads captured
from Streamlit's media storage, not recreated from session state.
"""

import io
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[2] / "app.py"


def click(app, label):
    next(button for button in app.button if button.label == label).click().run(timeout=90)
    assert not app.exception


def manual_rows(second_crop, dated=False, reversed_order=False):
    rows = []
    windows = [("2025-01-01", "2025-01-02"), ("2025-01-04", "2025-01-05")]
    if reversed_order:
        windows.reverse()
    for number, crop in enumerate(["Blé", second_crop]):
        rows.append({"crop": crop, "crop_cycle": f"controle_{number + 1}",
            "growth_stage": "Fenêtre technique de contrôle ; stade agronomique inconnu",
            "start": windows[number][0] if dated else None,
            "end": windows[number][1] if dated else None,
            "planting_date": None, "harvest_date": None,
            "kc": None, "kc_source": "", "validated": False,
            "regional_applicability": "", "kc_reference_surface": ""})
    return {"edited_rows": {0: rows[0]}, "added_rows": [rows[1]], "deleted_rows": []}


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("AGRINOVA_LIVE_TEST") != "1", reason="Live NASA explicitly opt-in")
def test_real_nasa_manual_farmer_workflow_and_actual_downloads(monkeypatch):
    downloads = {}
    original = MemoryMediaFileStorage.load_and_get_id

    def capture(storage, *args, **kwargs):
        identifier = original(storage, *args, **kwargs)
        media = storage.get_file(identifier)
        if media.filename:
            downloads[media.filename] = media.content
        return identifier

    monkeypatch.setattr(MemoryMediaFileStorage, "load_and_get_id", capture)
    app = AppTest.from_file(str(APP)).run(timeout=30)
    next(d for d in app.date_input if d.label == "Début de l’historique").set_value(date(2025, 1, 1))
    next(d for d in app.date_input if d.label == "Fin de l’historique").set_value(date(2025, 12, 31))
    click(app, "Charger les données NASA")
    assert "climate_error" not in app.session_state
    climate = app.session_state["climate"]
    assert climate.provenance["requested_coordinates"] == {"latitude": 32.34, "longitude": -6.36}
    assert climate.provenance["returned_geometry"]["coordinates"][:2] == [-6.36, 32.34]
    assert climate.provenance["time_standard"] == "UTC"
    assert len(climate.daily) == 365
    assert len(app.get("plotly_chart")) == 2

    # Actual widget inputs in manual mode. Profile values are software-validation
    # declarations, not measurements or an actual farmer's private information.
    next(n for n in app.number_input if n.label.startswith("Surface de la parcelle")).set_value(2.)
    next(t for t in app.text_input if t.label.startswith("Sol :")).set_value("Inconnu — aucune analyse de sol fournie")
    next(t for t in app.text_input if t.label.startswith("Irrigation :")).set_value("Disponibilité inconnue — aucune eau disponible supposée")
    next(t for t in app.text_area if t.label.startswith("Contraintes et historique")).set_value(
        "VALIDATION LOGICIELLE MANUELLE : profil et successions de test, pas un historique agricole réel. "
        "Surface fictive de 2 ha. Les dates ultérieures sont des fenêtres techniques d’analyse, "
        "pas des dates de semis/récolte ni un calendrier cultural. Aucun Kc fourni.")
    next(m for m in app.multiselect if m.label == "Vos priorités").set_value(["Réduction du risque", "Santé du sol"])
    for index, crop in enumerate(["Blé", "Féverole", "Pois chiche"]):
        app.session_state[f"stages_{index}"] = manual_rows(crop)
    click(app, "Comparer les trois rotations")
    undated = app.session_state["comparison"]
    assert undated["mode"] == "farmer_input"
    assert undated["farm"]["surface_ha"] == 2.
    assert "VALIDATION LOGICIELLE MANUELLE" in undated["farm"]["notes"]
    assert [r["name"] for r in undated["results"]] == ["Rotation actuelle", "Alternative 1", "Alternative 2"]
    for result in undated["results"]:
        assert not result.get("is_demo", False)
        assert any("dates absentes" in issue for issue in result["issues"])
        assert result["agronomy"]["calendar"]["boundary_status"] == "unknown"
        assert result["agronomy"]["calendar"]["potential_bare_soil_periods"] == []
        assert not result["climate_evidence"]
    assert undated["results"][0]["agronomy"]["sequence"][0]["same_crop"] is True
    assert undated["results"][1]["agronomy"]["cycles"][1]["family"] == "Fabaceae"
    assert undated["results"][2]["agronomy"]["cycles"][1]["taxon"] == "Cicer arietinum"
    undated_bytes = downloads["agrinova_comparison.json"]

    click(app, "Calculer l’ET₀ FAO-56 avec NASA POWER")
    eto = app.session_state["nasa_eto_result"]
    assert eto.provenance["expected_days"] == 365
    assert eto.provenance["available_days"] > 0
    assert eto.provenance["available_days"] + eto.provenance["missing_days"] == 365
    assert eto.daily.loc[eto.daily.eto_mm.isna(), "reason"].str.len().gt(0).all()
    label = "Utiliser cette ET₀ calculée pour les rotations" if eto.complete else "Utiliser les jours ET₀ disponibles, avec contrôle de chaque saison"
    next(c for c in app.checkbox if c.label == label).check().run(timeout=30)
    for index, crop in enumerate(["Blé", "Féverole", "Pois chiche"]):
        app.session_state[f"stages_{index}"] = manual_rows(crop, dated=True)
    click(app, "Comparer les trois rotations")
    saved = app.session_state["comparison"]
    assert saved["mode"] == "farmer_input"
    assert saved["eto_derivation"]["source_payload_sha256"] == climate.provenance["payload_sha256"]
    assert saved["eto_metadata"]["location"] == climate.provenance["requested_coordinates"]
    for result in saved["results"]:
        assert not result["issues"]
        assert result["water"] is None  # no coefficients or applicability invented
        assert not result["calculation_availability"]["etc"]
        assert result["statuses"]["agronomic_validation"] == "not_performed"
        assert result["coverage"]["crop_days"] == 4
        assert result["coverage"]["expected_days"] == 365
        assert not result["coverage"]["comparison_eligible"]
        assert len(result["climate_evidence"]) == 2
        for evidence in result["climate_evidence"]:
            actual = climate.daily.loc[evidence["début"]:evidence["fin"]]
            assert evidence["jours attendus"] == len(actual) == 2
            assert evidence["température moyenne °C (jours disponibles)"] == pytest.approx(actual.T2M.mean())
            assert evidence["pluie mm (complète uniquement)"] == pytest.approx(actual.PRECTOTCORR.sum())
        assert result["agronomy"]["evidence"]
        assert result["potential_benefits"]
        assert result["risks"] and result["missing_information"] and result["limitations"]
        assert result["agronomy"]["references"]
        for crop in result["crop_results"]:
            assert crop["water"] is None
            assert crop["coverage"]["expected_days"] == 2
    assert not saved["comparability"]["quantitative_comparison_allowed"]
    assert saved["comparability"]["ranking"] is None
    displayed = next(d for d in app.dataframe if "Stratégie" in d.value.columns)
    assert displayed.value["ETc des stades saisis (mm)"].isna().all()
    assert displayed.value["Volume ETc (m³)"].isna().all()
    assert "ETc des stades saisis (mm)" not in displayed.proto.column_order
    assert "Volume ETc (m³)" not in displayed.proto.column_order

    # Parse bytes that were genuinely registered by the download widgets.
    comparison_bytes = downloads["agrinova_comparison.json"]
    exported = json.loads(comparison_bytes.decode("utf-8"))
    assert exported["farm"] == saved["farm"]
    assert exported["mode"] == "farmer_input"
    assert exported["eto_source"] == exported["eto_metadata"]["source"]
    climate_csv = pd.read_csv(io.BytesIO(downloads["nasa_power_daily.csv"]), index_col=0, parse_dates=True)
    pd.testing.assert_frame_equal(climate_csv, climate.daily, check_freq=False, check_names=False)
    eto_csv = pd.read_csv(io.BytesIO(downloads["agrinova_eto_fao56_daily.csv"]), index_col=0)
    assert len(eto_csv) == 365
    assert eto_csv.eto_mm.isna().sum() == eto.provenance["missing_days"]
    assert json.loads(downloads["nasa_power_raw.json"])["header"]["time_standard"] == "UTC"
    assert json.loads(downloads["nasa_power_provenance.json"])["payload_sha256"] == climate.provenance["payload_sha256"]
    assert json.loads(downloads["agrinova_eto_fao56_provenance.json"])["available_days"] == eto.provenance["available_days"]

    # A deliberate input error must be reported, then corrected, not sorted away.
    app.session_state["stages_0"] = manual_rows("Blé", dated=True, reversed_order=True)
    click(app, "Comparer les trois rotations")
    invalid = app.session_state["comparison"]["results"][0]
    assert any("ordre chronologique" in issue for issue in invalid["issues"])
    assert invalid["water"] is None
    app.session_state["stages_0"] = manual_rows("Blé", dated=True)
    click(app, "Comparer les trois rotations")
    assert not app.session_state["comparison"]["results"][0]["issues"]
    assert len(app.get("plotly_chart")) == 2
    assert len(app.tabs) == 3

    report = {"verification": "Streamlit AppTest, no visual browser verification",
        "input_status": "Manual software-validation declarations; not a real farmer profile or crop calendar; no Kc",
        "coordinates": climate.provenance["requested_coordinates"],
        "climate_period": [climate.provenance["start"], climate.provenance["end"]],
        "climate_valid_days": climate.daily.count().to_dict(),
        "eto_available_days": eto.provenance["available_days"], "eto_expected_days": 365,
        "eto_unavailable_dates": eto.provenance["unavailable_dates"],
        "eto_unavailability_reasons": {d.date().isoformat(): reason for d, reason in eto.daily.loc[eto.daily.eto_mm.isna(), "reason"].items()},
        "etc": "Unavailable as expected: no documented Kc or applicability provided",
        "quantitative_comparison_allowed": False,
        "exports_verified": sorted(downloads), "manual_workflow": "passed",
        "error_discovered_and_fixed": "Comparison JSON eto_source was empty for computed NASA ET0; now read from validated metadata. No formula changes."}
    output = os.environ.get("AGRINOVA_VALIDATION_DIR")
    if output:
        destination = Path(output).resolve()
        assert destination.is_relative_to(APP.parent)
        destination.mkdir(parents=True, exist_ok=True)
        for name, content in downloads.items():
            (destination / name).write_bytes(content)
        (destination / "agrinova_comparison_undated.json").write_bytes(undated_bytes)
        report["eto_unavailability_reasons"] = {str(k): v for k, v in report["eto_unavailability_reasons"].items()}
        (destination / "validation_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, default=str))
