"""Pydantic schemas and query parsing helpers for the REST API."""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.errors import DomainError
from app.science.transform import MODES


def parse_float_param(raw: str | None) -> float:
    """Convert a query string value to float like JS ``Number(search.get(...))``.

    - Missing/None becomes ``0.0`` (``Number(null) === 0``) so the downstream
      domain validator emits its exact user-facing error message.
    - Non-numeric strings become ``math.nan`` so range checks reject them with
      the domain message instead of a generic FastAPI 422 response.
    """
    if raw is None:
        return 0.0
    text = raw.strip()
    if text == "":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return math.nan


def parse_year_param(raw: str | None) -> int | float:
    """Convert a query string year to an int when integral, or float/NaN otherwise."""
    value = parse_float_param(raw)
    if math.isfinite(value) and value.is_integer():
        return int(value)
    return value


def validate_mode(mode: str | None) -> str:
    """Validate the temporal processing mode."""
    resolved = mode if mode is not None else "annual"
    if resolved not in MODES:
        raise DomainError("Unsupported analysis mode.")
    return resolved


class RegionCoordinates(BaseModel):
    """Region coordinate pair submitted to ``POST /api/comparison``."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    name: str | None = None
    biome: str | None = None
    latitude: Any = None
    longitude: Any = None


class ComparisonRequest(BaseModel):
    """Payload for ``POST /api/comparison``."""

    model_config = ConfigDict(extra="ignore")

    parameter: str | None = "T2M"
    start: Any = None
    end: Any = None
    mode: str | None = "annual"
    regionA: dict[str, Any] | None = None
    regionB: dict[str, Any] | None = None
