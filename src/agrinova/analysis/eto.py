"""Daily grass-reference ET0, FAO Irrigation and Drainage Paper 56.

Equations 6-9, 11-13, 17/19, 21-25, 37-40, 42 and 47.
https://www.fao.org/4/X0490E/x0490e07.htm
https://www.fao.org/4/X0490E/x0490e08.htm (independent example 18).
No missing-weather substitution, crop coefficients, or irrigation calculation.
"""

from dataclasses import dataclass
from math import acos, cos, exp, isfinite, log, pi, sin, sqrt, tan

import pandas as pd

FAO_METEOROLOGY = "https://www.fao.org/4/X0490E/x0490e07.htm"
FAO_REFERENCE_CASE = "https://www.fao.org/4/X0490E/x0490e08.htm"
REQUIRED_POWER_UNITS = {"T2M": "C", "T2M_MIN": "C", "T2M_MAX": "C", "RH2M": "%",
                        "WS2M": "m/s", "ALLSKY_SFC_SW_DWN": "MJ/m^2/day", "PS": "kPa"}


class EtoError(ValueError):
    """An input or output cannot support the documented daily method."""


def finite(value, name):
    if isinstance(value, bool):
        raise EtoError(f"{name} : valeur booléenne invalide")
    try:
        number = float(value)
        if not isfinite(number):
            raise ValueError()
        return number
    except (TypeError, ValueError, OverflowError) as exc:
        raise EtoError(f"{name} : valeur absente ou non finie") from exc


def saturation_pressure(temperature_c):
    """Eq. 11, kPa; reject inputs outside the equation's mathematical domain."""
    t = finite(temperature_c, "température")
    if t <= -237.3:
        raise EtoError("Température hors domaine de la pression de vapeur saturante")
    try:
        return finite(0.6108 * exp(17.27 * t / (t + 237.3)), "pression de vapeur saturante")
    except OverflowError as exc:
        raise EtoError("Pression de vapeur saturante non finie") from exc


def pressure_from_elevation(elevation_m):
    """FAO eq. 7, kPa, only for explicitly sourced elevation; never a default."""
    z = finite(elevation_m, "altitude")
    base = (293 - .0065 * z) / 293
    if base <= 0:
        raise EtoError("Altitude hors domaine de l’équation FAO-56")
    return finite(101.3 * base ** 5.26, "pression atmosphérique")


def wind_at_two_metres(speed_ms, measurement_height_m):
    """FAO eq. 47; not applied to POWER WS2M (already at two metres)."""
    speed, height = finite(speed_ms, "vent"), finite(measurement_height_m, "hauteur du vent")
    if speed < 0 or 67.8 * height - 5.42 <= 1:
        raise EtoError("Vent ou hauteur de mesure hors domaine")
    return finite(speed * 4.87 / log(67.8 * height - 5.42), "vent à 2 m")


def vapour_pressure_from_rh(tmin_c, tmax_c, *, rh_mean=None, rh_min=None, rh_max=None):
    """Eq. 17 for RH extrema, or explicit eq. 19 for daily mean RH.

    POWER supplies a time-averaged daily RH. Its use in eq. 19 is an identified
    approximation, not an inference of absent RH extrema. Eq. 17 is used by the
    published reference case, never fabricated from RH2M.
    """
    emin, emax = saturation_pressure(tmin_c), saturation_pressure(tmax_c)
    if rh_min is not None or rh_max is not None:
        low, high = finite(rh_min, "RHmin"), finite(rh_max, "RHmax")
        if not 0 <= low <= high <= 100:
            raise EtoError("RHmin/RHmax hors [0,100] ou inversées")
        return (emin * high + emax * low) / 200
    rh = finite(rh_mean, "RH moyenne")
    if not 0 <= rh <= 100:
        raise EtoError("RH moyenne hors [0,100] %")
    return (emin + emax) / 2 * rh / 100


def fao56_daily(*, tmin_c, tmax_c, wind_2m_ms, solar_mj_m2_day,
                pressure_kpa, actual_vapour_pressure_kpa, latitude_deg, day_of_year, elevation_m):
    """FAO daily eq. 6, with reference-surface net radiation (not crop albedo).

    Tmean=(Tmax+Tmin)/2 (eq.9); albedo=.23 (reference grass); G=0 (eq.42,
    daily reference grass); Stefan-Boltzmann=4.903e-9 MJ/K4/m2/day.
    The documented Rs/Rso upper limit is 1 (eq.39). The FAO recommended
    minimum u2=0.5 m/s is recorded separately from the input wind; it accounts
    for buoyancy in calm conditions and is not a fabricated observation.
    No arbitrary lower radiation bound or negative-output clipping is applied.
    """
    tmin, tmax = finite(tmin_c, "Tmin"), finite(tmax_c, "Tmax")
    u2, rs, p = finite(wind_2m_ms, "WS2M"), finite(solar_mj_m2_day, "Rs"), finite(pressure_kpa, "PS")
    ea, lat = finite(actual_vapour_pressure_kpa, "ea"), finite(latitude_deg, "latitude")
    doy, z = finite(day_of_year, "jour de l’année"), finite(elevation_m, "altitude")
    if tmin > tmax or tmin <= -237.3 or u2 < 0 or rs < 0 or p <= 0 or ea < 0:
        raise EtoError("Entrées physiques incohérentes : températures, vent, rayonnement, pression ou vapeur")
    if not -90 <= lat <= 90 or not 1 <= doy <= 366 or doy != int(doy):
        raise EtoError("Latitude ou jour de l’année invalide")
    try:
        raw_wind = u2
        u2 = max(u2, .5)  # FAO-56 chapter 3, low-wind/buoyancy recommendation.
        tmean = (tmin + tmax) / 2
        es = (saturation_pressure(tmin) + saturation_pressure(tmax)) / 2
        if ea > es:
            raise EtoError("Pression de vapeur réelle supérieure à la saturation moyenne")
        delta = 4098 * saturation_pressure(tmean) / (tmean + 237.3) ** 2
        gamma = .000665 * p
        phi = lat * pi / 180
        dr = 1 + .033 * cos(2 * pi * doy / 365)
        declination = .409 * sin(2 * pi * doy / 365 - 1.39)
        sunset = acos(max(-1., min(1., -tan(phi) * tan(declination))))
        ra = 24 * 60 / pi * .0820 * dr * (sunset * sin(phi) * sin(declination) + cos(phi) * cos(declination) * sin(sunset))
        rso = (.75 + 2e-5 * z) * ra
        if not isfinite(rso) or rso <= 0:
            raise EtoError("Rayonnement de ciel clair nul/invalide : calcul journalier indisponible")
        raw_ratio = rs / rso
        ratio = min(raw_ratio, 1.)  # FAO eq.39 explicit upper bound, recorded below.
        cloud = 1.35 * ratio - .35
        emissivity = .34 - .14 * sqrt(ea)
        if cloud < 0:
            raise EtoError(f"Facteur radiatif FAO-56 négatif (nébulosité eq.39) : Rs/Rso={raw_ratio:.6f}, facteur={cloud:.6f}. Aucun remplacement arbitraire.")
        if emissivity < 0:
            raise EtoError(f"Facteur radiatif FAO-56 négatif (humidité eq.39) : ea={ea:.6f} kPa. Calcul indisponible.")
        rns = .77 * rs
        rnl = 4.903e-9 * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * emissivity * cloud
        rn = rns - rnl
        denominator = delta + gamma * (1 + .34 * u2)
        eto = (.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea)) / denominator
        output = {"eto_mm": eto, "tmean_fao_c": tmean, "es_kpa": es, "ea_kpa": ea,
                  "delta_kpa_c": delta, "gamma_kpa_c": gamma, "ra_mj_m2_day": ra,
                  "rso_mj_m2_day": rso, "rs_mj_m2_day": rs, "rns_mj_m2_day": rns,
                  "rnl_mj_m2_day": rnl, "rn_mj_m2_day": rn, "g_mj_m2_day": 0.,
                  "rs_rso_uncapped": raw_ratio, "rs_rso_used": ratio,
                  "wind_2m_input_ms": raw_wind, "wind_2m_used_ms": u2}
        if not all(isfinite(v) for v in output.values()):
            raise EtoError("Résultat ou intermédiaire FAO-56 non fini")
        if eto < 0:
            raise EtoError("ET₀ calculée négative : indisponible, sans remplacement par zéro")
        return output
    except (OverflowError, ZeroDivisionError, ValueError) as exc:
        if isinstance(exc, EtoError):
            raise
        raise EtoError(f"Calcul FAO-56 hors domaine numérique : {exc}") from exc


@dataclass
class EtoResult:
    daily: pd.DataFrame
    provenance: dict

    @property
    def complete(self):
        return not self.daily.empty and bool(self.daily["eto_mm"].notna().all())

    def available_frame(self):
        """Never silently export a partial series as a complete input for ETc."""
        if not self.complete:
            raise EtoError("ET₀ indisponible sur la période complète ; consulter les motifs journaliers")
        return self.daily[["eto_mm"]].rename_axis("date").reset_index()


def calculate_power_eto(climate):
    """Adapt verified POWER daily UTC variables, with explicit availability per day."""
    provenance = climate.provenance
    units = provenance.get("units", {})
    global_issues = []
    if provenance.get("time_standard") != "UTC":
        global_issues.append("Standard temporel UTC absent ou différent")
    for variable, expected_unit in REQUIRED_POWER_UNITS.items():
        if variable not in climate.daily:
            global_issues.append(f"Variable manquante : {variable}")
        if units.get(variable) not in ({expected_unit, "kW-hr/m^2/day"} if variable == "ALLSKY_SFC_SW_DWN" else {expected_unit}):
            global_issues.append(f"Unité invalide/absente : {variable} ({units.get(variable)!r}), attendue {expected_unit}")
    try:
        elevation = finite(provenance.get("grid_elevation_m"), "Altitude MERRA-2 documentée")
        point = provenance["requested_coordinates"]
        latitude = finite(point["latitude"], "latitude")
        if not provenance.get("grid_elevation_source"):
            raise EtoError("Source de l’altitude absente")
    except (KeyError, EtoError) as exc:
        elevation, latitude = None, None
        global_issues.append(str(exc))
    index = pd.date_range(provenance["start"], provenance["end"], freq="D", name="date")
    if (not isinstance(climate.daily.index, pd.DatetimeIndex) or climate.daily.index.has_duplicates
            or climate.daily.index.tz is not None):
        global_issues.append("Index météo dupliqué ou muni d’un fuseau inattendu")
        frame = pd.DataFrame(index=index)
    else:
        frame = climate.daily.reindex(index)
    rows = []
    for date, weather in frame.iterrows():
        issues = list(global_issues)
        missing = [v for v in REQUIRED_POWER_UNITS if v not in weather or pd.isna(weather[v])]
        if missing:
            issues.append("Valeurs manquantes : " + ", ".join(missing))
        output = {"date": date, "eto_mm": float("nan"), "reason": ""}
        if not issues:
            try:
                mean = finite(weather.T2M, "T2M")
                tmin, tmax = finite(weather.T2M_MIN, "Tmin"), finite(weather.T2M_MAX, "Tmax")
                if not tmin <= mean <= tmax:
                    raise EtoError("T2M hors intervalle Tmin–Tmax")
                ea = vapour_pressure_from_rh(tmin, tmax, rh_mean=weather.RH2M)
                radiation = finite(weather.ALLSKY_SFC_SW_DWN, "ALLSKY_SFC_SW_DWN")
                if units["ALLSKY_SFC_SW_DWN"] == "kW-hr/m^2/day":
                    radiation *= 3.6  # exact kWh→MJ conversion, never a weather estimate.
                output.update(fao56_daily(tmin_c=tmin, tmax_c=tmax, wind_2m_ms=weather.WS2M,
                    solar_mj_m2_day=radiation, pressure_kpa=weather.PS, actual_vapour_pressure_kpa=ea,
                    latitude_deg=latitude, day_of_year=date.dayofyear, elevation_m=elevation))
            except EtoError as exc:
                issues.append(str(exc))
        output["reason"] = "; ".join(issues)
        rows.append(output)
    daily = pd.DataFrame(rows).set_index("date")
    return EtoResult(daily, {
        "source": "NASA POWER daily AG UTC", "source_payload_sha256": provenance.get("payload_sha256"),
        "source_url": provenance.get("url"), "method": "FAO-56 Penman-Monteith daily eq.6",
        "method_version": "agrinova_fao56_daily_v1", "references": [FAO_METEOROLOGY, FAO_REFERENCE_CASE],
        "reference_case": "FAO-56 chapter 4 example 18, Uccle 6 July: approximately 3.9 mm/day",
        "units": "mm/day", "reference_surface": "short_grass", "time_standard": "UTC",
        "location": provenance.get("requested_coordinates"), "period": {"start": provenance["start"], "end": provenance["end"]},
        "input_units": {v: units.get(v) for v in REQUIRED_POWER_UNITS},
        "elevation_m": elevation, "elevation_source": provenance.get("grid_elevation_source"),
        "expected_days": len(index), "available_days": int(daily.eto_mm.count()),
        "missing_days": int(daily.eto_mm.isna().sum()),
        "unavailable_dates": [value.date().isoformat() for value in daily.index[daily.eto_mm.isna()]],
        "assumptions": ["Tmean FAO = (Tmax+Tmin)/2 ; T2M NASA conservée pour le climat et le contrôle qualité",
            "ea via RH2M moyenne et équation 19 : approximation documentée, moins souhaitable que RHmin/RHmax",
            "Albédo 0,23 et G journalier nul pour l’herbe de référence (FAO-56)",
            "Altitude moyenne de maille MERRA-2, pas une altitude de parcelle mesurée",
            "Rso FAO eq.37 ; Rs/Rso limité à 1 selon eq.39, sans borne inférieure inventée",
            "WS2M déjà à 2 m ; minimum de calcul 0,5 m/s recommandé par FAO-56 pour la convection en air calme, avec vent source conservé",
            "Aucune interpolation ni estimation d’une variable météo manquante"],
        "validation": "Équations et cas de référence vérifiables ; aucune validation agronomique locale indépendante",
    })
