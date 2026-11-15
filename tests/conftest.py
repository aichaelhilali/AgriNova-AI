"""Artificial metadata for software tests; never crop reference data."""

import pytest


@pytest.fixture
def eto_metadata():
    return {"calculation_method": "Artificial arithmetic fixture, not FAO-56 validation",
            "units": "mm/day", "reference_surface": "short_grass", "time_standard": "UTC",
            "location": {"latitude": 32.34, "longitude": -6.36}}
