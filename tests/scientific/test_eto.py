"""FAO-56 example 18 is independent published evidence, not a NASA fixture.

Reference: https://www.fao.org/4/X0490E/x0490e08.htm, example 18.
Uccle, 6 July, latitude 50°48'N, elevation 100 m; Tmax=21.5°C,
Tmin=12.3°C, RHmax=84%, RHmin=63%, wind 10 km/h at 10 m.
The published Rs=22.07 MJ/m²/day is used, rather than inventing solar data
or implementing a sunshine-based substitute. Published ET0=3.88≈3.9 mm/day.
All other fixtures below are explicitly artificial robustness tests.
"""

from copy import deepcopy

import pandas as pd
import pytest

from agrinova.analysis.eto import (EtoError, REQUIRED_POWER_UNITS, calculate_power_eto,
    fao56_daily, pressure_from_elevation, saturation_pressure, vapour_pressure_from_rh, wind_at_two_metres)
from agrinova.data.power import ClimateData


def reference_inputs():
    return dict(tmin_c=12.3, tmax_c=21.5, wind_2m_ms=wind_at_two_metres(10 / 3.6, 10),
        solar_mj_m2_day=22.07, pressure_kpa=pressure_from_elevation(100),
        actual_vapour_pressure_kpa=vapour_pressure_from_rh(12.3, 21.5, rh_min=63, rh_max=84),
        latitude_deg=50.8, day_of_year=187, elevation_m=100)


def test_fao56_published_daily_reference_example_18():
    result = fao56_daily(**reference_inputs())
    assert result["eto_mm"] == pytest.approx(3.88, abs=.01)
    assert round(result["eto_mm"], 1) == 3.9
    assert result["ra_mj_m2_day"] == pytest.approx(41.09, abs=.01)
    assert result["rn_mj_m2_day"] == pytest.approx(13.28, abs=.015)
    assert result["ea_kpa"] == pytest.approx(1.409, abs=.001)
    assert result["tmean_fao_c"] == 16.9
    assert result["wind_2m_used_ms"] == pytest.approx(2.078, abs=.001)


def test_fao56_example_5_independently_checks_humidity_branches():
    # FAO chapter 3 example 5: 18°C/82%, 25°C/54%, 1.70 kPa (eq17),
    # approximately 1.78 kPa for mean RH=68% (eq19, less desirable).
    assert vapour_pressure_from_rh(18, 25, rh_min=54, rh_max=82) == pytest.approx(1.70, abs=.01)
    assert vapour_pressure_from_rh(18, 25, rh_mean=68) == pytest.approx(1.78, abs=.01)


@pytest.fixture
def artificial_climate():
    # Not NASA observations: a two-day adapter test, using reference-case scales.
    frame = pd.DataFrame({"T2M": [16.9, 16.9], "T2M_MIN": [12.3, 12.3], "T2M_MAX": [21.5, 21.5],
        "RH2M": [73.5, 73.5], "WS2M": [2.078, 2.078], "ALLSKY_SFC_SW_DWN": [22.07, 22.07],
        "PS": [100.1, 100.1]}, index=pd.date_range("2025-07-06", periods=2))
    provenance = {"units": dict(REQUIRED_POWER_UNITS), "time_standard": "UTC", "grid_elevation_m": 100.,
        "grid_elevation_source": "Artificial adapter fixture, not a NASA measurement",
        "requested_coordinates": {"latitude": 50.8, "longitude": 4.4},
        "start": "2025-07-06", "end": "2025-07-07", "url": "https://example.invalid/eto-fixture"}
    return ClimateData(frame, provenance, {})


@pytest.mark.parametrize("variable", list(REQUIRED_POWER_UNITS))
def test_missing_meteorological_variables_remain_unavailable(variable, artificial_climate):
    artificial_climate.daily = artificial_climate.daily.drop(columns=variable)
    result = calculate_power_eto(artificial_climate)
    assert not result.complete
    assert result.daily.eto_mm.isna().all()
    assert all(variable in reason for reason in result.daily.reason)
    with pytest.raises(EtoError):
        result.available_frame()


@pytest.mark.parametrize("variable", list(REQUIRED_POWER_UNITS))
def test_invalid_or_undocumented_units_are_not_guessed(variable, artificial_climate):
    artificial_climate.provenance["units"][variable] = "invalid units"
    result = calculate_power_eto(artificial_climate)
    assert not result.complete
    assert all(variable in reason and "Unité" in reason for reason in result.daily.reason)


@pytest.mark.parametrize("variable", list(REQUIRED_POWER_UNITS))
def test_missing_daily_values_are_not_interpolated(variable, artificial_climate):
    artificial_climate.daily.loc[artificial_climate.daily.index[0], variable] = float("nan")
    result = calculate_power_eto(artificial_climate)
    assert pd.isna(result.daily.eto_mm.iloc[0])
    assert pd.notna(result.daily.eto_mm.iloc[1])
    assert variable in result.daily.reason.iloc[0]


def test_missing_day_is_reported_on_expected_daily_index(artificial_climate):
    artificial_climate.daily = artificial_climate.daily.iloc[:1]
    result = calculate_power_eto(artificial_climate)
    assert len(result.daily) == 2
    assert result.provenance["expected_days"] == 2
    assert result.provenance["available_days"] == 1
    assert result.provenance["missing_days"] == 1
    assert "Valeurs manquantes" in result.daily.reason.iloc[1]
    with pytest.raises(EtoError):
        result.available_frame()


@pytest.mark.parametrize("field,value", [("grid_elevation_m", None), ("grid_elevation_source", None), ("time_standard", "LST")])
def test_missing_elevation_provenance_or_wrong_time_standard_blocks_calculation(field, value, artificial_climate):
    artificial_climate.provenance[field] = value
    assert not calculate_power_eto(artificial_climate).complete


@pytest.mark.parametrize("variable,value", [("WS2M", -1), ("RH2M", 101), ("RH2M", -1),
    ("PS", 0), ("PS", float("inf")), ("ALLSKY_SFC_SW_DWN", -1), ("T2M_MIN", 30), ("T2M", 50)])
def test_invalid_physical_values_do_not_produce_eto(variable, value, artificial_climate):
    artificial_climate.daily.loc[artificial_climate.daily.index[0], variable] = value
    result = calculate_power_eto(artificial_climate)
    assert pd.isna(result.daily.eto_mm.iloc[0])
    assert result.daily.reason.iloc[0]


def test_explicit_kwh_to_mj_conversion_is_equivalent(artificial_climate):
    expected = calculate_power_eto(artificial_climate).daily.eto_mm.copy()
    artificial_climate.daily["ALLSKY_SFC_SW_DWN"] /= 3.6
    artificial_climate.provenance["units"]["ALLSKY_SFC_SW_DWN"] = "kW-hr/m^2/day"
    actual = calculate_power_eto(artificial_climate).daily.eto_mm
    assert actual.tolist() == pytest.approx(expected.tolist(), abs=1e-12)


def test_no_input_mutation_and_provenance_is_not_a_local_validation(artificial_climate):
    before = artificial_climate.daily.copy(deep=True)
    metadata_before = deepcopy(artificial_climate.provenance)
    result = calculate_power_eto(artificial_climate)
    assert result.complete
    assert result.available_frame().columns.tolist() == ["date", "eto_mm"]
    assert artificial_climate.daily.equals(before)
    assert artificial_climate.provenance == metadata_before
    assert "aucune validation agronomique locale" in result.provenance["validation"]
    assert result.provenance["reference_surface"] == "short_grass"


def test_documented_reference_wind_bound_keeps_source_value():
    inputs = {**reference_inputs(), "wind_2m_ms": .1}
    result = fao56_daily(**inputs)
    assert result["wind_2m_input_ms"] == .1
    assert result["wind_2m_used_ms"] == .5


def test_documented_radiation_upper_bound_keeps_source_value():
    result = fao56_daily(**{**reference_inputs(), "solar_mj_m2_day": 40})
    assert result["rs_rso_uncapped"] > 1
    assert result["rs_rso_used"] == 1
    assert result["rs_mj_m2_day"] == 40


def test_negative_result_is_unavailable_not_clipped_to_zero():
    with pytest.raises(EtoError, match="négative"):
        fao56_daily(tmin_c=10., tmax_c=10., wind_2m_ms=.5, solar_mj_m2_day=1.,
            pressure_kpa=100., actual_vapour_pressure_kpa=saturation_pressure(10),
            latitude_deg=60., day_of_year=355, elevation_m=100.)


def test_nonfinite_result_or_intermediates_are_refused():
    with pytest.raises(EtoError):
        fao56_daily(**{**reference_inputs(), "pressure_kpa": 1e308, "wind_2m_ms": 1e308})


def test_too_dark_for_radiation_equation_is_reported_without_an_arbitrary_bound(artificial_climate):
    artificial_climate.daily["ALLSKY_SFC_SW_DWN"] = 0.
    result = calculate_power_eto(artificial_climate)
    assert result.daily.eto_mm.isna().all()
    assert all("Facteur radiatif" in reason for reason in result.daily.reason)


def test_computed_eto_passes_existing_etc_metadata_contract_without_crop_defaults(artificial_climate):
    from agrinova.analysis.water import validate_eto, calculate_etc
    result = calculate_power_eto(artificial_climate)
    eto = validate_eto(result.available_frame(), "Artificial wiring test, not agricultural evidence", True,
        {"calculation_method": result.provenance["method"], "units": "mm/day", "reference_surface": "short_grass",
         "time_standard": "UTC", "location": result.provenance["location"]})
    # The coefficient is ONLY an artificial arithmetic test factor, not a crop value.
    rows = [{"crop": "Artificial arithmetic crop", "start": "2025-07-06", "end": "2025-07-07",
             "kc": .5, "kc_source": "Artificial test factor, not a crop reference", "validated": True,
             "growth_stage": "Artificial stage", "regional_applicability": "Artificial test only",
             "kc_reference_surface": "short_grass"}]
    water = calculate_etc(rows, eto)
    assert water["etc_mm"] == pytest.approx(result.daily.eto_mm.sum() * .5)
    assert water["volume_m3"] is None
