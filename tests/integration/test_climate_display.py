"""Isolated artificial parser/display cases; never application climate data."""

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from agrinova.data.power import PARAMETERS, parse_response

APP = Path(__file__).resolve().parents[2] / "app.py"


def artificial_climate(missing=False):
    # Three-day, cross-year arithmetic case, not observations or crop references.
    dates = ["20241231", "20250101", "20250102"]
    values = {"T2M": [10, 20, 30], "T2M_MIN": [5, 15, 25],
              "T2M_MAX": [15, 25, 35], "PRECTOTCORR": [1, 2, 3]}
    if missing:
        values["T2M"][1] = -999
        values["PRECTOTCORR"][2] = -999
    payload = {"header": {"fill_value": -999, "time_standard": "UTC"},
               "geometry": {"type": "Point", "coordinates": [-6.36, 32.34, 0]},
               "properties": {"parameter": {v: dict(zip(dates, values[v])) for v in PARAMETERS}},
               "parameters": {v: {"units": "mm/day" if v == "PRECTOTCORR" else "C"} for v in PARAMETERS}}
    return parse_response(payload, date(2024, 12, 31), date(2025, 1, 2), 32.34, -6.36,
                          "https://example.invalid/artificial-display-test")


@pytest.mark.parametrize("missing", [False, True])
def test_climate_metrics_and_period_labels(missing):
    app = AppTest.from_file(str(APP))
    app.session_state["climate"] = artificial_climate(missing)
    app.session_state["climate_period_kind"] = "Saison agricole"
    app.run(timeout=30)
    assert not app.exception
    # Independent arithmetic: (10+20+30)/3 = (10+30)/2 = 20 °C.
    assert app.metric[0].value == "20.0 °C"
    assert app.metric[1].value == ("Indisponible : lacunes" if missing else "6.0 mm")
    assert app.metric[2].value == ("2/3 · 2/3" if missing else "3/3 · 3/3")
    assert len(app.get("plotly_chart")) == 2
    assert any("32.3400°" in m.value and "-6.3600°" in m.value
               and "2024-12-31 → 2025-01-02" in m.value for m in app.markdown)
    assert any("Saison agricole" in c.value for c in app.caption)
    assert any("ne représente pas l’eau disponible pour l’irrigation" in w.value for w in app.warning)
    assert next(d for d in app.date_input if d.label == "Début de l’horizon commun").value == date(2024, 12, 31)
    assert next(d for d in app.date_input if d.label == "Fin de l’horizon commun").value == date(2025, 1, 2)


def test_all_missing_mean_is_not_zero():
    data = artificial_climate()
    data.daily["T2M"] = float("nan")
    app = AppTest.from_file(str(APP))
    app.session_state["climate"] = data
    app.run(timeout=30)
    assert not app.exception
    assert app.metric[0].value == "Indisponible"
    assert app.metric[1].value == "6.0 mm"
    assert app.metric[2].value == "0/3 · 3/3"


def test_season_has_no_invented_dates_and_requires_both_bounds(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Missing season dates must not reach NASA")
    monkeypatch.setattr("requests.get", unexpected)
    app = AppTest.from_file(str(APP)).run(timeout=30)
    next(s for s in app.selectbox if s.label == "Cadre de l’analyse").select("Saison agricole").run(timeout=30)
    dates = [d for d in app.date_input if "historique" in d.label]
    assert all(d.value is None for d in dates)
    next(b for b in app.button if b.label == "Charger les données NASA").click().run(timeout=30)
    assert not app.exception
    assert "climate" not in app.session_state
    assert "Renseignez le début et la fin" in app.session_state["climate_error"]


def test_leap_year_coverage_uses_366_days():
    data = artificial_climate()
    # Reindexing creates missing days, not synthetic observations.
    import pandas as pd
    data.daily = data.daily.reindex(pd.date_range("2024-01-01", "2024-12-31"))
    data.provenance.update(start="2024-01-01", end="2024-12-31")
    app = AppTest.from_file(str(APP))
    app.session_state["climate"] = data
    app.run(timeout=30)
    assert not app.exception
    assert app.metric[2].value == "1/366 · 1/366"
    assert app.metric[1].value == "Indisponible : lacunes"
