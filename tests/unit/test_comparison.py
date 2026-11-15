"""Scenarios are artificial test inputs, not proposed rotations."""

from agrinova.rotation.compare import CONSTRAINTS, evaluate_rotation


def evaluate(stages, checks=None):
    return evaluate_rotation("Rotation actuelle", stages, checks or {}, "2025-01-01", "2025-01-03")


def test_no_assumed_existing_rotation():
    result = evaluate([])
    assert result["stages"] == []
    assert result["water"] is None
    assert result["status"].startswith("Bloquée")


def test_unknown_constraints_never_imply_suitability():
    result = evaluate([{"crop": "Test only", "start": "2025-01-01", "end": "2025-01-03"}])
    assert result["status"].startswith("Non évaluée")
    assert len(result["risks"]) >= len(CONSTRAINTS)
    assert "score" not in result


def test_compatible_without_evidence_is_unknown():
    checks = {c: {"status": "Compatible", "evidence": ""} for c in CONSTRAINTS}
    result = evaluate([{"crop": "Test only", "start": "2025-01-01", "end": "2025-01-03"}], checks)
    assert all(c["status"] == "Inconnu" for c in result["checks"].values())


def test_incompatibility_blocks_even_if_others_compatible():
    checks = {c: {"status": "Compatible", "evidence": "Artificial test evidence"} for c in CONSTRAINTS}
    checks["Sol"]["status"] = "Incompatible"
    result = evaluate([{"crop": "Test only", "start": "2025-01-01", "end": "2025-01-03"}], checks)
    assert result["status"].startswith("Bloquée")


def test_gap_is_explicit_and_no_water_is_invented():
    result = evaluate([{"crop": "Test only", "start": "2025-01-01", "end": "2025-01-02"}])
    assert result["uncovered_days"] == 1
    assert result["water"] is None


def test_out_of_horizon_and_overlap_block_calculation():
    stage = {"crop": "Test only", "start": "2024-12-31", "end": "2025-01-03"}
    result = evaluate([stage, stage])
    assert len(result["issues"]) == 3
    assert result["water"] is None
