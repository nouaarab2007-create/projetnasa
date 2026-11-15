"""Unit tests for the statistical engine and risk screening (port of tests/statistics.test.ts)."""

from __future__ import annotations

import math

import pytest

from app.core.errors import DomainError
from app.science.risk import assess_risk
from app.science.statistics import analyze, linear_regression, mann_kendall, sens_slope
from app.science.transform import transform


def test_fits_perfect_increasing_ols_trend() -> None:
    result = linear_regression([1, 3, 5, 7, 9])
    assert result["slope"] == pytest.approx(2.0)
    assert result["intercept"] == pytest.approx(1.0)
    assert result["rSquared"] == pytest.approx(1.0)
    assert result["pValue"] == 0.0
    assert math.isinf(result["tStatistic"])


def test_detects_monotonic_mann_kendall_trend() -> None:
    result = mann_kendall([1, 2, 3, 4, 5, 6, 7, 8])
    assert result["s"] == 28
    assert result["tau"] == pytest.approx(1.0)
    assert result["pValue"] < 0.01
    assert result["significant"] is True


def test_corrects_mann_kendall_variance_for_ties() -> None:
    result = mann_kendall([1, 1, 2, 2, 3])
    assert result["variance"] < 16.6667
    assert result["s"] == 8


def test_computes_robust_sen_slope() -> None:
    assert sens_slope([1, 3, 5, 7, 100]) == pytest.approx(2.0)


def test_aggregates_annual_values_and_calculates_monthly_anomalies() -> None:
    points = [
        {"date": "2020-01", "value": 10.0},
        {"date": "2020-02", "value": 20.0},
        {"date": "2021-01", "value": 14.0},
        {"date": "2021-02", "value": 18.0},
    ]
    assert transform(points, "annual") == [
        {"date": "2020", "value": 15.0},
        {"date": "2021", "value": 16.0},
    ]
    assert [point["value"] for point in transform(points, "anomaly")] == [-2.0, 1.0, 2.0, -1.0]


def test_returns_nuanced_verdict_when_neither_test_is_significant() -> None:
    points = [{"date": str(2000 + index), "value": float(value)} for index, value in enumerate([1, 2, 1, 2, 1, 2])]
    result = analyze(points)
    assert result["verdict"] == "No statistically significant trend detected"


def test_produces_bounded_heat_risk_screening_score_for_strong_warming_trend() -> None:
    points = [{"date": str(2000 + index), "value": 10 + index * 0.3} for index in range(25)]
    analysis = analyze(points, "T2M")
    assert 50 < analysis["risk"]["score"] <= 100
    assert analysis["risk"]["phenomenon"] == "Warming and heat stress"
    assert analysis["risk"]["horizonYears"] == 5


def test_does_not_turn_beneficial_precipitation_increase_into_drought_risk() -> None:
    points = [{"date": str(2000 + index), "value": 2 + index * 0.1} for index in range(25)]
    values = [point["value"] for point in points]
    regression = linear_regression(values)
    mk = mann_kendall(values)
    risk = assess_risk(
        points,
        "PRECTOTCORR",
        {
            "regression": regression,
            "mannKendall": mk,
            "trendPerDecade": regression["slope"] * 10,
        },
    )
    assert risk["score"] == 0


def test_rejects_too_few_observations() -> None:
    with pytest.raises(DomainError, match="At least three observations"):
        linear_regression([1.0, 2.0])
    with pytest.raises(DomainError, match="At least three observations"):
        mann_kendall([1.0, 2.0])
