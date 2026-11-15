"""Flash-drought onset detection from monthly root-zone soil moisture.

A flash drought is an event, not a long-term trend: soil moisture collapses within
a few weeks during the warm season. The standard definition (Ford & Labosier 2017;
Christian et al. 2019) is a fall of root-zone soil moisture from at or above the
40th percentile to at or below the 20th percentile within about a month.

NASA POWER gives monthly means, so this module applies a monthly approximation:

* each month's value is ranked against the same calendar month in every year of the
  climatology (empirical percentile, Weibull plotting position);
* an onset is a month whose percentile is <= 20 while one of the two previous months
  was >= 40 (monthly averages smooth a 3-6 week collapse, so a two-month window is
  allowed). Every month counts except those whose normal daily maximum temperature is
  below 10 °C (frozen or dormant ground), which comes from the data, not the region;
* the hazard score is the share of growing seasons in the chosen period with at
  least one onset.

This is the FALLBACK used when daily soil moisture is unavailable; the main detector
is ``flash_drought_daily`` (5-day means). Monthly means smooth the fastest events.
"""

from __future__ import annotations

from typing import Any

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
COLD_TMAX = 10.0  # °C: months whose normal daily maximum is lower are skipped (frozen/dormant)


def active_months_from_tmax(points: list[dict[str, Any]]) -> list[int]:
    """Months whose mean daily maximum temperature is at least COLD_TMAX (from the data)."""
    sums: dict[int, list[float]] = {}
    for point in points:
        date = str(point.get("date", ""))
        if len(date) >= 7 and isinstance(point.get("value"), (int, float)):
            sums.setdefault(int(date[5:7]), []).append(float(point["value"]))
    return [m for m in range(1, 13) if m not in sums or sum(sums[m]) / len(sums[m]) >= COLD_TMAX]


WET_PCTL = 40.0
DRY_PCTL = 20.0
MAX_LAG_MONTHS = 2
MIN_CLIMATOLOGY_YEARS = 10

REFERENCES = [
    "Ford, T. W. & Labosier, C. F. (2017). Meteorological conditions associated with the "
    "onset of flash drought in the eastern United States. Agric. For. Meteorol. 247, 414-423.",
    "Christian, J. I. et al. (2019). A methodology for flash drought identification. "
    "J. Hydrometeorol. 20, 833-846.",
]


def _level(score: float) -> str:
    if score >= 35:
        return "Very high"
    if score >= 20:
        return "High"
    if score >= 10:
        return "Moderate"
    return "Low"


def _percentiles(series: dict[tuple[int, int], float]) -> dict[tuple[int, int], float]:
    """Rank each value against the same calendar month in all years (0-100)."""
    by_month: dict[int, list[float]] = {}
    for (_, month), value in series.items():
        by_month.setdefault(month, []).append(value)
    out: dict[tuple[int, int], float] = {}
    for (year, month), value in series.items():
        values = by_month[month]
        below = sum(1 for v in values if v < value)
        ties = sum(1 for v in values if v == value)
        rank = below + (ties + 1) / 2  # mid-rank for ties
        out[(year, month)] = 100.0 * rank / (len(values) + 1)
    return out


def _monthly(points: list[dict[str, Any]]) -> dict[tuple[int, int], float]:
    series: dict[tuple[int, int], float] = {}
    for point in points:
        date = str(point.get("date", ""))
        value = point.get("value")
        if len(date) < 7 or not isinstance(value, (int, float)):
            continue
        series[(int(date[:4]), int(date[5:7]))] = float(value)
    return series


def _shift(year: int, month: int, back: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) - back
    return index // 12, index % 12 + 1


def detect_flash_droughts(
    soil_points: list[dict[str, Any]],
    start: int,
    end: int,
    *,
    climatology_note: str = "",
    active_months: list[int] | None = None,
) -> dict[str, Any]:
    """Return onset events and a hazard score for ``start``..``end``."""
    series = _monthly(soil_points)
    years_all = sorted({year for year, _ in series})
    if len(years_all) < MIN_CLIMATOLOGY_YEARS:
        raise ValueError(
            f"Flash-drought detection needs at least {MIN_CLIMATOLOGY_YEARS} years of monthly soil moisture."
        )
    pct = _percentiles(series)
    months = sorted(active_months) if active_months else list(range(1, 13))

    events: list[dict[str, Any]] = []
    for (year, month), p_now in sorted(pct.items()):
        if month not in months or p_now > DRY_PCTL:
            continue
        for lag in range(1, MAX_LAG_MONTHS + 1):
            prev = _shift(year, month, lag)
            p_prev = pct.get(prev)
            if p_prev is not None and p_prev >= WET_PCTL:
                # Skip if the previous month already counted as an onset (same event).
                if events and _shift(year, month, 1) == (events[-1]["calendarYear"], events[-1]["monthNumber"]):
                    break
                events.append(
                    {
                        "year": year,
                        "calendarYear": year,
                        "monthNumber": month,
                        "month": f"{year}-{month:02d}",
                        "fromPercentile": round(p_prev, 1),
                        "toPercentile": round(p_now, 1),
                        "fromMonth": f"{prev[0]}-{prev[1]:02d}",
                        "weeks": lag * 4,
                    }
                )
                break

    def seasons(lo: int, hi: int) -> list[int]:
        # Only growing seasons fully present in the data count.
        return [y for y in range(lo, hi + 1) if all((y, m) in series for m in months)]

    season_text = ", ".join(MONTH_NAMES[m - 1] for m in months) if len(months) < 12 else "all year"
    window_years = seasons(start, end)
    if not window_years:
        raise ValueError(f"No complete growing season ({season_text}) in the selected period.")
    event_years = sorted({e["year"] for e in events if e["year"] in window_years})
    all_years = seasons(years_all[0], years_all[-1])
    all_event_years = sorted({e["year"] for e in events if e["year"] in all_years})

    score = round(100 * len(event_years) / len(window_years))
    baseline = round(100 * len(all_event_years) / len(all_years)) if all_years else None

    return {
        "phenomenon": "Flash drought",
        "activeSeason": season_text,
        "resolution": "monthly",
        "score": score,
        "level": _level(score),
        "seasonsAnalysed": len(window_years),
        "seasonsWithEvents": len(event_years),
        "eventYears": event_years,
        "events": [e for e in events if e["year"] in window_years],
        "baselineScore": baseline,
        "baselinePeriod": f"{all_years[0]}-{all_years[-1]}" if all_years else None,
        "baselineEventYears": all_event_years,
        "variable": "GWETROOT",
        "variableName": "Root-zone soil wetness",
        "source": "NASA POWER",
        "method": (
            "Monthly root-zone soil wetness is ranked against the same month in every year of "
            f"the climatology. An onset is a growing-season ({season_text}) month at or below the {DRY_PCTL:.0f}th "
            f"percentile within {MAX_LAG_MONTHS} months of being at or above the {WET_PCTL:.0f}th. "
            "The score is the share of growing seasons in the period with at least one onset."
        ),
        "caveat": (
            "Monthly means smooth out the fastest events, so this undercounts flash droughts "
            "compared with daily or weekly data. It describes how often they happened, not a "
            "forecast. " + climatology_note
        ).strip(),
        "references": REFERENCES,
    }
