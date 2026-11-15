"""Tests for the trained flash-drought model endpoints (the model itself is mocked)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import flash_forecast


def _ok(horizon: int) -> dict:
    return {
        "status": "ok",
        "date": "2026-07-15",
        "risk_percentage": 12.3,
        "risk_level": "HIGH",
        "horizon_days": horizon,
        "usual_percentage": 4.0,
        "risk_ratio_vs_usual": 3.1,
        "top_drivers": [],
        "relief_factors": [],
        "state": "AT_RISK_SET",
    }


@pytest.fixture(autouse=True)
def _clear() -> None:
    flash_forecast._cache.clear()


def test_forecast_returns_all_horizons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(flash_forecast, "_predict_sync", lambda lat, lon, date, h: _ok(h))
    with TestClient(create_app()) as client:
        response = client.get("/api/flash-forecast", params={"latitude": 42, "longitude": -93.5})
    body = response.json()
    assert response.status_code == 200
    assert body["available"] is True
    assert set(body["forecasts"]) == {"H7", "H14", "H30"}
    assert body["forecasts"]["H14"]["risk_percentage"] == 12.3


def test_forecast_single_horizon_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(flash_forecast, "_predict_sync", lambda lat, lon, date, h: _ok(h))
    with TestClient(create_app()) as client:
        one = client.get("/api/flash-forecast", params={"latitude": 1, "longitude": 2, "horizon": 7})
        assert list(one.json()["forecasts"]) == ["H7"]
        assert client.get("/api/flash-forecast", params={"latitude": 1, "longitude": 2, "horizon": 9}).status_code == 400
        assert client.get("/api/flash-forecast", params={"latitude": 95, "longitude": 2}).status_code == 400
        assert client.get("/api/flash-forecast", params={"latitude": 1, "longitude": 2, "date": "bad"}).status_code == 400


def test_model_info_reads_registry() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/flash-forecast/model")
    body = response.json()
    assert response.status_code == 200
    assert [m["horizonDays"] for m in body["models"]] == [7, 14, 30]
    assert all(m["test"]["prAuc"] for m in body["models"])
