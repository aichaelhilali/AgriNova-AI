"""NASA POWER daily point access. Never substitute fabricated observations."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import isfinite
from hashlib import sha256
import json
from copy import deepcopy

import pandas as pd
import requests

ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = ("T2M", "T2M_MIN", "T2M_MAX", "PRECTOTCORR")
ET0_PARAMETERS = ("RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PS")
REQUEST_PARAMETERS = PARAMETERS + ET0_PARAMETERS


class PowerError(ValueError):
    """Unavailable or scientifically unusable POWER response."""


@dataclass
class ClimateData:
    daily: pd.DataFrame
    provenance: dict
    raw_payload: dict


def parse_response(payload, start, end, latitude, longitude, url):
    payload = deepcopy(payload)
    try:
        if payload["header"].get("time_standard") != "UTC":
            raise ValueError("Standard temporel NASA différent de UTC ou absent")
        geometry = payload["geometry"]
        if geometry.get("type") != "Point":
            raise ValueError("Géométrie NASA attendue : Point")
        returned_lon, returned_lat = map(float, geometry["coordinates"][:2])
        if (not isfinite(returned_lon) or not isfinite(returned_lat)
                or abs(returned_lon - longitude) > 0.0001 or abs(returned_lat - latitude) > 0.0001):
            raise ValueError("Coordonnées NASA retournées différentes du point demandé")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        series = payload["properties"]["parameter"]
        metadata = payload["parameters"]
        fill = float(payload["header"]["fill_value"])
        index = pd.date_range(start, end, freq="D", name="date")
        frame = pd.DataFrame(index=index)
        units = {}
        for variable in REQUEST_PARAMETERS:
            # Preserve climate charts if ancillary ET0 variables are absent.
            # Their absence is reported by the ET0 service, never filled.
            if variable in ET0_PARAMETERS and variable not in series:
                frame[variable] = float("nan")
                units[variable] = metadata.get(variable, {}).get("units")
                continue
            values = series[variable]
            units[variable] = metadata.get(variable, {}).get("units") if variable in ET0_PARAMETERS else metadata[variable]["units"]
            if not isinstance(values, dict):
                raise ValueError(f"Série invalide : {variable}")
            parsed = pd.Series({pd.to_datetime(k, format="%Y%m%d"): v for k, v in values.items()})
            parsed = pd.to_numeric(parsed, errors="raise").astype(float)
            frame[variable] = parsed.reindex(index)
            frame[variable] = frame[variable].mask(
                (frame[variable] == fill) | ~frame[variable].map(isfinite)
            )
        if any(units[v].upper() != "C" for v in PARAMETERS[:3]):
            raise ValueError(f"Unités de température inattendues : {units}")
        if units["PRECTOTCORR"].lower() != "mm/day":
            raise ValueError(f"Unité de précipitation inattendue : {units['PRECTOTCORR']}")
        if (frame["PRECTOTCORR"].dropna() < 0).any():
            raise ValueError("Précipitation négative hors valeur manquante")
        complete_temp = frame[list(PARAMETERS[:3])].dropna()
        if ((complete_temp.T2M_MIN > complete_temp.T2M) | (complete_temp.T2M > complete_temp.T2M_MAX)).any():
            raise ValueError("Températures min/moyenne/max incohérentes")
        if not frame.notna().any().any():
            raise ValueError("Aucune observation exploitable pour la période")
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
        raise PowerError(f"Réponse NASA POWER non exploitable : {exc}") from exc
    elevation = geometry["coordinates"][2] if len(geometry["coordinates"]) > 2 else None
    if elevation == fill or not isinstance(elevation, (int, float)) or not isfinite(elevation):
        elevation = None
    return ClimateData(frame, {
        "source": "NASA POWER · météorologie maillée dérivée de modèles/réanalyses",
        "url": url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_coordinates": {"latitude": latitude, "longitude": longitude},
        "returned_geometry": payload.get("geometry"),
        "start": start.isoformat(), "end": end.isoformat(),
        "time_standard": payload.get("header", {}).get("time_standard", "UTC demandé"),
        "header": payload.get("header", {}),
        "units": units,
        "parameters": metadata,
        "messages": payload.get("messages", []),
        "payload_sha256": sha256(canonical.encode("utf-8")).hexdigest(),
        "hash_method": "SHA-256 du JSON canonique UTF-8 : clés triées, séparateurs compacts, ensure_ascii=False",
        "processing_version": "agrinova_power_v3_eto_inputs",
        "grid_elevation_m": elevation,
        "grid_elevation_source": "NASA POWER response geometry: MERRA-2 average for 0.5 x 0.625 degree grid (metres)" if elevation is not None else None,
        "coordinate_identity_tolerance_degrees": 0.0001,
    }, payload)


def fetch_daily(latitude: float, longitude: float, start: date, end: date) -> ClimateData:
    if not (isfinite(latitude) and isfinite(longitude) and -90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise PowerError("Coordonnées invalides")
    if start > end or end >= datetime.now(timezone.utc).date():
        raise PowerError("Choisir une période passée, avec début ≤ fin")
    if (end - start).days > 3660:
        raise PowerError("Limiter chaque requête à dix ans")
    params = {"parameters": ",".join(REQUEST_PARAMETERS), "community": "AG",
              "latitude": latitude, "longitude": longitude,
              "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
              "format": "JSON", "time-standard": "UTC"}
    try:
        response = requests.get(ENDPOINT, params=params, timeout=(10, 60))
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise PowerError(f"Échec NASA POWER ({type(exc).__name__}) : {exc}") from exc
    return parse_response(payload, start, end, latitude, longitude, response.url)
