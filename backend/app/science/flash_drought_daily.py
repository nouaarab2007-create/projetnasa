"""Flash-drought detection from daily root-zone soil moisture (5-day "pentad" means).

Standard definition, applied the same way everywhere (Ford & Labosier 2017;
Otkin et al. 2018; Christian et al. 2019 use the same idea with other indicators):

1. Daily soil moisture is averaged into 73 pentads per year (Feb 29 joins Feb 28).
2. Each pentad is ranked against the same time of year in every year of the record
   (the pentad and its two neighbours, so each climatology has ~3 x N values).
3. **Onset** = a pentad at or below the 20th percentile that was at or above the
   40th percentile at most 4 pentads (20 days) earlier.
4. **Persistence** = it stays at or below the 20th percentile for at least 4 pentads
   (20 days); shorter dips are noise, not drought (Otkin et al. 2018: a flash drought
   must last long enough to harm vegetation).
5. One event lasts until the soil moisture rises above the 20th percentile again.

Nothing is tied to a region or a calendar. The active season comes from the data:
* if daily maximum temperature is given, pentads whose normal maximum is below
  10 °C are skipped (frozen or dormant ground, no crop water demand);
* pentads whose soil moisture hardly varies from year to year (deserts, permanently
  saturated soils) are skipped, because percentiles mean nothing there.

Score = share of complete years in the chosen period with at least one flash drought.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

PENTADS = 73
WET_PCTL = 40.0
DRY_PCTL = 20.0
MAX_ONSET_PENTADS = 4  # <= 20 days from wet to dry
MIN_DRY_PENTADS = 4  # stays dry >= 20 days
COLD_TMAX = 10.0  # °C
MIN_RELATIVE_SPREAD = 0.02  # (p80 - p20) / median below this = no meaningful variability
MIN_YEARS = 10
YEAR_COMPLETENESS = 0.9

REFERENCES = [
    "Ford, T. W. & Labosier, C. F. (2017). Meteorological conditions associated with the onset of flash "
    "drought in the eastern United States. Agric. For. Meteorol. 247, 414-423.",
    "Otkin, J. A. et al. (2018). Flash droughts: a review and assessment of the challenges imposed by "
    "rapid-onset droughts in the United States. Bull. Amer. Meteor. Soc. 99, 911-919.",
    "Christian, J. I. et al. (2019). A methodology for flash drought identification. J. Hydrometeorol. 20, 833-846.",
]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def level_for(score: float) -> str:
    if score >= 35:
        return "Very high"
    if score >= 20:
        return "High"
    if score >= 10:
        return "Moderate"
    return "Low"


def pentad_of(day: date) -> int:
    """0..72; Feb 29 shares Feb 28's pentad."""
    doy = day.timetuple().tm_yday
    leap = day.year % 4 == 0 and (day.year % 100 != 0 or day.year % 400 == 0)
    if leap and doy >= 60:
        doy -= 1
    return min(PENTADS - 1, (doy - 1) // 5)


def pentad_start(year: int, pentad: int) -> date:
    return date(year, 1, 1) + timedelta(days=5 * pentad)


def _pentad_means(samples: list[tuple[str, float]]) -> dict[tuple[int, int], float]:
    sums: dict[tuple[int, int], list[float]] = defaultdict(list)
    for day_text, value in samples:
        if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
            continue
        try:
            day = date.fromisoformat(str(day_text)[:10])
        except ValueError:
            continue
        sums[(day.year, pentad_of(day))].append(float(value))
    return {key: sum(v) / len(v) for key, v in sums.items() if len(v) >= 3}


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * pct / 100.0
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _rank(reference: list[float], value: float) -> float:
    below = sum(1 for v in reference if v < value)
    equal = sum(1 for v in reference if v == value)
    return 100.0 * (below + 0.5 * equal + 0.5) / (len(reference) + 1)


def _season_text(active: list[bool]) -> str:
    months = sorted({pentad_start(2001, p).month for p in range(PENTADS) if active[p]})
    if not months:
        return "none"
    if len(months) == 12:
        return "all year"
    # Describe the active months as ranges, wrapping over the new year when needed.
    ranges, run = [], [months[0]]
    for m in months[1:]:
        if m == run[-1] + 1:
            run.append(m)
        else:
            ranges.append(run)
            run = [m]
    ranges.append(run)
    if len(ranges) > 1 and ranges[0][0] == 1 and ranges[-1][-1] == 12:
        ranges[0] = ranges.pop() + ranges[0]
    return ", ".join(f"{MONTHS[r[0] - 1]}-{MONTHS[r[-1] - 1]}" if len(r) > 1 else MONTHS[r[0] - 1] for r in ranges)


def detect_flash_droughts_daily(
    soil: list[tuple[str, float]],
    start: int,
    end: int,
    *,
    tmax: list[tuple[str, float]] | None = None,
) -> dict[str, Any]:
    series = _pentad_means(soil)
    counts: dict[int, int] = defaultdict(int)
    for (year, _) in series:
        counts[year] += 1
    years = sorted(y for y, n in counts.items() if n >= YEAR_COMPLETENESS * PENTADS)
    if len(years) < MIN_YEARS:
        raise ValueError(f"Flash-drought detection needs at least {MIN_YEARS} complete years of daily soil moisture.")

    # Climatology of each pentad: that pentad and its neighbours in every complete year.
    reference: list[list[float]] = []
    for p in range(PENTADS):
        window = [(p + k) % PENTADS for k in (-1, 0, 1)]
        reference.append([series[(y, q)] for y in years for q in window if (y, q) in series])

    # Active pentads, from the data.
    active = [True] * PENTADS
    for p in range(PENTADS):
        ref = reference[p]
        median = _percentile(ref, 50)
        spread = _percentile(ref, 80) - _percentile(ref, 20)
        if not ref or abs(median) < 1e-9 or spread / abs(median) < MIN_RELATIVE_SPREAD:
            active[p] = False
    cold_note = ""
    if tmax:
        temps = _pentad_means(tmax)
        normal_tmax = defaultdict(list)
        for (_, p), value in temps.items():
            normal_tmax[p].append(value)
        for p in range(PENTADS):
            if normal_tmax[p] and sum(normal_tmax[p]) / len(normal_tmax[p]) < COLD_TMAX:
                active[p] = False
        if not all(active):
            cold_note = f" Pentads with a normal daily maximum below {COLD_TMAX:.0f} °C are skipped."
    if not any(active):
        raise ValueError("Soil moisture here hardly varies from year to year, so flash droughts cannot be measured.")

    # Percentile of every pentad, as one continuous sequence.
    timeline: list[tuple[int, int, float | None]] = []
    for year in range(years[0], years[-1] + 1):
        for p in range(PENTADS):
            value = series.get((year, p))
            timeline.append((year, p, None if value is None else _rank(reference[p], value)))

    events: list[dict[str, Any]] = []
    index = 0
    while index < len(timeline):
        year, p, pct = timeline[index]
        if pct is None or pct > DRY_PCTL or not active[p]:
            index += 1
            continue
        wet_at = None
        for back in range(1, MAX_ONSET_PENTADS + 1):
            if index - back >= 0:
                prev = timeline[index - back][2]
                if prev is not None and prev >= WET_PCTL:
                    wet_at = back
                    break
        following = [timeline[index + k][2] for k in range(MIN_DRY_PENTADS) if index + k < len(timeline)]
        persists = len(following) == MIN_DRY_PENTADS and all(v is not None and v <= DRY_PCTL for v in following)
        if wet_at is None or not persists:
            index += 1
            continue
        length = 0
        while index + length < len(timeline):
            value = timeline[index + length][2]
            if value is None or value > DRY_PCTL:
                break
            length += 1
        onset = pentad_start(year, p)
        events.append(
            {
                "year": year,
                "month": onset.isoformat()[:7],
                "start": onset.isoformat(),
                "collapseDays": 5 * wet_at,
                "durationDays": 5 * length,
                "fromPercentile": round(timeline[index - wet_at][2], 1),
                "toPercentile": round(pct, 1),
                "label": f"{onset.day} {MONTHS[onset.month - 1]} {year} (dry in {5 * wet_at} days, lasted {5 * length})",
            }
        )
        index += length  # one event until the soil recovers above the 20th percentile

    window = [y for y in years if start <= y <= end]
    if not window:
        raise ValueError(f"No complete year of daily soil moisture between {start} and {end}.")
    event_years = sorted({e["year"] for e in events if e["year"] in window})
    all_event_years = sorted({e["year"] for e in events if e["year"] in years})
    score = round(100 * len(event_years) / len(window))
    season = _season_text(active)
    return {
        "phenomenon": "Flash drought",
        "score": score,
        "level": level_for(score),
        "seasonsAnalysed": len(window),
        "seasonsWithEvents": len(event_years),
        "eventYears": event_years,
        "events": [e for e in events if e["year"] in window],
        "baselineScore": round(100 * len(all_event_years) / len(years)),
        "baselinePeriod": f"{years[0]}-{years[-1]}",
        "baselineEventYears": all_event_years,
        "activeSeason": season,
        "resolution": "daily (5-day means)",
        "method": (
            "Daily root-zone soil moisture is averaged over 5 days and ranked against the same time of year "
            f"in {years[0]}-{years[-1]}. A flash drought starts when it falls from at or above the "
            f"{WET_PCTL:.0f}th to at or below the {DRY_PCTL:.0f}th percentile within "
            f"{5 * MAX_ONSET_PENTADS} days and stays there for at least {5 * MIN_DRY_PENTADS} days "
            f"(Ford & Labosier 2017). Active season found in the data here: {season}.{cold_note}"
        ),
        "caveat": (
            "Gridded soil moisture describes a 50 km cell, not one field. It shows how often flash droughts "
            "happened, not a forecast."
        ),
        "references": REFERENCES,
    }
