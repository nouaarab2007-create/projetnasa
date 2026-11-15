"""Temporal processing modes applied to NASA POWER monthly series."""

from __future__ import annotations

from typing import Literal, TypedDict

Mode = Literal["raw", "annual", "anomaly"]
MODES: tuple[str, ...] = ("raw", "annual", "anomaly")


class Point(TypedDict):
    date: str  # "YYYY-MM" (monthly) or "YYYY" (annual)
    value: float


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def ensure_enough_points(points: list[Point], mode: str) -> list[Point]:
    """Fail with an actionable message when a processing mode leaves too few points."""
    if len(points) < 3:
        from app.core.errors import DomainError  # local import keeps this module dependency-free

        if mode == "annual":
            raise DomainError(
                "Annual averages need at least three years with most months covered. Choose a longer "
                "period, or 'Monthly anomalies' / 'Raw monthly values' for short records such as SWOT."
            )
        raise DomainError("At least three observations are required.")
    return points


def transform(points: list[Point], mode: str) -> list[Point]:
    """Convert a monthly series according to the analysis mode.

    - ``raw``: monthly values unchanged.
    - ``annual``: one mean value per calendar year.
    - ``anomaly``: each month minus that calendar month's mean (climatology).
    """
    if mode == "raw":
        return points

    if mode == "annual":
        years: dict[str, list[float]] = {}
        for point in points:
            years.setdefault(point["date"][:4], []).append(point["value"])
        # A year with many missing months (e.g. the current, unfinished year or a gap in
        # a satellite or station record) would bias the annual mean towards the
        # months it has. Keep years with at least 75 % of the best-covered year's months.
        fullest = max((len(values) for values in years.values()), default=0)
        return [
            {"date": year, "value": mean(values)}
            for year, values in years.items()
            if len(values) >= 0.75 * fullest
        ]

    climatology: dict[str, list[float]] = {}
    for point in points:
        climatology.setdefault(point["date"][5:7], []).append(point["value"])
    normals = {month: mean(values) for month, values in climatology.items()}
    return [
        {**point, "value": point["value"] - normals.get(point["date"][5:7], 0.0)}
        for point in points
    ]
