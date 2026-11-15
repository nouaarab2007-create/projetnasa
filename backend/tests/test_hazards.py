"""Heat waves, extreme rainfall and severe drought: detectors and the /api/hazards endpoint."""

from __future__ import annotations

import math
import random
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app
from app.science.extremes import (
    detect_extreme_rain,
    detect_heat_waves,
    detect_rain_drought,
    percentile,
    rank_percentile,
    warm_season,
)
from app.services.daily import clear_daily_cache, parse_power_daily
from app.services.datasets import clear_dataset_cache
from app.services.giovanni import clear_giovanni_cache
from app.services.nasa_power import clear_power_cache


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_daily_cache()
    clear_dataset_cache()
    clear_giovanni_cache()
    clear_power_cache()
    for name in ("EARTHDATA_TOKEN", "TD_EARTHDATA_TOKEN", "NOAA_CDO_TOKEN", "TD_NOAA_CDO_TOKEN"):
        monkeypatch.delenv(name, raising=False)


def _days(first: int, last: int):
    day = date(first, 1, 1)
    while day <= date(last, 12, 31):
        yield day
        day += timedelta(days=1)


def tmax_record(heat: dict[int, tuple[int, int]], first=1981, last=2024, south=False, seed=1):
    """Seasonal daily maxima with persistent noise; ``heat`` maps year -> (day-of-year, length)."""
    rng, anomaly, rows = random.Random(seed), 0.0, []
    for day in _days(first, last):
        anomaly = 0.7 * anomaly + rng.gauss(0, 1.2)
        doy = day.timetuple().tm_yday
        season = math.cos(2 * math.pi * (doy - 200) / 365.25)
        value = 22 + (-1 if south else 1) * 10 * season + anomaly
        if day.year in heat:
            start, length = heat[day.year]
            if start <= doy < start + length:
                value += 12
        rows.append((day.isoformat(), round(value, 2)))
    return rows


def rain_record(storms: dict[int, float], dry: dict[int, tuple[int, int]], first=1981, last=2024, seed=3):
    """Daily rain: wet days ~ exponential (max ~35-45 mm/yr). ``storms`` adds one big day;
    ``dry`` maps year -> (first month, last month) with no rain at all."""
    rng, rows = random.Random(seed), []
    for day in _days(first, last):
        value = rng.expovariate(1 / 8) if rng.random() < 0.3 else 0.0
        if day.year in dry and dry[day.year][0] <= day.month <= dry[day.year][1]:
            value = 0.0
        if day.year in storms and day.month == 7 and day.day == 10:
            value = storms[day.year]
        rows.append((day.isoformat(), round(value, 2)))
    return rows


# --- helpers -------------------------------------------------------------------


def test_percentile_and_rank_helpers() -> None:
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile([0, 10], 95) == pytest.approx(9.5)
    assert rank_percentile(list(range(1, 30)), 0) < 6.7  # lower than all 29 values
    assert rank_percentile(list(range(1, 30)), 15) == pytest.approx(50)


def test_warm_season_by_hemisphere() -> None:
    assert warm_season(40) == ([5, 6, 7, 8, 9], 0)
    assert warm_season(-35) == ([11, 12, 1, 2, 3], 11)


def test_warm_season_comes_from_the_data() -> None:
    from datetime import date as d

    def series(peak_doy: int, amp: float) -> dict:
        out, day = {}, d(2000, 1, 1)
        while day.year < 2003:
            doy = day.timetuple().tm_yday
            out[day] = 30 + amp * math.cos(2 * math.pi * (doy - peak_doy) / 365.25)
            day += timedelta(days=1)
        return out

    assert warm_season(22, series(135, 6)) == ([3, 4, 5, 6, 7], 0)  # pre-monsoon heat (India)
    assert warm_season(-34, series(20, 7)) == ([11, 12, 1, 2, 3], 11)  # southern summer
    assert warm_season(1, series(60, 1))[0] == list(range(1, 13))  # no seasonal cycle
    assert warm_season(5)[0] == list(range(1, 13))


# --- heat waves ----------------------------------------------------------------


def test_inserted_heat_waves_are_found_and_counted_in_the_period() -> None:
    background = detect_heat_waves(tmax_record({}), 39, 2000, 2024)
    quiet = [y for y in range(2011, 2025) if y not in background["eventYears"]][:3]  # outside 1981-2010
    assert len(quiet) == 3
    inserted = {quiet[0]: (210, 6), quiet[1]: (180, 5), quiet[2]: (190, 4)}
    res = detect_heat_waves(tmax_record(inserted), 39, 2000, 2024)
    assert set(inserted) <= set(res["eventYears"])
    assert res["yearsWithEvents"] == background["yearsWithEvents"] + 3
    assert res["yearsAnalysed"] == 25
    assert res["score"] == round(100 * res["yearsWithEvents"] / 25)
    wave = next(e for e in res["events"] if e["year"] == quiet[1])
    assert wave["days"] >= 5 and wave["start"].startswith(f"{quiet[1]}-06")
    assert res["baselinePeriod"] == "1981-2010"
    assert res["trend"]["unit"] == "heat-wave days per year"


def test_two_hot_days_add_no_heat_wave_days() -> None:
    plain = detect_heat_waves(tmax_record({}), 39, 2012, 2012)["heatWaveDays"]["2012"]
    spike = detect_heat_waves(tmax_record({2012: (100, 2)}), 39, 2012, 2012)  # 2 hot days in April
    assert spike["heatWaveDays"]["2012"] == plain


def test_stable_climate_scores_about_one_year_in_five() -> None:
    for seed in (1, 2, 3):
        heat = detect_heat_waves(tmax_record({}, seed=seed), 39, 1981, 2010)
        rain = detect_extreme_rain(rain_record({}, {}, seed=seed), 1981, 2010)
        dry = detect_rain_drought(rain_record({}, {}, seed=seed), 1981, 2010)
        assert 15 <= heat["score"] <= 25 and 15 <= rain["score"] <= 25 and dry["score"] <= 25


def test_period_excludes_later_heat_waves_but_reports_them() -> None:
    res = detect_heat_waves(tmax_record({2012: (180, 6)}), 39, 2000, 2011)
    assert 2012 not in res["eventYears"] and 2012 in res["laterEventYears"]


def test_southern_hemisphere_summer_spans_new_year() -> None:
    # A January heat wave belongs to that summer (Nov-Mar), counted for the January year.
    res = detect_heat_waves(tmax_record({2019: (15, 5)}, south=True), -34, 2015, 2020)
    assert 2019 in res["eventYears"]


def test_heat_waves_need_ten_complete_years() -> None:
    with pytest.raises(ValueError):
        detect_heat_waves(tmax_record({}, first=2018, last=2022), 39, 2018, 2022)


# --- extreme rainfall ------------------------------------------------------------


def test_extreme_rain_flags_years_above_the_five_year_daily_total() -> None:
    res = detect_extreme_rain(rain_record({2015: 160.0, 2019: 140.0}, {}), 2000, 2024)
    assert {2015, 2019} <= set(res["eventYears"])
    assert next(e for e in res["events"] if e["year"] == 2015)["amount"] == 160
    # About one year in five exceeds the reference threshold by construction.
    assert 10 <= res["baselineScore"] <= 30
    assert res["threshold"] < 140


def test_incomplete_year_is_left_out() -> None:
    rows = [r for r in rain_record({}, {}) if not r[0].startswith("2010-0")]  # Jan-Sep 2010 missing
    res = detect_extreme_rain(rows, 2005, 2015)
    assert res["yearsAnalysed"] == 10


# --- severe drought --------------------------------------------------------------


def test_rain_drought_finds_dry_seasons() -> None:
    res = detect_rain_drought(rain_record({}, {2002: (5, 8), 2018: (6, 9)}), 1990, 2024)
    assert {2002, 2018} <= set(res["eventYears"])
    event = next(e for e in res["events"] if e["year"] == 2018)
    assert event["months"] >= 2 and "% of normal" in event["label"]
    assert res["score"] <= 30


# --- endpoint -------------------------------------------------------------------


def _q(request: httpx.Request) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(str(request.url)).query).items()}


def _power_daily(request: httpx.Request) -> httpx.Response:
    query = _q(request)
    first, last = int(query["start"][:4]), int(query["end"][:4])
    assert query["parameters"] == "T2M_MAX,PRECTOTCORR,GWETROOT"
    tmax = dict(tmax_record({2012: (180, 6)}, first, last))
    from climate_sim import CLIMATES, daily_soil_and_tmax

    soil, _ = daily_soil_and_tmax(CLIMATES[0], first, last, flash=[date(2012, 6, 20)], seed=3)
    rain = dict(rain_record({2015: 160.0}, {2002: (5, 8)}, first, last))
    as_power = lambda rows: {d.replace("-", ""): v for d, v in rows.items()}  # noqa: E731
    t = as_power(tmax)
    t["19810105"] = -999  # missing value is skipped
    return httpx.Response(200, json={"properties": {"parameter": {
        "T2M_MAX": t, "PRECTOTCORR": as_power(rain), "GWETROOT": as_power(dict(soil))}}})


def _power_monthly(request: httpx.Request) -> httpx.Response:
    query = _q(request)
    first, last = int(query["start"]), int(query["end"])
    rng, anomaly, series = random.Random(5), 0.0, {}
    for year in range(first, last + 1):
        for month in range(1, 13):
            anomaly = 0.9 * anomaly + rng.gauss(0, 0.006)
            value = 0.5 + anomaly - (0.12 if year == 2012 and month >= 6 else 0) + (0.05 if (year, month) == (2012, 5) else 0)
            series[f"{year}{month:02d}"] = round(value, 4)
        series[f"{year}13"] = -999
    return httpx.Response(200, json={"properties": {"parameter": {query["parameters"]: series}}})


def _noaa(request: httpx.Request) -> httpx.Response:
    query = _q(request)
    datatype = query["dataTypes"]
    first, last = int(query["startDate"][:4]), int(query["endDate"][:4])
    if query["dataset"] == "global-summary-of-the-month":
        return httpx.Response(200, json=[
            {"STATION": "USW00003928", "NAME": "WICHITA AIRPORT, KS US", "DATE": f"{y}-{m:02d}", datatype: "20",
             "LATITUDE": "37.65", "LONGITUDE": "-97.43"}
            for y in range(first, last + 1) for m in range(1, 13)
        ])
    assert query["dataset"] == "daily-summaries" and query["stations"] == "USW00003928"
    rows = tmax_record({2011: (200, 7)}, first, last, seed=9) if datatype == "TMAX" else rain_record({}, {}, first, last)
    return httpx.Response(200, json=[{"STATION": "USW00003928", "DATE": d, datatype: f"{v:.1f}"} for d, v in rows])


@respx.mock
def test_hazards_endpoint_combines_sources_and_explains_missing_ones() -> None:
    respx.get(url__startswith=settings.power_daily_url).mock(side_effect=_power_daily)
    respx.get(url__startswith=settings.power_url).mock(side_effect=_power_monthly)
    respx.get(url__startswith=settings.noaa_access_url).mock(side_effect=_noaa)
    with TestClient(create_app()) as client:
        response = client.get("/api/hazards", params={"latitude": "38.27", "longitude": "-98.58", "start": "2000", "end": "2024"})
    assert response.status_code == 200, response.text
    hazards = response.json()["hazards"]
    assert set(hazards) == {"heatWave", "extremeRain", "rainDrought", "flashDrought"}

    heat = hazards["heatWave"]["results"]
    assert [r["provider"] for r in heat] == ["power", "noaa"]
    assert 2012 in heat[0]["eventYears"] and heat[0]["sourceLabel"] == "NASA POWER"
    assert 2011 in heat[1]["eventYears"] and heat[1]["sourceLabel"] == "NOAA station Wichita Airport"
    assert 2015 in hazards["extremeRain"]["results"][0]["eventYears"]
    assert 2002 in hazards["rainDrought"]["results"][0]["eventYears"]
    flash = hazards["flashDrought"]["results"][0]
    assert 2012 in flash["eventYears"] and flash["resolution"] == "daily (5-day means)"
    assert any(e["start"].startswith("2012-06") for e in flash["events"])

    # GPM IMERG and GLDAS need an Earthdata token: reported, not fatal.
    imerg = next(r for r in hazards["extremeRain"]["results"] if r["provider"] == "giovanni")
    assert "EARTHDATA_TOKEN" in imerg["error"]
    gldas = next(r for r in hazards["flashDrought"]["results"] if r["provider"] == "giovanni")
    assert "EARTHDATA_TOKEN" in gldas["error"]


@respx.mock
def test_hazards_can_be_limited_to_power_and_survive_an_outage() -> None:
    respx.get(url__startswith=settings.power_daily_url).mock(return_value=httpx.Response(503))
    respx.get(url__startswith=settings.power_url).mock(side_effect=_power_monthly)
    noaa = respx.get(url__startswith=settings.noaa_access_url)
    with TestClient(create_app()) as client:
        response = client.get("/api/hazards", params={
            "latitude": "38.27", "longitude": "-98.58", "start": "2000", "end": "2024", "sources": "power"})
    assert response.status_code == 200
    hazards = response.json()["hazards"]
    assert not noaa.called
    assert "503" in hazards["heatWave"]["results"][0]["error"]
    assert hazards["flashDrought"]["results"][0]["score"] >= 0  # monthly soil data still worked


@respx.mock
def test_imerg_daily_through_giovanni(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EARTHDATA_TOKEN", "t")
    respx.get(f"{settings.giovanni_url}/configured-variables").mock(
        return_value=httpx.Response(200, text="GPM_3IMERGDF_07_precipitation\nGLDAS_NOAH025_M_2_1_RootMoist_inst"))
    calls = []

    def timeseries(request: httpx.Request) -> httpx.Response:
        query = _q(request)
        calls.append(query["data"])
        first, last = (int(p[:4]) for p in query["time"].split("/"))
        if query["data"].startswith("GPM"):
            lines = ["unit,mm/day", "lat,38.25", "lon,-98.55", "Timestamp (UTC),Data"]
            lines += [f"{d}T00:00:00,{v}" for d, v in rain_record({2016: 170.0}, {}, first, last)]
            return httpx.Response(200, text="\n".join(lines))
        lines = ["unit,kg m-2", "Timestamp (UTC),Data"]
        lines += [f"{y}-{m:02d}-01T00:00:00,{300 - (60 if y == 2012 and m >= 6 else 0) + (5 * math.sin(y * 13 + m))}"
                  for y in range(first, last + 1) for m in range(1, 13)]
        return httpx.Response(200, text="\n".join(lines))

    respx.get(f"{settings.giovanni_url}/timeseries").mock(side_effect=timeseries)
    with TestClient(create_app()) as client:
        response = client.get("/api/hazards", params={
            "latitude": "38.27", "longitude": "-98.58", "start": "2005", "end": "2024", "sources": "giovanni"})
    hazards = response.json()["hazards"]
    rain = hazards["extremeRain"]["results"][0]
    assert rain["sourceLabel"] == "NASA GPM IMERG" and 2016 in rain["eventYears"]
    assert rain["baselinePeriod"].startswith("2001")  # record too short for 1981-2010
    assert hazards["heatWave"]["results"] == []  # no temperature from these sources
    flash = hazards["flashDrought"]["results"][0]
    assert flash["sourceLabel"] == "NASA GLDAS" and 2012 in flash["eventYears"], flash
    assert calls.count("GPM_3IMERGDF_07_precipitation") == 3  # 2001-2010, 2011-2020, 2021-...


def test_power_daily_parser_skips_missing_values() -> None:
    parsed = parse_power_daily({"properties": {"parameter": {"T2M_MAX": {"20200101": 5.5, "20200102": -999}}}}, ["T2M_MAX"])
    assert parsed == {"T2M_MAX": [("2020-01-01", 5.5)]}


def test_hazards_rejects_bad_coordinates() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/hazards", params={"latitude": "120", "longitude": "0", "start": "2000", "end": "2020"})
    assert response.status_code == 400


# --- flash drought season and Giovanni retries ------------------------------------


def _soil(collapses: dict[tuple[int, int], int], first=1981, last=2024):
    """Monthly soil wetness; ``collapses`` maps (year, month) of the dry month -> 1."""
    rng, anomaly, points = random.Random(11), 0.0, []
    for y in range(first, last + 1):
        for m in range(1, 13):
            anomaly = 0.9 * anomaly + rng.gauss(0, 0.01)
            value = 0.5 + 0.1 * math.cos((m - 2) / 12 * 2 * math.pi) + anomaly
            if (y, m - 1 if m > 1 else 12) in collapses or ((y, m) in collapses and False):
                pass
            for (cy, cm) in collapses:
                before = (cy, cm - 1) if cm > 1 else (cy - 1, 12)
                if (y, m) == before:
                    value += 0.06
                if (y, m) == (cy, cm):
                    value -= 0.2
            points.append({"date": f"{y}-{m:02d}", "value": round(value, 4)})
    return points


def test_monthly_fallback_counts_any_active_month() -> None:
    from app.science.flash_drought import detect_flash_droughts

    pts = _soil({(2012, 3): 1, (2017, 10): 1})
    mild = detect_flash_droughts(pts, 2005, 2023)  # no cold months: every month counts
    assert {"2012-03", "2017-10"} <= {e["month"] for e in mild["events"]}
    cold_spring = detect_flash_droughts(pts, 2005, 2023, active_months=list(range(4, 12)))
    assert "2012-03" not in {e["month"] for e in cold_spring["events"]}


@respx.mock
def test_giovanni_server_error_is_retried_in_smaller_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EARTHDATA_TOKEN", "t")
    respx.get(f"{settings.giovanni_url}/configured-variables").mock(return_value=httpx.Response(200, text=""))
    spans = []

    def timeseries(request: httpx.Request) -> httpx.Response:
        first, last = (int(p[:4]) for p in _q(request)["time"].split("/"))
        spans.append((first, last))
        if last - first >= 3:
            return httpx.Response(500, text="Internal Server Error")
        lines = ["unit,kg m-2", "Timestamp (UTC),Data"]
        for y in range(first, last + 1):
            for m in range(1, 13):
                for hour in (0, 12):
                    lines.append(f"{y}-{m:02d}-15T{hour:02d}:00:00,{300 + 10 * math.sin(m + y)}")
        return httpx.Response(200, text="\n".join(lines))

    respx.get(f"{settings.giovanni_url}/timeseries").mock(side_effect=timeseries)
    with TestClient(create_app()) as client:
        response = client.get("/api/analysis", params={
            "parameter": "GLDAS_ROOT_ZONE_SM", "latitude": "37.4", "longitude": "-6", "start": "2005",
            "end": "2014", "mode": "raw"})
    assert response.status_code == 200, response.text
    assert len(response.json()["points"]) == 120
    assert all(last - first < 3 for first, last in spans if (first, last) != spans[0]) or spans[0][1] - spans[0][0] < 3


@respx.mock
def test_gldas_three_hourly_soil_moisture_is_used_daily(monkeypatch: pytest.MonkeyPatch) -> None:
    from climate_sim import CLIMATES, daily_soil_and_tmax

    monkeypatch.setenv("EARTHDATA_TOKEN", "t")
    respx.get(f"{settings.giovanni_url}/configured-variables").mock(return_value=httpx.Response(200, text=""))
    soil = dict(daily_soil_and_tmax(CLIMATES[1], 2000, 2025, flash=[date(2012, 3, 10), date(2017, 9, 25)], seed=4)[0])  # soil normal before both drops
    windows = []

    def timeseries(request: httpx.Request) -> httpx.Response:
        query = _q(request)
        if not query["data"].startswith("GLDAS_NOAH025_3H"):
            return httpx.Response(404)
        first, last = (int(p[:4]) for p in query["time"].split("/"))
        windows.append((first, last))
        lines = ["unit,kg m-2", "Timestamp (UTC),Data"]
        for day, value in soil.items():
            if first <= int(day[:4]) <= last:
                lines += [f"{day}T{h:02d}:00:00,{value * 400:.3f}" for h in range(0, 24, 3)]
        return httpx.Response(200, text="\n".join(lines))

    respx.get(f"{settings.giovanni_url}/timeseries").mock(side_effect=timeseries)
    respx.get(url__startswith=settings.power_daily_url).mock(return_value=httpx.Response(503))
    with TestClient(create_app()) as client:
        response = client.get("/api/hazards", params={
            "latitude": "37.4", "longitude": "-6", "start": "2005", "end": "2024", "sources": "giovanni"})
    flash = response.json()["hazards"]["flashDrought"]["results"][0]
    assert flash["sourceLabel"] == "NASA GLDAS" and flash["resolution"] == "daily (5-day means)", flash
    starts = [e["start"] for e in flash["events"]]
    assert any(s.startswith(("2012-03", "2012-02")) for s in starts), starts  # winter-spring event found
    assert any(s.startswith(("2017-09", "2017-10")) for s in starts), starts
    assert all(b - a <= 2 for a, b in windows)  # 3-year windows
