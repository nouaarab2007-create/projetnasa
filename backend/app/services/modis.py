"""MODIS land products from the ORNL DAAC MODIS/VIIRS web service (TESViS).

These are the same MODIS collections AppEEARS distributes (MOD13Q1, MOD15A2H,
MOD11A2), but served as an instant pixel time series instead of a queued
AppEEARS task. No account is needed.

API: https://modis.ornl.gov/rst/api/v1/{product}/dates and /{product}/subset
(at most 10 composite dates per subset request).
"""

from __future__ import annotations

import asyncio
import re
from datetime import date, timedelta
from typing import Any, Callable

import httpx

from app.config import settings
from app.core.errors import DomainError
from app.services.series import Sample, get_checked, monthly_means, require_points

SOURCE = "NASA MODIS (ORNL DAAC)"


def _kelvin_to_celsius(value: float) -> float:
    return value - 273.15


# code -> product, band, scale factor, valid raw range, unit conversion, resolution
PRODUCTS: dict[str, dict[str, Any]] = {
    "MOD13Q1_NDVI": {
        "product": "MOD13Q1",
        "band": "250m_16_days_NDVI",
        "scale": 0.0001,
        "valid": (-2000, 10000),
        "convert": None,
        "resolution": "250 m pixel, 16-day composites",
    },
    "MOD13Q1_EVI": {
        "product": "MOD13Q1",
        "band": "250m_16_days_EVI",
        "scale": 0.0001,
        "valid": (-2000, 10000),
        "convert": None,
        "resolution": "250 m pixel, 16-day composites",
    },
    "MOD15A2H_LAI": {
        "product": "MOD15A2H",
        "band": "Lai_500m",
        "scale": 0.1,
        "valid": (0, 100),
        "convert": None,
        "resolution": "500 m pixel, 8-day composites",
    },
    "MOD11A2_LST_DAY": {
        "product": "MOD11A2",
        "band": "LST_Day_1km",
        "scale": 0.02,
        "valid": (7500, 65535),
        "convert": _kelvin_to_celsius,
        "resolution": "1 km pixel, 8-day composites",
    },
}

_MODIS_DATE = re.compile(r"^A(\d{4})(\d{3})$")


def modis_to_iso(modis_date: str) -> str | None:
    """Convert a MODIS composite date ``AYYYYDDD`` to ``YYYY-MM-DD``."""
    match = _MODIS_DATE.match(modis_date or "")
    if not match:
        return None
    day = date(int(match.group(1)), 1, 1) + timedelta(days=int(match.group(2)) - 1)
    return day.isoformat()


def parse_subset(payload: Any, band: str, scale: float, valid: tuple[float, float],
                 convert: Callable[[float], float] | None) -> list[Sample]:
    """Extract scaled values from a /subset response; fill and out-of-range values are dropped."""
    samples: list[Sample] = []
    records = payload.get("subset", []) if isinstance(payload, dict) else []
    low, high = valid
    for record in records:
        if not isinstance(record, dict) or record.get("band") not in (None, band):
            continue
        iso = record.get("calendar_date") or modis_to_iso(str(record.get("modis_date", "")))
        if not iso:
            continue
        raw = [v for v in record.get("data", []) if isinstance(v, (int, float)) and low <= v <= high]
        if not raw:
            continue
        value = (sum(raw) / len(raw)) * scale
        samples.append((str(iso)[:10], convert(value) if convert else value))
    return samples


async def fetch_modis(
    client: httpx.AsyncClient,
    code: str,
    latitude: float,
    longitude: float,
    start: int,
    end: int,
) -> dict[str, Any]:
    spec = PRODUCTS[code]
    product, band = spec["product"], spec["band"]
    base = f"{settings.modis_url}/{product}"

    dates_response = await get_checked(
        client, f"{base}/dates", source=SOURCE,
        params={"latitude": latitude, "longitude": longitude}, timeout=settings.modis_timeout,
    )
    try:
        all_dates = [d.get("modis_date") for d in dates_response.json().get("dates", [])]
    except (ValueError, AttributeError) as exc:
        raise DomainError("NASA MODIS returned an unreadable list of dates.") from exc
    wanted = [d for d in all_dates if isinstance(d, str) and _MODIS_DATE.match(d) and start <= int(d[1:5]) <= end]
    if not wanted:
        raise DomainError(f"No {product} composites are available between {start} and {end} at this location.")

    chunks = [wanted[i:i + 10] for i in range(0, len(wanted), 10)]
    semaphore = asyncio.Semaphore(max(1, settings.modis_concurrency))

    async def fetch_chunk(chunk: list[str]) -> list[Sample]:
        async with semaphore:
            response = await get_checked(
                client, f"{base}/subset", source=SOURCE,
                params={
                    "latitude": latitude, "longitude": longitude, "band": band,
                    "startDate": chunk[0], "endDate": chunk[-1],
                    "kmAboveBelow": 0, "kmLeftRight": 0,
                },
                timeout=settings.modis_timeout,
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise DomainError("NASA MODIS returned an unreadable subset.") from exc
        return parse_subset(payload, band, spec["scale"], spec["valid"], spec["convert"])

    results = await asyncio.gather(*(fetch_chunk(chunk) for chunk in chunks))
    samples = [sample for chunk in results for sample in chunk]
    points, used = monthly_means(samples)
    require_points(points, SOURCE)
    return {
        "points": points,
        "product": f"{product} / {band}",
        "spatialResolution": spec["resolution"],
        "processing": (
            f"{len(wanted)} composites requested in {len(chunks)} batches; {used} valid composites after "
            "removing fill and out-of-range values; scale factor applied; monthly mean of composites."
        ),
        "quality": (
            "Satellite observation of a single pixel. MODIS QA flags are not applied, so residual cloud, "
            "snow or aerosol contamination can remain."
        ),
        "documentation": "https://modis.ornl.gov/data/modis_webservice.html",
    }
