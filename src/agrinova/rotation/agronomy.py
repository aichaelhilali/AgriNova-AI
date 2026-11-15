"""Small referenced rule set for existing pilot crops, not a crop dataset.

Exact documented names only. General biological evidence never establishes
local feasibility, nitrogen credits, measured soil change or crop thresholds.
"""

from copy import deepcopy
import unicodedata

import pandas as pd

from agrinova.analysis.water import day, has_reference, WaterInputError, json_safe

REFERENCES = {
    "wheat_family": {"title": "Kew POWO · Triticum", "url": "https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:30034910-2", "scope": "Taxonomie du genre ; espèce et variété de blé non déduites."},
    "faba_family": {"title": "Kew POWO · Vicia faba", "url": "https://powo.science.kew.org/taxon/524737-1", "scope": "Taxonomie ; aucune aptitude locale déduite."},
    "chickpea_family": {"title": "Kew POWO · Cicer arietinum", "url": "https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:486336-1/general-information", "scope": "Taxonomie ; aucune aptitude locale déduite."},
    "faba_n": {"title": "USDA NRCS · Fava Bean Plant Guide", "url": "https://plants.usda.gov/DocumentLibrary/plantguide/pdf/pg_vifa.pdf", "scope": "Symbiose de Vicia faba ; guide américain, sans validation de parcelle marocaine."},
    "chickpea_n": {"title": "Australian OGTR · Biology of Cicer arietinum (2019), §7.3.1", "url": "https://www.ogtr.gov.au/sites/default/files/files/2021-07/the_biology_of_chickpeas_-_version_1_march_2019_0.pdf", "scope": "Biologie de la symbiose ; pratiques australiennes non transposées au Maroc."},
    "sequence": {"title": "FAO · What is the best cropping sequence for the farm?", "url": "https://www.fao.org/4/y5146e/y5146e0a.htm", "scope": "Principes de succession et bilan azoté ; effets dépendants du contexte, sans gain local prédit."},
    "soil_cover": {"title": "FAO · Sustainable crop rotations, chapitre 4", "url": "https://www.fao.org/4/v9926e/v9926e06.htm", "scope": "Principes de couverture et de gestion des résidus ; aucun effet mesuré ici."},
}


def normalized(value):
    if not has_reference(value):
        return None
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", value.strip().casefold())
        if not unicodedata.combining(c)).split())


def identify_crop(name):
    """No substring guesses, fuzzy matches or inferred properties for new crops."""
    word = normalized(name)
    entries = [
        ({"ble", "wheat", "triticum", "triticum spp."}, "wheat", "Triticum spp.", "Poaceae", False),
        ({"feverole", "feve", "faba bean", "fava bean", "broad bean", "vicia faba"}, "faba", "Vicia faba", "Fabaceae", True),
        ({"pois chiche", "chickpea", "chick pea", "cicer arietinum"}, "chickpea", "Cicer arietinum", "Fabaceae", True),
    ]
    for aliases, key, taxon, family, legume in entries:
        if word in aliases:
            return {"crop_id": key, "taxon": taxon, "family": family, "legume": legume,
                "identification": "documented_name_match", "reference_ids": [f"{key}_family"]}
    return {"crop_id": None, "taxon": None, "family": None, "legume": None,
        "identification": "unknown", "reference_ids": []}


def _cycles(stages):
    """Collapse explicit growth stages, not repeated undated crop entries."""
    cycles = []
    for number, row in enumerate(stages, 1):
        identity = identify_crop(row.get("crop"))
        key = (identity["crop_id"] or normalized(row.get("crop")), normalized(row.get("crop_cycle")))
        merge = bool(cycles and key[0] and key == cycles[-1]["key"] and
            (key[1] or (has_reference(row.get("growth_stage")) and
             all(has_reference(r.get("growth_stage")) for r in cycles[-1]["rows"]))))
        if merge:
            cycles[-1]["rows"].append(row)
            cycles[-1]["stage_rows"].append(number)
        else:
            cycles.append({"key": key, "crop": row.get("crop") if has_reference(row.get("crop")) else None,
                "identity": identity, "rows": [row], "stage_rows": [number]})
    return cycles


def analyze_agronomy(stages, start, end):
    """Qualitative assessment, with a separate declared-calendar calculation."""
    cycles = _cycles(stages)
    evidence, benefits, risks, missing, sequence = [], [], [], [], []
    reference_ids = set()

    def finding(target, code, text, refs=(), **details):
        target.append({"code": code, "text": text, "reference_ids": list(refs), **details})
        reference_ids.update(refs)

    for number, cycle in enumerate(cycles, 1):
        identity = cycle["identity"]
        crop = cycle["crop"] or f"Ligne {cycle['stage_rows'][0]} sans culture"
        if identity["family"] is None:
            finding(missing, "unknown_crop", f"{crop} : famille, statut de légumineuse et propriétés non vérifiés.", cycle=number)
            nitrogen = {"status": "unknown", "amount_kg_ha": None, "reference_ids": []}
        else:
            finding(evidence, "crop_family", f"{crop} : {identity['taxon']}, famille {identity['family']}.", identity["reference_ids"], cycle=number)
            if identity["legume"]:
                ref = identity["crop_id"] + "_n"
                symbiont = "Rhizobium leguminosarum bv. viciae" if identity["crop_id"] == "faba" else "Mesorhizobium spp."
                nitrogen = {"status": "conditional_potential", "symbiont": symbiont,
                    "amount_kg_ha": None, "residual_n_credit_kg_ha": None, "reference_ids": [ref, "sequence"]}
                finding(benefits, "conditional_fixation", f"{crop} : fixation d’azote possible avec une symbiose efficace ({symbiont}). Aucun apport net au sol ni crédit pour la culture suivante n’est calculé.", [ref, "sequence"], cycle=number)
                finding(missing, "nitrogen_balance", f"{crop} : nodulation, biomasse, azote minéral du sol, exportations à la récolte et devenir des résidus inconnus. Les légumineuses ne procurent pas un bénéfice azoté identique.", ["sequence"], cycle=number)
            else:
                nitrogen = {"status": "not_a_legume", "amount_kg_ha": None, "reference_ids": identity["reference_ids"]}
        cycle["nitrogen_fixation"] = nitrogen

    for number, (previous, current) in enumerate(zip(cycles, cycles[1:]), 1):
        left, right = previous["identity"], current["identity"]
        same_crop = None if not left["crop_id"] or not right["crop_id"] else left["crop_id"] == right["crop_id"]
        same_family = None if not left["family"] or not right["family"] else left["family"] == right["family"]
        sequence.append({"from_cycle": number, "to_cycle": number + 1,
            "same_crop": same_crop, "same_family": same_family, "basis": "entered_order"})
        if same_crop is True or same_family is True:
            finding(risks, "repetition", f"Cycles {number} → {number + 1} : répétition de culture ou de famille. Risque de maintien de certains bioagresseurs à examiner selon leurs hôtes et l’historique ; aucune infestation n’est diagnostiquée.", ["sequence"])
        elif same_family is False:
            finding(benefits, "family_change", f"Cycles {number} → {number + 1} : changement de famille. Une rupture de certains cycles de maladies est possible si les cultures ne partagent pas les hôtes concernés ; efficacité locale inconnue.", ["sequence"])
        else:
            finding(missing, "sequence_unknown", f"Cycles {number} → {number + 1} : propriétés non vérifiées, effet de succession inconnu.")

    calendar_errors, boundaries = [], []
    for number, cycle in enumerate(cycles, 1):
        parsed = {}
        for field in ("planting_date", "harvest_date"):
            values = []
            for row in cycle["rows"]:
                value = row.get(field)
                if value is None or (not isinstance(value, (dict, list)) and pd.isna(value)) or value == "":
                    continue
                try:
                    values.append(day(value))
                except WaterInputError:
                    calendar_errors.append(f"Cycle {number} : {field} invalide.")
            if len(set(values)) > 1:
                calendar_errors.append(f"Cycle {number} : dates {field} contradictoires entre stades.")
            parsed[field] = values[0] if values else None
        planting, harvest = parsed["planting_date"], parsed["harvest_date"]
        if planting is None or harvest is None:
            finding(missing, "crop_boundaries", f"Cycle {number} : dates explicites de semis et de récolte requises pour analyser les intercultures ; les dates de stades ne les remplacent pas.")
        else:
            if planting > harvest or planting < day(start) or harvest > day(end):
                calendar_errors.append(f"Cycle {number} : semis/récolte inversés ou hors horizon commun.")
            for row in cycle["rows"]:
                try:
                    a, b = day(row.get("start")), day(row.get("end"))
                    if a < planting or b > harvest or a > b:
                        calendar_errors.append(f"Cycle {number} : stade hors des limites semis/récolte.")
                except WaterInputError:
                    pass  # Existing stage validation reports absent dates separately.
        boundaries.append(parsed)
    complete_boundaries = bool(cycles) and all(b["planting_date"] is not None and b["harvest_date"] is not None for b in boundaries)
    periods = []
    for number, (previous, current) in enumerate(zip(boundaries, boundaries[1:]), 1):
        if previous["harvest_date"] is not None and current["planting_date"] is not None:
            if current["planting_date"] <= previous["harvest_date"]:
                calendar_errors.append(f"Cycles {number} → {number + 1} : chevauchement ou ordre semis/récolte invalide.")
            elif complete_boundaries:
                a, b = previous["harvest_date"] + pd.Timedelta(days=1), current["planting_date"] - pd.Timedelta(days=1)
                if a <= b:
                    periods.append({"start": a.date().isoformat(), "end": b.date().isoformat(), "days": (b-a).days + 1,
                        "after_cycle": number, "before_cycle": number + 1,
                        "actual_soil_cover": "unknown", "status": "potential_uncovered_intercrop"})
    if calendar_errors:
        periods = []
    finding(missing, "local_calendar", "Compatibilité avec les fenêtres locales, variété, matériel et main-d’œuvre non vérifiée ; aucun calendrier de semis local n’est imposé.")
    finding(missing, "soil_management", "Analyses du sol, pente, couverture réelle, travail du sol et gestion des résidus à renseigner.")
    if cycles:
        finding(benefits, "soil_cover_conditional", "Une couverture et une gestion appropriées des résidus peuvent contribuer à protéger le sol ; leur présence et leurs effets sur cette parcelle ne sont pas établis.", ["soil_cover"])
    if periods:
        finding(risks, "potential_bare_soil", "Intercultures repérées entre récolte et semis : risque d’exposition du sol si aucun couvert ni résidu protecteur n’est présent. Les dates seules ne prouvent pas un sol nu.", ["soil_cover"])
    public_cycles = [{"number": i, "crop": c["crop"], "crop_cycle": c["key"][1], "stage_rows": c["stage_rows"],
        **c["identity"], "nitrogen_fixation": c["nitrogen_fixation"], **boundaries[i-1]} for i, c in enumerate(cycles, 1)]
    return json_safe({"method_version": "referenced_rotation_rules_v1", "cycles": public_cycles,
        "sequence": sequence, "evidence": evidence, "potential_benefits": benefits, "risks": risks,
        "missing_information": missing, "calendar": {"boundary_status": "invalid" if calendar_errors else ("complete_declared" if complete_boundaries else "unknown"),
            "errors": calendar_errors, "potential_bare_soil_periods": periods,
            "local_agronomic_compatibility": "not_verified", "scope": "internal_intercrop_intervals_only"},
        "references": [{"id": key, **deepcopy(REFERENCES[key])} for key in sorted(reference_ids)],
        "limitations": ["Identification limitée aux noms documentés du blé, de la féverole et du pois chiche ; autres cultures inconnues.",
            "Les stades d’un même cycle ne sont pas des répétitions culturales ; distinguer les cycles successifs avec leur identifiant.",
            "Ordre déclaré analysé sans réorganisation ; dates absentes : chronologie non vérifiable.",
            "Principes généraux référencés, sans mesure d’amélioration du sol ni validation agronomique locale.",
            "Aucun crédit azoté, rendement, score d’aptitude ou meilleur choix automatique."]})
