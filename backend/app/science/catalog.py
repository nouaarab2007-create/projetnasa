"""Scientific catalogue: variables, predefined regions and data sources.

This module is the single source of truth for the catalogue; the frontend
loads it through ``/api/variables``, ``/api/regions`` and ``/api/sources``
(and ``scripts/generate_site.py`` embeds it into the static bundle).

Every selectable variable names the ``provider`` connector that retrieves it
(see ``app/services/datasets.py``), the first year it can be requested
(``minYear``) and how it is accessed (``access``). Variables with
``featureInput`` need a feature identifier (a SWOT river reach or lake ID)
instead of coordinates.
"""

from __future__ import annotations

from typing import Any

_POWER = {"provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account"}
_MODIS = {
    "provider": "modis",
    "source": "NASA MODIS (ORNL DAAC)",
    "minYear": 2000,
    "access": "Open, no account",
}
_GLDAS = {
    "provider": "giovanni",
    "source": "NASA GLDAS (Giovanni)",
    "minYear": 2000,
    "access": "Earthdata token on the server (EARTHDATA_TOKEN)",
}
_GIOVANNI = {
    "provider": "giovanni",
    "source": "NASA GPM IMERG (Giovanni)",
    "minYear": 2001,
    "access": "Earthdata token on the server (EARTHDATA_TOKEN)",
}
_NOAA = {
    "provider": "noaa",
    "source": "NOAA NCEI stations",
    "minYear": 1900,
    "access": "Open, no account (nearest station with data)",
}
_SWOT = {
    "provider": "swot",
    "source": "NASA SWOT (Hydrocron)",
    "minYear": 2023,
    "access": "Open, no account; needs a SWOT river reach or lake ID",
    "featureInput": True,
}

VARIABLES: list[dict[str, Any]] = [
    # --- NASA POWER -------------------------------------------------------
    {
        "code": "T2M",
        "name": "Air temperature",
        "unit": "°C",
        "category": "Temperature",
        "definition": "Mean air temperature at 2 metres above the surface.",
        "why": "Tracks warming and cooling patterns that affect ecosystems, health, and energy demand.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "T2M_MAX",
        "name": "Maximum air temperature",
        "unit": "°C",
        "category": "Temperature",
        "definition": "Maximum air temperature at 2 metres.",
        "why": "Reveals changes in heat extremes.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "T2M_MIN",
        "name": "Minimum air temperature",
        "unit": "°C",
        "category": "Temperature",
        "definition": "Minimum air temperature at 2 metres.",
        "why": "Shows changes in overnight and cold-season conditions.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "TS",
        "name": "Earth skin temperature",
        "unit": "°C",
        "category": "Temperature",
        "definition": "Radiative temperature of the land or ocean surface.",
        "why": "Connects surface energy balance with land and water conditions.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "PRECTOTCORR",
        "name": "Precipitation",
        "unit": "mm/day",
        "category": "Water & humidity",
        "definition": "Bias-corrected total precipitation rate.",
        "why": "Supports drought, flood, and water-availability investigations.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "RH2M",
        "name": "Relative humidity",
        "unit": "%",
        "category": "Water & humidity",
        "definition": "Relative humidity at 2 metres.",
        "why": "Describes atmospheric moisture and heat-stress conditions.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "QV2M",
        "name": "Specific humidity",
        "unit": "g/kg",
        "category": "Water & humidity",
        "definition": "Mass of water vapour per mass of moist air at 2 metres.",
        "why": "Measures absolute atmospheric moisture.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "GWETROOT",
        "name": "Root-zone soil wetness",
        "unit": "fraction",
        "category": "Water & humidity",
        "definition": "Modelled root-zone soil wetness fraction.",
        "why": "Indicates water available to vegetation.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "ALLSKY_SFC_SW_DWN",
        "name": "Solar radiation",
        "unit": "kWh/m²/day",
        "category": "Radiation & clouds",
        "definition": "All-sky shortwave radiation reaching the surface.",
        "why": "Influences photosynthesis, evaporation, and solar resources.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "CLOUD_AMT",
        "name": "Cloud amount",
        "unit": "%",
        "category": "Radiation & clouds",
        "definition": "Fraction of sky covered by cloud.",
        "why": "Helps interpret radiation and precipitation changes.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "WS10M",
        "name": "Wind speed",
        "unit": "m/s",
        "category": "Wind & pressure",
        "definition": "Mean wind speed at 10 metres.",
        "why": "Affects evaporation, storms, and wind-energy potential.",
        **_POWER,
        "selectable": True,
    },
    {
        "code": "PS",
        "name": "Surface pressure",
        "unit": "kPa",
        "category": "Wind & pressure",
        "definition": "Atmospheric pressure at the surface.",
        "why": "Supports interpretation of circulation and weather patterns.",
        **_POWER,
        "selectable": True,
    },
    # --- MODIS land products (same products AppEEARS serves) ---------------
    {
        "code": "MOD13Q1_NDVI",
        "name": "NDVI vegetation index",
        "unit": "index",
        "category": "Vegetation",
        "definition": "Satellite vegetation greenness from MODIS Terra (MOD13Q1, 250 m, 16-day composites).",
        "why": "Can reveal vegetation stress and seasonal ecosystem change.",
        **_MODIS,
        "selectable": True,
    },
    {
        "code": "MOD13Q1_EVI",
        "name": "EVI vegetation index",
        "unit": "index",
        "category": "Vegetation",
        "definition": "Enhanced vegetation index from MODIS Terra (MOD13Q1, 250 m, 16-day composites).",
        "why": "Saturates less than NDVI over dense forest canopies.",
        **_MODIS,
        "selectable": True,
    },
    {
        "code": "MOD15A2H_LAI",
        "name": "Leaf area index",
        "unit": "m²/m²",
        "category": "Vegetation",
        "definition": "One-sided green leaf area per unit ground area (MOD15A2H, 500 m, 8-day composites).",
        "why": "Tracks canopy density, forest disturbance and recovery.",
        **_MODIS,
        "minYear": 2002,
        "selectable": True,
    },
    {
        "code": "MOD11A2_LST_DAY",
        "name": "Daytime land surface temperature",
        "unit": "°C",
        "category": "Temperature",
        "definition": "Daytime land skin temperature from MODIS Terra (MOD11A2, 1 km, 8-day composites).",
        "why": "Sensitive to urban heat, drought and land-cover change.",
        **_MODIS,
        "selectable": True,
    },
    # --- GLDAS land surface model (via Giovanni) -----------------------------
    {
        "code": "GLDAS_SOILM_0_10",
        "name": "Surface soil moisture (0–10 cm)",
        "unit": "kg/m²",
        "category": "Hydrology",
        "definition": "Water stored in the top 10 cm of soil, GLDAS-2.1 Noah model (1 kg/m² = 1 mm).",
        "why": "Early indicator of agricultural drought.",
        **_GLDAS,
        "selectable": True,
    },
    {
        "code": "GLDAS_ROOT_ZONE_SM",
        "name": "Root-zone soil moisture",
        "unit": "kg/m²",
        "category": "Hydrology",
        "definition": "Water available to plant roots, GLDAS-2.1 Noah model (1 kg/m² = 1 mm).",
        "why": "Links rainfall deficits to vegetation stress.",
        **_GLDAS,
        "selectable": True,
    },
    {
        "code": "GLDAS_EVAP",
        "name": "Evapotranspiration",
        "unit": "mm/day",
        "category": "Hydrology",
        "definition": "Water returned to the atmosphere by soil evaporation and plant transpiration (GLDAS-2.1).",
        "why": "Shows how the water and energy balance of the land is changing.",
        **_GLDAS,
        "selectable": True,
    },
    {
        "code": "GLDAS_SWE",
        "name": "Snow water equivalent",
        "unit": "kg/m²",
        "category": "Hydrology",
        "definition": "Water contained in the snowpack, GLDAS-2.1 Noah model (1 kg/m² = 1 mm).",
        "why": "Tracks snowpack loss and seasonal water supply.",
        **_GLDAS,
        "selectable": True,
    },
    # --- Giovanni: GPM IMERG satellite precipitation ------------------------
    {
        "code": "GPM_IMERG_PRECIP",
        "name": "Satellite precipitation (GPM IMERG)",
        "unit": "mm/day",
        "category": "Water & humidity",
        "definition": "Multi-satellite precipitation estimate from the GPM IMERG product, served by Giovanni.",
        "why": "Independent satellite check on rainfall trends.",
        **_GIOVANNI,
        "selectable": True,
    },
    # --- NOAA ground stations -----------------------------------------------
    {
        "code": "NOAA_TAVG",
        "name": "Station mean temperature",
        "unit": "°C",
        "category": "Temperature",
        "definition": "Monthly mean temperature measured at the nearest NOAA GHCN station with data (GSOM).",
        "why": "Ground-truth check on gridded and satellite temperature trends.",
        **_NOAA,
        "selectable": True,
    },
    {
        "code": "NOAA_TMAX",
        "name": "Station maximum temperature",
        "unit": "°C",
        "category": "Temperature",
        "definition": "Monthly mean of daily maximum temperature at the nearest NOAA station (GSOM).",
        "why": "Ground-based view of changing heat extremes.",
        **_NOAA,
        "selectable": True,
    },
    {
        "code": "NOAA_TMIN",
        "name": "Station minimum temperature",
        "unit": "°C",
        "category": "Temperature",
        "definition": "Monthly mean of daily minimum temperature at the nearest NOAA station (GSOM).",
        "why": "Ground-based view of night-time warming.",
        **_NOAA,
        "selectable": True,
    },
    {
        "code": "NOAA_PRCP",
        "name": "Station precipitation",
        "unit": "mm/month",
        "category": "Water & humidity",
        "definition": "Monthly total precipitation measured at the nearest NOAA station (GSOM).",
        "why": "Rain-gauge check on satellite and model precipitation.",
        **_NOAA,
        "selectable": True,
    },
    # --- SWOT -------------------------------------------------------------------
    {
        "code": "SWOT_WSE",
        "name": "Surface water elevation",
        "unit": "m",
        "category": "Hydrology",
        "definition": "Water-surface elevation of a river reach or lake observed by SWOT (monthly mean of passes).",
        "why": "Supports lake, river, reservoir, and flood investigations.",
        **_SWOT,
        "selectable": True,
    },
]

REGIONS: list[dict[str, Any]] = [
    {"id": "svalbard", "name": "Svalbard / Arctic", "latitude": 78.2, "longitude": 15.6, "biome": "Polar"},
    {"id": "sahel", "name": "Sahel / Niger", "latitude": 13.5, "longitude": 2.1, "biome": "Semi-arid"},
    {"id": "sahara", "name": "Sahara", "latitude": 23, "longitude": 13, "biome": "Desert"},
    {"id": "amazon", "name": "Amazon", "latitude": -3.1, "longitude": -60, "biome": "Tropical forest"},
    {"id": "himalayas", "name": "Himalayas", "latitude": 28, "longitude": 85, "biome": "Mountain"},
    {"id": "atacama", "name": "Atacama Desert", "latitude": -24, "longitude": -69.5, "biome": "Desert"},
    {"id": "ganges", "name": "Ganges Delta", "latitude": 22.5, "longitude": 89, "biome": "River delta"},
    {"id": "los-angeles", "name": "Los Angeles", "latitude": 34.05, "longitude": -118.25, "biome": "Urban coast"},
    {"id": "reef", "name": "Great Barrier Reef", "latitude": -18.3, "longitude": 147.7, "biome": "Coral reef"},
    {"id": "marrakech", "name": "Marrakech", "latitude": 31.63, "longitude": -8, "biome": "Semi-arid city"},
]

SOURCES: list[dict[str, Any]] = [
    {
        "id": "power",
        "provider": "NASA",
        "name": "POWER",
        "status": "FULLY INTEGRATED",
        "kind": "Reanalysis / satellite-derived",
        "topics": ["Climate", "Hydrology", "Radiation"],
        "coverage": "Global · 1981–present",
        "resolution": "0.5° latitude × 0.625° longitude",
        "auth": "None",
        "api": "POWER Monthly Point API",
        "url": "https://power.larc.nasa.gov/",
    },
    {
        "id": "giovanni",
        "provider": "NASA GES DISC",
        "name": "Giovanni",
        "status": "FULLY INTEGRATED",
        "kind": "Time-series service (GPM IMERG precipitation, GLDAS)",
        "topics": ["Climate", "Hydrology", "Atmosphere"],
        "coverage": "Global · product-dependent",
        "resolution": "0.1° (IMERG) – 0.25° (GLDAS)",
        "auth": "Earthdata token on the server (EARTHDATA_TOKEN)",
        "api": "Giovanni in the Cloud: Time Series",
        "url": "https://giovanni.gsfc.nasa.gov/giovanni/",
    },
    {
        "id": "appeears",
        "provider": "NASA LP DAAC / ORNL DAAC",
        "name": "MODIS land products",
        "status": "FULLY INTEGRATED",
        "kind": "Satellite observations (MOD13Q1 NDVI/EVI, MOD15A2H LAI, MOD11A2 LST)",
        "topics": ["Vegetation", "Land surface", "Ecosystems"],
        "coverage": "Global land · 2000–present",
        "resolution": "250 m–1 km",
        "auth": "None",
        "api": (
            "ORNL DAAC MODIS web service (same MODIS products as AppEEARS, served instantly "
            "instead of as a queued AppEEARS task)"
        ),
        "url": "https://modis.ornl.gov/data/modis_webservice.html",
    },
    {
        "id": "gldas",
        "provider": "NASA GES DISC",
        "name": "GLDAS",
        "status": "FULLY INTEGRATED",
        "kind": "Land data assimilation model (GLDAS-2.1 Noah)",
        "topics": ["Hydrology", "Land surface"],
        "coverage": "Global land · 2000–present",
        "resolution": "0.25°",
        "auth": "Earthdata token on the server (EARTHDATA_TOKEN)",
        "api": "Giovanni in the Cloud: Time Series (replaces Hydrology Data Rods)",
        "url": "https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_3H_2.1/summary",
    },
    {
        "id": "noaa",
        "provider": "NOAA NCEI",
        "name": "Climate Data Online",
        "status": "FULLY INTEGRATED",
        "kind": "Ground station observations (Global Summary of the Month)",
        "topics": ["Climate"],
        "coverage": "Station-dependent",
        "resolution": "Nearest station point",
        "auth": "None (NOAA_CDO_TOKEN optional for the CDO v2 fallback)",
        "api": "NCEI Access Data Service, with Climate Data Online v2 as fallback",
        "url": "https://www.ncei.noaa.gov/cdo-web/webservices/v2",
    },
    {
        "id": "swot",
        "provider": "NASA / CNES / CSA / UKSA",
        "name": "SWOT",
        "status": "FULLY INTEGRATED",
        "kind": "Satellite radar altimetry (river reaches and lakes)",
        "topics": ["Hydrology", "Ocean"],
        "coverage": "Near-global · 2023–present",
        "resolution": "River reach (~10 km) or lake",
        "auth": "None; analysis needs a SWOT reach or lake ID",
        "api": "PO.DAAC Hydrocron",
        "url": "https://podaac.github.io/hydrocron/",
    },
    {
        "id": "radarsat",
        "provider": "Canadian Space Agency",
        "name": "RADARSAT Constellation Mission",
        "status": "EXTERNAL TOOL / MANUAL WORKFLOW",
        "kind": "Synthetic aperture radar imagery (no public time-series API)",
        "topics": ["Radar observations", "Ecosystems", "Ocean"],
        "coverage": "Global acquisitions",
        "resolution": "Mode-dependent",
        "auth": "EODMS account; access and licensing vary",
        "api": "Imagery ordered through EODMS; no point time-series service to connect",
        "url": "https://donnees-data.asc-csa.gc.ca/en/dataset/rcm",
    },
    {
        "id": "geo",
        "provider": "Government of Canada",
        "name": "GEO.CA",
        "status": "EXTERNAL TOOL / MANUAL WORKFLOW",
        "kind": "Geospatial catalogue (maps and datasets, not time series)",
        "topics": ["Land surface", "Ecosystems", "Hydrology"],
        "coverage": "Canada",
        "resolution": "Dataset-dependent",
        "auth": "Dataset-dependent",
        "api": "Catalogue of layers; no point time-series service to connect",
        "url": "https://geo.ca/",
    },
]


def find_variable(code: str) -> dict[str, Any] | None:
    """Return the catalogue entry for ``code`` (selectable or not)."""
    return next((item for item in VARIABLES if item["code"] == code), None)


def find_selectable_variable(code: str, provider: str | None = None) -> dict[str, Any] | None:
    """Return the variable if it has a working retrieval workflow (optionally for one provider)."""
    return next(
        (
            item
            for item in VARIABLES
            if item["code"] == code
            and item["selectable"]
            and (provider is None or item["provider"] == provider)
        ),
        None,
    )
