"""Season-scoped ETc workflow; no crop parameters or calendars are supplied.

Each entered interval uses a constant, user-documented Kc. Development/late
season curves must be supplied as sufficiently resolved intervals; no automatic
FAO curve construction, local calibration, or interpolation is claimed.
"""

from math import isfinite

import pandas as pd

from agrinova.analysis.water import WaterInputError, calculate_etc, day, validate_eto, has_reference

FAO_CROP_REFERENCE = "https://www.fao.org/4/X0490E/x0490e0b.htm"


def computed_eto_for_crops(result, expected_location=None):
    """Keep available daily values, explicitly retaining full derivation and gaps.

    This is not a complete-period export. calculate_etc still requires every day
    of each selected crop interval. Missing days are never filled or interpolated.
    """
    for key, expected in {"units": "mm/day", "time_standard": "UTC", "reference_surface": "short_grass"}.items():
        if result.provenance.get(key) != expected:
            raise WaterInputError(f"ET₀ calculée : métadonnée {key} invalide ou absente ; attendu {expected}")
    frame = result.daily[["eto_mm"]].copy()
    valid = frame.eto_mm.map(lambda v: pd.notna(v) and isfinite(v) and v >= 0)
    if not valid.any():
        raise WaterInputError("ET₀ : aucun jour calculable disponible")
    series = validate_eto(frame.loc[valid].rename_axis("date").reset_index(),
        result.provenance.get("source_url") or "NASA POWER · FAO-56 calculée",
        True, metadata={"calculation_method": "FAO-56 eq.6, RH moyenne eq.19, Rn eq.37–40, G=0 quotidien",
            "units": "mm/day", "reference_surface": "short_grass", "time_standard": "UTC",
            "location": result.provenance["location"]}, expected_location=expected_location)
    series.attrs["eto_derivation"] = result.provenance
    series.attrs["unavailable_dates"] = [d.date().isoformat() for d in frame.index[~valid]]
    return series


def crop_water_results(stages, eto, area_ha=None):
    """Report consecutive same-crop intervals as one explicitly entered season.

    A change of crop starts another season. Consecutive cycles of the same crop
    can be separated using an optional crop_cycle identifier. Gaps inside a
    season prevent a seasonal total, even if all entered stages are calculable.
    All stages of a crop must be complete before its total is exposed.
    """
    groups = []
    for stage in stages:
        cycle = stage.get("crop_cycle")
        key = (stage.get("crop"), cycle.strip() if has_reference(cycle) else None)
        if not groups or groups[-1][0] != key:
            groups.append((key, []))
        groups[-1][1].append(stage)
    reports = []
    for (crop, cycle), rows in groups:
        report = {"crop": crop, "crop_cycle": cycle, "status": "unavailable", "water": None,
            "error": None, "stages": [], "agronomic_validation": "not_performed",
            "method_reference": FAO_CROP_REFERENCE,
            "limitations": ["Kc constant sur chaque intervalle saisi ; aucune courbe interpolée automatiquement.",
                "Références et applicabilité déclarées, sans validation locale indépendante au Maroc.",
                "ETc en conditions standard modélisées, ni consommation mesurée ni besoin d’irrigation.",
                "La saison est définie par les dates saisies ; semis et récolte ne sont pas vérifiés."]}
        try:
            first, last = day(rows[0]["start"]), day(rows[-1]["end"])
            if first > last:
                raise WaterInputError("Saison : ordre chronologique invalide")
            expected = pd.date_range(first, last)
            declared = set()
            for row in rows:
                a, b = day(row.get("start")), day(row.get("end"))
                if a > b:
                    raise WaterInputError("Dates de stade invalides")
                declared.update(pd.date_range(a, b))
                dates = pd.date_range(a, b)
                values = eto.reindex(dates) if eto is not None else pd.Series(index=dates, dtype=float)
                valid = values.map(lambda v: pd.notna(v) and isfinite(v) and v >= 0)
                report["stages"].append({"growth_stage": row.get("growth_stage"),
                    "start": a.date().isoformat(), "end": b.date().isoformat(),
                    "expected_days": len(dates), "available_eto_days": int(valid.sum()),
                    "missing_eto_dates": [d.date().isoformat() for d in dates[~valid]],
                    "kc": row.get("kc"), "source": row.get("kc_source"),
                    "applicability": row.get("regional_applicability"),
                    "validation_status": "user_declared" if row.get("validated") is True else "not_confirmed",
                    "independent_verification": "not_performed"})
            values = eto.reindex(expected) if eto is not None else pd.Series(index=expected, dtype=float)
            valid = values.map(lambda v: pd.notna(v) and isfinite(v) and v >= 0)
            missing = expected[~valid]
            stage_gaps = set(expected) - declared
            report["coverage"] = {"start": first.date().isoformat(), "end": last.date().isoformat(),
                "expected_days": len(expected), "available_eto_days": int(valid.sum()),
                "eto_fraction": float(valid.mean()),
                "missing_eto_dates": [d.date().isoformat() for d in missing],
                "missing_stage_dates": [d.date().isoformat() for d in sorted(stage_gaps)],
                "required_fraction": 1.0}
            if stage_gaps:
                raise WaterInputError("Saison : jours sans Kc/stade : " + ", ".join(report["coverage"]["missing_stage_dates"]))
            if len(missing):
                raise WaterInputError("ET₀ manquante aux dates culturales : " + ", ".join(report["coverage"]["missing_eto_dates"]))
            water = calculate_etc(rows, eto, area_ha)
            # The existing strict service checks coefficients, metadata and all
            # intervals. Sum each interval independently for auditable contributions.
            for row, stage_report in zip(rows, report["stages"]):
                stage_report["etc_mm"] = calculate_etc([row], eto)["etc_mm"]
            cumulative = 0.
            for record in water["daily"]:
                cumulative += record["etc_mm"]
                if not isfinite(cumulative):
                    raise WaterInputError("Cumul ETc non fini")
                record["cumulative_etc_mm"] = cumulative
            report.update(status="complete", water=water)
        except (WaterInputError, KeyError, TypeError, ValueError) as exc:
            report["error"] = str(exc)
        if "coverage" in report:
            report["coverage"].update(calculated_etc_days=len(report["water"]["daily"]) if report["water"] else 0,
                etc_fraction=1.0 if report["water"] else 0.0,
                seasonal_total_available=report["water"] is not None)
        reports.append(report)
    return reports
