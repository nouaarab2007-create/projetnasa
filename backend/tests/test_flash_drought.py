"""Flash-drought onset detection (monthly root-zone soil moisture)."""

import math
import random

import pytest

from app.science.flash_drought import active_months_from_tmax, detect_flash_droughts

APR_OCT = list(range(4, 11))


def _record(collapses: dict[int, tuple[int, int]], years=range(1981, 2025)):
    """Smooth seasonal soil wetness with year-to-year noise; ``collapses`` maps
    year -> (wet month, dry month) where the soil goes from wet to very dry."""
    # Soil moisture is persistent: AR(1) anomalies with month-to-month correlation 0.9.
    rng = random.Random(42)
    anomaly = 0.0
    points = []
    for y in years:
        for m in range(1, 13):
            anomaly = 0.9 * anomaly + rng.gauss(0, 0.012)
            noise = anomaly
            value = 0.55 + 0.05 * math.cos((m - 4) / 12 * 2 * math.pi) + noise
            if y in collapses:
                wet, dry = collapses[y]
                if m == wet:
                    value += 0.08
                if m >= dry:
                    value -= 0.20
            points.append({"date": f"{y}-{m:02d}", "value": round(value, 4)})
    return points


def test_inserted_collapses_are_detected_on_top_of_background():
    background = set(detect_flash_droughts(_record({}), 1981, 2024, active_months=APR_OCT)["eventYears"])
    inserted = {1995: (5, 7), 2009: (6, 7), 2012: (5, 7)}
    assert not background & set(inserted)
    res = detect_flash_droughts(_record(inserted), 1981, 2024, active_months=APR_OCT)
    assert set(inserted) <= set(res["eventYears"])
    onset = [e for e in res["events"] if e["year"] == 2012][0]
    assert onset["toPercentile"] <= 20 and onset["fromPercentile"] >= 40 and onset["weeks"] in (4, 8)
    assert res["seasonsAnalysed"] == 44
    assert res["score"] == round(100 * len(res["eventYears"]) / 44)


def test_score_counts_only_the_selected_period():
    pts = _record({2012: (5, 7)})
    before = detect_flash_droughts(pts, 2000, 2011)
    with_2012 = detect_flash_droughts(pts, 2000, 2012)
    assert 2012 not in before["eventYears"] and 2012 in with_2012["eventYears"]
    assert with_2012["seasonsAnalysed"] == before["seasonsAnalysed"] + 1
    assert 2012 in before["baselineEventYears"]  # the full-record context still shows it


def test_slow_decline_is_not_a_flash_drought():
    # Gradual drying over many years lowers percentiles but never collapses in 1-2 months.
    pts = []
    for y in range(1981, 2025):
        for m in range(1, 13):
            pts.append({"date": f"{y}-{m:02d}", "value": 0.7 - 0.006 * (y - 1981) + 0.0005 * m})
    res = detect_flash_droughts(pts, 1981, 2024)
    assert res["events"] == []


def test_needs_enough_years():
    with pytest.raises(ValueError):
        detect_flash_droughts(_record({}, years=range(2015, 2020)), 2015, 2019)


def test_active_months_come_from_temperature_data() -> None:
    # Normal daily maximum: cold Dec-Feb (below 10 °C), warm otherwise.
    tmax = [{"date": f"{y}-{m:02d}", "value": 4.0 if m in (12, 1, 2) else 20.0} for y in range(1990, 2000) for m in range(1, 13)]
    assert active_months_from_tmax(tmax) == list(range(3, 12))
    warm = [{"date": f"{y}-{m:02d}", "value": 18.0} for y in range(1990, 2000) for m in range(1, 13)]
    assert active_months_from_tmax(warm) == list(range(1, 13))  # mild winters: all year
