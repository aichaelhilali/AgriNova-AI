import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from agrinova.rotation.demo import DEMO_NAMES

APP = Path(__file__).resolve().parents[2] / "app.py"


def click(app, label):
    next(b for b in app.button if b.label == label).click().run(timeout=30)
    assert not app.exception
    return app


def loaded_demo():
    return click(AppTest.from_file(str(APP)).run(timeout=30), "Charger un scénario de démonstration")


def test_demo_button_populates_and_compares_fictional_undated_sequences():
    app = loaded_demo()
    assert app.session_state["demo_mode"]
    assert all("Rotation actuelle" != h.value for h in app.subheader)
    assert any("La référence A n’est pas la rotation réelle" in w.value for w in app.warning)
    click(app, "Comparer les trois rotations")
    saved = app.session_state["comparison"]
    assert saved["mode"] == "demonstration"
    assert [r["name"] for r in saved["results"]] == list(DEMO_NAMES)
    assert [r["declared_crops"] for r in saved["results"]] == [["Blé", "Blé"], ["Blé", "Féverole"], ["Blé", "Pois chiche"]]
    assert all(r["water"] is None for r in saved["results"])
    assert all("qualitative" in r["status"] for r in saved["results"])
    table = next(d.value for d in app.dataframe if "Stratégie" in d.value.columns)
    assert table["Cultures / stades"].tolist() == ["Blé → Blé", "Blé → Féverole", "Blé → Pois chiche"]
    # Export payload keeps fictional provenance, not just on-screen labels.
    exported = json.loads(json.dumps(saved, ensure_ascii=False, default=str))
    assert all(r["is_demo"] for r in exported["results"])
    assert "fictives" in exported["rotation_origin"]
    assert "agriculteur" not in exported["results"][0]["data_origin"]


def test_demo_sequences_remain_editable_and_annotations_follow_edits():
    app = loaded_demo()
    revision = app.session_state["demo_revision"]
    app.session_state[f"demo_{revision}_stages_1"] = {
        "edited_rows": {1: {"crop": "Edited test crop"}}, "added_rows": [], "deleted_rows": []}
    click(app, "Comparer les trois rotations")
    result = app.session_state["comparison"]["results"][1]
    assert result["declared_crops"] == ["Blé", "Edited test crop"]
    assert result["agronomic_context"]["references"] == []
    assert result["water"] is None


def test_reloading_demo_resets_examples_and_invalidates_old_comparison():
    app = loaded_demo()
    revision = app.session_state["demo_revision"]
    app.session_state[f"demo_{revision}_stages_0"] = {
        "edited_rows": {0: {"crop": "Edited test crop"}}, "added_rows": [], "deleted_rows": []}
    click(app, "Comparer les trois rotations")
    click(app, "Charger un scénario de démonstration")
    assert "comparison" not in app.session_state
    click(app, "Comparer les trois rotations")
    assert app.session_state["comparison"]["results"][0]["declared_crops"] == ["Blé", "Blé"]


def test_clearing_a_demo_crop_does_not_crash_or_invent_a_replacement():
    app = loaded_demo()
    revision = app.session_state["demo_revision"]
    app.session_state[f"demo_{revision}_stages_0"] = {
        "edited_rows": {0: {"crop": None}}, "added_rows": [], "deleted_rows": []}
    click(app, "Comparer les trois rotations")
    result = app.session_state["comparison"]["results"][0]
    assert result["declared_crops"] == ["Blé"]
    assert result["declared_stages"][0]["crop"] is None
    assert result["water"] is None


def test_quitting_demo_restores_manual_mode_and_saved_edits():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    app.session_state["stages_0"] = {"edited_rows": {0: {"crop": "Manual test crop", "start": "2025-01-01", "end": "2025-12-31"}}, "added_rows": [], "deleted_rows": []}
    click(app, "Comparer les trois rotations")
    click(app, "Charger un scénario de démonstration")
    click(app, "Quitter le mode démonstration")
    assert app.session_state["demo_mode"] is False
    assert "comparison" not in app.session_state
    click(app, "Comparer les trois rotations")
    saved = app.session_state["comparison"]
    assert saved["mode"] == "farmer_input"
    assert [r["name"] for r in saved["results"]] == ["Rotation actuelle", "Alternative 1", "Alternative 2"]
    assert saved["results"][0]["stages"][0]["crop"] == "Manual test crop"
