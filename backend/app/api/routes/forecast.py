"""GET /api/flash-forecast and GET /api/flash-forecast/model — trained flash-drought early-warning model."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.errors import error_message
from app.core.http import SafeJSONResponse
from app.schemas import parse_float_param
from app.services.flash_forecast import HORIZONS, forecast_for, model_info

router = APIRouter()


@router.get("/flash-forecast/model")
async def get_model_info() -> SafeJSONResponse:
    try:
        return SafeJSONResponse(model_info())
    except Exception as exc:  # noqa: BLE001
        return SafeJSONResponse({"error": error_message(exc, "Model information unavailable.")}, status_code=503)


@router.get("/flash-forecast")
async def get_flash_forecast(request: Request) -> SafeJSONResponse:
    """Probability of a flash-drought onset in the next 7, 14 and 30 days at a point.

    Query: ``latitude``, ``longitude``, optional ``date`` (YYYY-MM-DD, default: latest
    available) and ``horizon`` (7, 14 or 30; default: all three).
    """
    try:
        search = request.query_params
        raw = search.get("horizon")
        if raw and (not raw.isdigit() or int(raw) not in HORIZONS):
            return SafeJSONResponse({"error": "horizon must be 7, 14 or 30."}, status_code=400)
        horizons = (int(raw),) if raw else HORIZONS
        result = await forecast_for(
            parse_float_param(search.get("latitude")),
            parse_float_param(search.get("longitude")),
            search.get("date"),
            horizons,
        )
        return SafeJSONResponse(result)
    except Exception as exc:  # noqa: BLE001 — uniform JSON error payload
        return SafeJSONResponse({"error": error_message(exc, "Flash-drought forecast failed.")}, status_code=400)
