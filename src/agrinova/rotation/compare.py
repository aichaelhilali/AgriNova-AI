"""Compare farmer-defined scenarios without suitability scores or invented crops."""

from math import isfinite
import pandas as pd

from agrinova.analysis.water import WaterInputError, calculate_etc, validate_eto, has_reference, day, json_safe
from agrinova.analysis.crop_water import crop_water_results
from agrinova.rotation.agronomy import analyze_agronomy

CONSTRAINTS = ("Sol", "Eau disponible", "Calendrier", "Successions / phytosanitaire", "Matériel et main-d’œuvre", "Débouchés")
STATUSES = ("Inconnu", "Compatible", "Incompatible")


def evaluate_rotation(name, stages, checks, start, end, eto=None, area_ha=None, climate=None, climate_provenance=None):
    issues, risks, evidence = [], [], []
    clean, dates_seen = [], set()
    horizon = pd.date_range(start, end, freq="D")
    if horizon.empty:
        raise ValueError("Horizon commun invalide")
    previous_start = None
    for number, raw in enumerate(stages, 1):
        if not has_reference(raw.get("crop")):
            issues.append(f"Ligne {number} : culture manquante")
            continue
        crop = raw["crop"].strip()
        try:
            first, last = day(raw.get("start")), day(raw.get("end"))
            if pd.isna(first) or pd.isna(last) or first > last:
                raise ValueError()
            if first < horizon[0] or last > horizon[-1]:
                issues.append(f"{crop} : dates hors horizon commun")
            if previous_start is not None and first < previous_start:
                issues.append(f"Ligne {number} ({crop}) : ordre chronologique invalide ; les dates précèdent la ligne antérieure. Aucune réorganisation automatique.")
            previous_start = first
            days = set(pd.date_range(first, last))
            if dates_seen.intersection(days):
                issues.append(f"{crop} : stades/cultures superposés ; cultures associées non prises en charge")
            dates_seen.update(days)
            clean.append({**raw, "crop": crop, "start": first, "end": last})
        except (TypeError, ValueError):
            issues.append(f"{crop} : dates absentes ou invalides")
    if not clean:
        issues.append("Aucune culture datée fournie ; rotation non renseignée")
    agronomy = analyze_agronomy(stages, start, end)
    issues.extend(agronomy["calendar"]["errors"])
    checks_out = {}
    for constraint in CONSTRAINTS:
        entry = checks.get(constraint, {})
        status = entry.get("status", "Inconnu")
        raw_note = entry.get("evidence", "")
        note = raw_note.strip() if has_reference(raw_note) else ""
        if status not in STATUSES or (status != "Inconnu" and not note):
            status = "Inconnu"
        checks_out[constraint] = {"status": status, "evidence": note, "origin": "user_declared",
                                  "agronomic_verification": "not_performed"}
        if status == "Incompatible":
            risks.append(f"{constraint} : incompatibilité déclarée — {note}")
        elif status == "Inconnu":
            risks.append(f"{constraint} : compatibilité non établie")
        else:
            evidence.append(f"Déclaration utilisateur non vérifiée — {constraint} : compatible selon déclaration — {note}")
    uncovered = len(set(horizon) - dates_seen)
    if uncovered:
        risks.append(f"{uncovered} jours sans stade renseigné : ET du sol/jachère non calculée ; totaux de rotation non comparables")
    water, water_error = None, None
    crop_results = crop_water_results(clean, eto, area_ha) if not issues else []
    if not issues:
        try:
            water = calculate_etc(clean, eto, area_ha)
        except WaterInputError as exc:
            water_error = str(exc)
    else:
        water_error = "Corriger les cultures et dates avant calcul"
    if water:
        evidence.append("ETc calculée : somme journalière de Kc × ET₀, selon références et validation déclarées par l’utilisateur")
    else:
        risks.append(f"Calcul hydrique indisponible : {water_error}")
    climate_evidence = []
    climate_index_valid = (climate is not None and isinstance(climate.index, pd.DatetimeIndex)
        and not climate.index.has_duplicates and climate.index.tz is None
        and bool((climate.index == climate.index.normalize()).all()))
    if climate_index_valid:
        for stage in clean:
            dates = pd.date_range(stage["start"], stage["end"])
            subset = climate.reindex(dates)
            expected = len(dates)
            def valid_values(parameter):
                values = pd.to_numeric(subset.get(parameter, pd.Series(index=dates, dtype=float)), errors="coerce")
                values = values.where(values.map(isfinite))
                return values.where(values >= 0) if parameter == "PRECTOTCORR" else values
            rain, temp = valid_values("PRECTOTCORR"), valid_values("T2M")
            tmin, tmax = valid_values("T2M_MIN"), valid_values("T2M_MAX")
            climate_evidence.append({"culture": stage["crop"], "stade": stage.get("growth_stage"),
                "début": stage["start"].date().isoformat(),
                "fin": stage["end"].date().isoformat(), "jours attendus": expected,
                "jours pluie valides": int(rain.count()), "pluie mm (complète uniquement)": float(rain.sum()) if rain.notna().all() else None,
                "jours température valides": int(temp.count()), "température moyenne °C (jours disponibles)": float(temp.mean()) if temp.count() else None,
                "couverture pluie": float(rain.notna().mean()), "couverture température": float(temp.notna().mean()),
                "dates pluie manquantes": [d.date().isoformat() for d in dates[rain.isna()]],
                "dates température manquantes": [d.date().isoformat() for d in dates[temp.isna()]],
                "température minimale °C (jours disponibles)": float(tmin.min()) if tmin.count() else None,
                "température maximale °C (jours disponibles)": float(tmax.max()) if tmax.count() else None,
                "jours Tmin valides": int(tmin.count()), "jours Tmax valides": int(tmax.count()),
                "aptitude climatique": "Non évaluée : seuils culturaux locaux non fournis"})
    status = "Non évaluée — données manquantes"
    if issues or any(v["status"] == "Incompatible" for v in checks_out.values()):
        status = "Bloquée — saisie ou contrainte incompatible"
    elif all(v["status"] == "Compatible" for v in checks_out.values()):
        status = "Déclarations renseignées — faisabilité agronomique non validée"
    expected = set(horizon)
    crop_days = expected.intersection(dates_seen)
    calculated = {pd.Timestamp(row["date"]) for row in water["daily"]} if water else set()
    covered = expected.intersection(calculated)
    eligible = not issues and len(crop_days) == len(expected) and len(covered) == len(expected)
    def period(values):
        return None if not values else {"start": min(values).date().isoformat(), "end": max(values).date().isoformat()}
    coverage = {"expected_period": period(expected), "expected_days": len(expected),
                "calculated_period": period(calculated), "crop_days": len(crop_days),
                "crop_coverage": len(crop_days) / len(expected), "crop_missing_days": len(expected - crop_days),
                "etc_days": len(covered), "etc_coverage": len(covered) / len(expected),
                "missing_etc_days": len(expected - covered), "comparison_eligible": eligible,
                "status": "complete" if eligible else ("invalid" if issues else "incomplete")}
    def coefficient_complete(row):
        try:
            return (not isinstance(row.get("kc"), bool) and isfinite(float(row.get("kc"))) and float(row["kc"]) >= 0
                    and row.get("validated") is True and has_reference(row.get("kc_source"))
                    and has_reference(row.get("growth_stage")) and has_reference(row.get("regional_applicability"))
                    and row.get("kc_reference_surface") == "short_grass"
                    and row.get("reference_status", "user_declared") == "user_declared")
        except (TypeError, ValueError):
            return False
    eto_complete = False
    if eto is not None:
        try:
            provenance = eto.attrs.get("agrinova_metadata", {})
            checked = validate_eto(eto.rename("eto_mm").rename_axis("date").reset_index(),
                                   provenance.get("source"), provenance.get("declaration_confirmed"), provenance)
            eto_complete = checked.reindex(horizon).notna().all()
        except WaterInputError:
            pass
    statuses = {
        "information_origin": "user_declared",
        "farmer_declarations": "recorded" if all(v["status"] != "Inconnu" for v in checks_out.values()) else "incomplete",
        "data_complete": bool(not issues and not uncovered and eto_complete and all(coefficient_complete(row) for row in clean)),
        "calculation_available": water is not None,
        "agronomic_validation": "not_performed",
        "declared_incompatibility": any(v["status"] == "Incompatible" for v in checks_out.values()),
    }
    missing_information = [item["text"] for item in agronomy["missing_information"]]
    missing_information.extend(f"{constraint} : informations ou justification manquantes" for constraint, entry in checks_out.items() if entry["status"] == "Inconnu")
    if water is None:
        missing_information.append(f"ETc indisponible : {water_error}")
    if not climate_index_valid or not clean:
        missing_information.append("Climat par stade indisponible : dates et série journalière avec index unique requis")
    elif any(row["couverture pluie"] < 1 or row["couverture température"] < 1 for row in climate_evidence):
        missing_information.append("Climat incomplet sur certains stades ; dates manquantes détaillées dans les preuves climatiques")
    return {"name": name, "status": status, "stages": json_safe(clean), "issues": issues,
            "agronomy": agronomy, "missing_information": missing_information,
            "potential_benefits": agronomy["potential_benefits"],
            "calculation_availability": {"etc": water is not None, "etc_reason": water_error,
                "climate_stage_evidence": bool(climate_evidence),
                "calendar_boundaries": agronomy["calendar"]["boundary_status"],
                "agronomic_validation": "not_performed"},
            "crop_results": json_safe(crop_results),
            "statuses": statuses, "coverage": coverage,
            "declared_stages": json_safe(stages),
            "checks": checks_out, "evidence": evidence, "risks": risks,
            "water": water, "water_error": water_error, "uncovered_days": uncovered,
            "climate_evidence": climate_evidence,
            "climate_provenance": json_safe(climate_provenance),
            "purpose": "Référence fournie par l’agriculteur" if name == "Rotation actuelle" else "Alternative saisie par l’agriculteur, à examiner selon ses priorités",
            "benefit": "Quantifier les compromis et les contrôles manquants ; aucun gain agronomique ou économique démontré",
            "limitations": ["Pas de diagnostic pédologique, de rendement ni de marge calculés",
                            "ETc en conditions standard ≠ irrigation nécessaire ou consommation réelle",
                            "Aucun classement global d’aptitude ; un résultat hydrique ne démontre pas l’aptitude agricole",
                            "Les validations saisies sont déclaratives, sans certification automatique"]}


def assess_comparability(results):
    """Decide whether totals share a complete period and the same ET0 basis.

    No ranking is produced. Agronomic feasibility is a separate, unverified axis.
    """
    reasons = []
    if len(results) < 2:
        reasons.append("Au moins deux rotations sont nécessaires")
    if any(not r["coverage"]["comparison_eligible"] for r in results):
        reasons.append("Cultures ou ETc incomplètes/invalides sur l’horizon attendu")
    periods = {tuple(sorted(r["coverage"]["expected_period"].items())) for r in results}
    if len(periods) > 1:
        reasons.append("Les horizons attendus diffèrent")
    bases = []
    for r in results:
        if r["water"]:
            meta = r["water"]["eto_provenance"]
            bases.append((meta["data_sha256"], meta["calculation_method"], meta["time_standard"],
                          meta["reference_surface"], tuple(sorted(meta["location"].items()))))
    if len(set(bases)) > 1:
        reasons.append("Les séries ET₀, méthodes, lieux ou standards temporels diffèrent")
    comparable = not reasons
    areas = {r["water"]["area_ha"] for r in results if r["water"]}
    return {"status": "comparable_etc_totals" if comparable else "not_comparable",
            "quantitative_comparison_allowed": comparable, "reasons": reasons,
            "volume_comparison_allowed": comparable and len(areas) == 1 and None not in areas,
            "agronomic_validation": "not_performed", "ranking": None}
