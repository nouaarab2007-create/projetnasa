"""GET /api/geocode — OpenStreetMap Nominatim place search proxy."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Request

from app.core.errors import DomainError, error_message
from app.core.http import SafeJSONResponse, get_http_client
from app.services.geocoding import geocode_place

router = APIRouter()


@router.get("/geocode")
async def get_geocode(
    request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SafeJSONResponse:
    query = (request.query_params.get("q") or "").strip()
    if not query:
        return SafeJSONResponse({"error": "A place name is required."}, status_code=400)
    try:
        results = await geocode_place(client, query)
        return SafeJSONResponse({"results": results})
    except DomainError as exc:
        return SafeJSONResponse({"error": exc.message}, status_code=exc.status_code)
    except Exception as exc:  # noqa: BLE001
        return SafeJSONResponse(
            {"error": error_message(exc, "Place search failed.")},
            status_code=502,
        )
