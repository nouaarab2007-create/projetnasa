"""Synthetic daily climates for validating the hazard detectors everywhere, not on one example.

Each climate has its own soil-moisture seasonal cycle, temperature cycle and noise.
Flash droughts (fast collapse), slow droughts (gradual decline) and heat waves can be
inserted at known dates so detection and false-alarm rates can be measured.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Climate:
    name: str
    latitude: float
    soil_mean: float  # root-zone wetness (0-1)
    soil_amp: float  # seasonal amplitude
    soil_peak_doy: int  # wettest day of year
    soil_noise: float  # daily AR(1) innovation sd
    tmax_mean: float  # °C
    tmax_amp: float
    tmax_peak_doy: int  # hottest day of year


CLIMATES = [
    Climate("Great Plains (Kansas)", 38.3, 0.55, 0.10, 120, 0.004, 19, 15, 200),
    Climate("Mediterranean (Seville)", 37.4, 0.45, 0.18, 30, 0.005, 25, 9, 205),
    Climate("Southern Australia", -34.0, 0.40, 0.14, 210, 0.005, 23, 7, 20),
    Climate("Monsoon (central India)", 22.0, 0.45, 0.22, 240, 0.005, 33, 6, 140),
    Climate("Equatorial (Congo)", 0.5, 0.75, 0.04, 100, 0.004, 30, 1.5, 60),
    Climate("Boreal (Saskatchewan)", 53.0, 0.60, 0.08, 140, 0.004, 8, 18, 200),
    Climate("Sahel (Niger)", 13.5, 0.25, 0.15, 240, 0.004, 36, 5, 120),
    Climate("Pampas (Argentina)", -34.5, 0.55, 0.08, 120, 0.004, 23, 7, 15),
]


def _days(first: int, last: int):
    day = date(first, 1, 1)
    while day <= date(last, 12, 31):
        yield day
        day += timedelta(days=1)


def daily_soil_and_tmax(
    climate: Climate,
    first: int = 1981,
    last: int = 2024,
    *,
    flash: list[date] = (),
    slow: list[date] = (),
    seed: int = 0,
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    """``flash``: onset dates of fast collapses (wet build-up, then a drop of ~3 interannual sd
    over 12 days, held 35 days, slow recovery). ``slow``: start of a 200-day gradual decline."""
    rng = random.Random(seed)
    # Interannual variability of soil moisture comes mostly from a slow AR(1) anomaly.
    phi = 0.992
    sd = climate.soil_noise / math.sqrt(1 - phi**2)  # stationary sd of the anomaly
    anomaly, t_anom = 0.0, 0.0
    soil, tmax = [], []
    flash_set = list(flash)
    for day in _days(first, last):
        doy = day.timetuple().tm_yday
        anomaly = phi * anomaly + rng.gauss(0, climate.soil_noise)
        value = climate.soil_mean + climate.soil_amp * math.cos(2 * math.pi * (doy - climate.soil_peak_doy) / 365.25) + anomaly
        for onset in flash_set:
            k = (day - onset).days
            if -20 <= k < 0:
                value += 1.0 * sd  # wet (or normal-to-wet) before the collapse
            elif 0 <= k < 12:
                value += 1.0 * sd - (k + 1) / 12 * 4.0 * sd
            elif 12 <= k < 47:
                value -= 3.0 * sd
            elif 47 <= k < 107:
                value -= 3.0 * sd * (1 - (k - 47) / 60)
        for onset in slow:
            k = (day - onset).days
            if 0 <= k < 200:
                value -= 3.0 * sd * k / 200
            elif 200 <= k < 260:
                value -= 3.0 * sd * (1 - (k - 200) / 60)
        soil.append((day.isoformat(), round(max(0.01, value), 5)))
        t_anom = 0.7 * t_anom + rng.gauss(0, 1.5)
        t = climate.tmax_mean + climate.tmax_amp * math.cos(2 * math.pi * (doy - climate.tmax_peak_doy) / 365.25) + t_anom
        tmax.append((day.isoformat(), round(t, 2)))
    return soil, tmax


def active_onset_dates(climate: Climate, years: list[int], seed: int) -> list[date]:
    """One random onset date per year, inside the part of the year the detector should watch
    (normal daily maximum >= 12 °C, a margin above the 10 °C rule)."""
    rng = random.Random(seed)
    out = []
    for year in years:
        for _ in range(200):
            doy = rng.randint(30, 320)
            normal = climate.tmax_mean + climate.tmax_amp * math.cos(2 * math.pi * (doy - climate.tmax_peak_doy) / 365.25)
            if normal >= 12:
                out.append(date(year, 1, 1) + timedelta(days=doy - 1))
                break
    return out


# Rainfall regimes: (mean mm/day at the wettest time, wettest day of year, share of the year that is dry)
RAIN = {
    "Great Plains (Kansas)": (3.5, 160, 0.0),
    "Mediterranean (Seville)": (2.5, 15, 0.35),  # dry summer
    "Southern Australia": (1.8, 190, 0.0),
    "Monsoon (central India)": (12.0, 210, 0.55),  # long dry season
    "Equatorial (Congo)": (5.0, 100, 0.0),
    "Boreal (Saskatchewan)": (2.5, 190, 0.0),
    "Sahel (Niger)": (6.0, 225, 0.7),
    "Pampas (Argentina)": (3.0, 30, 0.0),
}


def heat_dates(climate: Climate, years: list[int], seed: int) -> list[date]:
    """One date per year near the climatological hottest time (+-40 days)."""
    rng = random.Random(seed)
    return [date(y, 1, 1) + timedelta(days=(climate.tmax_peak_doy + rng.randint(-40, 40)) % 360) for y in years]


def daily_tmax(climate: Climate, first=1981, last=2024, *, heat: list[date] = (), seed=0, trend=0.0):
    """Daily maximum temperature; ``heat`` inserts 6-day heat waves (+9 °C); ``trend`` in °C/year."""
    rng, anomaly, rows = random.Random(seed), 0.0, []
    for day in _days(first, last):
        doy = day.timetuple().tm_yday
        anomaly = 0.7 * anomaly + rng.gauss(0, 1.5)
        value = climate.tmax_mean + climate.tmax_amp * math.cos(2 * math.pi * (doy - climate.tmax_peak_doy) / 365.25)
        value += anomaly + trend * (day.year - first)
        if any(0 <= (day - h).days < 6 for h in heat):
            value += 9
        rows.append((day.isoformat(), round(value, 2)))
    return rows


def daily_rain(climate: Climate, first=1981, last=2024, *, dry: list[tuple[date, int]] = (), seed=0):
    """Daily rain following the climate's wet season; ``dry`` = (start, days) with no rain at all."""
    peak, wettest, dry_share = RAIN[climate.name]
    rng, rows = random.Random(seed), []
    for day in _days(first, last):
        doy = day.timetuple().tm_yday
        phase = math.cos(2 * math.pi * (doy - wettest) / 365.25)  # 1 at the wettest time
        if dry_share and phase < math.cos(math.pi * (1 - dry_share)):
            mean = 0.0  # dry season: essentially no rain
        else:
            mean = peak * (0.35 + 0.65 * (phase + 1) / 2)
        value = rng.expovariate(1 / (mean / 0.35)) if mean > 0 and rng.random() < 0.35 else 0.0
        if any(0 <= (day - start).days < length for start, length in dry):
            value = 0.0
        rows.append((day.isoformat(), round(value, 2)))
    return rows


def wet_season_start(climate: Climate, year: int) -> date:
    """Start of a 100-day window centred on the wettest time of year."""
    _, wettest, _ = RAIN[climate.name]
    return date(year, 1, 1) + timedelta(days=wettest - 50)  # may start in the previous year
