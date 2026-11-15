"""Artificial response shapes ONLY for parser tests, never application data."""

from datetime import date

import pandas as pd
import pytest
import requests

from agrinova.data.power import PARAMETERS, PowerError, fetch_daily, parse_response


@pytest.fixture
def artificial_payload():
    return {"header": {"fill_value": -999, "time_standard": "UTC"},
            "geometry": {"type": "Point", "coordinates": [-6.36, 32.34, 0]},
            "properties": {"parameter": {name: {"20250101": value, "20250102": -999}
                for name, value in zip(PARAMETERS, [10, 5, 15, 2])}},
            "parameters": {name: {"units": "mm/day" if name == "PRECTOTCORR" else "C"} for name in PARAMETERS}}


def parse(payload):
    return parse_response(payload, date(2025, 1, 1), date(2025, 1, 3), 32.34, -6.36, "https://example.invalid/artificial-test")


def test_missing_and_fill_values_stay_missing(artificial_payload):
    result = parse(artificial_payload)
    assert len(result.daily) == 3
    assert result.daily.iloc[1:].isna().all().all()
    assert result.daily.iloc[0].PRECTOTCORR == 2
    assert result.provenance["units"]["T2M"] == "C"


@pytest.mark.parametrize("mutation", ["units", "negative_rain", "missing_variable", "temperature_order", "all_missing"])
def test_invalid_response_rejected(artificial_payload, mutation):
    p = artificial_payload
    if mutation == "units":
        p["parameters"]["PRECTOTCORR"]["units"] = "inches"
    elif mutation == "negative_rain":
        p["properties"]["parameter"]["PRECTOTCORR"]["20250101"] = -1
    elif mutation == "missing_variable":
        del p["properties"]["parameter"]["T2M"]
    elif mutation == "temperature_order":
        p["properties"]["parameter"]["T2M_MIN"]["20250101"] = 20
    else:
        for values in p["properties"]["parameter"].values():
            values["20250101"] = -999
    with pytest.raises(PowerError):
        parse(p)


def test_network_failure_is_explicit(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.Timeout("artificial timeout for test")
    monkeypatch.setattr(requests, "get", fail)
    with pytest.raises(PowerError, match="Timeout"):
        fetch_daily(32.34, -6.36, date(2025, 1, 1), date(2025, 1, 2))


@pytest.mark.parametrize("lat,lon,start,end", [(91, 0, date(2025, 1, 1), date(2025, 1, 2)),
    (0, float("nan"), date(2025, 1, 1), date(2025, 1, 2)),
    (0, 0, date(2025, 1, 2), date(2025, 1, 1))])
def test_bad_query_never_reaches_network(monkeypatch, lat, lon, start, end):
    def unexpected(*args, **kwargs):
        pytest.fail("Invalid query must not call network")
    monkeypatch.setattr(requests, "get", unexpected)
    with pytest.raises(PowerError):
        fetch_daily(lat, lon, start, end)


@pytest.mark.parametrize("standard", ["LST", None, ""])
def test_response_must_confirm_utc(artificial_payload, standard):
    artificial_payload["header"]["time_standard"] = standard
    with pytest.raises(PowerError, match="UTC"):
        parse(artificial_payload)


@pytest.mark.parametrize("coordinates", [[0, 0], [32.34, -6.36], [-6.36], [-6.36, float("inf")]])
def test_response_must_match_requested_coordinates(artificial_payload, coordinates):
    artificial_payload["geometry"]["coordinates"] = coordinates
    with pytest.raises(PowerError):
        parse(artificial_payload)


def test_raw_provenance_hash_is_reproducible(artificial_payload):
    from hashlib import sha256
    import json
    canonical = json.dumps(artificial_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    result = parse(artificial_payload)
    assert result.provenance["payload_sha256"] == sha256(canonical.encode("utf-8")).hexdigest()
    assert result.raw_payload == artificial_payload
    artificial_payload["properties"]["parameter"]["T2M"]["20250101"] = 11
    assert result.raw_payload["properties"]["parameter"]["T2M"]["20250101"] == 10
    assert parse(artificial_payload).provenance["payload_sha256"] != result.provenance["payload_sha256"]
