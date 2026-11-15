"""POST /api/comparison — compare two regions over the same variable and period."""

from __future__ import annotations

import asyncio
import math
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request

from app.core.errors import DomainError, error_message
from app.core.http import SafeJSONResponse, get_http_client
from app.schemas import validate_mode
from app.science.statistics import analyze
from app.science.transform import ensure_enough_points, transform
from app.services.datasets import fetch_series

router = APIRouter()


def _to_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip() or "0")
    except ValueError:
        return math.nan


def _to_year(value: Any) -> int | float:
    num = _to_number(value)
    if math.isfinite(num) and num.is_integer():
        return int(num)
    return num


@router.post("/comparison")
async def post_comparison(
    request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SafeJSONResponse:
    try:
        try:
            body: Any = await request.json()
        except ValueError as exc:
            raise DomainError("Invalid JSON request body.") from exc
        if not isinstance(body, dict):
            raise DomainError("Two regions are required.")

        region_a = body.get("regionA")
        region_b = body.get("regionB")
        if not isinstance(region_a, dict) or not isinstance(region_b, dict):
            raise DomainError("Two regions are required.")

        parameter = body.get("parameter") or "T2M"
        start = _to_year(body.get("start"))
        end = _to_year(body.get("end"))
        mode = validate_mode(body.get("mode") or "annual")

        first, second = await asyncio.gather(
            fetch_series(
                client,
                parameter=parameter,
                latitude=_to_number(region_a.get("latitude")),
                longitude=_to_number(region_a.get("longitude")),
                start=start,
                end=end,
                feature_id=region_a.get("featureId"),
            ),
            fetch_series(
                client,
                parameter=parameter,
                latitude=_to_number(region_b.get("latitude")),
                longitude=_to_number(region_b.get("longitude")),
                start=start,
                end=end,
                feature_id=region_b.get("featureId"),
            ),
        )
        points_a = ensure_enough_points(transform(first["points"], mode), mode)
        points_b = ensure_enough_points(transform(second["points"], mode), mode)
        analysis_a = analyze(points_a, parameter)
        analysis_b = analyze(points_b, parameter)
        return SafeJSONResponse(
            {
                "regionA": {
                    "points": points_a,
                    "metadata": first["metadata"],
                    "analysis": analysis_a,
                },
                "regionB": {
                    "points": points_b,
                    "metadata": second["metadata"],
                    "analysis": analysis_b,
                },
                "differencePerDecade": analysis_a["trendPerDecade"] - analysis_b["trendPerDecade"],
                "interpretation": (
                    "Different regional trends can coexist; this comparison does not establish a "
                    "shared or distinct cause."
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001 — return uniform 400 JSON payload
        message = error_message(exc, "Unable to compare regions.")
        return SafeJSONResponse({"error": message}, status_code=400)
