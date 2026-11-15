"""Aggregate all REST endpoints under ``/api``."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import analysis, catalog, comparison, data, forecast, geocode, health, tiles

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(catalog.router, tags=["catalog"])
api_router.include_router(data.router, tags=["science"])
api_router.include_router(analysis.router, tags=["science"])
api_router.include_router(comparison.router, tags=["science"])
api_router.include_router(forecast.router, tags=["science"])
api_router.include_router(geocode.router, tags=["geospatial"])
api_router.include_router(tiles.router, tags=["geospatial"])

