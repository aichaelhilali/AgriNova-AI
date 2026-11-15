"""Explicitly fictional sequences: no observations, planting dates or Kc values."""

from copy import deepcopy
import unicodedata

import pandas as pd
from agrinova.analysis.water import json_safe

DEMO_NAMES = (
    "A · Référence fictive — démonstration",
    "B · Alternative 1 fictive — démonstration",
    "C · Alternative 2 fictive — démonstration",
)
DEMO_CROPS = (("Blé", "Blé"), ("Blé", "Féverole"), ("Blé", "Pois chiche"))
DEMO_NOTICE = (
    "DÉMONSTRATION — Toutes les rotations ci-dessous sont fictives et modifiables. "
    "La référence A n’est pas la rotation réelle d’un agriculteur. "
    "Aucune date de plantation, aucun Kc et aucune validation locale ne sont fournis. "
    "Ces exemples illustrent le parcours de l’application, pas des recommandations agricoles."
)
REFERENCE = {
    "title": "FAO · Sustainable crop rotations — principes généraux",
    "url": "https://www.fao.org/4/v9926e/v9926e06.htm",
    "scope": "Référence générale ; aucune validation des trois séquences à Beni Mellal–Afourer",
}


def scenario_frame(index):
    """Return independent editable rows in sequence order, without calendar claims."""
    return pd.DataFrame({
        "crop": list(DEMO_CROPS[index]),
        "start": pd.Series([None, None], dtype="datetime64[ns]"),
        "end": pd.Series([None, None], dtype="datetime64[ns]"),
        "kc": pd.Series([None, None], dtype="float64"),
        "kc_source": ["", ""], "validated": [False, False],
    })


def activate_demo(state):
    state["demo_mode"] = True
    state["demo_revision"] = state.get("demo_revision", 0) + 1
    state.pop("comparison", None)


def deactivate_demo(state):
    state["demo_mode"] = False
    state.pop("comparison", None)
    # Restore complete table values, not widget edit deltas: Streamlit discards
    # the state of editors while they are hidden by the other mode.
    state["manual_rotation_seed"] = deepcopy(state.get("manual_rotation_snapshot", {}))
    for i in range(3):
        state.pop(f"stages_{i}", None)
        state.pop(f"checks_{i}", None)


def _crop_kind(crop):
    word = "".join(c for c in unicodedata.normalize("NFKD", crop.casefold().strip()) if not unicodedata.combining(c))
    if word in {"ble", "wheat"}:
        return "wheat"
    if word in {"feverole", "feve", "faba bean", "pois chiche", "chickpea"}:
        return "pulse"
    return "unknown"


def annotate_demo(result, stages):
    """Attach honest qualitative context; leave numerical calculations untouched.

    Notes are derived from the edited sequence, never the original scenario ID.
    """
    crops = [row["crop"].strip() for row in stages
             if isinstance(row.get("crop"), str) and row["crop"].strip()]
    kinds = [_crop_kind(crop) for crop in crops]
    benefits = []
    references = []
    if "wheat" in kinds and "pulse" in kinds and "unknown" not in kinds:
        benefits.append("Potentiel général : diversification céréale–légumineuse et contribution possible de la fixation biologique d’azote si la nodulation est effective. Effets locaux et gains non établis (FAO).")
        references = [dict(REFERENCE)]
    elif crops and set(kinds) == {"wheat"}:
        benefits.append("Bénéfice agronomique de la répétition du blé : inconnu dans ce prototype. Cette séquence sert uniquement de repère fictif, sans diversification entre les cultures saisies.")
    else:
        benefits.append("Bénéfices agronomiques de la séquence modifiée : inconnus ; références adaptées et revue agronomique nécessaires.")
    notes = {
        "potential_benefits": benefits,
        "risks_and_unknowns": [
            "Pression des maladies, ravageurs et adventices : inconnue ; vérifier l’historique, les cultures et les successions avec un conseiller.",
            "Adaptation locale, sol, eau disponible et calendrier : non validés par ces exemples.",
            "Rendement, économie d’eau, coût et débouchés : inconnus ; aucun gain ni classement n’est calculé.",
        ],
        "references": references,
    }
    result.update({
        "is_demo": True, "data_origin": "Séquence fictive de démonstration, éventuellement modifiée par l’utilisateur",
        "declared_crops": crops,
        "declared_stages": json_safe(stages),
        "purpose": "Référence fictive de démonstration ; aucune rotation réelle d’agriculteur n’est connue" if result["name"] == DEMO_NAMES[0]
                   else "Alternative fictive de démonstration ; exemple éditable, sans recommandation validée",
        "benefit": "Illustrer la comparaison de séquences et les informations nécessaires ; aucun bénéfice de terrain démontré",
        "agronomic_context": notes,
    })
    result["statuses"]["information_origin"] = "fictional_demonstration"
    only_undated = len(crops) == len(stages) and bool(stages) and all(
        pd.isna(row.get("start")) and pd.isna(row.get("end")) for row in stages
    )
    incompatible = any(c["status"] == "Incompatible" for c in result["checks"].values())
    if only_undated and not incompatible:
        result["status"] = "Démonstration qualitative — calendrier et calculs indisponibles"
        result["issues"] = [issue for issue in result["issues"] if issue != "Aucune culture datée fournie ; rotation non renseignée"]
    return result
