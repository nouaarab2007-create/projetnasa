"""Flash-drought early-warning model (trained LightGBM + SHAP) served to the API.

Wraps ``app.ml`` (the trained model code and the exported ``models/fd_bundle``):
for any place and date it pulls the last days (and, the first time a place is seen,
the 2005-2014 baseline) from NASA POWER daily, then returns the calibrated
probability that a flash drought *starts* within the next H days, with SHAP drivers.

The heavy scientific libraries are imported lazily so the rest of the site still
works if they are not installed.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.core.cache import TTLCache
from app.core.errors import DomainError

HORIZONS = (7, 14, 30)
POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_LAG_DAYS = 3  # POWER daily data trails real time by a few days

_lock = threading.Lock()  # the model library writes baselines on disk: one prediction at a time
_state: dict[str, Any] = {"lib": None, "client": None, "fd": None, "pc": None}
_cache: TTLCache[dict[str, Any]] = TTLCache(ttl=6 * 3600, max_entries=512)


def bundle_dir() -> Path:
    return Path(settings.fd_bundle_dir)


def _load() -> tuple[Any, Any, Any]:
    """Import the model code and open the exported bundle (once)."""
    if _state["lib"] is not None:
        return _state["fd"], _state["pc"], _state["lib"]
    try:
        from app.ml import flash_drought_model as fd
        from app.ml import power_client as pc
    except ImportError as exc:  # numpy / pandas / scikit-learn / lightgbm / shap missing
        raise DomainError(
            f"The flash-drought model needs extra packages ({exc.name}). "
            "Run: pip install -r backend/requirements.txt"
        ) from exc
    root = bundle_dir()
    if not (root / "registry.json").is_file():
        raise DomainError(f"Trained model bundle not found at {root}.")
    _state["fd"], _state["pc"] = fd, pc
    _state["lib"] = fd.Library(str(root))
    _state["client"] = pc.NasaPowerClient(fetch=_make_fetch(pc), pause=0.0, verbose=False)
    return fd, pc, _state["lib"]


def _make_fetch(pc: Any):
    """Daily NASA POWER download (sync, runs in a worker thread)."""
    import pandas as pd

    def fetch(lat: float, lon: float, start: Any, end: Any, parameters: list[str]):
        query = {
            "parameters": ",".join(parameters),
            "community": pc.COMMUNITY,
            "longitude": lon,
            "latitude": lat,
            "start": pd.Timestamp(start).strftime("%Y%m%d"),
            "end": pd.Timestamp(end).strftime("%Y%m%d"),
            "format": "JSON",
        }
        last: Exception | None = None
        for _ in range(3):
            try:
                with httpx.Client(timeout=settings.power_daily_timeout) as http:
                    response = http.get(POWER_DAILY_URL, params=query)
                if response.status_code in (400, 422):
                    raise DomainError("NASA POWER rejected the request (coordinates or dates).")
                response.raise_for_status()
                payload = response.json()
                pc.check_units(payload)
                table = pd.DataFrame(payload["properties"]["parameter"])
                table.index = pd.to_datetime(table.index, format="%Y%m%d")
                table.index.name = "date"
                return table.reset_index()
            except DomainError:
                raise
            except Exception as exc:  # noqa: BLE001 — retry transient network errors
                last = exc
        raise DomainError(f"NASA POWER daily data unavailable: {last}")

    return fetch


def _predict_sync(lat: float, lon: float, date: str, horizon: int) -> dict[str, Any]:
    fd, pc, lib = _load()
    client = _state["client"]
    with _lock:
        result = pc.predict_live(lib, client, lat, lon, date, H=horizon)
        # POWER lags real time: step back to the latest day that has complete values.
        for _ in range(2):
            if result.get("status") == "data_not_available_yet" and result.get("latest_date_with_data"):
                result = pc.predict_live(lib, client, lat, lon, result["latest_date_with_data"], H=horizon)
    return result


def _round_coord(value: float) -> float:
    return round(float(value), 2)


async def forecast_for(
    latitude: float, longitude: float, date: str | None, horizons: tuple[int, ...] = HORIZONS
) -> dict[str, Any]:
    """Risk of a flash-drought onset at a point for each requested horizon."""
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise DomainError("Latitude must be between -90 and 90 and longitude between -180 and 180.")
    day = date or (datetime.now(timezone.utc) - timedelta(days=POWER_LAG_DAYS)).strftime("%Y-%m-%d")
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError as exc:
        raise DomainError("The date must use the YYYY-MM-DD format.") from exc
    lat, lon = _round_coord(latitude), _round_coord(longitude)

    forecasts: dict[str, Any] = {}
    for horizon in horizons:
        key = f"{lat}|{lon}|{day}|{horizon}"
        cached = _cache.get(key)
        if cached is None:
            cached = await asyncio.to_thread(_predict_sync, lat, lon, day, horizon)
            if cached.get("status") == "ok":
                _cache.set(key, cached)
        forecasts[f"H{horizon}"] = cached
    ok = [item for item in forecasts.values() if item.get("status") == "ok"]
    return {
        "latitude": lat,
        "longitude": lon,
        "requestedDate": day,
        "forecasts": forecasts,
        "available": bool(ok),
        "note": "Statistical association learned from NASA POWER 2005-2024, not a weather forecast.",
    }


def model_info() -> dict[str, Any]:
    """Metadata and test scores of the trained models (no heavy imports needed)."""
    import json

    registry = json.loads((bundle_dir() / "registry.json").read_text(encoding="utf-8"))
    models = []
    for horizon_key, model_id in sorted(registry.get("active", {}).items(), key=lambda kv: int(kv[0][1:])):
        entry = registry["models"].get(model_id, {})
        test = entry.get("test", {})
        models.append(
            {
                "id": model_id,
                "horizonDays": entry.get("H"),
                "lookbackDays": entry.get("L"),
                "algorithm": entry.get("algorithm"),
                "validationPrAuc": entry.get("val_PR_AUC"),
                "test": {
                    "prAuc": test.get("PR_AUC"),
                    "rocAuc": test.get("ROC_AUC"),
                    "brier": test.get("Brier"),
                    "eventRate": test.get("event_rate"),
                    "climatologyPrAuc": (test.get("climatology") or {}).get("PR_AUC"),
                },
            }
        )
    return {"models": models, "trainingPeriod": "2005-2023", "testYear": 2024}
