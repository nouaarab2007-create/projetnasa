"""Helpers shared by the dataset connectors (MODIS, Giovanni, NOAA, SWOT).

Every connector returns raw dated samples; these helpers validate the request,
average samples into calendar months and build the provenance metadata in the
same shape as the NASA POWER connector, so the routes and the frontend treat
all sources identically.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from app.core.errors import DomainError, UpstreamError
from app.science.transform import Point

Sample = tuple[str, float]  # ("YYYY-MM-DD..." , value)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def to_float(raw: Any) -> float | None:
    """Parse a numeric value from JSON/CSV; return None for blanks, text or non-finite values."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw) if math.isfinite(raw) else None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def validate_query(
    definition: dict[str, Any],
    latitude: float,
    longitude: float,
    start: Any,
    end: Any,
    *,
    needs_location: bool = True,
) -> tuple[int, int, str]:
    """Validate coordinates and years. Returns (start, end, note).

    A start year earlier than the dataset's first year is moved forward (with a
    note) instead of failing, so one period can be reused across datasets.
    """
    if needs_location:
        if not is_number(latitude) or latitude < -90 or latitude > 90:
            raise DomainError("Latitude must be between -90 and 90.")
        if not is_number(longitude) or longitude < -180 or longitude > 180:
            raise DomainError("Longitude must be between -180 and 180.")
    current_year = datetime.now(timezone.utc).year
    min_year = int(definition.get("minYear", 1981))
    if not (is_number(start) and float(start).is_integer() and is_number(end) and float(end).is_integer()):
        raise DomainError(f"Choose a valid period from {min_year} to the current year.")
    start_year, end_year = int(start), int(end)
    if start_year > end_year or end_year > current_year:
        raise DomainError(f"Choose a valid period from {min_year} to the current year.")
    if end_year < min_year:
        raise DomainError(f"{definition['source']} data starts in {min_year}; choose an end year from {min_year}.")
    note = ""
    if start_year < min_year:
        note = f"Requested start {start_year} moved to {min_year}, the first year of this dataset. "
        start_year = min_year
    return start_year, end_year, note


def monthly_means(samples: Iterable[Sample]) -> tuple[list[Point], int]:
    """Average dated samples per calendar month. Returns (points, number of samples used)."""
    buckets: dict[str, list[float]] = {}
    used = 0
    for date, value in samples:
        if not is_number(value) or len(date) < 7:
            continue
        buckets.setdefault(date[:7], []).append(float(value))
        used += 1
    points: list[Point] = [
        {"date": month, "value": sum(values) / len(values)} for month, values in sorted(buckets.items())
    ]
    return points, used


def require_points(points: list[Point], source: str) -> list[Point]:
    if len(points) < 3:
        raise DomainError(
            f"{source} returned too few valid monthly values for this location and period "
            "(the point may be outside the dataset's coverage, e.g. over water)."
        )
    return points


def build_metadata(
    *,
    provider: str,
    product: str,
    parameter: str,
    unit: str,
    latitude: float | None,
    longitude: float | None,
    spatial_resolution: str,
    points: list[Point],
    processing: str,
    quality: str,
    documentation: str,
    temporal_resolution: str = "Monthly (mean of native observations)",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "provider": provider,
        "product": product,
        "parameter": parameter,
        "unit": unit,
        "latitude": latitude,
        "longitude": longitude,
        "temporalResolution": temporal_resolution,
        "spatialResolution": spatial_resolution,
        "coverage": f"{points[0]['date']} to {points[-1]['date']}",
        "retrievalDate": now_iso(),
        "processing": processing.strip(),
        "quality": quality,
        "documentation": documentation,
    }
    if extra:
        metadata.update(extra)
    metadata["simulated"] = False
    return metadata


async def get_checked(
    client: httpx.AsyncClient,
    url: str,
    *,
    source: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> httpx.Response:
    """GET with uniform, user-readable errors for network failures and HTTP status codes."""
    try:
        response = await client.get(url, params=params, headers=headers, timeout=timeout)
    except httpx.TimeoutException as exc:
        raise UpstreamError(f"{source} did not answer in time. Try a shorter period or retry later.") from exc
    except httpx.HTTPError as exc:
        raise UpstreamError(f"{source} could not be reached ({exc.__class__.__name__}).") from exc
    if response.status_code in (401, 403):
        raise UpstreamError(f"{source} refused the request (HTTP {response.status_code}): check the access token.")
    if response.status_code == 429:
        raise UpstreamError(f"{source} rate limit reached (HTTP 429). Wait a minute and retry.")
    if response.status_code >= 400:
        detail = _error_detail(response)
        raise UpstreamError(f"{source} request failed with status {response.status_code}{detail}")
    return response


def _error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip().splitlines()[0] if response.text.strip() else ""
        return f": {text[:200]}" if text and "<" not in text[:1] else "."
    if isinstance(payload, dict):
        for key in ("error", "message", "errorMessage", "detail"):
            if payload.get(key):
                return f": {str(payload[key])[:200]}"
    return "."
