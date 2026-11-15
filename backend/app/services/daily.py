"""Daily point series for event detection (heat waves, extreme rainfall, drought).

* NASA POWER Daily Point API — gridded, global, 1981-present, no account.
  GET .../api/temporal/daily/point?parameters=T2M_MAX,PRECTOTCORR&community=AG
      &latitude=..&longitude=..&start=YYYYMMDD&end=YYYYMMDD&format=JSON
  -> properties.parameter.<NAME>.{"YYYYMMDD": value}, -999 = missing.
* NOAA NCEI GHCN-Daily (Access Data Service, dataset=daily-summaries) — the
  station is chosen with the same rule as the monthly NOAA connector, then its
  daily TMAX / PRCP record is downloaded (metric units).
* NASA GPM IMERG Final daily precipitation through Giovanni (Earthdata token).

Each fetcher returns ``{"samples": [(YYYY-MM-DD, value)], "label": ..., "product": ..., "note": ...}``.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import httpx

from app.config import settings
from app.core.cache import TTLCache
from app.core.errors import DomainError, UpstreamError
from app.services import giovanni, noaa
from app.services.series import get_checked, to_float

_cache: TTLCache[dict[str, Any]] = TTLCache(ttl=86400, max_entries=128)


def clear_daily_cache() -> None:
    _cache.clear()


def _key(*parts: Any) -> str:
    return ":".join(str(p) for p in parts)


def parse_power_daily(payload: Any, parameters: list[str]) -> dict[str, list[tuple[str, float]]]:
    params = (((payload or {}).get("properties") or {}).get("parameter") or {}) if isinstance(payload, dict) else {}
    out: dict[str, list[tuple[str, float]]] = {}
    for name in parameters:
        series = params.get(name)
        rows: list[tuple[str, float]] = []
        if isinstance(series, dict):
            for key, value in series.items():
                number = to_float(value)
                if len(str(key)) == 8 and str(key).isdigit() and number is not None and number > -990:
                    rows.append((f"{key[:4]}-{key[4:6]}-{key[6:]}", number))
        rows.sort()
        out[name] = rows
    return out


async def power_daily(
    client: httpx.AsyncClient, latitude: float, longitude: float, first: int, last: int
) -> dict[str, dict[str, Any]]:
    """Daily T2M_MAX, PRECTOTCORR and GWETROOT in one request. Returns {parameter: result}."""
    parameters = ["T2M_MAX", "PRECTOTCORR", "GWETROOT"]
    key = _key("power", round(latitude, 4), round(longitude, 4), first, last)
    cached = _cache.get(key)
    if cached is not None:
        return copy.deepcopy(cached)
    response = await get_checked(
        client, settings.power_daily_url, source="NASA POWER (daily)", timeout=settings.power_daily_timeout,
        params={
            "parameters": ",".join(parameters),
            "community": "AG",
            "latitude": str(round(latitude, 4)),
            "longitude": str(round(longitude, 4)),
            "start": f"{first}0101",
            "end": f"{last}1231",
            "format": "JSON",
        },
    )
    try:
        parsed = parse_power_daily(response.json(), parameters)
    except ValueError as exc:
        raise UpstreamError("NASA POWER (daily) returned an unreadable response.") from exc
    result: dict[str, dict[str, Any]] = {}
    for name, rows in parsed.items():
        result[name] = {
            "samples": rows,
            "label": "NASA POWER",
            "product": f"POWER Daily Point API · {name}",
            "note": "Gridded 0.5° cell (MERRA-2 / satellite based)",
        }
    if not any(r["samples"] for r in result.values()):
        raise DomainError("NASA POWER returned no daily values for this point.")
    _cache.set(key, result)
    return copy.deepcopy(result)


async def noaa_daily(
    client: httpx.AsyncClient, datatype: str, latitude: float, longitude: float, first: int, last: int
) -> dict[str, Any]:
    """Daily TMAX or PRCP from the best nearby GHCN station (°C / mm)."""
    key = _key("noaa", datatype, round(latitude, 4), round(longitude, 4), first, last)
    cached = _cache.get(key)
    if cached is not None:
        return copy.deepcopy(cached)
    # Choose the station from its monthly record (small response), as the monthly connector does.
    station = await noaa._via_access_service(client, datatype, latitude, longitude, first, last)  # noqa: SLF001
    if station is None:
        raise DomainError(f"No NOAA station with {datatype} data was found near this point.")
    response = await get_checked(
        client, settings.noaa_access_url, source="NOAA NCEI (daily)", timeout=settings.noaa_timeout,
        params={
            "dataset": "daily-summaries",
            "stations": station["id"],
            "dataTypes": datatype,
            "startDate": f"{first}-01-01",
            "endDate": f"{last}-12-31",
            "units": "metric",
            "format": "json",
        },
    )
    try:
        rows = response.json()
    except ValueError as exc:
        raise UpstreamError("NOAA NCEI (daily) returned an unreadable response.") from exc
    samples: list[tuple[str, float]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        value = to_float(row.get(datatype))
        day = str(row.get("DATE", ""))[:10]
        if value is not None and len(day) == 10:
            samples.append((day, value))
    samples.sort()
    if not samples:
        raise DomainError(f"NOAA station {station['id']} has no daily {datatype} values for {first}-{last}.")
    distance = station.get("distanceKm")
    where = f", {distance:.0f} km away" if isinstance(distance, (int, float)) and math.isfinite(distance) else ""
    name = (station.get("name") or station["id"]).split(",")[0].title()
    result = {
        "samples": samples,
        "label": f"NOAA station {name}",
        "product": f"GHCN-Daily · {datatype} · {station['id']}",
        "note": f"Ground station {station['id']}{where}",
    }
    _cache.set(key, result)
    return copy.deepcopy(result)


IMERG_DAILY = {
    "candidates": ["GPM_3IMERGDF_07_precipitation", "GPM_3IMERGDF_06_precipitationCal"],
    "fallback": "GPM_3IMERGDF_07_precipitation",
}


async def imerg_daily(
    client: httpx.AsyncClient, latitude: float, longitude: float, first: int, last: int
) -> dict[str, Any]:
    """GPM IMERG Final daily precipitation (mm/day) from Giovanni, June 2000 onward."""
    first = max(first, 2001)  # first complete year
    key = _key("imerg", round(latitude, 4), round(longitude, 4), first, last)
    cached = _cache.get(key)
    if cached is not None:
        return copy.deepcopy(cached)
    token = giovanni.require_token()
    giovanni.VARIABLES.setdefault(
        "GPM_IMERG_DAILY",
        {**IMERG_DAILY, "native_unit": "mm/day", "resolution": "0.1°", "documentation": "", "quality": ""},
    )
    data_id = await giovanni.resolve_data_id(client, "GPM_IMERG_DAILY", token)
    samples: list[tuple[str, float]] = []
    unit = ""
    for start in range(first, last + 1, 10):  # sequential windows, as for the monthly connector
        end = min(last, start + 9)
        header, rows = await giovanni.fetch_csv(client, data_id, latitude, longitude, start, end, token)
        unit = unit or header.get("unit", "")
        samples.extend((day[:10], value) for day, value in rows)
    factor, _ = giovanni.unit_factor(unit, "mm/day")
    by_day: dict[str, float] = {}
    for day, value in samples:
        by_day[day] = value * factor
    result = {
        "samples": sorted(by_day.items()),
        "label": "NASA GPM IMERG",
        "product": f"Giovanni · {data_id}",
        "note": "Satellite precipitation, 0.1° cell, from 2001",
    }
    _cache.set(key, result)
    return copy.deepcopy(result)


GLDAS_3H_ROOT = "GLDAS_NOAH025_3H_2_1_RootMoist_inst"


async def gldas_root_daily(
    client: httpx.AsyncClient, latitude: float, longitude: float, first: int, last: int
) -> dict[str, Any]:
    """GLDAS-2.1 root-zone soil moisture (3-hourly, Giovanni) averaged to daily values, 2000 onward."""
    first = max(first, 2000)
    key = _key("gldas", round(latitude, 4), round(longitude, 4), first, last)
    cached = _cache.get(key)
    if cached is not None:
        return copy.deepcopy(cached)
    token = giovanni.require_token()
    sums: dict[str, list[float]] = {}
    for start in range(first, last + 1, 3):  # 3-year windows; fetch_csv halves a window on a server error
        end = min(last, start + 2)
        _, rows = await giovanni.fetch_csv(client, GLDAS_3H_ROOT, latitude, longitude, start, end, token)
        for stamp, value in rows:
            sums.setdefault(stamp[:10], []).append(value)
    samples = sorted((day, sum(v) / len(v)) for day, v in sums.items() if len(v) >= 4)
    if not samples:
        raise DomainError("GLDAS returned no soil moisture for this point (it may be over water or ice).")
    result = {
        "samples": samples,
        "label": "NASA GLDAS",
        "product": f"Giovanni · {GLDAS_3H_ROOT} (daily means)",
        "note": "Land-surface model, 0.25° cell, from 2000",
    }
    _cache.set(key, result)
    return copy.deepcopy(result)
