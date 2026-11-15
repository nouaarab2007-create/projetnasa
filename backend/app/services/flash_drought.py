"""Fetch the soil-moisture record and run flash-drought detection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.errors import DomainError
from app.science.flash_drought import active_months_from_tmax, detect_flash_droughts
from app.services.nasa_power import fetch_power_data

CLIMATOLOGY_START = 1981  # first year of NASA POWER MERRA-2 soil wetness


async def flash_drought_for(
    client: httpx.AsyncClient, latitude: float, longitude: float, start: int, end: int
) -> dict[str, Any]:
    """Rank the chosen period against the full 1981-present record at this point."""
    last_full_year = datetime.now(timezone.utc).year - 1
    note = ""
    try:
        record = await fetch_power_data(
            client,
            parameter="GWETROOT",
            latitude=latitude,
            longitude=longitude,
            start=CLIMATOLOGY_START,
            end=last_full_year,
        )
        climatology = f"{CLIMATOLOGY_START}-{last_full_year}"
    except Exception:  # noqa: BLE001 — fall back to the chosen period only
        record = await fetch_power_data(
            client, parameter="GWETROOT", latitude=latitude, longitude=longitude, start=start, end=end
        )
        climatology = f"{start}-{end}"
        note = "Percentiles were computed from the selected period only because the full record was unavailable."
    try:  # active season from the data: months whose normal daily maximum is >= 10 °C
        temps = await fetch_power_data(
            client, parameter="T2M_MAX", latitude=latitude, longitude=longitude,
            start=CLIMATOLOGY_START, end=last_full_year,
        )
        active = active_months_from_tmax(temps["points"])
    except Exception:  # noqa: BLE001 — without temperature, every month counts
        active = None
    try:
        result = detect_flash_droughts(
            record["points"], int(start), int(end), climatology_note=note, active_months=active
        )
    except ValueError as exc:
        raise DomainError(str(exc)) from exc
    result["climatology"] = climatology
    result["latitude"] = record["metadata"].get("latitude")
    result["longitude"] = record["metadata"].get("longitude")
    return result
