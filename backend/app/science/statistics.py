"""Trend statistics: OLS regression, Mann–Kendall test and Sen's slope.

Pure-Python port of the original TypeScript engine. Formulas, approximations
and thresholds are kept identical so results match the reference design.
"""

from __future__ import annotations

import math
from typing import Any

from app.core.errors import DomainError
from app.science.transform import Point, mean


def js_round(value: float) -> int:
    """Round half up, like JavaScript's ``Math.round`` (Python rounds half to even)."""
    return math.floor(value + 0.5)


def _sign(value: float) -> int:
    return (value > 0) - (value < 0)


# --- Special functions -----------------------------------------------------

_LANCZOS = (
    676.5203681218851,
    -1259.1392167224028,
    771.3234287776531,
    -176.6150291621406,
    12.507343278686905,
    -0.13857109526572012,
    9.984369578019572e-6,
    1.5056327351493116e-7,
)


def log_gamma(value: float) -> float:
    """Natural log of the gamma function (Lanczos approximation, g = 7)."""
    if value < 0.5:
        return math.log(math.pi) - math.log(math.sin(math.pi * value)) - log_gamma(1 - value)
    x = 0.9999999999998099
    z = value - 1
    for index, coefficient in enumerate(_LANCZOS):
        x += coefficient / (z + index + 1)
    t = z + len(_LANCZOS) - 0.5
    return 0.5 * math.log(2 * math.pi) + (z + 0.5) * math.log(t) - t + math.log(x)


def _beta_fraction(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    max_iterations = 200
    epsilon = 3e-12
    tiny = 1e-30
    qab = a + b
    qap = a + 1
    qam = a - 1
    c = 1.0
    d = 1 - (qab * x) / qap
    if abs(d) < tiny:
        d = tiny
    d = 1 / d
    h = d
    for m in range(1, max_iterations + 1):
        m2 = 2 * m
        aa = (m * (b - m) * x) / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1 / d
        h *= d * c
        aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < epsilon:
            break
    return h


def regularized_beta(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(
        log_gamma(a + b) - log_gamma(a) - log_gamma(b) + a * math.log(x) + b * math.log(1 - x)
    )
    if x < (a + 1) / (a + b + 2):
        return (bt * _beta_fraction(a, b, x)) / a
    return 1 - (bt * _beta_fraction(b, a, 1 - x)) / b


def student_t_p_value(t: float, degrees_freedom: float) -> float:
    """Two-sided p-value of Student's t distribution."""
    x = degrees_freedom / (degrees_freedom + t * t)
    return regularized_beta(x, degrees_freedom / 2, 0.5)


def normal_cdf(x: float) -> float:
    """Standard normal CDF (Abramowitz & Stegun 7.1.26 erf approximation)."""
    sign = -1 if x < 0 else 1
    z = abs(x) / math.sqrt(2)
    t = 1 / (1 + 0.3275911 * z)
    erf = sign * (
        1
        - (((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t)
        * math.exp(-z * z)
    )
    return 0.5 * (1 + erf)


# --- Trend estimators ------------------------------------------------------


def linear_regression(values: list[float], x: list[float] | None = None) -> dict[str, Any]:
    """Ordinary least squares against ``x`` (the observation index when ``x`` is omitted)."""
    if len(values) < 3:
        raise DomainError("At least three observations are required.")
    if x is None:
        x = list(range(len(values)))
    x_mean = mean(x)
    y_mean = mean(values)
    sxx = sum((value - x_mean) ** 2 for value in x)
    sxy = sum((value - x_mean) * (values[index] - y_mean) for index, value in enumerate(x))
    slope = sxy / sxx
    intercept = y_mean - slope * x_mean
    fitted = [intercept + slope * value for value in x]
    residual_ss = sum((value - fitted[index]) ** 2 for index, value in enumerate(values))
    total_ss = sum((value - y_mean) ** 2 for value in values)
    degrees_freedom = len(values) - 2
    standard_error = math.sqrt(residual_ss / degrees_freedom / sxx)
    # A perfect fit has no residual error: the reference engine reports +Infinity.
    t_statistic = math.inf if standard_error == 0 else slope / standard_error
    p_value = student_t_p_value(abs(t_statistic), degrees_freedom) if math.isfinite(t_statistic) else 0.0
    critical = 1.96 if degrees_freedom >= 30 else 2.228 if degrees_freedom >= 10 else 2.776
    return {
        "slope": slope,
        "intercept": intercept,
        "standardError": standard_error,
        "tStatistic": t_statistic,
        "degreesFreedom": degrees_freedom,
        "pValue": p_value,
        "confidenceInterval": [slope - critical * standard_error, slope + critical * standard_error],
        "rSquared": 1.0 if total_ss == 0 else 1 - residual_ss / total_ss,
        "fitted": fitted,
    }


def mann_kendall(values: list[float]) -> dict[str, Any]:
    """Mann–Kendall monotonic trend test with tie and continuity corrections."""
    n = len(values)
    if n < 3:
        raise DomainError("At least three observations are required.")
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += _sign(values[j] - values[i])
    ties: dict[float, int] = {}
    for value in values:
        ties[value] = ties.get(value, 0) + 1
    tie_correction = sum(
        count * (count - 1) * (2 * count + 5) for count in ties.values() if count > 1
    )
    variance = (n * (n - 1) * (2 * n + 5) - tie_correction) / 18
    if variance == 0:
        z = 0.0
    elif s > 0:
        z = (s - 1) / math.sqrt(variance)
    elif s < 0:
        z = (s + 1) / math.sqrt(variance)
    else:
        z = 0.0
    p_value = 2 * (1 - normal_cdf(abs(z)))
    tau = s / (0.5 * n * (n - 1))
    return {
        "s": s,
        "variance": variance,
        "z": z,
        "pValue": p_value,
        "tau": tau,
        "significant": p_value < 0.05,
    }


def sens_slope(values: list[float], x: list[float] | None = None) -> float:
    """Median of all pairwise slopes (Theil–Sen estimator) against ``x`` (index by default)."""
    if x is None:
        x = list(range(len(values)))
    slopes = sorted(
        (values[j] - values[i]) / (x[j] - x[i])
        for i in range(len(values) - 1)
        for j in range(i + 1, len(values))
        if x[j] != x[i]
    )
    middle = len(slopes) // 2
    if len(slopes) % 2:
        return slopes[middle]
    return (slopes[middle - 1] + slopes[middle]) / 2


def _is_monthly(points: list[Point]) -> bool:
    return any(len(point["date"]) >= 7 for point in points)


def time_in_years(date: str) -> float:
    """Decimal year of a ``YYYY`` or ``YYYY-MM`` label (months placed at their start)."""
    year = float(date[:4])
    if len(date) >= 7:
        return year + (int(date[5:7]) - 1) / 12
    return year


def analyze(
    points: list[Point],
    parameter: str = "T2M",
    *,
    alpha: float = 0.05,
    horizon_years: int = 5,
) -> dict[str, Any]:
    """Run the full statistical workflow and the risk screening on a series."""
    from app.science.risk import assess_risk  # local import avoids a cycle

    valid = [point for point in points if math.isfinite(point["value"])]
    values = [point["value"] for point in valid]
    # Regress on real time (decimal years), not on the row index, so missing months or
    # years keep their true spacing. For gap-free series this equals the index-based
    # result rescaled to "per year" (index slope x 12 for monthly data).
    times = [time_in_years(point["date"]) for point in valid]
    regression = linear_regression(values, times)
    mk = mann_kendall(values)
    mk["significant"] = mk["pValue"] < alpha
    sen = sens_slope(values, times)
    factor = 10  # slopes are per year -> per decade
    slope = regression["slope"]
    direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
    if regression["pValue"] < alpha and mk["significant"]:
        verdict = f"Significant {direction} trend"
    elif regression["pValue"] < alpha or mk["significant"]:
        verdict = "Mixed statistical evidence"
    else:
        verdict = "No statistically significant trend detected"
    core = {
        "regression": regression,
        "mannKendall": mk,
        "senSlope": sen,
        "trendPerDecade": slope * factor,
        "senPerDecade": sen * factor,
        "slopePerYear": slope,
        "slopeUnit": "per year",
        "alpha": alpha,
        "verdict": verdict,
        "validObservations": len(values),
    }
    return {**core, "risk": assess_risk(points, parameter, core, horizon_years=horizon_years)}
