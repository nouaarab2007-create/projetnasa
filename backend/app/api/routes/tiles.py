"""GET /api/tiles/{z}/{x}/{y} — OpenStreetMap raster tile proxy."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.errors import DomainError
from app.core.http import get_http_client
from app.services.tiles import fetch_osm_tile

router = APIRouter()


@router.get("/tiles/{z}/{x}/{y}")
async def get_tile(
    z: str,
    x: str,
    y: str,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> Response:
    try:
        tile_bytes = await fetch_osm_tile(client, z, x, y)
    except DomainError as exc:
        return Response(
            content=exc.message,
            status_code=exc.status_code,
            media_type="text/plain; charset=utf-8",
        )
    return Response(
        content=tile_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=604800, stale-while-revalidate=86400",
        },
    )
