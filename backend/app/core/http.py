"""Shared HTTP client and JSON response helpers."""

from __future__ import annotations

import json
import math
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings


def create_http_client() -> httpx.AsyncClient:
    """Create the application-wide async HTTP client (connection pooling)."""
    return httpx.AsyncClient(
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
    )


def get_http_client(request: Request) -> httpx.AsyncClient:
    """FastAPI dependency returning the client created during app startup."""
    return request.app.state.http


def to_json_safe(value: Any) -> Any:
    """Replace non-finite floats with ``None``.

    JavaScript's ``JSON.stringify`` turns ``Infinity``/``NaN`` into ``null``;
    Python would otherwise emit invalid JSON. This keeps the original contract.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]
    return value


class SafeJSONResponse(JSONResponse):
    """JSON response that tolerates non-finite floats and keeps UTF-8 text."""

    def render(self, content: Any) -> bytes:
        return json.dumps(
            to_json_safe(content),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
