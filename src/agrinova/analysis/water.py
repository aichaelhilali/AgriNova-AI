"""FAO-56 single-coefficient arithmetic; no inferred crop coefficients or ET0."""

from hashlib import sha256
from math import fsum, isfinite

import pandas as pd


class WaterInputError(ValueError):
    pass


def has_reference(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {
        "nan", "none", "null", "nat", "<na>", "unknown", "inconnu", "inconnue", "à renseigner"}


def json_safe(value):
    """Preserve rejected inputs explicitly without invalid JSON NaN/Infinity."""
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not isfinite(value):
        return None if pd.isna(value) else str(value)
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def day(value):
    """Accept a calendar day, never silently discard time or timezone information."""
    try:
        result = pd.Timestamp(value)
        if pd.isna(result) or result.tzinfo is not None or result != result.normalize():
            raise ValueError()
        return result
    except (ValueError, TypeError, OverflowError) as exc:
        raise WaterInputError("Date journalière absente ou invalide (sans heure ni fuseau)") from exc


def location(value):
    try:
        lat, lon = value["latitude"], value["longitude"]
        if isinstance(lat, bool) or isinstance(lon, bool):
            raise ValueError()
        lat, lon = float(lat), float(lon)
        if not isfinite(lat) or not isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError()
        return {"latitude": lat, "longitude": lon}
    except (KeyError, TypeError, ValueError) as exc:
        raise WaterInputError("Localisation : latitude et longitude explicites requises") from exc


def declared_reference(metadata):
    if metadata.get("reference_status", "user_declared") != "user_declared":
        raise WaterInputError("Une déclaration utilisateur ne constitue pas une vérification indépendante")
    return {"reference_status": "user_declared", "independent_verification": "not_performed"}


def validate_eto(frame, source, validated, metadata=None, expected_location=None):
    """Validate structure and declared provenance, not scientific FAO-56 compliance.

    Series.attrs carries the provenance into calculations and exports. No external
    reference is independently verified by a checkbox or by these file checks.
    """
    if validated is not True or not has_reference(source):
        raise WaterInputError("ET₀ : source et confirmation de la déclaration requises")
    if not {"date", "eto_mm"}.issubset(frame.columns):
        raise WaterInputError("Le CSV ET₀ doit contenir date et eto_mm")
    result = frame[["date", "eto_mm"]].copy()
    try:
        result["date"] = pd.to_datetime(result["date"], format="%Y-%m-%d", errors="raise")
        result["eto_mm"] = pd.to_numeric(result["eto_mm"], errors="raise").astype(float)
    except (ValueError, TypeError) as exc:
        raise WaterInputError(f"CSV ET₀ invalide : {exc}") from exc
    if result.empty or result["date"].isna().any() or result["date"].duplicated().any():
        raise WaterInputError("ET₀ : dates absentes ou dupliquées")
    if result["date"].dt.tz is not None:
        raise WaterInputError("ET₀ : fournir des dates journalières sans heure, avec UTC dans les métadonnées")
    if not (result["date"] == result["date"].dt.normalize()).all():
        raise WaterInputError("ET₀ doit avoir un pas journalier sans heure")
    if not result["eto_mm"].map(isfinite).all() or (result["eto_mm"] < 0).any():
        raise WaterInputError("ET₀ : valeurs manquantes, infinies ou négatives")
    if metadata is not None and not isinstance(metadata, dict):
        raise WaterInputError("ET₀ : métadonnées structurées requises")
    meta = dict(metadata or {})
    if not has_reference(meta.get("calculation_method")):
        raise WaterInputError("ET₀ : méthode de calcul à documenter")
    if meta.get("units") != "mm/day":
        raise WaterInputError("ET₀ : unité explicite mm/day requise ; aucune conversion implicite")
    if meta.get("reference_surface") != "short_grass":
        raise WaterInputError("ET₀ : surface de référence herbe courte requise pour ce calcul")
    if meta.get("time_standard") != "UTC":
        raise WaterInputError("ET₀ : standard UTC explicite requis ; aucune conversion de dates implicite")
    site = location(meta.get("location"))
    if expected_location is not None:
        target = location(expected_location)
        if any(abs(site[key] - target[key]) > 0.0001 for key in site):
            raise WaterInputError("ET₀ : localisation différente du point d’étude")
    series = result.set_index("date").sort_index()["eto_mm"]
    period = {"start": series.index.min().date().isoformat(), "end": series.index.max().date().isoformat()}
    if "period" in meta and meta["period"] != period:
        raise WaterInputError("ET₀ : période déclarée différente des dates du fichier")
    series.attrs["agrinova_metadata"] = {
        "source": source.strip(), "calculation_method": meta["calculation_method"].strip(),
        "units": "mm/day", "reference_surface": "short_grass", "location": site,
        "period": period, "time_standard": "UTC", **declared_reference(meta),
        "declaration_confirmed": True, "structural_validation": "passed",
        "fao56_compliance": "not_verified",
        "data_sha256": sha256(series.to_csv(date_format="%Y-%m-%d").encode("utf-8")).hexdigest(),
    }
    return series


def calculate_etc(stages, eto, area_ha=None):
    """Stages must cover the full declared crop schedule without overlaps.

    Gaps between crops are reported separately by the comparison engine: the
    result covers declared crop stages, never soil evaporation on fallow days.
    """
    if eto is None:
        raise WaterInputError("ET₀ journalière documentée indisponible")
    if not stages:
        raise WaterInputError("Aucun stade cultural saisi")
    if area_ha is not None and (isinstance(area_ha, bool) or not isfinite(area_ha) or area_ha <= 0):
        raise WaterInputError("La surface doit être positive et finie")
    provenance = eto.attrs.get("agrinova_metadata", {})
    if provenance.get("structural_validation") != "passed":
        raise WaterInputError("ET₀ : importer la série avec ses métadonnées avant calcul")
    # Recheck a copied/mutated Series at the calculation boundary.
    checked_eto = validate_eto(eto.rename("eto_mm").rename_axis("date").reset_index(),
        provenance.get("source"), provenance.get("declaration_confirmed"), provenance)
    seen = set()
    records = []
    coefficients = []
    previous_start = None
    for stage in stages:
        if not has_reference(stage.get("crop")):
            raise WaterInputError("Culture manquante")
        if stage.get("validated") is not True or not has_reference(stage.get("kc_source")):
            raise WaterInputError("Kc : référence par stade et applicabilité déclarée requises")
        try:
            if isinstance(stage.get("kc"), bool):
                raise ValueError()
            kc = float(stage["kc"])
            start, end = day(stage["start"]), day(stage["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise WaterInputError("Kc ou dates absents/invalides") from exc
        if not isfinite(kc) or kc < 0:
            raise WaterInputError("Kc doit être fini et positif ou nul")
        if pd.isna(start) or pd.isna(end) or start > end:
            raise WaterInputError("Dates de stade invalides")
        if previous_start is not None and start < previous_start:
            raise WaterInputError("Ordre chronologique des stades invalide ; aucune réorganisation automatique")
        previous_start = start
        if not has_reference(stage.get("growth_stage")) or not has_reference(stage.get("regional_applicability")):
            raise WaterInputError("Kc : stade de croissance et applicabilité régionale à documenter")
        if stage.get("kc_reference_surface") != provenance["reference_surface"]:
            raise WaterInputError("Kc : surface de référence absente ou différente de celle de l’ET₀")
        reference = declared_reference({"reference_status": stage.get("reference_status", "user_declared")})
        coefficients.append({"crop": stage["crop"].strip(), "growth_stage": stage["growth_stage"].strip(),
            "coefficient": kc, "source": stage["kc_source"].strip(),
            "regional_applicability": stage["regional_applicability"].strip(),
            "reference_surface": stage["kc_reference_surface"],
            "period": {"start": start.date().isoformat(), "end": end.date().isoformat()}, **reference})
        dates = pd.date_range(start, end, freq="D")
        if seen.intersection(dates):
            raise WaterInputError("Chevauchement de stades : risque de double comptage")
        seen.update(dates)
        values = checked_eto.reindex(dates)
        if values.isna().any() or not values.map(isfinite).all() or (values < 0).any():
            bad = values.isna() | ~values.map(isfinite) | (values < 0)
            raise WaterInputError("ET₀ incomplète ou invalide pour les dates culturales : " +
                ", ".join(d.date().isoformat() for d in dates[bad]))
        for current_day, value in values.items():
            product = float(value) * kc
            if not isfinite(product):
                raise WaterInputError("ETc non finie : produit ET₀ × Kc hors domaine numérique")
            records.append({"date": current_day.date().isoformat(), "culture": stage["crop"], "eto_mm": float(value),
                            "growth_stage": stage["growth_stage"], "stage_number": len(coefficients),
                            "kc": kc, "etc_mm": product, "kc_source": stage["kc_source"]})
    daily = pd.DataFrame(records).sort_values("date")
    try:
        total = fsum(daily["etc_mm"])
        volume = None if area_ha is None else total * area_ha * 10
        if not isfinite(total) or (volume is not None and not isfinite(volume)):
            raise OverflowError()
    except OverflowError as exc:
        raise WaterInputError("Total ETc ou volume non fini : calcul refusé") from exc
    return {"etc_mm": total, "volume_m3": volume, "area_ha": area_ha,
            "days": len(daily), "daily": daily.to_dict(orient="records"),
            "method": "daily_single_coefficient_v2", "units": {"etc_mm": "mm", "volume_m3": "m3"},
            "eto_provenance": checked_eto.attrs["agrinova_metadata"], "kc_metadata": coefficients,
            "eto_derivation": eto.attrs.get("eto_derivation"),
            "limitations": ["Kc constant sur chaque intervalle documenté ; aucune interpolation automatique.",
                "ETc standard modélisée, pas un besoin d’irrigation ni une consommation mesurée."]}
