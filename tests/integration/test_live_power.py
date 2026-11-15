"""Opt in with AGRINOVA_LIVE_TEST=1; no synthetic observations or silent fallback."""

import os
from datetime import date
from pathlib import Path

import pytest

@pytest.mark.live
@pytest.mark.skipif(os.environ.get("AGRINOVA_LIVE_TEST") != "1", reason="Real NASA API test is explicitly opt-in")
def test_real_beni_mellal_daily_api():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py"))
    app.run(timeout=30)
    next(d for d in app.date_input if d.label == "Début de l’historique").set_value(date(2025, 1, 1))
    next(d for d in app.date_input if d.label == "Fin de l’historique").set_value(date(2025, 12, 31))
    next(b for b in app.button if b.label == "Charger les données NASA").click().run(timeout=90)
    assert not app.exception
    assert "climate_error" not in app.session_state
    result = app.session_state["climate"]
    assert len(result.daily) == 365
    assert result.daily.notna().all().all()
    assert result.provenance["url"].startswith("https://power.larc.nasa.gov/")
    assert result.provenance["time_standard"] == "UTC"
    assert len(result.provenance["payload_sha256"]) == 64
    assert result.provenance["returned_geometry"]["coordinates"][:2] == [-6.36, 32.34]
    print(result.daily.describe().to_string())
    # Exercise the actual download button and charts with real data, never mocks.
    assert len(app.get("plotly_chart")) == 2
    assert app.metric[0].value == f"{result.daily.T2M.mean():.1f} °C"
    assert app.metric[1].value == f"{result.daily.PRECTOTCORR.sum():.1f} mm"
    assert app.metric[2].value == "365/365 · 365/365"
    next(b for b in app.button if b.label == "Charger un scénario de démonstration").click().run(timeout=30)
    assert not app.exception
    assert len(app.get("plotly_chart")) == 2
    assert app.session_state["climate"].daily.equals(result.daily)
    next(b for b in app.button if b.label == "Comparer les trois rotations").click().run(timeout=30)
    assert not app.exception
    assert all(r["water"] is None for r in app.session_state["comparison"]["results"])
    assert app.session_state["comparison"]["climate_provenance"] == result.provenance
    assert len(app.get("download_button")) == 5
    next(b for b in app.button if b.label == "Calculer l’ET₀ FAO-56 avec NASA POWER").click().run(timeout=90)
    assert not app.exception
    derived = app.session_state["nasa_eto_result"]
    assert len(derived.daily) == 365
    assert derived.provenance["expected_days"] == 365
    assert derived.provenance["available_days"] > 0
    assert derived.provenance["available_days"] + derived.provenance["missing_days"] == 365
    assert (derived.daily.eto_mm.dropna() >= 0).all()
    assert derived.daily.loc[derived.daily.eto_mm.isna(), "reason"].str.len().gt(0).all()
    assert derived.provenance["source_payload_sha256"] == result.provenance["payload_sha256"]
    assert len(app.get("download_button")) == 7
    print("Real POWER ET0 availability:", derived.provenance["available_days"], "/365")
    print("Unavailable dates:", derived.provenance["unavailable_dates"])
    print(derived.daily.loc[derived.daily.eto_mm.isna(), "reason"].value_counts().to_string())
