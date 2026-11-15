"""Tests for the MODIS, Giovanni (GLDAS / GPM), NOAA and SWOT connectors.

Upstream services are mocked with responses that follow each service's
documented format, so the suite runs offline.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app
from app.science.statistics import analyze
from app.science.transform import transform
from app.services.datasets import clear_dataset_cache
from app.services.giovanni import clear_giovanni_cache, parse_timeseries_csv
from app.services.nasa_power import clear_power_cache

NDVI_TREND = 0.004  # per year, built into the fake MODIS service


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_dataset_cache()
    clear_giovanni_cache()
    clear_power_cache()
    for name in ("EARTHDATA_TOKEN", "TD_EARTHDATA_TOKEN", "NOAA_CDO_TOKEN", "TD_NOAA_CDO_TOKEN"):
        monkeypatch.delenv(name, raising=False)


def _query(request: httpx.Request) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlparse(str(request.url)).query).items()}


def _analysis(client: TestClient, **params: str) -> httpx.Response:
    base = {"latitude": "31.63", "longitude": "-8", "start": "2015", "end": "2019", "mode": "annual"}
    return client.get("/api/analysis", params={**base, **params})


# --- MODIS (ORNL DAAC) ---------------------------------------------------------


def _composites(first: date, last: date, step: int = 16):
    day = first
    while day <= last:
        yield day
        nxt = day + timedelta(days=step)
        day = date(nxt.year, 1, 1) if nxt.year != day.year else nxt


def _modis_code(day: date) -> str:
    return f"A{day.year}{day.timetuple().tm_yday:03d}"


def _modis_dates(request: httpx.Request) -> httpx.Response:
    dates = [{"modis_date": _modis_code(d), "calendar_date": d.isoformat()}
             for d in _composites(date(2008, 1, 1), date(2020, 12, 31))]
    return httpx.Response(200, json={"dates": dates})


def _modis_subset(request: httpx.Request) -> httpx.Response:
    query = _query(request)
    first = date(int(query["startDate"][1:5]), 1, 1) + timedelta(days=int(query["startDate"][5:]) - 1)
    last = date(int(query["endDate"][1:5]), 1, 1) + timedelta(days=int(query["endDate"][5:]) - 1)
    assert (last - first).days <= 16 * 10, "at most 10 composites per request"
    records = []
    for day in _composites(first, last):
        t = day.year - 2000 + day.timetuple().tm_yday / 365.0
        ndvi = 0.5 + NDVI_TREND * t + 0.2 * math.sin(2 * math.pi * t)
        # -3000 is the MODIS fill value; the same calendar composite is missing every year.
        raw = -3000 if day.timetuple().tm_yday == 17 else int(round(ndvi / 0.0001))
        records.append({"band": query["band"], "modis_date": _modis_code(day), "data": [raw]})
    return httpx.Response(200, json={"subset": records})


@respx.mock
def test_modis_ndvi_is_scaled_aggregated_and_trend_is_per_year() -> None:
    respx.get(url__startswith=f"{settings.modis_url}/MOD13Q1/dates").mock(side_effect=_modis_dates)
    subset = respx.get(url__startswith=f"{settings.modis_url}/MOD13Q1/subset").mock(side_effect=_modis_subset)
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="MOD13Q1_NDVI", start="2010")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert [point["date"] for point in payload["points"]] == [str(year) for year in range(2010, 2020)]
    assert all(0.3 < point["value"] < 0.7 for point in payload["points"])
    assert payload["analysis"]["trendPerDecade"] == pytest.approx(NDVI_TREND * 10, abs=0.005)
    metadata = payload["metadata"]
    assert metadata["provider"] == "NASA MODIS (ORNL DAAC)"
    assert "moved to 2000" not in metadata["processing"]  # 2010 is after the first year
    assert metadata["simulated"] is False
    assert subset.called
    assert all(_query(call.request)["band"] == "250m_16_days_NDVI" for call in subset.calls)


@respx.mock
def test_modis_start_year_is_moved_to_first_available_year() -> None:
    respx.get(url__startswith=f"{settings.modis_url}/MOD13Q1/dates").mock(side_effect=_modis_dates)
    respx.get(url__startswith=f"{settings.modis_url}/MOD13Q1/subset").mock(side_effect=_modis_subset)
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="MOD13Q1_NDVI", start="1990", end="2016")
    assert response.status_code == 200, response.text
    assert "moved to 2000" in response.json()["metadata"]["processing"]


@respx.mock
def test_modis_upstream_failure_is_reported() -> None:
    respx.get(url__startswith=f"{settings.modis_url}/MOD13Q1/dates").mock(return_value=httpx.Response(503))
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="MOD13Q1_NDVI")
    assert response.status_code == 400
    assert "503" in response.json()["error"]


# --- Giovanni (GLDAS, GPM IMERG) -------------------------------------------------


def _giovanni_csv(data_id: str, unit: str, value_of, start: int, end: int, monthly: bool = True) -> str:
    header = [
        f"prod_name,{data_id}", f"param_short_name,{data_id.rsplit('_', 2)[-1]}", f"param_name,{data_id}",
        f"unit,{unit}", "begin_time,x", "end_time,x", "time_resolution,x", "lat,31.625", "lon,-8.125",
        "request_lat,31.63", "request_lon,-8.0", "begin_date,x", "end_date,x",
    ]
    rows = ["Timestamp (UTC),Data"]
    for year in range(start, end + 1):
        for month in range(1, 13):
            if monthly:
                rows.append(f"{year}-{month:02d}-01T00:00:00,{value_of(year, month)}")
            else:
                for hour in (0, 12):
                    rows.append(f"{year}-{month:02d}-15T{hour:02d}:00:00,{value_of(year, month)}")
    rows.insert(5, f"{start}-03-01T00:00:00,-9999.0")  # fill value is ignored
    return "\n".join(header + rows)


def test_gldas_without_token_explains_how_to_get_one() -> None:
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="GLDAS_SOILM_0_10")
    assert response.status_code == 400
    assert "EARTHDATA_TOKEN" in response.json()["error"]


@respx.mock
def test_gldas_soil_moisture_uses_monthly_product_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EARTHDATA_TOKEN", "test-token")
    data_id = "GLDAS_NOAH025_M_2_1_SoilMoi0_10cm_inst"
    respx.get(f"{settings.giovanni_url}/configured-variables").mock(
        return_value=httpx.Response(200, json={"variables": [data_id, "GLDAS_NOAH025_3H_2_1_Tair_f_inst"]})
    )

    def timeseries(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        query = _query(request)
        assert query["data"] == data_id
        assert query["location"] == "[31.63,-8.0]"
        first, last = (int(part[:4]) for part in query["time"].split("/"))
        return httpx.Response(200, text=_giovanni_csv(data_id, "kg m-2", lambda y, m: 30 - (y - 2015), first, last))

    respx.get(f"{settings.giovanni_url}/timeseries").mock(side_effect=timeseries)
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="GLDAS_SOILM_0_10")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["metadata"]["product"] == data_id
    assert [round(p["value"], 3) for p in payload["points"]] == [30, 29, 28, 27, 26]
    assert payload["analysis"]["trendPerDecade"] == pytest.approx(-10)
    assert payload["analysis"]["risk"]["phenomenon"] == "Surface soil drying"


@respx.mock
def test_evapotranspiration_flux_is_converted_to_mm_per_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EARTHDATA_TOKEN", "test-token")
    respx.get(f"{settings.giovanni_url}/configured-variables").mock(return_value=httpx.Response(500))
    seen: list[str] = []

    def timeseries(request: httpx.Request) -> httpx.Response:
        query = _query(request)
        seen.append(query["data"])
        first, last = (int(part[:4]) for part in query["time"].split("/"))
        csv = _giovanni_csv(query["data"], "kg m-2 s-1", lambda y, m: 2e-5, first, last, monthly=False)
        return httpx.Response(200, text=csv)

    respx.get(f"{settings.giovanni_url}/timeseries").mock(side_effect=timeseries)
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="GLDAS_EVAP", mode="raw")
    assert response.status_code == 200, response.text
    assert set(seen) == {"GLDAS_NOAH025_3H_2_1_Evap_tavg"}  # list unavailable -> 3-hourly fallback
    assert len(seen) == 3  # 3-hourly data is requested in 2-year windows (2015-16, 2017-18, 2019)
    assert response.json()["points"][0]["value"] == pytest.approx(2e-5 * 86400)
    assert "mm/day" in response.json()["metadata"]["processing"]


def test_giovanni_csv_parser_reads_headers_and_skips_fill_values() -> None:
    csv = _giovanni_csv("X_Y_Z", "kg m-2", lambda y, m: 5.0, 2001, 2001)
    headers, samples = parse_timeseries_csv(csv)
    assert headers["unit"] == "kg m-2"
    assert headers["lat"] == "31.625"
    assert len(samples) == 12 and all(value == 5.0 for _, value in samples)


# --- NOAA NCEI --------------------------------------------------------------------


def _noaa_rows(station: str, name: str, lat: float, lon: float, months: int, start: int = 2015) -> list[dict]:
    rows = []
    for index in range(months):
        year, month = start + index // 12, index % 12 + 1
        rows.append({
            "STATION": station, "DATE": f"{year}-{month:02d}", "TAVG": f" {10 + 0.03 * index:.2f}",
            "NAME": name, "LATITUDE": str(lat), "LONGITUDE": str(lon),
        })
    return rows


@respx.mock
def test_noaa_picks_nearest_station_with_a_near_complete_record() -> None:
    rows = (
        _noaa_rows("FAR00000001", "FAR AIRPORT", 31.9, -8.4, 60)  # complete, ~50 km away
        + _noaa_rows("NEAR0000001", "MARRAKECH", 31.62, -8.03, 54)  # 90 % complete, ~3 km away
        + _noaa_rows("TINY0000001", "TINY", 31.63, -8.0, 10)  # too short a record
    )

    def access(request: httpx.Request) -> httpx.Response:
        query = _query(request)
        assert query["dataset"] == "global-summary-of-the-month"
        assert query["dataTypes"] == "TAVG" and query["units"] == "metric"
        return httpx.Response(200, json=rows)

    respx.get(url__startswith=settings.noaa_access_url).mock(side_effect=access)
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="NOAA_TAVG", mode="raw")
    assert response.status_code == 200, response.text
    metadata = response.json()["metadata"]
    assert metadata["station"].startswith("NEAR0000001")
    assert metadata["stationDistance"].endswith("km from the selected point")
    assert metadata["latitude"] == 31.63  # the point the user chose


@respx.mock
def test_noaa_widens_search_then_reports_no_station() -> None:
    route = respx.get(url__startswith=settings.noaa_access_url).mock(return_value=httpx.Response(200, json=[]))
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="NOAA_PRCP")
    assert response.status_code == 400
    assert "No NOAA station" in response.json()["error"]
    assert route.call_count == 3


@respx.mock
def test_noaa_falls_back_to_cdo_when_token_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOAA_CDO_TOKEN", "cdo-token")
    respx.get(url__startswith=settings.noaa_access_url).mock(return_value=httpx.Response(500))

    def stations(request: httpx.Request) -> httpx.Response:
        assert request.headers["token"] == "cdo-token"
        return httpx.Response(200, json={"results": [
            {"id": "GHCND:MO000060230", "name": "MARRAKECH, MO", "latitude": 31.6, "longitude": -8.03,
             "datacoverage": 0.95},
        ]})

    def data(request: httpx.Request) -> httpx.Response:
        query = _query(request)
        assert int(query["enddate"][:4]) - int(query["startdate"][:4]) <= 9, "10-year limit"
        first = int(query["startdate"][:4])
        last = int(query["enddate"][:4])
        results = [
            {"date": f"{y}-{m:02d}-01T00:00:00", "datatype": "TAVG", "station": query["stationid"], "value": 20.0 + y - 2015}
            for y in range(first, last + 1) for m in range(1, 13)
        ]
        return httpx.Response(200, json={"results": results})

    respx.get(f"{settings.noaa_cdo_url}/stations").mock(side_effect=stations)
    respx.get(f"{settings.noaa_cdo_url}/data").mock(side_effect=data)
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="NOAA_TAVG")
    assert response.status_code == 200, response.text
    assert "Climate Data Online v2" in response.json()["metadata"]["processing"]
    assert response.json()["analysis"]["trendPerDecade"] == pytest.approx(10)


# --- SWOT Hydrocron -------------------------------------------------------------


def test_swot_requires_a_valid_feature_id() -> None:
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="SWOT_WSE", start="2023", end="2025")
    assert response.status_code == 400
    assert "reach ID" in response.json()["error"]


@respx.mock
def test_swot_reach_series_drops_fill_and_bad_quality_passes() -> None:
    lines = ["reach_id,time_str,wse,reach_q,wse_units,reach_q_units"]
    for month in range(1, 13):
        lines.append(f"78340600051,2024-{month:02d}-03T10:00:00Z,{386 + month * 0.1:.2f},0,m,na")
        lines.append(f"78340600051,2024-{month:02d}-20T10:00:00Z,{386 + month * 0.1:.2f},1,m,na")
    lines.append("78340600051,no_data,-999999999999.0,0,m,na")
    lines.append("78340600051,2024-06-10T10:00:00Z,500.0,3,m,na")  # bad quality

    def hydrocron(request: httpx.Request) -> httpx.Response:
        query = _query(request)
        assert query["feature"] == "Reach" and query["feature_id"] == "78340600051"
        assert query["output"] == "csv"
        return httpx.Response(200, json={"status": "200 OK", "hits": len(lines) - 1,
                                         "results": {"csv": "\n".join(lines), "geojson": {}}})

    respx.get(url__startswith=settings.hydrocron_url).mock(side_effect=hydrocron)
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="SWOT_WSE", start="2023", end="2024", mode="raw",
                             featureId="78340600051")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["points"]) == 12
    assert payload["points"][5]["value"] == pytest.approx(386.6)  # bad pass of June excluded
    assert "2 removed" in payload["metadata"]["processing"]
    assert payload["metadata"]["featureId"] == "78340600051"


# --- Statistics on gappy series --------------------------------------------------


def test_trend_uses_real_time_when_months_are_missing() -> None:
    points = []
    for index in range(120):
        if index % 12 in (5, 6, 7) and index > 60:  # summers missing in the second half
            continue
        year, month = 2010 + index // 12, index % 12 + 1
        points.append({"date": f"{year}-{month:02d}", "value": 0.5 * (year + (month - 1) / 12 - 2010)})
    result = analyze(points)
    assert result["slopePerYear"] == pytest.approx(0.5)
    assert result["trendPerDecade"] == pytest.approx(5.0)
    assert result["senPerDecade"] == pytest.approx(5.0)


def test_gap_free_monthly_trend_is_unchanged_by_the_time_axis() -> None:
    points = [{"date": f"{2000 + i // 12}-{i % 12 + 1:02d}", "value": 0.01 * i} for i in range(48)]
    assert analyze(points)["trendPerDecade"] == pytest.approx(0.01 * 120)


def test_annual_mode_drops_years_missing_many_months() -> None:
    points = [{"date": f"2020-{m:02d}", "value": 10.0} for m in range(1, 13)]
    points += [{"date": f"2021-{m:02d}", "value": 20.0} for m in range(1, 13)]
    points += [{"date": f"2022-{m:02d}", "value": 99.0} for m in range(1, 4)]  # unfinished year
    assert [p["date"] for p in transform(points, "annual")] == ["2020", "2021"]


@respx.mock
def test_short_record_in_annual_mode_suggests_monthly_modes() -> None:
    lines = ["reach_id,time_str,wse,reach_q"]
    lines += [f"78340600051,{y}-{m:02d}-05T10:00:00Z,386.0,0" for y in (2024, 2025) for m in range(1, 13)]
    respx.get(url__startswith=settings.hydrocron_url).mock(
        return_value=httpx.Response(200, json={"status": "200 OK", "results": {"csv": "\n".join(lines)}})
    )
    with TestClient(create_app()) as client:
        response = _analysis(client, parameter="SWOT_WSE", start="2023", end="2025", featureId="78340600051")
    assert response.status_code == 400
    assert "Raw monthly values" in response.json()["error"]


@respx.mock
def test_region_scan_covers_all_coordinate_sources_and_reports_skipped_ones() -> None:
    from test_api import _sample_power_payload

    def power(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_sample_power_payload(_query(request)["parameters"]))

    respx.get(url__startswith=settings.power_url).mock(side_effect=power)
    respx.get(url__regex=rf"{settings.modis_url}/\w+/dates").mock(side_effect=_modis_dates)

    def subset(request: httpx.Request) -> httpx.Response:
        band = _query(request)["band"]
        response = _modis_subset(request)
        if band in ("Lai_500m", "LST_Day_1km"):  # keep raw values inside each product's valid range
            payload = response.json()
            for record in payload["subset"]:
                record["data"] = [30 if band == "Lai_500m" else 15000]
            return httpx.Response(200, json=payload)
        return response

    respx.get(url__regex=rf"{settings.modis_url}/\w+/subset").mock(side_effect=subset)
    noaa_rows = _noaa_rows("NEAR0000001", "MARRAKECH", 31.62, -8.03, 72, start=2018)
    for row in noaa_rows:
        for key in ("TMAX", "TMIN", "PRCP"):
            row[key] = row["TAVG"]
    respx.get(url__startswith=settings.noaa_access_url).mock(return_value=httpx.Response(200, json=noaa_rows))

    with TestClient(create_app()) as client:
        response = client.get("/api/scan", params={
            "latitude": "31.63", "longitude": "-8", "start": "2018", "end": "2020", "mode": "annual",
        })
    assert response.status_code == 200, response.text
    payload = response.json()
    scanned = {item["code"] for item in payload["items"]}
    assert {"T2M", "MOD13Q1_NDVI", "MOD15A2H_LAI", "NOAA_TAVG", "NOAA_PRCP"} <= scanned
    assert "SWOT_WSE" not in scanned  # needs a river/lake ID, not coordinates
    skipped = {item["code"]: item["reason"] for item in payload["skipped"]}
    assert set(skipped) == {"GLDAS_SOILM_0_10", "GLDAS_ROOT_ZONE_SM", "GLDAS_EVAP", "GLDAS_SWE", "GPM_IMERG_PRECIP"}
    assert all("EARTHDATA_TOKEN" in reason for reason in skipped.values())
    assert payload["totalScanned"] == 20
    assert all("source" in item for item in payload["phenomena"])


@respx.mock
def test_region_scan_can_be_limited_to_some_sources() -> None:
    from test_api import _sample_power_payload

    respx.get(url__startswith=settings.power_url).mock(
        side_effect=lambda request: httpx.Response(200, json=_sample_power_payload(_query(request)["parameters"]))
    )
    with TestClient(create_app()) as client:
        response = client.get("/api/scan", params={
            "latitude": "31.63", "longitude": "-8", "start": "2018", "end": "2023", "sources": "power",
        })
    assert response.status_code == 200, response.text
    assert response.json()["totalScanned"] == 12
    assert response.json()["skipped"] == []


@respx.mock
def test_scan_items_have_the_fields_the_explorer_page_reads() -> None:
    from test_api import _sample_power_payload

    respx.get(url__startswith=settings.power_url).mock(
        side_effect=lambda request: httpx.Response(200, json=_sample_power_payload(_query(request)["parameters"]))
    )
    with TestClient(create_app()) as client:
        payload = client.get("/api/scan", params={
            "latitude": "31.63", "longitude": "-8", "start": "2018", "end": "2023", "sources": "power",
        }).json()
    for item in payload["items"]:
        for key in ("pValue", "trendPerDecade", "senPerDecade", "firstValue", "lastValue", "risk",
                    "points", "analysis", "metadata", "source"):
            assert key in item, key
        assert "score" in item["risk"]
    assert all("score" in p["risk"] for p in payload["phenomena"])
