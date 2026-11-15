"""OpenStreetMap raster tile proxy with 7-day in-memory caching."""

from __future__ import annotations

import re

import httpx

from app.config import settings
from app.core.cache import TTLCache
from app.core.errors import DomainError, UpstreamError

_DIGITS = re.compile(r"^\d+$")
_tile_cache: TTLCache[bytes] = TTLCache(
    ttl=settings.tile_cache_seconds,
    max_entries=settings.tile_cache_entries,
)


def clear_tile_cache() -> None:
    """Clear the in-memory tile cache (used by tests)."""
    _tile_cache.clear()


async def fetch_osm_tile(client: httpx.AsyncClient, z: str, x: str, y: str) -> bytes:
    """Fetch a PNG raster tile from OpenStreetMap, validating integer coordinates."""
    if not all(_DIGITS.match(part) for part in (z, x, y)):
        raise DomainError("Invalid tile coordinates.", status_code=400)

    key = f"{z}/{x}/{y}"
    cached = _tile_cache.get(key)
    if cached is not None:
        return cached

    url = settings.tile_url.format(z=z, x=x, y=y)
    try:
        response = await client.get(
            url,
            headers={"User-Agent": settings.user_agent},
            timeout=settings.tile_timeout,
        )
    except httpx.HTTPError as exc:
        raise UpstreamError("Map tile unavailable.", status_code=502) from exc

    if response.status_code != 200:
        raise UpstreamError("Map tile unavailable.", status_code=response.status_code)

    content = response.content
    _tile_cache.set(key, content)
    return content
