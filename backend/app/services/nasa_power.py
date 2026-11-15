"""NASA POWER monthly point API adapter.

Validates user queries, fetches monthly gridded observations from NASA POWER,
filters out sentinel ``-999`` values and annual ``13`` month summaries, and
attaches explicit provenance metadata. Responses are cached in memory for
24 hours, matching the ``next: { revalidate: 86400 }`` policy of the original
Next.js implementation.
"""

from __future__ import annotations

import copy
import math
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.core.cache import TTLCache
from app.core.errors import DomainError, UpstreamError
from app.science.catalog import find_selectable_variable
from app.science.transform import Point

_MONTH_KEY = re.compile(r"^\d{6}$")
_power_cache: TTLCache[dict[str, Any]] = TTLCache(
    ttl=settings.power_cache_seconds,
    max_entries=256,
)


def clear_power_cache() -> None:
    """Clear the in-memory NASA POWER response cache (used by tests)."""
    _power_cache.clear()


def _is_finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _is_integer_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value) and value.is_integer()
    return False


def validate_power_query(
    parameter: str,
    latitude: float,
    longitude: float,
    start: int | float,
    end: int | float,
) -> dict[str, Any]:
    """Validate a NASA POWER query and return the variable definition."""
    definition = find_selectable_variable(parameter, provider="power")
    if not definition:
        raise DomainError("Unsupported NASA POWER parameter.")
    if not _is_finite_number(latitude) or latitude < -90 or latitude > 90:
        raise DomainError("Latitude must be between -90 and 90.")
    if not _is_finite_number(longitude) or longitude < -180 or longitude > 180:
        raise DomainError("Longitude must be between -180 and 180.")
    current_year = datetime.now(timezone.utc).year
    if (
        not _is_integer_value(start)
        or not _is_integer_value(end)
        or int(start) < 1981
        or int(end) > current_year
        or int(start) > int(end)
    ):
        raise DomainError("Choose a valid period from 1981 to the current year.")
    return definition


def parse_power_response(payload: Any, parameter: str) -> list[Point]:
    """Extract and sort valid monthly observations from a NASA POWER payload."""
    series = None
    if isinstance(payload, dict):
        properties = payload.get("properties")
        if isinstance(properties, dict):
            parameters = properties.get("parameter")
            if isinstance(parameters, dict):
                series = parameters.get(parameter)
    if not isinstance(series, dict) or not series:
        raise DomainError("NASA POWER returned no observations for this parameter.")

    points: list[Point] = []
    for key, value in series.items():
        if (
            isinstance(key, str)
            and _MONTH_KEY.match(key)
            and key[4:] != "13"
            and _is_finite_number(value)
            and value != -999
        ):
            points.append({"date": f"{key[:4]}-{key[4:6]}", "value": float(value)})
    points.sort(key=lambda item: item["date"])
    return points


def _format_num(value: float) -> int | float:
    return int(value) if float(value).is_integer() else float(value)


async def fetch_power_data(
    client: httpx.AsyncClient,
    *,
    parameter: str,
    latitude: float,
    longitude: float,
    start: int,
    end: int,
) -> dict[str, Any]:
    """Fetch and validate monthly point data from the NASA POWER API."""
    definition = validate_power_query(parameter, latitude, longitude, start, end)
    start_year = int(start)
    end_year = int(end)
    lat_num = _format_num(latitude)
    lon_num = _format_num(longitude)
    cache_key = f"{parameter}:{lat_num}:{lon_num}:{start_year}:{end_year}"
    cached = _power_cache.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)

    params = {
        "parameters": parameter,
        "community": "AG",
        "longitude": str(lon_num),
        "latitude": str(lat_num),
        "start": str(start_year),
        "end": str(end_year),
        "format": "JSON",
    }
    try:
        response = await client.get(
            settings.power_url,
            params=params,
            timeout=settings.power_timeout,
        )
    except httpx.HTTPError as exc:
        raise UpstreamError("NASA POWER request failed or timed out.") from exc

    if response.status_code != 200:
        raise UpstreamError(f"NASA POWER request failed with status {response.status_code}.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise UpstreamError("NASA POWER returned an invalid JSON payload.") from exc

    points = parse_power_response(payload, parameter)
    if len(points) < 3:
        raise DomainError("NASA POWER returned too few valid observations for analysis.")

    result = {
        "points": points,
        "metadata": {
            "provider": "NASA Prediction Of Worldwide Energy Resources",
            "product": "POWER Monthly Point API",
            "parameter": parameter,
            "unit": definition["unit"],
            "latitude": lat_num,
            "longitude": lon_num,
            "temporalResolution": "Monthly",
            "spatialResolution": "0.5° latitude × 0.625° longitude (parameter-dependent gridded cell)",
            "coverage": f"{points[0]['date']} to {points[-1]['date']}",
            "retrievalDate": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "processing": "Invalid -999 values and annual month-13 entries removed.",
            "quality": (
                "Gridded, model- and satellite-derived data; not a direct measurement at the "
                "selected point."
            ),
            "documentation": "https://power.larc.nasa.gov/docs/services/api/",
            "simulated": False,
        },
    }
    _power_cache.set(cache_key, result)
    return copy.deepcopy(result)
