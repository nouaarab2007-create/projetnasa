"""SWOT water-surface elevation from PO.DAAC Hydrocron (no account needed).

GET https://soto.podaac.earthdatacloud.nasa.gov/hydrocron/v1/timeseries
    ?feature=Reach|Node|PriorLake&feature_id=<id>&start_time=...Z&end_time=...Z
    &fields=reach_id,time_str,wse,reach_q&output=csv
Response JSON: {"status": "200 OK", "hits": n, "results": {"csv": "...", "geojson": {}}}

SWOT observes a feature, not a coordinate, so the request needs an ID:
  - river reach  : 11 digits (CBBBBBRRRRT), e.g. 78340600051
  - river node   : 14 digits (CBBBBBRRRRNNNT)
  - prior lake   : 10 digits (CBBNNNNNNT), e.g. 6350036102
IDs can be looked up on the SWORD / PLD explorers (https://www.swordexplorer.com).
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

import httpx

from app.config import settings
from app.core.errors import DomainError, UpstreamError
from app.services.series import Sample, get_checked, monthly_means, require_points, to_float

SOURCE = "NASA SWOT (Hydrocron)"

FEATURES: dict[int, dict[str, str]] = {
    11: {"feature": "Reach", "id_field": "reach_id", "quality": "reach_q",
         "collection": "SWOT_L2_HR_RiverSP_reach_D", "label": "river reach"},
    14: {"feature": "Node", "id_field": "node_id", "quality": "node_q",
         "collection": "SWOT_L2_HR_RiverSP_node_D", "label": "river node"},
    10: {"feature": "PriorLake", "id_field": "lake_id", "quality": "quality_f",
         "collection": "SWOT_L2_HR_LakeSP_prior_D", "label": "lake"},
}
BAD_QUALITY = 3  # Hydrocron quality flags: 0 nominal, 1 suspect, 2 degraded, 3 bad


def feature_spec(feature_id: str | None) -> dict[str, str]:
    text = (feature_id or "").strip()
    if not re.fullmatch(r"\d+", text) or len(text) not in FEATURES:
        raise DomainError(
            "SWOT needs a river reach ID (11 digits), river node ID (14 digits) or lake ID "
            "(10 digits). Look one up at https://www.swordexplorer.com and paste it in the "
            "'SWOT reach or lake ID' field."
        )
    return FEATURES[len(text)]


def parse_hydrocron(payload: Any, quality_field: str) -> tuple[list[Sample], int, int]:
    """Return (samples, passes, rejected) from a Hydrocron output=csv response."""
    csv_text = ""
    if isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, dict):
            csv_text = str(results.get("csv") or "")
    samples: list[Sample] = []
    passes = rejected = 0
    for row in csv.DictReader(io.StringIO(csv_text)):
        passes += 1
        when = (row.get("time_str") or "").strip()
        value = to_float(row.get("wse"))
        flag = to_float(row.get(quality_field))
        if not re.match(r"^\d{4}-\d{2}-\d{2}", when) or value is None or value < -1e10:
            rejected += 1
            continue
        if flag is not None and int(flag) >= BAD_QUALITY:
            rejected += 1
            continue
        samples.append((when[:10], value))
    return samples, passes, rejected


async def fetch_swot(
    client: httpx.AsyncClient,
    feature_id: str | None,
    start: int,
    end: int,
) -> dict[str, Any]:
    spec = feature_spec(feature_id)
    feature_id = (feature_id or "").strip()
    params = {
        "feature": spec["feature"],
        "feature_id": feature_id,
        "start_time": f"{start}-01-01T00:00:00Z",
        "end_time": f"{end}-12-31T23:59:59Z",
        "fields": f"{spec['id_field']},time_str,wse,{spec['quality']}",
        "output": "csv",
        "collection_name": spec["collection"],
    }
    try:
        response = await get_checked(
            client, settings.hydrocron_url, source=SOURCE, params=params, timeout=settings.hydrocron_timeout
        )
    except UpstreamError as exc:
        if "not found" in exc.message.lower() or "status 400" in exc.message or "status 404" in exc.message:
            # Retry with the service's default collection before giving up.
            params.pop("collection_name")
            try:
                response = await get_checked(
                    client, settings.hydrocron_url, source=SOURCE, params=params, timeout=settings.hydrocron_timeout
                )
            except UpstreamError:
                raise DomainError(
                    f"SWOT has no observations for {spec['label']} {feature_id} between {start} and {end}. "
                    "Check the ID (SWOT science data start in mid-2023)."
                ) from exc
        else:
            raise
    try:
        payload = response.json()
    except ValueError as exc:
        raise UpstreamError("Hydrocron returned an unreadable response.") from exc
    samples, passes, rejected = parse_hydrocron(payload, spec["quality"])
    points, used = monthly_means(samples)
    require_points(points, SOURCE)
    return {
        "points": points,
        "product": f"{params.get('collection_name', 'Hydrocron default collection')} · {spec['feature']} {feature_id}",
        "spatialResolution": f"SWOT {spec['label']} (feature average)",
        "processing": (
            f"{passes} satellite passes returned; {rejected} removed (no data, fill value or quality flag = bad); "
            f"monthly mean of {used} valid passes."
        ),
        "quality": (
            "Satellite radar altimetry; a few passes per month. The record starts in 2023, so trends "
            "describe short-term change, not long-term climate."
        ),
        "documentation": "https://podaac.github.io/hydrocron/",
        "extra": {"featureId": feature_id, "featureType": spec["label"]},
    }
