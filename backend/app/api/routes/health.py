"""GET /api/health — service health probe and dataset readiness."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from app.config import earthdata_token, noaa_cdo_token

router = APIRouter()


@router.get("/health")
async def get_health() -> dict[str, Any]:
    has_earthdata = bool(earthdata_token())
    return {
        "status": "ok",
        "service": "Trend Detective",
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        # Only whether each token is set is reported, never its value.
        "credentials": {
            "EARTHDATA_TOKEN": has_earthdata,
            "NOAA_CDO_TOKEN": bool(noaa_cdo_token()),
        },
        "datasets": {
            "power": "ready",
            "modis": "ready",
            "noaa": "ready",
            "swot": "ready (needs a reach or lake ID per request)",
            "giovanni": "ready" if has_earthdata else "needs EARTHDATA_TOKEN",
            "gldas": "ready" if has_earthdata else "needs EARTHDATA_TOKEN",
        },
    }
