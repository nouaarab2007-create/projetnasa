"""GET /api/data — retrieve transformed observations (any catalogue source) without statistics."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Request

from app.core.errors import error_message
from app.core.http import SafeJSONResponse, get_http_client
from app.schemas import parse_float_param, parse_year_param, validate_mode
from app.science.transform import transform
from app.services.datasets import fetch_series

router = APIRouter()


@router.get("/data")
async def get_data(
    request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SafeJSONResponse:
    try:
        search = request.query_params
        mode = validate_mode(search.get("mode"))
        parameter = search.get("parameter") or "T2M"
        result = await fetch_series(
            client,
            parameter=parameter,
            latitude=parse_float_param(search.get("latitude")),
            longitude=parse_float_param(search.get("longitude")),
            start=parse_year_param(search.get("start")),
            end=parse_year_param(search.get("end")),
            feature_id=search.get("featureId"),
        )
        return SafeJSONResponse(
            {
                **result,
                "points": transform(result["points"], mode),
                "mode": mode,
            }
        )
    except Exception as exc:  # noqa: BLE001 — return uniform 400 JSON payload
        message = error_message(exc, "Unable to retrieve data.")
        return SafeJSONResponse({"error": message, "simulated": False}, status_code=400)
