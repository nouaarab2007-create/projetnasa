"""OpenStreetMap Nominatim place search proxy."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.core.errors import DomainError, UpstreamError


async def geocode_place(client: httpx.AsyncClient, query: str | None) -> list[dict[str, str]]:
    """Resolve a free-text place query into up to 5 coordinate candidates."""
    cleaned = (query or "").strip()
    if not cleaned:
        raise DomainError("A place name is required.", status_code=400)
    try:
        response = await client.get(
            settings.geocode_url,
            params={"format": "json", "limit": "5", "q": cleaned},
            headers={"User-Agent": settings.user_agent},
            timeout=settings.geocode_timeout,
        )
    except httpx.HTTPError as exc:
        raise UpstreamError("Place search is temporarily unavailable.", status_code=502) from exc

    if response.status_code != 200:
        raise UpstreamError("Place search is temporarily unavailable.", status_code=502)

    try:
        payload: Any = response.json()
    except ValueError as exc:
        raise UpstreamError("Place search is temporarily unavailable.", status_code=502) from exc

    if not isinstance(payload, list):
        return []

    results: list[dict[str, str]] = []
    for item in payload:
        if isinstance(item, dict) and "lat" in item and "lon" in item and "display_name" in item:
            results.append(
                {
                    "lat": str(item["lat"]),
                    "lon": str(item["lon"]),
                    "display_name": str(item["display_name"]),
                }
            )
    return results
