"""Event-based risks at a point, computed from every dataset that can measure them.

| Hazard           | Sources (first available = headline, others = cross-check)       |
|------------------|-------------------------------------------------------------------|
| heatWave         | NASA POWER daily T2M_MAX · NOAA GHCN-Daily TMAX                   |
| extremeRain      | NASA POWER daily PRECTOTCORR · GPM IMERG daily · NOAA daily PRCP  |
| rainDrought      | same three rainfall sources                                       |
| flashDrought     | NASA POWER GWETROOT (monthly) · GLDAS root-zone soil moisture     |

``sources`` limits which providers run (the Explorer asks for "power" first, then
"giovanni,noaa"), so fast results show first. Each hazard returns a list of
per-source results; a source that fails returns ``{"error": ...}`` instead and
never stops the others.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import httpx

from app.core.errors import DomainError, error_message
from app.science.extremes import (
    detect_extreme_rain,
    detect_heat_waves,
    detect_rain_drought,
    from_flash_drought,
)
from app.science.flash_drought import detect_flash_droughts
from app.science.flash_drought_daily import detect_flash_droughts_daily
from app.services import daily
from app.services.datasets import fetch_series
from app.services.flash_drought import flash_drought_for

HAZARDS = ("heatWave", "extremeRain", "rainDrought", "flashDrought")
FIRST_YEAR = 1981

# Lower number = preferred headline source.
PRIORITY = {"power": 0, "giovanni": 1, "noaa": 2}


def _last_full_year() -> int:
    return datetime.now(timezone.utc).year - 1


async def hazards_for(
    client: httpx.AsyncClient,
    latitude: float,
    longitude: float,
    start: int,
    end: int,
    sources: set[str] | None = None,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    wanted = sources or {"power", "giovanni", "noaa"}
    last = _last_full_year()
    out: dict[str, dict[str, list[dict[str, Any]]]] = {h: {"results": []} for h in HAZARDS}
    jobs: list[Awaitable[None]] = []

    def add(hazard: str, provider: str, label: str, fn: Callable[[], Awaitable[dict[str, Any]]]) -> None:
        async def run() -> None:
            try:
                result = await fn()
                result.setdefault("sourceLabel", label)
            except Exception as exc:  # noqa: BLE001 — one source must not stop the others
                result = {"sourceLabel": label, "error": error_message(exc, "Retrieval failed.")}
            result["provider"] = provider
            result["priority"] = PRIORITY[provider]
            out[hazard]["results"].append(result)

        jobs.append(run())

    def daily_job(fetch: Callable[[], Awaitable[dict[str, Any]]], detect: Callable[[list], dict[str, Any]]):
        async def go() -> dict[str, Any]:
            series = await fetch()
            result = detect(series["samples"])
            result.update(sourceLabel=series["label"], product=series["product"], sourceNote=series["note"])
            return result

        return go

    if "power" in wanted:
        power_task: asyncio.Task | None = None

        async def power_series(name: str) -> dict[str, Any]:
            nonlocal power_task
            if power_task is None:  # one request serves the three hazards
                power_task = asyncio.ensure_future(daily.power_daily(client, latitude, longitude, FIRST_YEAR, last))
            return (await power_task)[name]

        add("heatWave", "power", "NASA POWER", daily_job(
            lambda: power_series("T2M_MAX"), lambda s: detect_heat_waves(s, latitude, start, end)))
        add("extremeRain", "power", "NASA POWER", daily_job(
            lambda: power_series("PRECTOTCORR"), lambda s: detect_extreme_rain(s, start, end)))
        add("rainDrought", "power", "NASA POWER", daily_job(
            lambda: power_series("PRECTOTCORR"), lambda s: detect_rain_drought(s, start, end)))

        async def power_flash() -> dict[str, Any]:
            # Main method: daily soil moisture in 5-day means. Monthly data only if daily fails.
            try:
                soil = await power_series("GWETROOT")
                tmax = await power_series("T2M_MAX")
                if not soil["samples"]:
                    raise DomainError("NASA POWER returned no daily soil moisture.")
            except Exception as exc:  # noqa: BLE001
                raw = await flash_drought_for(client, latitude, longitude, start, end)
                result = from_flash_drought(raw, end)
                result.update(
                    product="POWER Monthly Point API · GWETROOT",
                    sourceNote="Root-zone soil wetness, 0.5° cell",
                    resolution="monthly (fallback)",
                    caveat=f"{result['caveat']} Monthly fallback: {error_message(exc, 'daily data unavailable')}",
                )
                return result
            raw = detect_flash_droughts_daily(soil["samples"], start, end, tmax=tmax["samples"])
            result = from_flash_drought(raw, end)
            result.update(product="POWER Daily Point API · GWETROOT", sourceNote="Root-zone soil wetness, 0.5° cell")
            return result

        add("flashDrought", "power", "NASA POWER", power_flash)

    if "giovanni" in wanted:
        imerg_task: asyncio.Task | None = None

        async def imerg() -> dict[str, Any]:
            nonlocal imerg_task
            if imerg_task is None:
                imerg_task = asyncio.ensure_future(daily.imerg_daily(client, latitude, longitude, 2001, last))
            return await imerg_task

        add("extremeRain", "giovanni", "NASA GPM IMERG", daily_job(imerg, lambda s: detect_extreme_rain(s, start, end)))
        add("rainDrought", "giovanni", "NASA GPM IMERG", daily_job(imerg, lambda s: detect_rain_drought(s, start, end)))

        async def gldas_flash() -> dict[str, Any]:
            try:  # cold-season filter from NASA POWER temperature (usually cached by now)
                tmax = (await daily.power_daily(client, latitude, longitude, FIRST_YEAR, last))["T2M_MAX"]["samples"]
            except Exception:  # noqa: BLE001
                tmax = None
            try:
                soil = await daily.gldas_root_daily(client, latitude, longitude, 2000, last)
            except Exception as exc:  # noqa: BLE001 — monthly GLDAS as a fallback
                if "EARTHDATA_TOKEN" in error_message(exc, ""):
                    raise
                record = await fetch_series(
                    client, parameter="GLDAS_ROOT_ZONE_SM", latitude=latitude, longitude=longitude, start=2000, end=last
                )
                raw = detect_flash_droughts(record["points"], int(start), int(end))
                result = from_flash_drought(raw, end)
                result.update(
                    product=record["metadata"].get("product", "GLDAS-2.1 root-zone soil moisture"),
                    sourceNote="Land-surface model, 0.25° cell, from 2000",
                    resolution="monthly (fallback)",
                )
                return result
            raw = detect_flash_droughts_daily(soil["samples"], start, end, tmax=tmax)
            result = from_flash_drought(raw, end)
            result.update(product=soil["product"], sourceNote=soil["note"])
            return result

        add("flashDrought", "giovanni", "NASA GLDAS", gldas_flash)

    if "noaa" in wanted:
        add("heatWave", "noaa", "NOAA station", daily_job(
            lambda: daily.noaa_daily(client, "TMAX", latitude, longitude, FIRST_YEAR, last),
            lambda s: detect_heat_waves(s, latitude, start, end)))
        noaa_rain_task: asyncio.Task | None = None

        async def noaa_rain() -> dict[str, Any]:
            nonlocal noaa_rain_task
            if noaa_rain_task is None:
                noaa_rain_task = asyncio.ensure_future(
                    daily.noaa_daily(client, "PRCP", latitude, longitude, FIRST_YEAR, last))
            return await noaa_rain_task

        add("extremeRain", "noaa", "NOAA station", daily_job(noaa_rain, lambda s: detect_extreme_rain(s, start, end)))
        add("rainDrought", "noaa", "NOAA station", daily_job(noaa_rain, lambda s: detect_rain_drought(s, start, end)))

    await asyncio.gather(*jobs)
    for entry in out.values():
        entry["results"].sort(key=lambda r: r["priority"])
    return out
