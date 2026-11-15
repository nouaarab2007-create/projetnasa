"""GET /api/analysis and GET /api/scan — retrieve data from any catalogue source and run the trend analysis."""

from __future__ import annotations

import asyncio
import httpx
from fastapi import APIRouter, Depends, Request

from app.core.errors import error_message
from app.core.http import SafeJSONResponse, get_http_client
from app.schemas import parse_float_param, parse_year_param, validate_mode
from app.science.catalog import VARIABLES
from app.science.statistics import analyze
from app.science.transform import ensure_enough_points, transform
from app.services.datasets import fetch_series
from app.services.flash_drought import flash_drought_for
from app.services.hazards import hazards_for

router = APIRouter()


@router.get("/analysis")
async def get_analysis(
    request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SafeJSONResponse:
    try:
        search = request.query_params
        mode = validate_mode(search.get("mode"))
        parameter = search.get("parameter") or "T2M"
        result = await fetch_series(
            client,
            parameter=parameter,
            latitude=parse_float_param(search.get("latitude")),
            longitude=parse_float_param(search.get("longitude")),
            start=parse_year_param(search.get("start")),
            end=parse_year_param(search.get("end")),
            feature_id=search.get("featureId"),
        )
        points = ensure_enough_points(transform(result["points"], mode), mode)
        raw_alpha = search.get("alpha")
        alpha = float(raw_alpha) if raw_alpha in ("0.01", "0.05", "0.1", "0.10") else 0.05
        raw_horizon = search.get("horizon")
        horizon = int(raw_horizon) if raw_horizon in ("5", "10", "15", "20") else 5
        metadata = {
            **result["metadata"],
            "processing": f"{result['metadata']['processing']} Analysis mode: {mode}.",
        }
        return SafeJSONResponse(
            {
                "points": points,
                "metadata": metadata,
                "analysis": analyze(points, parameter, alpha=alpha, horizon_years=horizon),
                "mode": mode,
            }
        )
    except Exception as exc:  # noqa: BLE001 — return uniform 400 JSON payload
        message = error_message(exc, "Unable to analyse data.")
        return SafeJSONResponse({"error": message, "simulated": False}, status_code=400)


@router.get("/scan")
async def get_region_scan(
    request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SafeJSONResponse:
    try:
        search = request.query_params
        mode = validate_mode(search.get("mode"))
        latitude = parse_float_param(search.get("latitude"))
        longitude = parse_float_param(search.get("longitude"))
        start = parse_year_param(search.get("start"))
        end = parse_year_param(search.get("end"))
        raw_alpha = search.get("alpha")
        alpha = float(raw_alpha) if raw_alpha in ("0.01", "0.05", "0.1", "0.10") else 0.05
        raw_horizon = search.get("horizon")
        horizon = int(raw_horizon) if raw_horizon in ("5", "10", "15", "20") else 5

        # Every source that works from coordinates (SWOT needs a river/lake ID instead).
        # An optional ``sources`` list (e.g. "power,modis") limits the scan.
        wanted = {item.strip() for item in (search.get("sources") or "").split(",") if item.strip()}
        selectable = [
            v
            for v in VARIABLES
            if v["selectable"]
            and not v.get("featureInput")
            and (not wanted or v["provider"] in wanted)
        ]
        skipped: list[dict] = []

        async def _scan_one(var_def: dict) -> dict | None:
            code = var_def["code"]
            try:
                res = await fetch_series(
                    client,
                    parameter=code,
                    latitude=latitude,
                    longitude=longitude,
                    start=start,
                    end=end,
                )
                pts = ensure_enough_points(transform(res["points"], mode), mode)
                stats = analyze(pts, code, alpha=alpha, horizon_years=horizon)
                regression, mk = stats["regression"], stats["mannKendall"]
                is_sig = bool(regression["pValue"] < alpha or mk["significant"])
                # Same item shape as the browser-side scanner (frontend fetchScanDirect),
                # so the Explorer renders server and fallback results identically.
                return {
                    "code": code,
                    "name": var_def["name"],
                    "category": var_def["category"],
                    "unit": var_def["unit"],
                    "source": var_def["source"],
                    "provider": var_def["provider"],
                    "significant": is_sig,
                    "bothSignificant": bool(regression["pValue"] < alpha and mk["significant"]),
                    "verdict": stats["verdict"],
                    "trendPerDecade": stats["trendPerDecade"],
                    "senPerDecade": stats["senPerDecade"],
                    "pValue": regression["pValue"],
                    "mkPValue": mk["pValue"],
                    "rSquared": regression["rSquared"],
                    "firstValue": pts[0]["value"],
                    "lastValue": pts[-1]["value"],
                    "firstDate": pts[0]["date"],
                    "lastDate": pts[-1]["date"],
                    "risk": stats["risk"],
                    "points": pts,
                    "analysis": stats,
                    "metadata": res["metadata"],
                }
            except Exception as exc:  # noqa: BLE001 — one failing source must not stop the scan
                skipped.append(
                    {
                        "code": code,
                        "source": var_def["source"],
                        "reason": error_message(exc, "Retrieval failed."),
                    }
                )
                return None

        # Event-based risks (heat waves, extreme rainfall, droughts) come from /api/hazards.
        raw_items = await asyncio.gather(*(_scan_one(v) for v in selectable))
        items = [item for item in raw_items if item is not None]
        if not items:
            return SafeJSONResponse(
                {"error": "No dataset returned a valid series for this location.", "skipped": skipped, "simulated": False},
                status_code=400,
            )

        items.sort(
            key=lambda x: (
                not x["significant"],
                -x["analysis"]["risk"]["score"],
                x["analysis"]["regression"]["pValue"],
            )
        )
        significant_items = [x for x in items if x["significant"]]
        # Phenomena: the scanned items ranked by risk score (the page reads ``risk.score``);
        # the flat summary fields are kept for API clients.
        phenomena = sorted(
            [
                {
                    **x,
                    "variableName": x["name"],
                    "phenomenon": x["risk"]["phenomenon"],
                    "score": x["risk"]["score"],
                    "level": x["risk"]["level"],
                    "uncertainty": x["risk"]["uncertainty"],
                    "projectedChange": x["risk"]["projectedChange"],
                    "horizonYears": x["risk"]["horizonYears"],
                }
                for x in items
            ],
            key=lambda p: -p["score"],
        )

        return SafeJSONResponse(
            {
                "latitude": latitude,
                "longitude": longitude,
                "start": start,
                "end": end,
                "mode": mode,
                "alpha": alpha,
                "horizon": horizon,
                "totalScanned": len(items),
                "significantCount": len(significant_items),
                "items": items,
                "significantItems": significant_items,
                "phenomena": phenomena,
                "skipped": skipped,
                "simulated": False,
            }
        )
    except Exception as exc:  # noqa: BLE001
        message = error_message(exc, "Unable to scan region.")
        return SafeJSONResponse({"error": message, "simulated": False}, status_code=400)


@router.get("/flash-drought")
async def get_flash_drought(
    request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SafeJSONResponse:
    """Flash-drought onsets at a point (monthly root-zone soil moisture, NASA POWER)."""
    try:
        search = request.query_params
        result = await flash_drought_for(
            client,
            parse_float_param(search.get("latitude")),
            parse_float_param(search.get("longitude")),
            parse_year_param(search.get("start")),
            parse_year_param(search.get("end")),
        )
        return SafeJSONResponse(result)
    except Exception as exc:  # noqa: BLE001
        return SafeJSONResponse({"error": error_message(exc, "Flash-drought detection failed.")}, status_code=400)


@router.get("/hazards")
async def get_hazards(
    request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SafeJSONResponse:
    """Heat wave, extreme rainfall, severe drought and flash drought at a point.

    Each hazard lists one result per dataset (``sources=power,giovanni,noaa`` limits them).
    """
    try:
        search = request.query_params
        latitude = parse_float_param(search.get("latitude"))
        longitude = parse_float_param(search.get("longitude"))
        start = parse_year_param(search.get("start"))
        end = parse_year_param(search.get("end"))
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return SafeJSONResponse({"error": "Latitude must be between -90 and 90 and longitude between -180 and 180."}, status_code=400)
        if start > end:
            return SafeJSONResponse({"error": "The start year must not be after the end year."}, status_code=400)
        wanted = {item.strip() for item in (search.get("sources") or "").split(",") if item.strip()}
        hazards = await hazards_for(client, latitude, longitude, int(start), int(end), wanted or None)
        return SafeJSONResponse(
            {"latitude": latitude, "longitude": longitude, "start": start, "end": end, "hazards": hazards}
        )
    except Exception as exc:  # noqa: BLE001
        return SafeJSONResponse({"error": error_message(exc, "Risk detection failed.")}, status_code=400)
