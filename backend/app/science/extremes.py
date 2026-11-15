"""Event-based hazard detection from daily series (any source).

Each detector takes daily samples ``[("YYYY-MM-DD", value), ...]`` and returns how
often the event happened in the chosen years, with the same result shape:

* **Heat wave** — a year whose hottest 3-day spell (warm season) is hotter than the
  "1-in-5-year" value of the reference period (80th percentile of yearly maxima).
  Heat-wave days (runs of 3+ days above the 95th percentile of warm-season maxima,
  Perkins & Alexander 2013) are reported alongside, with their trend.
* **Extreme rainfall** — a year whose wettest day exceeds the "1-in-5-year" daily
  rainfall, i.e. the 80th percentile of the reference period's annual maxima
  (Rx1day, ETCCDI).
* **Severe drought** — a year whose driest 3-month rainfall total is a 1-in-5-year
  deficit and reaches severe drought: at or below the 6.7th percentile of the same
  months (equivalent to SPI-3 <= -1.5, McKee et al. 1993; empirical, not gamma-fitted).

All three are calibrated the same way: in a stable climate about 20 % of years
qualify, so a higher score means the event has become more frequent here.

The reference period is 1981-2010 (WMO climate normal) when the record has at
least 15 complete years in it; otherwise the whole record is used.

Score = share of complete years in the chosen period with at least one event.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from app.science.statistics import mann_kendall, sens_slope

Sample = tuple[str, float]

BASE_PERIOD = (1981, 2010)
MIN_BASE_YEARS = 15
MIN_YEARS = 10
DAY_COMPLETENESS = 0.9

HEAT_PCTL = 95.0
HEAT_MIN_DAYS = 3
RETURN_PCTL = 80.0  # 80th percentile of yearly maxima = 1-in-5-year event
DROUGHT_PCTL = 6.7  # SPI <= -1.5
DROUGHT_WINDOW = 3
MIN_NORMAL_RAIN = 10.0  # mm in 3 months

REFERENCES = {
    "heatWave": [
        "Perkins, S. E. & Alexander, L. V. (2013). On the measurement of heat waves. J. Climate 26, 4500-4517.",
    ],
    "extremeRain": [
        "Zhang, X. et al. (2011). Indices for monitoring changes in extremes based on daily temperature "
        "and precipitation data (ETCCDI). WIREs Climate Change 2, 851-870.",
    ],
    "rainDrought": [
        "McKee, T. B., Doesken, N. J. & Kleist, J. (1993). The relationship of drought frequency and "
        "duration to time scales. 8th Conf. on Applied Climatology, 179-184.",
    ],
}


def level_for(score: float) -> str:
    if score >= 60:
        return "Very high"
    if score >= 40:
        return "High"
    if score >= 20:
        return "Moderate"
    return "Low"


def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile (same as numpy's default)."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("No values")
    pos = (len(ordered) - 1) * pct / 100.0
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def rank_percentile(reference: list[float], value: float) -> float:
    """Weibull plotting-position percentile of ``value`` against ``reference``."""
    below = sum(1 for v in reference if v < value)
    equal = sum(1 for v in reference if v == value)
    return 100.0 * (below + 0.5 * equal + 0.5) / (len(reference) + 1)


def _clean(samples: list[Sample]) -> dict[date, float]:
    out: dict[date, float] = {}
    for day, value in samples:
        if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
            continue
        try:
            out[date.fromisoformat(str(day)[:10])] = float(value)
        except ValueError:
            continue
    return out


def warm_season(latitude: float, samples: dict[date, float] | None = None) -> tuple[list[int], int]:
    """(months, shift) of the warm season.

    From the data when given: the 5 consecutive calendar months with the highest mean
    daily maximum (e.g. Mar-Jul before the Indian monsoon, Nov-Mar in Australia). Without
    data it falls back to May-Sep (north), Nov-Mar (south), all year (tropics).
    ``shift`` = the first month of a season that crosses the new year; months from it
    onward count toward the next year.
    """
    if samples:
        totals, counts = [0.0] * 13, [0] * 13
        for day, value in samples.items():
            totals[day.month] += value
            counts[day.month] += 1
        if all(counts[m] for m in range(1, 13)):
            means = [totals[m] / counts[m] for m in range(1, 13)]
            spread = max(means) - min(means)
            if spread < 3.0:  # no real seasonal cycle (equatorial): the whole year
                return list(range(1, 13)), 0
            best = max(range(12), key=lambda i: sum(means[(i + k) % 12] for k in range(5)))
            months = [(best + k) % 12 + 1 for k in range(5)]
            return months, (months[0] if months[0] > months[-1] else 0)
    if abs(latitude) < 23.5:
        return list(range(1, 13)), 0
    if latitude >= 0:
        return [5, 6, 7, 8, 9], 0
    return [11, 12, 1, 2, 3], 11


def _season_year(day: date, shift: int) -> int:
    return day.year + 1 if shift and day.month >= shift else day.year


def _season_days(year: int, months: list[int], shift: int) -> int:
    total = 0
    for month in months:
        y = year - 1 if shift and month >= shift else year
        nxt = date(y + (month == 12), month % 12 + 1, 1)
        total += (nxt - date(y, month, 1)).days
    return total


def _reference_years(years: list[int]) -> tuple[list[int], str, str]:
    base = [y for y in years if BASE_PERIOD[0] <= y <= BASE_PERIOD[1]]
    if len(base) >= MIN_BASE_YEARS:
        return base, f"{BASE_PERIOD[0]}-{BASE_PERIOD[1]}", ""
    return years, f"{years[0]}-{years[-1]}", (
        "The record does not cover enough of 1981-2010, so the whole record is the reference."
    )


def _window(years: list[int], start: int, end: int, what: str) -> list[int]:
    if len(years) < MIN_YEARS:
        raise ValueError(f"{what} needs at least {MIN_YEARS} complete years of daily data; this record has {len(years)}.")
    chosen = [y for y in years if start <= y <= end]
    if not chosen:
        raise ValueError(f"No complete year of data between {start} and {end} for this source.")
    return chosen


def _trend(years: list[int], values: list[float], unit: str, label: str = "", unit_short: str = "") -> dict[str, Any] | None:
    """Sen's slope per decade and Mann-Kendall p-value of a yearly metric."""
    if len(years) < 8:
        return None
    slope = sens_slope(values, [float(y) for y in years])
    mk = mann_kendall(values)
    return {
        "perDecade": round(slope * 10, 2),
        "unit": unit,
        "label": label or unit,
        "unitShort": unit_short,
        "pValue": round(mk["pValue"], 4),
    }


def _result(
    key: str,
    phenomenon: str,
    chosen: list[int],
    event_years_all: list[int],
    ref_years: list[int],
    ref_label: str,
    end: int,
    events: list[dict[str, Any]],
    trend: dict[str, Any] | None,
    method: str,
    caveat: str,
    extra: dict[str, Any],
) -> dict[str, Any]:
    in_window = [y for y in event_years_all if y in chosen]
    score = round(100 * len(in_window) / len(chosen))
    ref_events = [y for y in event_years_all if y in ref_years]
    return {
        "hazard": key,
        "phenomenon": phenomenon,
        "score": score,
        "level": level_for(score),
        "yearsAnalysed": len(chosen),
        "yearsWithEvents": len(in_window),
        "eventYears": in_window,
        "laterEventYears": [y for y in event_years_all if y > end],
        "events": [e for e in events if e["year"] in chosen],
        "baselineScore": round(100 * len(ref_events) / len(ref_years)) if ref_years else None,
        "baselinePeriod": ref_label,
        "trend": trend,
        "method": method,
        "caveat": caveat,
        "references": REFERENCES.get(key, []),
        **extra,
    }


def detect_heat_waves(samples: list[Sample], latitude: float, start: int, end: int) -> dict[str, Any]:
    series = _clean(samples)
    months, shift = warm_season(latitude, series)
    by_year: dict[int, list[tuple[date, float]]] = defaultdict(list)
    for day, value in series.items():
        if day.month in months:
            by_year[_season_year(day, shift)].append((day, value))
    years = sorted(
        y for y, rows in by_year.items() if len(rows) >= DAY_COMPLETENESS * _season_days(y, months, shift)
    )
    chosen = _window(years, start, end, "Heat-wave detection")
    ref_years, ref_label, ref_note = _reference_years(years)
    threshold = percentile([v for y in ref_years for _, v in by_year[y]], HEAT_PCTL)

    # Heat-wave days: runs of >= 3 consecutive days above the 95th percentile.
    days_per_year: dict[int, int] = {}
    # Intensity: hottest 3-consecutive-day mean of the season (TX3x).
    hottest: dict[int, tuple[float, date]] = {}
    for year in years:
        rows = sorted(by_year[year])
        run, hw_days = 0, 0
        best: tuple[float, date] | None = None
        for index, (day, value) in enumerate(rows):
            consecutive = index > 0 and day - rows[index - 1][0] == timedelta(days=1)
            if value > threshold:
                run = run + 1 if consecutive else 1
            else:
                hw_days += run if run >= HEAT_MIN_DAYS else 0
                run = 0
            if index >= 2 and rows[index][0] - rows[index - 2][0] == timedelta(days=2):
                mean3 = (rows[index][1] + rows[index - 1][1] + rows[index - 2][1]) / 3
                if best is None or mean3 > best[0]:
                    best = (mean3, rows[index - 2][0])
        hw_days += run if run >= HEAT_MIN_DAYS else 0
        days_per_year[year] = hw_days
        if best is not None:
            hottest[year] = best
    years = [y for y in years if y in hottest]
    chosen = [y for y in chosen if y in hottest]
    ref_years = [y for y in ref_years if y in hottest]
    major = percentile([hottest[y][0] for y in ref_years], RETURN_PCTL)
    events = [
        {
            "year": y,
            "start": hottest[y][1].isoformat(),
            "days": days_per_year[y],
            "peak": round(hottest[y][0], 1),
            "label": f"{hottest[y][1].strftime('%b')} {y} ({hottest[y][0]:.1f} °C)",
        }
        for y in years
        if hottest[y][0] > major
    ]
    trend = _trend(chosen, [float(days_per_year[y]) for y in chosen], "heat-wave days per year", "Heat-wave days a year")
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    season_text = "all year" if len(months) == 12 else f"{names[months[0] - 1]}-{names[months[-1] - 1]}, the warmest months here"
    return _result(
        "heatWave",
        "Heat wave",
        chosen,
        [e["year"] for e in events],
        ref_years,
        ref_label,
        end,
        events,
        trend,
        method=(
            f"A year counts when its hottest 3-day spell ({season_text}) averages above {major:.1f}, the "
            f"1-in-5-year value of {ref_label} (80th percentile of yearly maxima). In a stable climate about "
            f"20 % of years exceed it. Heat-wave days are runs of {HEAT_MIN_DAYS}+ days above {threshold:.1f} "
            f"(the {HEAT_PCTL:.0f}th percentile of warm-season maxima)."
        ),
        caveat=("Gridded data smooth local peaks; a station record can show hotter days. " + ref_note).strip(),
        extra={
            "threshold": round(major, 2),
            "dailyThreshold": round(threshold, 2),
            "averageDaysPerYear": round(sum(days_per_year[y] for y in chosen) / len(chosen), 1),
            "heatWaveDays": {str(y): days_per_year[y] for y in chosen},
            "metricLabel": "heat-wave days per year",
        },
    )


def _complete_years(series: dict[date, float]) -> list[int]:
    counts: dict[int, int] = defaultdict(int)
    for day in series:
        counts[day.year] += 1
    return sorted(y for y, n in counts.items() if n >= DAY_COMPLETENESS * (366 if y % 4 == 0 else 365))


def detect_extreme_rain(samples: list[Sample], start: int, end: int) -> dict[str, Any]:
    series = _clean(samples)
    years = _complete_years(series)
    chosen = _window(years, start, end, "Extreme-rainfall detection")
    ref_years, ref_label, ref_note = _reference_years(years)
    wettest: dict[int, tuple[date, float]] = {}
    for day, value in series.items():
        if day.year in years and (day.year not in wettest or value > wettest[day.year][1]):
            wettest[day.year] = (day, value)
    threshold = percentile([wettest[y][1] for y in ref_years], RETURN_PCTL)
    events = [
        {
            "year": y,
            "start": wettest[y][0].isoformat(),
            "amount": round(wettest[y][1], 1),
            "label": f"{wettest[y][0].day} {wettest[y][0].strftime('%b')} {y} ({wettest[y][1]:.0f} mm)",
        }
        for y in years
        if wettest[y][1] > threshold and wettest[y][1] > 0
    ]
    trend = _trend(chosen, [wettest[y][1] for y in chosen], "mm on the wettest day", "Wettest day", "mm")
    return _result(
        "extremeRain",
        "Extreme rainfall",
        chosen,
        [e["year"] for e in events],
        ref_years,
        ref_label,
        end,
        events,
        trend,
        method=(
            f"A year counts when its wettest day exceeds {threshold:.0f} mm, the 1-in-5-year daily rainfall "
            f"(80th percentile of annual maxima, {ref_label}). In a stable climate about 20 % of years "
            "exceed it; a higher share means heavier downpours."
        ),
        caveat=("Daily totals; short cloudbursts inside one day are not resolved. " + ref_note).strip(),
        extra={"threshold": round(threshold, 1), "metricLabel": "mm on the wettest day"},
    )


def detect_rain_drought(samples: list[Sample], start: int, end: int) -> dict[str, Any]:
    series = _clean(samples)
    totals: dict[tuple[int, int], float] = defaultdict(float)
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for day, value in series.items():
        totals[(day.year, day.month)] += max(0.0, value)
        counts[(day.year, day.month)] += 1
    monthly: dict[tuple[int, int], float] = {}
    for (y, m), n in counts.items():
        length = (date(y + (m == 12), m % 12 + 1, 1) - date(y, m, 1)).days
        if n >= DAY_COMPLETENESS * length:
            monthly[(y, m)] = totals[(y, m)] * length / n  # fill small gaps at the month's mean rate

    def back(y: int, m: int, k: int) -> tuple[int, int]:
        index = y * 12 + (m - 1) - k
        return index // 12, index % 12 + 1

    rolling: dict[tuple[int, int], float] = {}
    for (y, m) in monthly:
        keys = [back(y, m, k) for k in range(DROUGHT_WINDOW)]
        if all(k in monthly for k in keys):
            rolling[(y, m)] = sum(monthly[k] for k in keys)
    years = sorted({y for (y, _) in rolling if all((y, m) in rolling for m in range(1, 13))})
    chosen = _window(years, start, end, "Drought detection")
    ref_years, ref_label, ref_note = _reference_years(years)

    # Percentile of every 3-month total against the same months in the reference years.
    pct: dict[tuple[int, int], float] = {}
    for month in range(1, 13):
        reference = [rolling[(y, month)] for y in ref_years]
        for y in years:
            pct[(y, month)] = rank_percentile(reference, rolling[(y, month)])
    # Only 3-month windows that normally get real rain can have a deficit: dry seasons of
    # deserts and monsoon climates (normal total under MIN_NORMAL_RAIN mm) are skipped.
    normal = {m: percentile([rolling[(y, m)] for y in ref_years], 50) for m in range(1, 13)}
    wet = [m for m in range(1, 13) if normal[m] >= MIN_NORMAL_RAIN]
    if not wet:
        raise ValueError("It almost never rains here, so a rainfall drought cannot be measured.")
    # Driest spell of each year as a share of normal (median) rain for those months.
    driest = {y: min((rolling[(y, m)] / normal[m], m) for m in wet) for y in years}
    major = percentile([driest[y][0] for y in ref_years], 100 - RETURN_PCTL)
    months_in_drought = {y: sum(1 for m in wet if pct[(y, m)] <= DROUGHT_PCTL) for y in years}
    summary: list[dict[str, Any]] = []
    for y in years:
        ratio, month = driest[y]
        low = pct[(y, month)]
        if ratio < major and low <= DROUGHT_PCTL:
            first = date(*back(y, month, DROUGHT_WINDOW - 1), 1)
            summary.append(
                {
                    "year": y,
                    "start": first.isoformat()[:7],
                    "months": months_in_drought[y],
                    "percentile": round(low, 1),
                    "label": f"{first.strftime('%b')}-{date(y, month, 1).strftime('%b')} {y} ({round(100 * ratio)}% of normal)",
                }
            )
    trend = _trend(chosen, [float(months_in_drought[y]) for y in chosen], "drought months per year", "Drought months a year")
    return _result(
        "rainDrought",
        "Severe drought",
        chosen,
        [e["year"] for e in summary],
        ref_years,
        ref_label,
        end,
        summary,
        trend,
        method=(
            f"A year counts when its driest {DROUGHT_WINDOW}-month rainfall total is a 1-in-5-year deficit "
            f"for {ref_label} and reaches severe drought (at or below the {DROUGHT_PCTL}th percentile of the "
            "same months, SPI-3 <= -1.5 equivalent). In a stable climate about 20 % of years qualify or fewer. "
            + ("" if len(wet) == 12 else f"Only the {len(wet)} months whose normal 3-month rain is at least {MIN_NORMAL_RAIN:.0f} mm are used (dry season skipped).")
        ),
        caveat=("Rainfall deficit only; heat and evaporation (as in SPEI) are not included. " + ref_note).strip(),
        extra={"metricLabel": "drought months per year"},
    )


def from_flash_drought(result: dict[str, Any], end: int) -> dict[str, Any]:
    """Map the flash-drought detector's output to the common hazard shape."""
    month = lambda iso: date(int(iso[:4]), int(iso[5:7]), 1).strftime("%b")  # noqa: E731
    return {
        "hazard": "flashDrought",
        "phenomenon": "Flash drought",
        "score": result["score"],
        "level": result["level"],
        "yearsAnalysed": result["seasonsAnalysed"],
        "yearsWithEvents": result["seasonsWithEvents"],
        "eventYears": result["eventYears"],
        "laterEventYears": [y for y in result.get("baselineEventYears", []) if y > end],
        "events": [{**e, "label": e.get("label") or f"{month(e['month'])} {e['month'][:4]}"} for e in result["events"]],
        "baselineScore": result.get("baselineScore"),
        "baselinePeriod": result.get("baselinePeriod"),
        "trend": None,
        "method": result["method"],
        "caveat": result["caveat"],
        "references": result.get("references", []),
        "metricLabel": "years with a rapid soil-moisture collapse",
        "activeSeason": result.get("activeSeason"),
        "resolution": result.get("resolution", "monthly"),
    }
