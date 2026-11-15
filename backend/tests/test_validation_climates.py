"""Every detector, checked in eight very different climates (not tuned to one place).

For each climate we insert events at known dates and measure:
* detection: inserted events that are found;
* false alarms: events found in records with nothing inserted;
* things that must NOT count (slow drying, a desert's dry season).
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.science.extremes import detect_heat_waves, detect_rain_drought, warm_season
from app.science.flash_drought_daily import detect_flash_droughts_daily
from climate_sim import (
    CLIMATES,
    active_onset_dates,
    daily_rain,
    daily_soil_and_tmax,
    daily_tmax,
    heat_dates,
    wet_season_start,
)

IDS = [c.name for c in CLIMATES]


@pytest.mark.parametrize("climate", CLIMATES, ids=IDS)
def test_flash_droughts_are_found_in_every_climate(climate) -> None:
    hits = total = false_alarms = years = 0
    for seed in range(2):
        rng = random.Random(seed * 31 + len(climate.name))
        chosen = sorted(rng.sample(range(1983, 2023), 6))
        onsets = active_onset_dates(climate, chosen, seed)
        soil, tmax = daily_soil_and_tmax(climate, flash=onsets, seed=seed)
        found = [date.fromisoformat(e["start"]) for e in detect_flash_droughts_daily(soil, 1981, 2024, tmax=tmax)["events"]]
        total += len(onsets)
        hits += sum(any(abs((f - o).days) <= 20 for f in found) for o in onsets)
        quiet, _ = daily_soil_and_tmax(climate, seed=seed)
        result = detect_flash_droughts_daily(quiet, 1981, 2024, tmax=tmax)
        false_alarms += len(result["events"])
        years += result["seasonsAnalysed"]
    assert hits / total >= 0.7, f"{climate.name}: found {hits} of {total}"
    assert false_alarms / years <= 0.45, f"{climate.name}: {false_alarms} events in {years} quiet years"


@pytest.mark.parametrize("climate", CLIMATES, ids=IDS)
def test_a_slow_drought_is_not_a_flash_drought(climate) -> None:
    # Without day-to-day noise, a 200-day decline never falls 20 percentiles within 20 days.
    soil, tmax = daily_soil_and_tmax(climate, slow=[date(2005, 3, 1), date(2015, 3, 1)], seed=0)
    smooth = [(d, v) for d, v in daily_soil_and_tmax(climate, seed=0)[0]]
    from climate_sim import Climate

    calm = Climate(**{**climate.__dict__, "soil_noise": 1e-6})
    soil, _ = daily_soil_and_tmax(calm, slow=[date(2005, 3, 1), date(2015, 3, 1)], seed=0)
    # Give the record realistic year-to-year differences so percentiles exist.
    soil = [(d, v + 0.02 * ((int(d[:4]) * 7919) % 11 - 5) / 5) for d, v in soil]
    events = detect_flash_droughts_daily(soil, 1981, 2024, tmax=tmax)["events"]
    assert not [e for e in events if e["year"] in (2005, 2015)], events
    assert smooth  # the noisy record is still generated


def test_frozen_season_is_ignored_and_reported() -> None:
    boreal = next(c for c in CLIMATES if c.name.startswith("Boreal"))
    soil, tmax = daily_soil_and_tmax(boreal, seed=1)
    result = detect_flash_droughts_daily(soil, 1981, 2024, tmax=tmax)
    assert result["activeSeason"] not in ("all year", "none")
    assert all(e["month"][5:7] not in ("12", "01", "02") for e in result["events"])
    assert "10 °C" in result["method"]


def test_soil_that_never_changes_is_reported_not_guessed() -> None:
    rows = [(d, 0.05) for d, _ in daily_soil_and_tmax(CLIMATES[0], seed=0)[0]]
    with pytest.raises(ValueError, match="hardly varies"):
        detect_flash_droughts_daily(rows, 1981, 2024)


@pytest.mark.parametrize("climate", CLIMATES, ids=IDS)
def test_heat_waves_are_found_in_every_climate(climate) -> None:
    years = [1999, 2004, 2013, 2019, 2022]
    dates = heat_dates(climate, years, seed=2)
    rows = daily_tmax(climate, heat=dates, seed=2)
    result = detect_heat_waves(rows, climate.latitude, 1981, 2024)
    # A summer that crosses the new year (southern hemisphere) is counted for the year it ends.
    months, shift = warm_season(climate.latitude, {date.fromisoformat(d): v for d, v in rows})
    expected = {d.year + 1 if shift and d.month >= shift else d.year for d in dates}
    assert expected <= set(result["eventYears"]), (climate.name, expected, result["eventYears"])
    quiet = detect_heat_waves(daily_tmax(climate, seed=3), climate.latitude, 1981, 2010)
    assert 10 <= quiet["score"] <= 30, (climate.name, quiet["score"])
    warmer = detect_heat_waves(daily_tmax(climate, seed=3, trend=0.07), climate.latitude, 2011, 2024)
    assert warmer["score"] >= 40, (climate.name, warmer["score"])  # warming shows up everywhere


@pytest.mark.parametrize("climate", CLIMATES, ids=IDS)
def test_rainfall_droughts_are_found_in_the_wet_season_only(climate) -> None:
    years = [1996, 2007, 2018]
    dry = [(wet_season_start(climate, y), 100) for y in years]
    result = detect_rain_drought(daily_rain(climate, dry=dry, seed=4), 1981, 2024)
    assert set(years) <= set(result["eventYears"]), (climate.name, result["eventYears"])
    quiet = detect_rain_drought(daily_rain(climate, seed=5), 1981, 2010)
    assert quiet["score"] <= 30, (climate.name, quiet["score"])  # the dry season is not a drought
