"""FastAPI application entry point for Trend Detective.

Mounts the REST API under ``/api``, serves static assets under ``/assets``
(plus ``/favicon.svg`` and Leaflet marker images at root for compatibility),
and maps the 9 frontend routes (``/``, ``/explorer``, ``/analysis``,
``/variables``, ``/regions``, ``/comparison``, ``/sources``, ``/methodology``,
``/about``) to their HTML pages. Unknown non-API routes receive ``404.html``
with HTTP status 404.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import settings
from app.core.http import SafeJSONResponse, create_http_client

PAGE_ROUTES: dict[str, str] = {
    "": "index.html",
    "explorer": "explorer.html",
    "analysis": "analysis.html",
    "variables": "variables.html",
    "sources": "sources.html",
    "about": "about.html",
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and cleanly close the shared async HTTP client."""
    async with create_http_client() as client:
        app.state.http = client
        yield


def create_app(frontend_dir: Path | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    resolved_frontend = frontend_dir or settings.frontend_dir
    pages_dir = resolved_frontend / "pages"
    assets_dir = resolved_frontend / "assets"

    app = FastAPI(
        title="Trend Detective API",
        description="NASA Earth science trend investigation platform (REST API + HTML5/CSS3/JS frontend).",
        version="1.0.0",
        lifespan=lifespan,
        default_response_class=SafeJSONResponse,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon() -> Response:
        icon_path = assets_dir / "images" / "favicon.svg"
        if icon_path.is_file():
            return FileResponse(icon_path, media_type="image/svg+xml")
        return Response(status_code=404)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_page(full_path: str) -> Response:
        normalized = full_path.strip("/")
        if normalized.startswith("pages/"):
            normalized = normalized[6:]
        if normalized.endswith(".html"):
            normalized = normalized[:-5]
            if normalized == "index":
                normalized = ""

        page_filename = PAGE_ROUTES.get(normalized)
        if page_filename:
            page_path = pages_dir / page_filename
            if page_path.is_file():
                return FileResponse(page_path, media_type="text/html; charset=utf-8")

        not_found_path = pages_dir / "404.html"
        if not_found_path.is_file():
            return HTMLResponse(
                content=not_found_path.read_text(encoding="utf-8"),
                status_code=404,
            )
        return HTMLResponse(content="<h1>Page Not Found</h1>", status_code=404)

    return app


app = create_app()
