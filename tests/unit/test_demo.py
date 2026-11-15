"""Demo safety and arithmetic tests; numbers are artificial test values only."""

import pandas as pd

from agrinova.rotation.compare import evaluate_rotation
from agrinova.analysis.water import validate_eto
from agrinova.rotation.demo import DEMO_NAMES, activate_demo, deactivate_demo, annotate_demo, scenario_frame


def evaluate(index, stages=None, eto=None):
    rows = scenario_frame(index).to_dict("records") if stages is None else stages
    result = evaluate_rotation(DEMO_NAMES[index], rows, {}, "2025-01-01", "2025-01-02", eto=eto)
    return annotate_demo(result, rows)


def test_demo_has_only_fictional_crop_sequences_without_agronomic_values():
    expected = [["Blé", "Blé"], ["Blé", "Féverole"], ["Blé", "Pois chiche"]]
    for i, sequence in enumerate(expected):
        frame = scenario_frame(i)
        assert frame.crop.tolist() == sequence
        assert frame[["start", "end", "kc"]].isna().all().all()
        assert frame.kc_source.tolist() == ["", ""]
        assert not frame.validated.any()
        result = evaluate(i)
        assert result["is_demo"] is True
        assert result["water"] is None
        assert result["declared_crops"] == sequence
        assert all(c["status"] == "Inconnu" for c in result["checks"].values())
        assert "score" not in result
        assert "fictif" in result["purpose"] or "fictive" in result["purpose"]
        assert all(row["start"] is None and row["kc"] is None for row in result["declared_stages"])


def test_frames_are_independent():
    first = scenario_frame(1)
    first.loc[0, "crop"] = "Edited"
    assert scenario_frame(1).loc[0, "crop"] == "Blé"


def test_notes_follow_edited_crops_and_never_reuse_seed_claims():
    rows = scenario_frame(1).to_dict("records")
    assert evaluate(1)["agronomic_context"]["references"]
    rows[1]["crop"] = "Unknown edited crop"
    context = evaluate(1, rows)["agronomic_context"]
    assert "inconnus" in context["potential_benefits"][0]
    assert context["references"] == []
    rows[1]["crop"] = "Blé"
    assert "répétition du blé" in evaluate(1, rows)["agronomic_context"]["potential_benefits"][0]


def test_demo_does_not_bypass_kc_validation_even_with_dates_and_eto(eto_metadata):
    rows = scenario_frame(1).to_dict("records")
    for i, row in enumerate(rows):
        row.update(start=pd.Timestamp(2025, 1, i + 1), end=pd.Timestamp(2025, 1, i + 1))
    eto = validate_eto(pd.DataFrame({"date": ["2025-01-01", "2025-01-02"], "eto_mm": [2., 4.]}),
                       "Artificial arithmetic fixture", True, eto_metadata)
    assert evaluate(1, rows, eto)["water"] is None
    for row in rows:
        row.update(kc=0.5, kc_source="Artificial arithmetic reference, not a crop value", validated=False,
                   growth_stage="Artificial stage", regional_applicability="Artificial fixture only",
                   kc_reference_surface="short_grass")
    assert evaluate(1, rows, eto)["water"] is None
    for row in rows:
        row["validated"] = True
    result = evaluate(1, rows, eto)
    assert result["water"]["etc_mm"] == 3.0  # (2 + 4) × 0.5; artificial arithmetic only
    assert result["is_demo"] is True


def test_mode_transition_preserves_manual_edits_and_climate():
    frame = pd.DataFrame({"crop": ["User draft"]})
    climate = object()
    state = {"manual_rotation_snapshot": {"stages_0": frame}, "climate": climate, "comparison": object()}
    activate_demo(state)
    assert state["demo_mode"] is True
    assert "comparison" not in state
    assert state["climate"] is climate
    activate_demo(state)  # reload must not overwrite saved manual edits
    deactivate_demo(state)
    assert state["demo_mode"] is False
    assert state["manual_rotation_seed"]["stages_0"].equals(frame)
    assert state["climate"] is climate
