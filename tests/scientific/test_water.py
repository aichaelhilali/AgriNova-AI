"""Pure arithmetic examples; these are NOT agricultural reference values."""

import pandas as pd
import pytest

from agrinova.analysis.water import WaterInputError, calculate_etc, validate_eto


def artificial_stages():
    return [{"crop": "Artificial unit-test crop", "start": "2025-01-01", "end": "2025-01-02",
             "kc": 0.5, "kc_source": "Artificial arithmetic test; not an agricultural reference", "validated": True,
             "growth_stage": "Artificial test stage", "regional_applicability": "Artificial test only, no local validation",
             "kc_reference_surface": "short_grass"}]


def artificial_eto():
    return pd.DataFrame({"date": ["2025-01-01", "2025-01-02"], "eto_mm": [2, 4]})


def test_daily_multiplication_and_unit_conversion(eto_metadata):
    eto = validate_eto(artificial_eto(), "Artificial arithmetic test", True, eto_metadata)
    result = calculate_etc(artificial_stages(), eto, 2)
    # Independently: (2 × .5) + (4 × .5) = 3 mm; 3 × 2 ha × 10 = 60 m³.
    assert result["etc_mm"] == 3
    assert result["volume_m3"] == 60
    assert result["days"] == 2


def test_missing_surface_does_not_invent_volume(eto_metadata):
    eto = validate_eto(artificial_eto(), "Artificial arithmetic test", True, eto_metadata)
    assert calculate_etc(artificial_stages(), eto)["volume_m3"] is None


@pytest.mark.parametrize("source,validated", [("", True), ("reference", False)])
def test_eto_requires_declared_validation_and_source(source, validated):
    with pytest.raises(WaterInputError):
        validate_eto(artificial_eto(), source, validated)


@pytest.mark.parametrize("bad", [None, -1, float("inf"), "not a number"])
def test_bad_eto_rejected(bad):
    data = artificial_eto().astype({"eto_mm": "object"})
    data.loc[0, "eto_mm"] = bad
    with pytest.raises(WaterInputError):
        validate_eto(data, "Artificial reference", True)


def test_duplicate_dates_rejected():
    data = artificial_eto()
    data.loc[1, "date"] = "2025-01-01"
    with pytest.raises(WaterInputError):
        validate_eto(data, "Artificial reference", True)


@pytest.mark.parametrize("mutation", ["missing_eto", "missing_day", "unvalidated_kc", "no_source", "negative_kc", "overlap", "invalid_dates"])
def test_water_calculation_refuses_insufficient_inputs(mutation, eto_metadata):
    stages = artificial_stages()
    eto = validate_eto(artificial_eto(), "Artificial reference", True, eto_metadata)
    if mutation == "missing_eto":
        eto = None
    elif mutation == "missing_day":
        eto = eto.iloc[:1]
    elif mutation == "unvalidated_kc":
        stages[0]["validated"] = False
    elif mutation == "no_source":
        stages[0]["kc_source"] = ""
    elif mutation == "negative_kc":
        stages[0]["kc"] = -1
    elif mutation == "overlap":
        stages.append(stages[0].copy())
    else:
        stages[0]["end"] = "2024-12-31"
    with pytest.raises(WaterInputError):
        calculate_etc(stages, eto)
