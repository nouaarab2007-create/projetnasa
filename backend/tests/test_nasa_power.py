"""Unit tests for the NASA POWER adapter (port of tests/nasa-power.test.ts)."""

from __future__ import annotations

import pytest

from app.core.errors import DomainError
from app.services.nasa_power import parse_power_response, validate_power_query


def test_parses_monthly_observations_and_removes_month_13_and_missing_sentinels() -> None:
    points = parse_power_response(
        {
            "properties": {
                "parameter": {
                    "T2M": {
                        "202001": 12.5,
                        "202002": -999,
                        "202012": 15,
                        "202013": 13.7,
                    }
                }
            }
        },
        "T2M",
    )
    assert points == [
        {"date": "2020-01", "value": 12.5},
        {"date": "2020-12", "value": 15.0},
    ]


def test_rejects_unsupported_parameters_and_invalid_coordinates() -> None:
    with pytest.raises(DomainError, match="Unsupported"):
        validate_power_query("FAKE", 0, 0, 2000, 2020)
    with pytest.raises(DomainError, match="Latitude"):
        validate_power_query("T2M", 91, 0, 2000, 2020)
    with pytest.raises(DomainError, match="Longitude"):
        validate_power_query("T2M", 0, -181, 2000, 2020)
    with pytest.raises(DomainError, match="valid period"):
        validate_power_query("T2M", 0, 0, 1979, 2020)
    with pytest.raises(DomainError, match="valid period"):
        validate_power_query("T2M", 0, 0, 2022, 2020)
