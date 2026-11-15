"""Artificial software cases; no proposed crops, observations or crop parameters."""

from copy import deepcopy
import json

import pandas as pd
import pytest

from agrinova.analysis.water import WaterInputError, calculate_etc, validate_eto, json_safe
from agrinova.rotation.compare import CONSTRAINTS, evaluate_rotation, assess_comparability

SOURCE = "Artificial arithmetic fixture, not an agricultural reference"


def stage(crop="Artificial crop", start="2025-01-01", end="2025-01-02", kc=1.0):
    return {"crop": crop, "start": start, "end": end, "kc": kc, "kc_source": SOURCE,
            "validated": True, "growth_stage": "Artificial stage", "regional_applicability": SOURCE,
            "kc_reference_surface": "short_grass"}


@pytest.fixture
def eto(eto_metadata):
    return validate_eto(pd.DataFrame({"date": ["2025-01-01", "2025-01-02"], "eto_mm": [1., 2.]}),
                        SOURCE, True, eto_metadata)


def evaluate(rows, eto=None, checks=None, end="2025-01-02", area=None):
    return evaluate_rotation("Artificial scenario", rows, checks or {}, "2025-01-01", end, eto=eto, area_ha=area)


@pytest.mark.parametrize("crop", [None, "", "  ", float("nan"), pd.NA, pd.NaT, "None", "null", "nan", "<NA>", 12])
def test_missing_crop_is_rejected_before_string_conversion(crop, eto):
    result = evaluate([stage(crop)], eto)
    assert result["stages"] == []
    assert result["water"] is None
    assert any("culture manquante" in issue for issue in result["issues"])
    assert not result["statuses"]["data_complete"]
    with pytest.raises(WaterInputError, match="Culture manquante"):
        calculate_etc([stage(crop)], eto)


def test_valid_sequence_and_reversed_sequence_are_distinguished(eto):
    rows = [stage("Earlier", end="2025-01-01"), stage("Later", start="2025-01-02")]
    assert evaluate(rows, eto)["issues"] == []
    reversed_result = evaluate(list(reversed(rows)), eto)
    assert any("ordre chronologique" in issue for issue in reversed_result["issues"])
    assert reversed_result["water"] is None
    assert [r["crop"] for r in reversed_result["stages"]] == ["Later", "Earlier"]
    with pytest.raises(WaterInputError, match="chronologique"):
        calculate_etc(list(reversed(rows)), eto)


def test_incomplete_crop_coverage_blocks_comparison_of_totals(eto):
    complete = evaluate([stage()], eto)
    partial = evaluate([stage(end="2025-01-01")], eto)
    coverage = partial["coverage"]
    assert partial["water"]["etc_mm"] == 1
    assert coverage["expected_period"] == {"start": "2025-01-01", "end": "2025-01-02"}
    assert coverage["calculated_period"] == {"start": "2025-01-01", "end": "2025-01-01"}
    assert coverage["crop_coverage"] == coverage["etc_coverage"] == .5
    assert coverage["crop_missing_days"] == coverage["missing_etc_days"] == 1
    assert not assess_comparability([complete, partial])["quantitative_comparison_allowed"]
    assert assess_comparability([complete, partial])["ranking"] is None


def test_equal_complete_periods_share_basis_without_implying_agronomic_validation(eto):
    a, b = evaluate([stage("A")], eto), evaluate([stage("B")], eto)
    assessment = assess_comparability([a, b])
    assert assessment["quantitative_comparison_allowed"]
    assert assessment["agronomic_validation"] == "not_performed"
    assert assessment["ranking"] is None


def test_different_expected_periods_or_eto_methods_are_not_comparable(eto):
    full = evaluate([stage()], eto)
    shorter = evaluate([stage(end="2025-01-01")], eto, end="2025-01-01")
    assert shorter["coverage"]["comparison_eligible"]
    assert not assess_comparability([full, shorter])["quantitative_comparison_allowed"]
    other = eto.copy(deep=True)
    other.attrs = deepcopy(eto.attrs)
    other.attrs["agrinova_metadata"]["calculation_method"] = "Another artificial method"
    assert not assess_comparability([full, evaluate([stage()], other)])["quantitative_comparison_allowed"]


def test_volume_comparison_requires_equal_known_areas(eto):
    assessment = assess_comparability([evaluate([stage()], eto, area=1.), evaluate([stage()], eto, area=2.)])
    assert assessment["quantitative_comparison_allowed"]
    assert not assessment["volume_comparison_allowed"]


def test_status_axes_do_not_treat_farmer_declarations_as_agronomic_validation(eto):
    checks = {c: {"status": "Compatible", "evidence": SOURCE} for c in CONSTRAINTS}
    no_calculation = evaluate([stage()], checks=checks)
    assert no_calculation["statuses"]["farmer_declarations"] == "recorded"
    assert not no_calculation["statuses"]["data_complete"]
    assert not no_calculation["statuses"]["calculation_available"]
    complete = evaluate([stage()], eto, checks)
    assert complete["statuses"]["data_complete"]
    assert complete["statuses"]["calculation_available"]
    assert complete["statuses"]["agronomic_validation"] == "not_performed"
    assert "compatibles" not in complete["status"]
    assert "non validée" in complete["status"]


@pytest.mark.parametrize("field", ["calculation_method", "units", "reference_surface", "location", "time_standard"])
def test_external_eto_requires_complete_metadata(field, eto_metadata):
    meta = dict(eto_metadata)
    del meta[field]
    with pytest.raises(WaterInputError):
        validate_eto(pd.DataFrame({"date": ["2025-01-01"], "eto_mm": [1.]}), SOURCE, True, meta)


@pytest.mark.parametrize("patch", [{"units": "inches/day"}, {"reference_surface": "alfalfa"},
    {"time_standard": "LST"}, {"location": {"latitude": None, "longitude": 0}},
    {"period": {"start": "2024-01-01", "end": "2025-01-01"}},
    {"reference_status": "independently_verified"}])
def test_metadata_mismatches_cannot_pass_as_validation(patch, eto_metadata):
    with pytest.raises(WaterInputError):
        validate_eto(pd.DataFrame({"date": ["2025-01-01"], "eto_mm": [1.]}), SOURCE, True, {**eto_metadata, **patch})


def test_eto_records_period_source_and_non_certified_reference_status(eto):
    meta = eto.attrs["agrinova_metadata"]
    assert meta["source"] == SOURCE
    assert meta["period"] == {"start": "2025-01-01", "end": "2025-01-02"}
    assert meta["reference_status"] == "user_declared"
    assert meta["independent_verification"] == "not_performed"
    assert meta["fao56_compliance"] == "not_verified"
    assert len(meta["data_sha256"]) == 64


def test_external_eto_location_must_match_explicit_target(eto_metadata):
    with pytest.raises(WaterInputError, match="localisation différente"):
        validate_eto(pd.DataFrame({"date": ["2025-01-01"], "eto_mm": [1.]}), SOURCE, True,
                     eto_metadata, expected_location={"latitude": 0., "longitude": 0.})


@pytest.mark.parametrize("field", ["growth_stage", "regional_applicability", "kc_reference_surface", "kc_source"])
def test_kc_metadata_is_required_per_stage(field, eto):
    row = stage()
    row[field] = ""
    with pytest.raises(WaterInputError):
        calculate_etc([row], eto)


def test_kc_metadata_round_trips_without_pretending_independent_verification(eto):
    water = calculate_etc([stage()], eto)
    meta = water["kc_metadata"][0]
    assert meta["crop"] == "Artificial crop"
    assert meta["growth_stage"] == "Artificial stage"
    assert meta["coefficient"] == 1.
    assert meta["source"] == SOURCE
    assert meta["regional_applicability"] == SOURCE
    assert meta["period"] == {"start": "2025-01-01", "end": "2025-01-02"}
    assert meta["reference_status"] == "user_declared"
    assert meta["independent_verification"] == "not_performed"


@pytest.mark.parametrize("case", ["daily_product", "total", "volume"])
def test_nonfinite_products_totals_and_volumes_are_refused(case, eto):
    row, area = stage(), None
    if case in {"daily_product", "total"}:
        row["kc"] = 1e308  # deliberately pathological arithmetic, never a crop reference
    if case == "total":
        eto = eto.copy(deep=True)
        eto[:] = 1.
    if case == "volume":
        area = 1e308
    with pytest.raises(WaterInputError, match="fini"):
        calculate_etc([row], eto, area)


def test_missing_eto_day_blocks_calculation_and_reports_missing_coverage(eto_metadata):
    eto = validate_eto(pd.DataFrame({"date": ["2025-01-01", "2025-01-03"], "eto_mm": [1., 2.]}),
                       SOURCE, True, eto_metadata)
    result = evaluate([stage(end="2025-01-03")], eto, end="2025-01-03")
    assert result["water"] is None
    assert result["coverage"]["etc_days"] == 0
    assert result["coverage"]["missing_etc_days"] == 3
    assert result["coverage"]["crop_days"] == 3


def test_invalid_input_exports_use_standard_json(eto):
    result = evaluate([stage(kc=float("inf"))], eto)
    encoded = json.dumps(json_safe(result), default=str, allow_nan=False)
    assert json.loads(encoded)["declared_stages"][0]["kc"] == "inf"


def test_independently_verified_kc_cannot_be_self_asserted(eto):
    row = {**stage(), "reference_status": "independently_verified"}
    with pytest.raises(WaterInputError, match="vérification indépendante"):
        calculate_etc([row], eto)


@pytest.mark.parametrize("value", [None, float("nan"), True, ""])
def test_missing_or_boolean_kc_is_never_replaced_by_a_default(value, eto):
    row = {**stage(), "kc": value}
    with pytest.raises(WaterInputError):
        calculate_etc([row], eto)


def test_data_completeness_and_calculation_availability_are_separate_on_overflow(eto):
    result = evaluate([stage(kc=1e308)], eto)
    assert result["statuses"]["data_complete"]
    assert not result["statuses"]["calculation_available"]
    assert result["statuses"]["agronomic_validation"] == "not_performed"


def test_kc_surface_and_eto_surface_must_match(eto):
    with pytest.raises(WaterInputError, match="surface de référence"):
        calculate_etc([{**stage(), "kc_reference_surface": "alfalfa"}], eto)
