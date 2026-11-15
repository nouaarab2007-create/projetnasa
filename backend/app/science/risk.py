"""Five-year phenomenon risk screening score.

The score is a transparent statistical screening indicator, *not* a calibrated
probability: it combines the standardized adverse trend (62 %), the recent
versus baseline shift (38 %), statistical evidence and record completeness.
"""

from __future__ import annotations

import math
from typing import Any, TypedDict

from app.science.statistics import js_round
from app.science.transform import Point, mean


class RiskProfile(TypedDict):
    phenomenon: str
    adverseDirection: int  # 1 = increase is adverse, -1 = decrease is adverse, 0 = both
    interpretation: str


RISK_PROFILES: dict[str, RiskProfile] = {
    "T2M": {
        "phenomenon": "Warming and heat stress",
        "adverseDirection": 1,
        "interpretation": "Higher mean air temperatures increase the screening signal.",
    },
    "T2M_MAX": {
        "phenomenon": "Extreme heat exposure",
        "adverseDirection": 1,
        "interpretation": "Rising maximum temperatures increase the screening signal.",
    },
    "T2M_MIN": {
        "phenomenon": "Night-time warming",
        "adverseDirection": 1,
        "interpretation": "Rising minimum temperatures increase the screening signal.",
    },
    "TS": {
        "phenomenon": "Surface heat stress",
        "adverseDirection": 1,
        "interpretation": "Rising land or ocean skin temperature increases the screening signal.",
    },
    "PRECTOTCORR": {
        "phenomenon": "Drying and rainfall deficit",
        "adverseDirection": -1,
        "interpretation": "Declining precipitation increases the drying screening signal.",
    },
    "RH2M": {
        "phenomenon": "Atmospheric dryness",
        "adverseDirection": -1,
        "interpretation": "Declining relative humidity increases the dryness screening signal.",
    },
    "QV2M": {
        "phenomenon": "Atmospheric moisture deficit",
        "adverseDirection": -1,
        "interpretation": "Declining specific humidity increases the moisture-deficit signal.",
    },
    "GWETROOT": {
        "phenomenon": "Root-zone drought stress",
        "adverseDirection": -1,
        "interpretation": "Declining root-zone wetness increases the drought-stress signal.",
    },
    "ALLSKY_SFC_SW_DWN": {
        "phenomenon": "Solar and evaporative stress",
        "adverseDirection": 1,
        "interpretation": "Increasing surface radiation raises the evaporative-stress signal.",
    },
    "CLOUD_AMT": {
        "phenomenon": "Reduced cloud cover",
        "adverseDirection": -1,
        "interpretation": "Declining cloud amount raises the reduced-cloud-cover signal.",
    },
    "WS10M": {
        "phenomenon": "Elevated wind exposure",
        "adverseDirection": 1,
        "interpretation": "Increasing wind speed raises the wind-exposure signal.",
    },
    "PS": {
        "phenomenon": "Surface pressure regime shift",
        "adverseDirection": 0,
        "interpretation": "A large pressure trend in either direction raises the regime-shift signal.",
    },
}

RISK_PROFILES.update(
    {
        "MOD13Q1_NDVI": {
            "phenomenon": "Vegetation browning",
            "adverseDirection": -1,
            "interpretation": "Declining greenness (NDVI) increases the vegetation-stress signal.",
        },
        "MOD13Q1_EVI": {
            "phenomenon": "Vegetation browning",
            "adverseDirection": -1,
            "interpretation": "Declining EVI increases the vegetation-stress signal.",
        },
        "MOD15A2H_LAI": {
            "phenomenon": "Canopy loss",
            "adverseDirection": -1,
            "interpretation": "Declining leaf area increases the canopy-loss signal.",
        },
        "MOD11A2_LST_DAY": {
            "phenomenon": "Land surface heat stress",
            "adverseDirection": 1,
            "interpretation": "Rising daytime land temperature increases the surface-heat signal.",
        },
        "GLDAS_SOILM_0_10": {
            "phenomenon": "Surface soil drying",
            "adverseDirection": -1,
            "interpretation": "Declining topsoil moisture increases the agricultural-drought signal.",
        },
        "GLDAS_ROOT_ZONE_SM": {
            "phenomenon": "Root-zone drought stress",
            "adverseDirection": -1,
            "interpretation": "Declining root-zone moisture increases the drought-stress signal.",
        },
        "GLDAS_EVAP": {
            "phenomenon": "Water-balance shift",
            "adverseDirection": 0,
            "interpretation": "A large evapotranspiration trend in either direction raises the signal.",
        },
        "GLDAS_SWE": {
            "phenomenon": "Snowpack loss",
            "adverseDirection": -1,
            "interpretation": "Declining snow water equivalent increases the snowpack-loss signal.",
        },
        "GPM_IMERG_PRECIP": {
            "phenomenon": "Drying and rainfall deficit",
            "adverseDirection": -1,
            "interpretation": "Declining satellite precipitation increases the drying signal.",
        },
        "NOAA_TAVG": {
            "phenomenon": "Warming and heat stress",
            "adverseDirection": 1,
            "interpretation": "Rising station temperatures increase the screening signal.",
        },
        "NOAA_TMAX": {
            "phenomenon": "Extreme heat exposure",
            "adverseDirection": 1,
            "interpretation": "Rising station maximum temperatures increase the screening signal.",
        },
        "NOAA_TMIN": {
            "phenomenon": "Night-time warming",
            "adverseDirection": 1,
            "interpretation": "Rising station minimum temperatures increase the screening signal.",
        },
        "NOAA_PRCP": {
            "phenomenon": "Drying and rainfall deficit",
            "adverseDirection": -1,
            "interpretation": "Declining gauge precipitation increases the drying signal.",
        },
        "SWOT_WSE": {
            "phenomenon": "Water-level regime shift",
            "adverseDirection": 0,
            "interpretation": "A falling (drought) or rising (flood) water level both raise the signal.",
        },
    }
)

DEFAULT_PROFILE: RiskProfile = {
    "phenomenon": "Environmental trend shift",
    "adverseDirection": 0,
    "interpretation": "A large trend in either direction raises the screening signal.",
}

METHOD = (
    "Screening score combining standardized adverse trend (62%), recent-versus-baseline shift "
    "(38%), statistical evidence, and data completeness."
)
DISCLAIMER = (
    "This is a statistical screening indicator, not a calibrated probability that a hazardous "
    "event will occur. It does not include exposure, vulnerability, local impacts, or causal drivers."
)


def _standard_deviation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    average = mean(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / (len(values) - 1))


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return min(maximum, max(minimum, value))


def _level(score: int) -> str:
    if score < 25:
        return "Low"
    if score < 50:
        return "Moderate"
    if score < 75:
        return "High"
    return "Very high"


def assess_risk(
    points: list[Point],
    parameter: str,
    analysis: dict[str, Any],
    horizon_years: int = 5,
) -> dict[str, Any]:
    """Compute the variable-specific screening score for a series."""
    values = [point["value"] for point in points if math.isfinite(point["value"])]
    profile = RISK_PROFILES.get(parameter, DEFAULT_PROFILE)
    deviation = _standard_deviation(values) or 1.0
    direction = profile["adverseDirection"]
    horizon = max(1, min(30, int(horizon_years)))

    def directed(value: float) -> float:
        return abs(value) if direction == 0 else direction * value

    recent_count = max(3, min(len(values), js_round(len(values) * 0.2)))
    recent_mean = mean(values[-recent_count:])
    baseline_mean = mean(values[:recent_count])
    trend_signal = directed(analysis["trendPerDecade"]) / deviation
    recent_signal = directed(recent_mean - baseline_mean) / deviation
    trend_component = _clamp(max(0.0, trend_signal) / 1.5)
    recent_component = _clamp(max(0.0, recent_signal) / 1.5)
    evidence_confidence = 1 - _clamp(
        (analysis["regression"]["pValue"] + analysis["mannKendall"]["pValue"]) / 2
    )
    completeness = _clamp(len(values) / 20)
    combined_signal = 0.62 * trend_component + 0.38 * recent_component
    horizon_scale = 1.0 if horizon == 5 else _clamp(0.85 + 0.03 * horizon, 0.75, 1.35)
    raw_score = 100 * combined_signal * (0.7 + 0.3 * evidence_confidence) * completeness * horizon_scale
    score = min(100, max(0, js_round(raw_score)))
    uncertainty = js_round(8 + 18 * (1 - evidence_confidence) + 10 * (1 - completeness) + max(0, horizon - 5) * 0.6)
    if "slopePerYear" in analysis:
        projected_change = analysis["slopePerYear"] * horizon
    else:  # slope expressed per observation
        monthly = any(len(point["date"]) >= 7 for point in points)
        projected_change = analysis["regression"]["slope"] * ((12 * horizon) if monthly else horizon)

    return {
        "phenomenon": profile["phenomenon"],
        "score": score,
        "level": _level(score),
        "uncertainty": uncertainty,
        "horizonYears": horizon,
        "projectedChange": projected_change,
        "trendComponent": js_round(trend_component * 100),
        "recentComponent": js_round(recent_component * 100),
        "evidenceConfidence": js_round(evidence_confidence * 100),
        "interpretation": profile["interpretation"],
        "method": METHOD,
        "disclaimer": DISCLAIMER,
    }
