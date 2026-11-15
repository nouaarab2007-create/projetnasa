"""Single entry point that routes a variable to the connector that retrieves it.

``fetch_series`` returns ``{"points": [...], "metadata": {...}}`` for every
source, in the shape the NASA POWER connector always used, so the
``/api/data``, ``/api/analysis`` and ``/api/comparison`` routes and the frontend
handle all datasets the same way.
"""

from __future__ import annotations

import copy
from typing import Any

import httpx

from app.config import settings
from app.core.cache import TTLCache
from app.core.errors import DomainError
from app.science.catalog import find_variable
from app.services.giovanni import fetch_giovanni
from app.services.modis import fetch_modis
from app.services.nasa_power import fetch_power_data
from app.services.noaa import fetch_noaa
from app.services.series import build_metadata, validate_query
from app.services.swot import fetch_swot

_series_cache: TTLCache[dict[str, Any]] = TTLCache(ttl=settings.dataset_cache_seconds, max_entries=256)


def clear_dataset_cache() -> None:
    _series_cache.clear()


async def fetch_series(
    client: httpx.AsyncClient,
    *,
    parameter: str,
    latitude: float,
    longitude: float,
    start: int | float,
    end: int | float,
    feature_id: str | None = None,
) -> dict[str, Any]:
    definition = find_variable(parameter)
    if not definition or not definition.get("selectable"):
        raise DomainError("Unsupported variable.")
    provider = definition["provider"]

    if provider == "power":
        return await fetch_power_data(
            client, parameter=parameter, latitude=latitude, longitude=longitude, start=start, end=end
        )

    needs_location = not definition.get("featureInput")
    start_year, end_year, note = validate_query(
        definition, latitude, longitude, start, end, needs_location=needs_location
    )
    location_key = (feature_id or "").strip() if not needs_location else f"{latitude:.4f}:{longitude:.4f}"
    cache_key = f"{parameter}:{location_key}:{start_year}:{end_year}"
    cached = _series_cache.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)

    if provider == "modis":
        raw = await fetch_modis(client, parameter, latitude, longitude, start_year, end_year)
    elif provider == "giovanni":
        raw = await fetch_giovanni(client, parameter, latitude, longitude, start_year, end_year)
    elif provider == "noaa":
        raw = await fetch_noaa(client, parameter, latitude, longitude, start_year, end_year)
    elif provider == "swot":
        raw = await fetch_swot(client, feature_id, start_year, end_year)
    else:  # pragma: no cover — guarded by the catalogue
        raise DomainError("Unsupported variable.")

    result = {
        "points": raw["points"],
        "metadata": build_metadata(
            provider=definition["source"],
            product=raw["product"],
            parameter=parameter,
            unit=definition["unit"],
            latitude=latitude if needs_location else None,
            longitude=longitude if needs_location else None,
            spatial_resolution=raw["spatialResolution"],
            points=raw["points"],
            processing=f"{note}{raw['processing']}",
            quality=raw["quality"],
            documentation=raw["documentation"],
            extra=raw.get("extra"),
        ),
    }
    _series_cache.set(cache_key, result)
    return copy.deepcopy(result)
