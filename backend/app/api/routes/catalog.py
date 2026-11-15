"""Catalogue endpoints: /api/variables, /api/regions, /api/sources."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.science.catalog import REGIONS, SOURCES, VARIABLES

router = APIRouter()


@router.get("/variables")
async def get_variables() -> dict[str, Any]:
    return {"variables": VARIABLES}


@router.get("/regions")
async def get_regions() -> dict[str, Any]:
    return {
        "regions": REGIONS,
        "note": (
            "NASA POWER values represent a grid cell, not an exact measurement at the selected "
            "coordinate."
        ),
    }


@router.get("/sources")
async def get_sources() -> dict[str, Any]:
    return {"sources": SOURCES}
