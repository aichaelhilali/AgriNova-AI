"""Synthetic schedules test referenced rules; not proposed local calendars."""

from copy import deepcopy
import json

import pandas as pd
import pytest

from agrinova.rotation.agronomy import analyze_agronomy, identify_crop
from agrinova.rotation.compare import evaluate_rotation, assess_comparability
from agrinova.analysis.water import validate_eto


def row(crop="Blé", start="2025-01-01", end="2025-01-02", **fields):
    return {"crop": crop, "start": start, "end": end, **fields}


def analyze(rows):
    return analyze_agronomy(rows, "2025-01-01", "2025-01-10")


@pytest.mark.parametrize("name,family,legume", [
    ("Blé", "Poaceae", False), (" WHEAT ", "Poaceae", False),
    ("Féverole", "Fabaceae", True), ("Faba bean", "Fabaceae", True),
    ("Pois chiche", "Fabaceae", True), ("Cicer arietinum", "Fabaceae", True)])
def test_documented_exact_identities(name, family, legume):
    identity = identify_crop(name)
    assert identity["family"] == family
    assert identity["legume"] is legume
    assert identity["reference_ids"]


@pytest.mark.parametrize("name", [None, pd.NA, float("nan"), "", "Unknown crop", "Wheat and chickpea", "bean", "Lentil"])
def test_unverified_names_are_unknown_never_guessed(name):
    identity = identify_crop(name)
    assert identity["family"] is None
    assert identity["legume"] is None
    assert identity["reference_ids"] == []


def test_legume_symbioses_are_distinct_and_not_nitrogen_credits():
    result = analyze([row("Féverole"), row("Pois chiche", "2025-01-03", "2025-01-04")])
    faba, chickpea = [c["nitrogen_fixation"] for c in result["cycles"]]
    assert faba["symbiont"] != chickpea["symbiont"]
    for nitrogen in [faba, chickpea]:
        assert nitrogen["status"] == "conditional_potential"
        assert nitrogen["amount_kg_ha"] is nitrogen["residual_n_credit_kg_ha"] is None
        assert nitrogen["reference_ids"]
    assert any(i["code"] == "nitrogen_balance" for i in result["missing_information"])
    assert result["sequence"][0]["same_family"] is True
    assert any(i["code"] == "repetition" for i in result["risks"])


def test_growth_stages_do_not_create_false_crop_repetition():
    result = analyze([row(growth_stage="Initial"), row(start="2025-01-03", end="2025-01-04", growth_stage="Development")])
    assert len(result["cycles"]) == 1
    assert result["sequence"] == []
    assert result["cycles"][0]["stage_rows"] == [1, 2]


def test_explicit_distinct_wheat_cycles_are_repetition():
    result = analyze([row(growth_stage="Initial", crop_cycle="one"),
        row(start="2025-01-04", end="2025-01-05", growth_stage="Initial", crop_cycle="two")])
    assert len(result["cycles"]) == 2
    assert result["sequence"][0]["same_crop"] is True


def test_undated_demo_repetition_still_analyzes_two_crops():
    result = analyze([{"crop": "Blé"}, {"crop": "Blé"}])
    assert len(result["cycles"]) == 2
    assert result["sequence"][0]["same_crop"] is True
    assert result["calendar"]["boundary_status"] == "unknown"


def test_unknown_intervening_crop_is_never_skipped_in_sequence():
    result = analyze([row(), row("Unknown"), row()])
    assert len(result["sequence"]) == 2
    assert all(item["same_crop"] is None for item in result["sequence"])
    assert not any(i["code"] == "repetition" for i in result["risks"])


def test_family_change_is_conditional_not_proof_of_disease_control():
    result = analyze([row(), row("Pois chiche", "2025-01-03", "2025-01-04")])
    assert result["sequence"][0]["same_family"] is False
    assert any(i["code"] == "family_change" and i["reference_ids"] for i in result["potential_benefits"])
    assert result["calendar"]["local_agronomic_compatibility"] == "not_verified"


def known_boundaries():
    return [row(planting_date="2025-01-01", harvest_date="2025-01-02"),
        row("Pois chiche", "2025-01-06", "2025-01-08", planting_date="2025-01-06", harvest_date="2025-01-08")]


def test_potential_bare_period_needs_explicit_crop_boundaries():
    rows = known_boundaries()
    result = analyze(rows)
    gap, = result["calendar"]["potential_bare_soil_periods"]
    assert (gap["start"], gap["end"], gap["days"]) == ("2025-01-03", "2025-01-05", 3)
    assert gap["actual_soil_cover"] == "unknown"
    assert result["calendar"]["scope"] == "internal_intercrop_intervals_only"
    for r in rows:
        r.pop("planting_date")
        r.pop("harvest_date")
    assert analyze(rows)["calendar"]["potential_bare_soil_periods"] == []
    assert analyze(rows)["calendar"]["boundary_status"] == "unknown"


def test_missing_intervening_boundaries_prevent_false_bare_intervals():
    rows = known_boundaries()
    rows.insert(1, row("Unknown", "2025-01-03", "2025-01-04"))
    assert analyze(rows)["calendar"]["potential_bare_soil_periods"] == []


@pytest.mark.parametrize("change", [
    {"planting_date": "2025-01-03"}, {"harvest_date": "2024-12-31"},
    {"planting_date": "invalid"}, {"harvest_date": "2025-01-01"},
    {"harvest_date": "2025-02-01"}])
def test_invalid_boundaries_report_errors_without_silently_reordering(change):
    rows = known_boundaries()
    rows[0].update(change)
    result = analyze(rows)
    assert result["calendar"]["boundary_status"] == "invalid"
    assert result["calendar"]["errors"]
    assert result["calendar"]["potential_bare_soil_periods"] == []
    evaluated = evaluate_rotation("Test", rows, {}, "2025-01-01", "2025-01-10")
    assert evaluated["water"] is None
    assert not evaluated["coverage"]["comparison_eligible"]


def test_contradictory_boundaries_across_stages_are_rejected():
    rows = [row(growth_stage="Initial", crop_cycle="a", planting_date="2025-01-01", harvest_date="2025-01-05"),
        row(start="2025-01-03", end="2025-01-05", growth_stage="Mid", crop_cycle="a", planting_date="2025-01-02")]
    assert any("contradictoires" in e for e in analyze(rows)["calendar"]["errors"])


def test_planting_harvest_overlap_is_not_masked_by_disjoint_stage_dates():
    rows = known_boundaries()
    rows[0]["harvest_date"] = "2025-01-07"
    result = analyze(rows)
    assert any("chevauchement" in e for e in result["calendar"]["errors"])


def test_every_agronomic_claim_has_a_resolvable_reference_and_inputs_unchanged():
    rows = known_boundaries()
    before = deepcopy(rows)
    result = analyze(rows)
    refs = {r["id"] for r in result["references"]}
    for item in result["evidence"] + result["potential_benefits"] + result["risks"]:
        assert item["reference_ids"]
        assert set(item["reference_ids"]) <= refs
    assert rows == before
    assert "score" not in result and "ranking" not in result
    json.dumps(result, allow_nan=False)


def test_climate_stage_evidence_coverage_units_missing_dates_and_provenance():
    climate = pd.DataFrame({"T2M": [10., float("inf"), 20.], "PRECTOTCORR": [1., 2., float("nan")],
        "T2M_MIN": [5., 8., 15.], "T2M_MAX": [15., 25., 30.]}, index=pd.date_range("2025-01-01", periods=3))
    result = evaluate_rotation("Test", [row(end="2025-01-04", growth_stage="Test stage")], {},
        "2025-01-01", "2025-01-04", climate=climate, climate_provenance={"payload_sha256": "artificial"})
    evidence, = result["climate_evidence"]
    assert evidence["stade"] == "Test stage"
    assert evidence["jours attendus"] == 4
    assert evidence["température moyenne °C (jours disponibles)"] == 15.
    assert evidence["pluie mm (complète uniquement)"] is None
    assert evidence["dates température manquantes"] == ["2025-01-02", "2025-01-04"]
    assert evidence["dates pluie manquantes"] == ["2025-01-03", "2025-01-04"]
    assert evidence["couverture température"] == .5
    assert result["climate_provenance"]["payload_sha256"] == "artificial"


def test_duplicate_climate_dates_are_not_counted_as_complete_evidence():
    climate = pd.DataFrame({"T2M": [10., 20.], "PRECTOTCORR": [1., 2.]}, index=[pd.Timestamp("2025-01-01")] * 2)
    result = evaluate_rotation("Test", [row()], {}, "2025-01-01", "2025-01-02", climate=climate)
    assert result["climate_evidence"] == []
    assert result["missing_information"]


def test_three_rotations_keep_quantitative_etc_separate_from_qualitative_rules(eto_metadata):
    eto = validate_eto(pd.DataFrame({"date": ["2025-01-01", "2025-01-02"], "eto_mm": [2., 4.]}),
        "Artificial arithmetic", True, eto_metadata)
    results = []
    for name, crop in [("Rotation actuelle", "Blé"), ("Alternative 1", "Féverole"), ("Alternative 2", "Pois chiche")]:
        r = row(crop, kc=.5, kc_source="Artificial arithmetic only", validated=True,
            growth_stage="Artificial stage", regional_applicability="Software test only", kc_reference_surface="short_grass")
        results.append(evaluate_rotation(name, [r], {}, "2025-01-01", "2025-01-02", eto=eto))
    assessment = assess_comparability(results)
    assert assessment["quantitative_comparison_allowed"]
    assert assessment["ranking"] is None
    assert [r["water"]["etc_mm"] for r in results] == [3., 3., 3.]
    assert all(r["statuses"]["agronomic_validation"] == "not_performed" for r in results)
    assert all(r["missing_information"] for r in results)
