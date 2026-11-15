"""NOAA NCEI Global Summary of the Month (GSOM) station data.

1. NCEI Access Data Service (no token):
   GET https://www.ncei.noaa.gov/access/services/data/v1?dataset=global-summary-of-the-month
       &dataTypes=TAVG&boundingBox=N,W,S,E&startDate=...&endDate=...&units=metric&format=json
       &includeStationName=true&includeStationLocation=1
   The search box grows until a station with data is found.
2. Climate Data Online v2 (fallback, needs NOAA_CDO_TOKEN in a ``token`` header):
   /stations?extent=S,W,N,E&datasetid=GSOM&datatypeid=..., then /data in 10-year windows
   (monthly data is limited to a ten-year range per request, 1000 rows per page).

The station with the most valid months is used; among stations with at least
80 % of that record, the nearest one wins.
"""

from __future__ import annotations

import math
from typing import Any

import httpx

from app.config import noaa_cdo_token, settings
from app.core.errors import DomainError, UpstreamError
from app.services.series import Sample, get_checked, monthly_means, require_points, to_float

SOURCE = "NOAA NCEI"
DATATYPES = {"NOAA_TAVG": "TAVG", "NOAA_TMAX": "TMAX", "NOAA_TMIN": "TMIN", "NOAA_PRCP": "PRCP"}
SEARCH_HALF_WIDTHS = (0.25, 0.75, 1.5)  # degrees around the point


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(a)))


def _box(latitude: float, longitude: float, half: float) -> tuple[float, float, float, float]:
    north = min(90.0, latitude + half)
    south = max(-90.0, latitude - half)
    west = max(-180.0, longitude - half)
    east = min(180.0, longitude + half)
    return north, west, south, east


def pick_station(stations: dict[str, dict[str, Any]], latitude: float, longitude: float) -> dict[str, Any] | None:
    """Most complete record; among those with >= 80 % of it, the nearest station."""
    usable = [s for s in stations.values() if len(s["samples"]) >= 3]
    if not usable:
        return None
    best = max(len(s["samples"]) for s in usable)
    finalists = [s for s in usable if len(s["samples"]) >= 0.8 * best]
    for station in finalists:
        if station.get("lat") is not None and station.get("lon") is not None:
            station["distanceKm"] = distance_km(latitude, longitude, station["lat"], station["lon"])
        else:
            station["distanceKm"] = math.inf
    return min(finalists, key=lambda s: (s["distanceKm"], -len(s["samples"])))


def group_access_rows(rows: Any, datatype: str) -> dict[str, dict[str, Any]]:
    """Group Access Data Service JSON rows by station."""
    stations: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return stations
    for row in rows:
        if not isinstance(row, dict):
            continue
        station_id = str(row.get("STATION", "")).strip()
        day = str(row.get("DATE", "")).strip()
        value = to_float(row.get(datatype))
        if not station_id or len(day) < 7 or value is None:
            continue
        entry = stations.setdefault(
            station_id,
            {
                "id": station_id,
                "name": str(row.get("NAME", "")).strip(),
                "lat": to_float(row.get("LATITUDE")),
                "lon": to_float(row.get("LONGITUDE")),
                "samples": [],
            },
        )
        entry["samples"].append((day[:7], value))
    return stations


async def _via_access_service(
    client: httpx.AsyncClient, datatype: str, latitude: float, longitude: float, start: int, end: int
) -> dict[str, Any] | None:
    for half in SEARCH_HALF_WIDTHS:
        north, west, south, east = _box(latitude, longitude, half)
        response = await get_checked(
            client, settings.noaa_access_url, source=SOURCE, timeout=settings.noaa_timeout,
            params={
                "dataset": "global-summary-of-the-month",
                "dataTypes": datatype,
                "boundingBox": f"{north},{west},{south},{east}",
                "startDate": f"{start}-01-01",
                "endDate": f"{end}-12-31",
                "units": "metric",
                "format": "json",
                "includeStationName": "true",
                "includeStationLocation": "1",
            },
        )
        try:
            rows = response.json()
        except ValueError as exc:
            raise UpstreamError("NOAA NCEI returned an unreadable response.") from exc
        station = pick_station(group_access_rows(rows, datatype), latitude, longitude)
        if station:
            station["api"] = "NCEI Access Data Service"
            station["searchHalfWidth"] = half
            return station
    return None


async def _via_cdo(
    client: httpx.AsyncClient, token: str, datatype: str, latitude: float, longitude: float, start: int, end: int
) -> dict[str, Any] | None:
    headers = {"token": token}
    for half in SEARCH_HALF_WIDTHS:
        north, west, south, east = _box(latitude, longitude, half)
        response = await get_checked(
            client, f"{settings.noaa_cdo_url}/stations", source="NOAA Climate Data Online",
            headers=headers, timeout=settings.noaa_timeout,
            params={
                "extent": f"{south},{west},{north},{east}",
                "datasetid": "GSOM",
                "datatypeid": datatype,
                "startdate": f"{start}-01-01",
                "enddate": f"{end}-12-31",
                "limit": 1000,
            },
        )
        found = (response.json() or {}).get("results") or []
        if not found:
            continue
        candidates = sorted(
            found,
            key=lambda s: (
                -float(s.get("datacoverage") or 0),
                distance_km(latitude, longitude, float(s.get("latitude", latitude)), float(s.get("longitude", longitude))),
            ),
        )[:3]
        stations: dict[str, dict[str, Any]] = {}
        for meta in candidates:
            samples: list[Sample] = []
            for first in range(start, end + 1, 10):  # ten-year limit per request
                last = min(end, first + 9)
                data = await get_checked(
                    client, f"{settings.noaa_cdo_url}/data", source="NOAA Climate Data Online",
                    headers=headers, timeout=settings.noaa_timeout,
                    params={
                        "datasetid": "GSOM",
                        "stationid": meta["id"],
                        "datatypeid": datatype,
                        "startdate": f"{first}-01-01",
                        "enddate": f"{last}-12-31",
                        "units": "metric",
                        "limit": 1000,
                    },
                )
                for row in (data.json() or {}).get("results") or []:
                    value = to_float(row.get("value"))
                    day = str(row.get("date", ""))
                    if value is not None and len(day) >= 7:
                        samples.append((day[:7], value))
            stations[meta["id"]] = {
                "id": meta["id"],
                "name": meta.get("name", ""),
                "lat": to_float(meta.get("latitude")),
                "lon": to_float(meta.get("longitude")),
                "samples": samples,
            }
        station = pick_station(stations, latitude, longitude)
        if station:
            station["api"] = "Climate Data Online v2"
            station["searchHalfWidth"] = half
            return station
    return None


async def fetch_noaa(
    client: httpx.AsyncClient,
    code: str,
    latitude: float,
    longitude: float,
    start: int,
    end: int,
) -> dict[str, Any]:
    datatype = DATATYPES[code]
    station: dict[str, Any] | None = None
    access_error: Exception | None = None
    try:
        station = await _via_access_service(client, datatype, latitude, longitude, start, end)
    except (DomainError, httpx.HTTPError) as exc:
        access_error = exc

    token = noaa_cdo_token()
    if station is None and token:
        try:
            station = await _via_cdo(client, token, datatype, latitude, longitude, start, end)
        except (ValueError, TypeError, KeyError) as exc:
            raise UpstreamError("NOAA Climate Data Online returned an unreadable response.") from exc

    if station is None:
        if access_error is not None:
            hint = "" if token else " Setting NOAA_CDO_TOKEN enables the Climate Data Online fallback."
            raise UpstreamError(f"{getattr(access_error, 'message', str(access_error))}{hint}")
        widest = SEARCH_HALF_WIDTHS[-1]
        raise DomainError(
            f"No NOAA station with monthly {datatype} data was found within about {widest}° of this "
            f"point for {start}–{end}. Try a point closer to a town or airport."
        )

    in_range = [(day, value) for day, value in station["samples"] if start <= int(day[:4]) <= end]
    points, used = monthly_means(in_range)
    require_points(points, SOURCE)
    distance = station.get("distanceKm")
    distance_text = f"{distance:.1f} km from the selected point" if distance not in (None, math.inf) else "distance unknown"
    unit_note = "monthly total (mm)" if datatype == "PRCP" else "monthly mean (°C)"
    return {
        "points": points,
        "product": f"Global Summary of the Month (GSOM) · {datatype}",
        "spatialResolution": "Single ground station (point measurement)",
        "processing": (
            f"{used} monthly {datatype} values from station {station['id']} ({station.get('name') or 'unnamed'}), "
            f"{distance_text}; retrieved through the {station['api']}; {unit_note}; metric units."
        ),
        "quality": (
            "In-situ measurement at one station. Station moves, instrument changes and gaps can "
            "affect long-term trends; GSOM values are not homogenized."
        ),
        "documentation": "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-monthly",
        "extra": {
            "station": f"{station['id']} {station.get('name', '')}".strip(),
            "stationLocation": (
                f"{station['lat']:.4f}, {station['lon']:.4f}"
                if station.get("lat") is not None and station.get("lon") is not None
                else "unknown"
            ),
            "stationDistance": distance_text,
        },
    }
