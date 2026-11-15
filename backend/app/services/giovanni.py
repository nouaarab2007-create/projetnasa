"""Giovanni in the Cloud: Time Series service (NASA GES DISC).

Serves GLDAS-2.1 land-surface variables and GPM IMERG precipitation as a point
time series. GES DISC recommends this service in place of the retired
Hydrology Data Rods. Requires an Earthdata Login token (``EARTHDATA_TOKEN``).

Request:  GET https://api.giovanni.earthdata.nasa.gov/timeseries
          ?data=<id>&location=[lat,lon]&time=<start>/<end>
          Authorization: Bearer <token>
Response: CSV text — ``key,value`` header lines (param_name, unit, lat, lon...),
          a column header line, then ``timestamp,value`` rows.

Variable ids are ``{collection}_{version}_{variable}``. The connector reads the
service's configured-variables list once a day and uses the first candidate it
offers (monthly product first, then the 3-hourly / half-hourly one).
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.config import earthdata_token, settings
from app.core.cache import TTLCache
from app.core.errors import DomainError, UpstreamError
from app.services.series import Sample, get_checked, monthly_means, require_points, to_float

SOURCE = "NASA Giovanni"

VARIABLES: dict[str, dict[str, Any]] = {
    "GLDAS_SOILM_0_10": {
        "candidates": ["GLDAS_NOAH025_M_2_1_SoilMoi0_10cm_inst", "GLDAS_NOAH025_3H_2_1_SoilMoi0_10cm_inst"],
        "fallback": "GLDAS_NOAH025_3H_2_1_SoilMoi0_10cm_inst",
        "native_unit": "kg m-2",
        "resolution": "0.25° GLDAS-2.1 Noah grid cell",
        "documentation": "https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_3H_2.1/summary",
        "quality": "Land-surface model output constrained by observations; not a direct measurement.",
    },
    "GLDAS_ROOT_ZONE_SM": {
        "candidates": ["GLDAS_NOAH025_M_2_1_RootMoist_inst", "GLDAS_NOAH025_3H_2_1_RootMoist_inst"],
        "fallback": "GLDAS_NOAH025_3H_2_1_RootMoist_inst",
        "native_unit": "kg m-2",
        "resolution": "0.25° GLDAS-2.1 Noah grid cell",
        "documentation": "https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_3H_2.1/summary",
        "quality": "Land-surface model output constrained by observations; not a direct measurement.",
    },
    "GLDAS_EVAP": {
        "candidates": ["GLDAS_NOAH025_M_2_1_Evap_tavg", "GLDAS_NOAH025_3H_2_1_Evap_tavg"],
        "fallback": "GLDAS_NOAH025_3H_2_1_Evap_tavg",
        "native_unit": "kg m-2 s-1",
        "resolution": "0.25° GLDAS-2.1 Noah grid cell",
        "documentation": "https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_3H_2.1/summary",
        "quality": "Land-surface model output constrained by observations; not a direct measurement.",
    },
    "GLDAS_SWE": {
        "candidates": ["GLDAS_NOAH025_M_2_1_SWE_inst", "GLDAS_NOAH025_3H_2_1_SWE_inst"],
        "fallback": "GLDAS_NOAH025_3H_2_1_SWE_inst",
        "native_unit": "kg m-2",
        "resolution": "0.25° GLDAS-2.1 Noah grid cell",
        "documentation": "https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_3H_2.1/summary",
        "quality": "Land-surface model output constrained by observations; not a direct measurement.",
    },
    "GPM_IMERG_PRECIP": {
        "candidates": [
            "GPM_3IMERGM_07_precipitation",
            "GPM_3IMERGHH_07_precipitation",
            "GPM_3IMERGHH_06_precipitationCal",
        ],
        "fallback": "GPM_3IMERGHH_06_precipitationCal",
        "native_unit": "mm/hr",
        "resolution": "0.1° GPM IMERG grid cell",
        "documentation": "https://gpm.nasa.gov/data/imerg",
        "quality": "Multi-satellite estimate calibrated with rain gauges; uncertainty is larger over complex terrain.",
    },
}

_catalog_cache: TTLCache[str] = TTLCache(ttl=86400, max_entries=2)


def clear_giovanni_cache() -> None:
    _catalog_cache.clear()


def require_token() -> str:
    token = earthdata_token()
    if not token:
        raise DomainError(
            "This dataset is served by NASA Giovanni, which needs a free Earthdata Login token. "
            "Create one at https://urs.earthdata.nasa.gov (Generate Token), then start the server "
            "with the environment variable EARTHDATA_TOKEN set."
        )
    return token


async def resolve_data_id(client: httpx.AsyncClient, code: str, token: str) -> str:
    """Pick the first candidate id listed by Giovanni's configured-variables endpoint."""
    spec = VARIABLES[code]
    listing = _catalog_cache.get("configured")
    if listing is None:
        try:
            response = await client.get(
                f"{settings.giovanni_url}/configured-variables",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            listing = response.text if response.status_code == 200 else ""
        except httpx.HTTPError:
            listing = ""
        if listing:
            _catalog_cache.set("configured", listing)
    for candidate in spec["candidates"]:
        if listing and re.search(rf"(?<![A-Za-z0-9_]){re.escape(candidate)}(?![A-Za-z0-9_])", listing):
            return candidate
    return spec["fallback"]


_DATA_ROW = re.compile(r"^\s*\"?(\d{4}-\d{2}-\d{2})[T ]?[^,]*,\s*(.*)$")


def parse_timeseries_csv(text: str) -> tuple[dict[str, str], list[Sample]]:
    """Parse Giovanni's CSV: ``key,value`` header lines, a column header, then data rows."""
    if not text.strip():
        raise DomainError(
            "Giovanni returned an empty time series: the point may be outside the dataset "
            "(e.g. over the ocean for GLDAS) or the token may be invalid."
        )
    if text.lstrip().startswith("{") or text.lstrip().lower().startswith("<"):
        raise UpstreamError(f"Giovanni returned an error instead of data: {text.strip()[:200]}")
    headers: dict[str, str] = {}
    samples: list[Sample] = []
    for line in text.splitlines():
        match = _DATA_ROW.match(line)
        if match:
            value = to_float(match.group(2).strip().strip('"'))
            if value is None or abs(value) >= 1e19 or value <= -9999:
                continue  # fill / missing value
            samples.append((match.group(1), value))
        elif "," in line and not samples:
            key, _, value = line.partition(",")
            if key.strip():
                headers[key.strip().strip('"')] = value.strip().strip('"')
    return headers, samples


def unit_factor(unit: str, native_unit: str) -> tuple[float, str]:
    """Return (multiplier, note) converting fluxes to the catalogue units."""
    normalized = re.sub(r"[\s*^]", "", (unit or native_unit)).lower()
    if normalized in ("kgm-2s-1", "kg/m2/s", "kgm-2/s", "mm/s", "mms-1"):
        return 86400.0, "converted from kg m-2 s-1 to mm/day (×86 400)"
    if normalized in ("mm/hr", "mm/h", "mmhr-1", "mmh-1", "mm/hour"):
        return 24.0, "converted from mm/hr to mm/day (×24)"
    return 1.0, ""


_RETRYABLE = re.compile(r"status 5\d\d|did not answer in time|could not be reached")


async def fetch_csv(
    client: httpx.AsyncClient,
    data_id: str,
    latitude: float,
    longitude: float,
    first: int,
    last: int,
    token: str,
) -> tuple[dict[str, str], list[Sample]]:
    """One time-series request for ``first``..``last`` (years). A server error or timeout on a
    multi-year window (Giovanni answers 500 when a request is too large) is retried as two
    halves, down to single years."""
    try:
        response = await get_checked(
            client, f"{settings.giovanni_url}/timeseries", source=SOURCE,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "data": data_id,
                "location": f"[{round(latitude, 4)},{round(longitude, 4)}]",
                "time": f"{first}-01-01T00:00:00/{last}-12-31T23:59:59",
            },
            timeout=settings.giovanni_timeout,
        )
    except UpstreamError as exc:
        if last > first and _RETRYABLE.search(exc.message):
            middle = (first + last) // 2
            head, rows_a = await fetch_csv(client, data_id, latitude, longitude, first, middle, token)
            tail, rows_b = await fetch_csv(client, data_id, latitude, longitude, middle + 1, last, token)
            return head or tail, rows_a + rows_b
        raise
    return parse_timeseries_csv(response.text)


async def fetch_giovanni(
    client: httpx.AsyncClient,
    code: str,
    latitude: float,
    longitude: float,
    start: int,
    end: int,
) -> dict[str, Any]:
    token = require_token()
    spec = VARIABLES[code]
    data_id = await resolve_data_id(client, code, token)
    # Monthly products: windows of 10 years; 3-hourly fallbacks: 2 years (far fewer rows each).
    step = 10 if "_M_" in data_id or "IMERGM" in data_id else 2
    windows = [(year, min(end, year + step - 1)) for year in range(start, end + 1, step)]
    results = []
    for first, last in windows:  # sequential: Giovanni applies a per-user quota
        results.append(await fetch_csv(client, data_id, latitude, longitude, first, last, token))
    header = next((h for h, _ in results if h), {})
    raw = [sample for _, part in results for sample in part]
    factor, conversion = unit_factor(header.get("unit", ""), spec["native_unit"])
    samples = [(day, value * factor) for day, value in raw]
    points, used = monthly_means(samples)
    require_points(points, SOURCE)
    grid = ""
    if header.get("lat") and header.get("lon"):
        grid = f" Grid cell centre: {header['lat']}, {header['lon']}."
    return {
        "points": points,
        "product": data_id,
        "spatialResolution": spec["resolution"],
        "processing": (
            f"{used} native time steps retrieved from Giovanni ({data_id}); fill values removed; "
            f"monthly mean{'; ' + conversion if conversion else ''}.{grid}"
        ),
        "quality": spec["quality"],
        "documentation": spec["documentation"],
        "extra": {"variableName": header.get("param_name", ""), "nativeUnit": header.get("unit", spec["native_unit"])},
    }
