"""Application settings.

Every value can be overridden with an environment variable of the same name
prefixed by ``TD_`` (for example ``TD_POWER_TIMEOUT=60``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


def _env(name: str, default: str) -> str:
    return os.getenv(f"TD_{name}", default)


def _secret(name: str) -> str:
    """Read a credential from ``NAME`` or ``TD_NAME``. Credentials are never hard-coded."""
    return (os.getenv(name) or os.getenv(f"TD_{name}") or "").strip()


def earthdata_token() -> str:
    """NASA Earthdata Login token (https://urs.earthdata.nasa.gov -> Generate Token)."""
    return _secret("EARTHDATA_TOKEN")


def noaa_cdo_token() -> str:
    """Optional NOAA Climate Data Online token (https://www.ncdc.noaa.gov/cdo-web/token)."""
    return _secret("NOAA_CDO_TOKEN")


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the API and the static frontend."""

    app_name: str = "Trend Detective"
    frontend_dir: Path = field(
        default_factory=lambda: Path(_env("FRONTEND_DIR", str(PROJECT_DIR / "frontend")))
    )
    user_agent: str = "Trend-Detective-NASA-Space-Apps/1.0"

    # NASA POWER monthly point API.
    power_url: str = "https://power.larc.nasa.gov/api/temporal/monthly/point"
    power_timeout: float = float(_env("POWER_TIMEOUT", "45"))
    power_cache_seconds: int = int(_env("POWER_CACHE_SECONDS", "86400"))
    power_daily_url: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
    power_daily_timeout: float = float(_env("POWER_DAILY_TIMEOUT", "120"))

    # OpenStreetMap Nominatim place search.
    geocode_url: str = "https://nominatim.openstreetmap.org/search"
    geocode_timeout: float = float(_env("GEOCODE_TIMEOUT", "10"))

    # OpenStreetMap raster tiles (proxied so the browser never calls OSM directly).
    tile_url: str = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    tile_timeout: float = float(_env("TILE_TIMEOUT", "10"))
    tile_cache_seconds: int = int(_env("TILE_CACHE_SECONDS", "604800"))
    tile_cache_entries: int = int(_env("TILE_CACHE_ENTRIES", "2000"))

    # Cache lifetime shared by the other dataset connectors (24 h by default).
    dataset_cache_seconds: int = int(_env("DATASET_CACHE_SECONDS", "86400"))

    # Trained flash-drought early-warning models (LightGBM + SHAP), exported by the training notebook.
    fd_bundle_dir: Path = field(
        default_factory=lambda: Path(_env("FD_BUNDLE_DIR", str(BACKEND_DIR / "models" / "fd_bundle")))
    )

    # MODIS land products (MOD13Q1, MOD11A2, MOD15A2H) via the ORNL DAAC web service.
    # No account needed; the service returns at most 10 composites per request.
    modis_url: str = "https://modis.ornl.gov/rst/api/v1"
    modis_timeout: float = float(_env("MODIS_TIMEOUT", "60"))
    modis_concurrency: int = int(_env("MODIS_CONCURRENCY", "4"))

    # Giovanni in the Cloud time-series service (GES DISC): GLDAS and GPM IMERG.
    # Needs EARTHDATA_TOKEN. Replaces the Hydrology Data Rods service.
    giovanni_url: str = "https://api.giovanni.earthdata.nasa.gov"
    giovanni_timeout: float = float(_env("GIOVANNI_TIMEOUT", "180"))

    # NOAA NCEI Global Summary of the Month. The Access Data Service needs no token;
    # Climate Data Online v2 is the fallback when NOAA_CDO_TOKEN is set.
    noaa_access_url: str = "https://www.ncei.noaa.gov/access/services/data/v1"
    noaa_cdo_url: str = "https://www.ncei.noaa.gov/cdo-web/api/v2"
    noaa_timeout: float = float(_env("NOAA_TIMEOUT", "60"))

    # SWOT Hydrocron (PO.DAAC): river reach / lake water-surface elevation. No account needed.
    hydrocron_url: str = "https://soto.podaac.earthdatacloud.nasa.gov/hydrocron/v1/timeseries"
    hydrocron_timeout: float = float(_env("HYDROCRON_TIMEOUT", "60"))


settings = Settings()
