"""Artificial coefficients/dates solely for arithmetic and workflow regression."""

import pandas as pd
import pytest

from agrinova.analysis.crop_water import computed_eto_for_crops, crop_water_results
from agrinova.analysis.eto import EtoResult
from agrinova.analysis.water import WaterInputError, validate_eto
from agrinova.rotation.compare import assess_comparability, evaluate_rotation


def stage(crop="Blé", start="2025-01-02", end="2025-01-03", kc=.5, **changes):
    return {"crop": crop, "start": start, "end": end, "kc": kc,
        "growth_stage": "Artificial test interval", "validated": True,
        "kc_source": "Artificial arithmetic only, not agricultural guidance",
        "regional_applicability": "Software testing only; not locally validated",
        "kc_reference_surface": "short_grass", **changes}


@pytest.fixture
def eto(eto_metadata):
    return validate_eto(pd.DataFrame({"date": pd.date_range("2025-01-01", periods=8),
        "eto_mm": [2., 2., 4., 6., 8., 2., 3., 4.]}), "Artificial test data", True, eto_metadata)


@pytest.mark.parametrize("crop", ["Blé", "Wheat", "Féverole", "Faba bean", "Pois chiche", "Chickpea"])
def test_stage_coefficients_daily_cumulative_and_contributions(crop, eto):
    rows = [stage(crop), stage(crop, "2025-01-04", "2025-01-05", 1., growth_stage="Second test interval")]
    report, = crop_water_results(rows, eto, 2.)
    assert report["status"] == "complete"
    water = report["water"]
    assert [d["etc_mm"] for d in water["daily"]] == [1., 2., 6., 8.]
    assert [d["cumulative_etc_mm"] for d in water["daily"]] == [1., 3., 9., 17.]
    assert [s["etc_mm"] for s in report["stages"]] == [3., 14.]
    assert water["etc_mm"] == 17.
    assert water["volume_m3"] == 340.
    assert water["daily"][2]["growth_stage"] == "Second test interval"
    assert water["daily"][2]["kc"] == 1.
    assert report["coverage"]["eto_fraction"] == 1.
    assert all(s["independent_verification"] == "not_performed" for s in report["stages"])


@pytest.mark.parametrize("missing", ["2025-01-01", "2025-01-04", "2025-01-08"])
def test_missing_dates_outside_crop_do_not_block_season(missing, eto, eto_metadata):
    sparse = eto.drop(pd.Timestamp(missing))
    sparse = validate_eto(sparse.rename_axis("date").reset_index(), "Artificial sparse source", True, eto_metadata)
    report, = crop_water_results([stage()], sparse)
    assert report["water"]["etc_mm"] == 3.
    assert report["coverage"]["missing_eto_dates"] == []


@pytest.mark.parametrize("missing", ["2025-01-02", "2025-01-03"])
def test_missing_dates_inside_crop_including_boundaries_are_exact(missing, eto):
    report, = crop_water_results([stage()], eto.drop(pd.Timestamp(missing)))
    assert report["water"] is None
    assert report["coverage"]["missing_eto_dates"] == [missing]
    assert report["coverage"]["eto_fraction"] == .5
    assert missing in report["error"]
    assert "etc_mm" not in report["stages"][0]


@pytest.mark.parametrize("field,value", [("validated", False), ("kc_source", ""),
    ("regional_applicability", ""), ("kc", None), ("kc", float("inf")),
    ("kc_reference_surface", "tall_crop"), ("reference_status", "independently_verified")])
def test_invalid_or_undeclared_kc_never_produces_seasonal_total(field, value, eto):
    report, = crop_water_results([stage(**{field: value})], eto)
    assert report["water"] is None
    assert report["status"] == "unavailable"
    assert report["error"]


def test_internal_stage_gap_is_not_a_complete_season(eto):
    report, = crop_water_results([stage(end="2025-01-02"), stage(start="2025-01-04", end="2025-01-04")], eto)
    assert report["coverage"]["missing_stage_dates"] == ["2025-01-03"]
    assert report["water"] is None


def test_stage_overlap_never_double_counts(eto):
    report, = crop_water_results([stage(), stage(start="2025-01-03", end="2025-01-04")], eto)
    assert report["water"] is None
    assert "Chevauchement" in report["error"]


def test_one_unavailable_crop_does_not_hide_another_complete_crop(eto):
    rows = [stage(), stage("Pois chiche", "2025-01-04", "2025-01-06", .25)]
    result = evaluate_rotation("Test", rows, {}, "2025-01-02", "2025-01-06",
        eto=eto.drop(pd.Timestamp("2025-01-05")))
    assert result["water"] is None  # no incomplete rotation total
    first, second = result["crop_results"]
    assert first["water"]["etc_mm"] == 3.
    assert second["water"] is None
    assert second["coverage"]["expected_days"] == 3
    assert second["coverage"]["missing_eto_dates"] == ["2025-01-05"]
    assert not assess_comparability([result, result])["quantitative_comparison_allowed"]


def test_different_durations_are_not_ranked_as_equivalent(eto):
    full = evaluate_rotation("A", [stage()], {}, "2025-01-02", "2025-01-03", eto=eto)
    short = evaluate_rotation("B", [stage(end="2025-01-02")], {}, "2025-01-02", "2025-01-03", eto=eto)
    assert short["crop_results"][0]["coverage"]["expected_days"] == 1
    assert short["water"] is not None  # qualified entered-stage total remains available
    assert not assess_comparability([full, short])["quantitative_comparison_allowed"]
    assert assess_comparability([full, full])["quantitative_comparison_allowed"]


def test_computed_sparse_series_keeps_gaps_and_derivation_explicit(eto_metadata):
    daily = pd.DataFrame({"eto_mm": [float("nan"), 2., 4.], "reason": ["Artificial gap", "", ""]},
        index=pd.date_range("2025-01-01", periods=3))
    result = EtoResult(daily, {**eto_metadata, "source_url": "https://example.invalid/test",
        "source_payload_sha256": "artificial", "unavailable_dates": ["2025-01-01"]})
    series = computed_eto_for_crops(result, eto_metadata["location"])
    assert series.attrs["unavailable_dates"] == ["2025-01-01"]
    report, = crop_water_results([stage()], series)
    assert report["water"]["etc_mm"] == 3.
    assert report["water"]["eto_derivation"]["source_payload_sha256"] == "artificial"
    assert daily.eto_mm.isna().sum() == 1  # source unmodified
    with pytest.raises(ValueError):
        result.available_frame()  # existing complete-period export remains strict


def test_empty_computed_series_is_unavailable(eto_metadata):
    result = EtoResult(pd.DataFrame({"eto_mm": [float("nan")]}, index=pd.date_range("2025-01-01", periods=1)), eto_metadata)
    with pytest.raises(WaterInputError, match="aucun jour"):
        computed_eto_for_crops(result)


def test_repeated_crop_can_have_explicit_cycles(eto):
    reports = crop_water_results([stage(crop_cycle="one"),
        stage(start="2025-01-05", end="2025-01-06", crop_cycle="two")], eto)
    assert len(reports) == 2
    assert all(r["status"] == "complete" for r in reports)


@pytest.mark.parametrize("key,value", [("units", "m/day"), ("time_standard", "LST"), ("reference_surface", "tall_crop")])
def test_computed_metadata_never_silently_relabelled(key, value, eto_metadata):
    meta = {**eto_metadata, "reference_surface": "short_grass", key: value}
    result = EtoResult(pd.DataFrame({"eto_mm": [2.]}, index=pd.date_range("2025-01-01", periods=1)), meta)
    with pytest.raises(WaterInputError, match=key):
        computed_eto_for_crops(result)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.])
def test_invalid_eto_in_season_never_becomes_zero(value, eto):
    eto = eto.copy(deep=True)
    eto.loc["2025-01-02"] = value
    report, = crop_water_results([stage()], eto)
    assert report["water"] is None
    assert report["coverage"]["missing_eto_dates"] == ["2025-01-02"]
    assert report["coverage"]["calculated_etc_days"] == 0
