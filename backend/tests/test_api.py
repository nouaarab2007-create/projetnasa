"""Integration tests for all REST API endpoints using mocked upstream HTTP."""

from __future__ import annotations

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app
from app.services.nasa_power import clear_power_cache
from app.services.tiles import clear_tile_cache


def _sample_power_payload(parameter: str = "T2M", base: float = -5.0, step: float = 0.2) -> dict:
    series: dict[str, float] = {}
    for year_offset in range(6):
        year = 2018 + year_offset
        for month in range(1, 13):
            series[f"{year}{month:02d}"] = round(base + year_offset * step + month * 0.05, 3)
        series[f"{year}13"] = -999
    return {"properties": {"parameter": {parameter: series}}}


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    clear_power_cache()
    clear_tile_cache()


def test_health_and_catalog_endpoints() -> None:
    with TestClient(create_app()) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.json()["service"] == "Trend Detective"

        assert set(health.json()["credentials"]) == {"EARTHDATA_TOKEN", "NOAA_CDO_TOKEN"}

        variables = client.get("/api/variables").json()["variables"]
        assert len(variables) == 26
        assert all(item["selectable"] for item in variables)
        assert {item["provider"] for item in variables} == {"power", "modis", "giovanni", "noaa", "swot"}

        regions = client.get("/api/regions").json()
        assert len(regions["regions"]) == 10
        assert "grid cell" in regions["note"]

        sources = client.get("/api/sources").json()["sources"]
        assert len(sources) == 8
        assert sources[0]["status"] == "FULLY INTEGRATED"
        assert sum(1 for item in sources if item["status"] == "FULLY INTEGRATED") == 6


@respx.mock
def test_analysis_and_data_endpoints() -> None:
    respx.get(settings.power_url).mock(
        return_value=httpx.Response(200, json=_sample_power_payload("T2M"))
    )
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/analysis",
            params={
                "parameter": "T2M",
                "latitude": "78.2",
                "longitude": "15.6",
                "start": "2018",
                "end": "2023",
                "mode": "annual",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["mode"] == "annual"
        assert len(payload["points"]) == 6
        assert payload["metadata"]["simulated"] is False
        assert "Analysis mode: annual." in payload["metadata"]["processing"]
        assert "regression" in payload["analysis"]
        assert "mannKendall" in payload["analysis"]
        assert "risk" in payload["analysis"]

        bad = client.get("/api/data", params={"mode": "invalid"})
        assert bad.status_code == 400
        assert bad.json()["simulated"] is False


@respx.mock
def test_comparison_endpoint() -> None:
    respx.get(settings.power_url).mock(
        side_effect=[
            httpx.Response(200, json=_sample_power_payload("T2M", base=-6.0, step=0.4)),
            httpx.Response(200, json=_sample_power_payload("T2M", base=25.0, step=0.1)),
        ]
    )
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/comparison",
            json={
                "parameter": "T2M",
                "start": 2018,
                "end": 2023,
                "mode": "annual",
                "regionA": {"latitude": 78.2, "longitude": 15.6},
                "regionB": {"latitude": -3.1, "longitude": -60},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert "regionA" in payload and "regionB" in payload
        assert payload["differencePerDecade"] > 0
        assert "caus" in payload["interpretation"]


@respx.mock
def test_geocode_and_tile_endpoints() -> None:
    respx.get(settings.geocode_url).mock(
        return_value=httpx.Response(
            200,
            json=[{"lat": "31.6295", "lon": "-7.9811", "display_name": "Marrakech, Maroc", "extra": 1}],
        )
    )
    respx.get("https://tile.openstreetmap.org/2/1/1.png").mock(
        return_value=httpx.Response(200, content=b"\x89PNG\r\n\x1a\n", headers={"Content-Type": "image/png"})
    )
    with TestClient(create_app()) as client:
        missing = client.get("/api/geocode")
        assert missing.status_code == 400

        geo = client.get("/api/geocode", params={"q": "Marrakech"})
        assert geo.status_code == 200
        assert geo.json() == {
            "results": [{"lat": "31.6295", "lon": "-7.9811", "display_name": "Marrakech, Maroc"}]
        }

        bad_tile = client.get("/api/tiles/a/1/1")
        assert bad_tile.status_code == 400

        tile = client.get("/api/tiles/2/1/1")
        assert tile.status_code == 200
        assert tile.headers["content-type"] == "image/png"
        assert tile.content.startswith(b"\x89PNG")


def test_multipage_html_routes() -> None:
    with TestClient(create_app()) as client:
        for route in (
            "/",
            "/explorer",
            "/analysis",
            "/variables",
            "/sources",
            "/about",
        ):
            res = client.get(route)
            assert res.status_code == 200, f"Route {route} failed"
            assert "text/html" in res.headers["content-type"]
            assert "Trend Detective" in res.text

        not_found = client.get("/unknown-route")
        assert not_found.status_code == 404
        assert "Page Not Found" in not_found.text
