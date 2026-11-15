/**
 * Trend Detective — Universal Vanilla JS Bundle.
 * Works identically on:
 *   1. FastAPI server (`http://127.0.0.1:8000`)
 *   2. Direct local file opening (`file:///.../frontend/index.html` or `pages/*.html`)
 *   3. Any static HTTP server (VS Code Live Server, etc.)
 */
(function () {
  'use strict';

  const CATALOG = {"variables": [{"code": "T2M", "name": "Air temperature", "unit": "°C", "category": "Temperature", "definition": "Mean air temperature at 2 metres above the surface.", "why": "Tracks warming and cooling patterns that affect ecosystems, health, and energy demand.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "T2M_MAX", "name": "Maximum air temperature", "unit": "°C", "category": "Temperature", "definition": "Maximum air temperature at 2 metres.", "why": "Reveals changes in heat extremes.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "T2M_MIN", "name": "Minimum air temperature", "unit": "°C", "category": "Temperature", "definition": "Minimum air temperature at 2 metres.", "why": "Shows changes in overnight and cold-season conditions.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "TS", "name": "Earth skin temperature", "unit": "°C", "category": "Temperature", "definition": "Radiative temperature of the land or ocean surface.", "why": "Connects surface energy balance with land and water conditions.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "PRECTOTCORR", "name": "Precipitation", "unit": "mm/day", "category": "Water & humidity", "definition": "Bias-corrected total precipitation rate.", "why": "Supports drought, flood, and water-availability investigations.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "RH2M", "name": "Relative humidity", "unit": "%", "category": "Water & humidity", "definition": "Relative humidity at 2 metres.", "why": "Describes atmospheric moisture and heat-stress conditions.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "QV2M", "name": "Specific humidity", "unit": "g/kg", "category": "Water & humidity", "definition": "Mass of water vapour per mass of moist air at 2 metres.", "why": "Measures absolute atmospheric moisture.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "GWETROOT", "name": "Root-zone soil wetness", "unit": "fraction", "category": "Water & humidity", "definition": "Modelled root-zone soil wetness fraction.", "why": "Indicates water available to vegetation.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "ALLSKY_SFC_SW_DWN", "name": "Solar radiation", "unit": "kWh/m²/day", "category": "Radiation & clouds", "definition": "All-sky shortwave radiation reaching the surface.", "why": "Influences photosynthesis, evaporation, and solar resources.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "CLOUD_AMT", "name": "Cloud amount", "unit": "%", "category": "Radiation & clouds", "definition": "Fraction of sky covered by cloud.", "why": "Helps interpret radiation and precipitation changes.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "WS10M", "name": "Wind speed", "unit": "m/s", "category": "Wind & pressure", "definition": "Mean wind speed at 10 metres.", "why": "Affects evaporation, storms, and wind-energy potential.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "PS", "name": "Surface pressure", "unit": "kPa", "category": "Wind & pressure", "definition": "Atmospheric pressure at the surface.", "why": "Supports interpretation of circulation and weather patterns.", "provider": "power", "source": "NASA POWER", "minYear": 1981, "access": "Open, no account", "selectable": true}, {"code": "MOD13Q1_NDVI", "name": "NDVI vegetation index", "unit": "index", "category": "Vegetation", "definition": "Satellite vegetation greenness from MODIS Terra (MOD13Q1, 250 m, 16-day composites).", "why": "Can reveal vegetation stress and seasonal ecosystem change.", "provider": "modis", "source": "NASA MODIS (ORNL DAAC)", "minYear": 2000, "access": "Open, no account", "selectable": true}, {"code": "MOD13Q1_EVI", "name": "EVI vegetation index", "unit": "index", "category": "Vegetation", "definition": "Enhanced vegetation index from MODIS Terra (MOD13Q1, 250 m, 16-day composites).", "why": "Saturates less than NDVI over dense forest canopies.", "provider": "modis", "source": "NASA MODIS (ORNL DAAC)", "minYear": 2000, "access": "Open, no account", "selectable": true}, {"code": "MOD15A2H_LAI", "name": "Leaf area index", "unit": "m²/m²", "category": "Vegetation", "definition": "One-sided green leaf area per unit ground area (MOD15A2H, 500 m, 8-day composites).", "why": "Tracks canopy density, forest disturbance and recovery.", "provider": "modis", "source": "NASA MODIS (ORNL DAAC)", "minYear": 2002, "access": "Open, no account", "selectable": true}, {"code": "MOD11A2_LST_DAY", "name": "Daytime land surface temperature", "unit": "°C", "category": "Temperature", "definition": "Daytime land skin temperature from MODIS Terra (MOD11A2, 1 km, 8-day composites).", "why": "Sensitive to urban heat, drought and land-cover change.", "provider": "modis", "source": "NASA MODIS (ORNL DAAC)", "minYear": 2000, "access": "Open, no account", "selectable": true}, {"code": "GLDAS_SOILM_0_10", "name": "Surface soil moisture (0–10 cm)", "unit": "kg/m²", "category": "Hydrology", "definition": "Water stored in the top 10 cm of soil, GLDAS-2.1 Noah model (1 kg/m² = 1 mm).", "why": "Early indicator of agricultural drought.", "provider": "giovanni", "source": "NASA GLDAS (Giovanni)", "minYear": 2000, "access": "Earthdata token on the server (EARTHDATA_TOKEN)", "selectable": true}, {"code": "GLDAS_ROOT_ZONE_SM", "name": "Root-zone soil moisture", "unit": "kg/m²", "category": "Hydrology", "definition": "Water available to plant roots, GLDAS-2.1 Noah model (1 kg/m² = 1 mm).", "why": "Links rainfall deficits to vegetation stress.", "provider": "giovanni", "source": "NASA GLDAS (Giovanni)", "minYear": 2000, "access": "Earthdata token on the server (EARTHDATA_TOKEN)", "selectable": true}, {"code": "GLDAS_EVAP", "name": "Evapotranspiration", "unit": "mm/day", "category": "Hydrology", "definition": "Water returned to the atmosphere by soil evaporation and plant transpiration (GLDAS-2.1).", "why": "Shows how the water and energy balance of the land is changing.", "provider": "giovanni", "source": "NASA GLDAS (Giovanni)", "minYear": 2000, "access": "Earthdata token on the server (EARTHDATA_TOKEN)", "selectable": true}, {"code": "GLDAS_SWE", "name": "Snow water equivalent", "unit": "kg/m²", "category": "Hydrology", "definition": "Water contained in the snowpack, GLDAS-2.1 Noah model (1 kg/m² = 1 mm).", "why": "Tracks snowpack loss and seasonal water supply.", "provider": "giovanni", "source": "NASA GLDAS (Giovanni)", "minYear": 2000, "access": "Earthdata token on the server (EARTHDATA_TOKEN)", "selectable": true}, {"code": "GPM_IMERG_PRECIP", "name": "Satellite precipitation (GPM IMERG)", "unit": "mm/day", "category": "Water & humidity", "definition": "Multi-satellite precipitation estimate from the GPM IMERG product, served by Giovanni.", "why": "Independent satellite check on rainfall trends.", "provider": "giovanni", "source": "NASA GPM IMERG (Giovanni)", "minYear": 2001, "access": "Earthdata token on the server (EARTHDATA_TOKEN)", "selectable": true}, {"code": "NOAA_TAVG", "name": "Station mean temperature", "unit": "°C", "category": "Temperature", "definition": "Monthly mean temperature measured at the nearest NOAA GHCN station with data (GSOM).", "why": "Ground-truth check on gridded and satellite temperature trends.", "provider": "noaa", "source": "NOAA NCEI stations", "minYear": 1900, "access": "Open, no account (nearest station with data)", "selectable": true}, {"code": "NOAA_TMAX", "name": "Station maximum temperature", "unit": "°C", "category": "Temperature", "definition": "Monthly mean of daily maximum temperature at the nearest NOAA station (GSOM).", "why": "Ground-based view of changing heat extremes.", "provider": "noaa", "source": "NOAA NCEI stations", "minYear": 1900, "access": "Open, no account (nearest station with data)", "selectable": true}, {"code": "NOAA_TMIN", "name": "Station minimum temperature", "unit": "°C", "category": "Temperature", "definition": "Monthly mean of daily minimum temperature at the nearest NOAA station (GSOM).", "why": "Ground-based view of night-time warming.", "provider": "noaa", "source": "NOAA NCEI stations", "minYear": 1900, "access": "Open, no account (nearest station with data)", "selectable": true}, {"code": "NOAA_PRCP", "name": "Station precipitation", "unit": "mm/month", "category": "Water & humidity", "definition": "Monthly total precipitation measured at the nearest NOAA station (GSOM).", "why": "Rain-gauge check on satellite and model precipitation.", "provider": "noaa", "source": "NOAA NCEI stations", "minYear": 1900, "access": "Open, no account (nearest station with data)", "selectable": true}, {"code": "SWOT_WSE", "name": "Surface water elevation", "unit": "m", "category": "Hydrology", "definition": "Water-surface elevation of a river reach or lake observed by SWOT (monthly mean of passes).", "why": "Supports lake, river, reservoir, and flood investigations.", "provider": "swot", "source": "NASA SWOT (Hydrocron)", "minYear": 2023, "access": "Open, no account; needs a SWOT river reach or lake ID", "featureInput": true, "selectable": true}], "regions": [{"id": "svalbard", "name": "Svalbard / Arctic", "latitude": 78.2, "longitude": 15.6, "biome": "Polar"}, {"id": "sahel", "name": "Sahel / Niger", "latitude": 13.5, "longitude": 2.1, "biome": "Semi-arid"}, {"id": "sahara", "name": "Sahara", "latitude": 23, "longitude": 13, "biome": "Desert"}, {"id": "amazon", "name": "Amazon", "latitude": -3.1, "longitude": -60, "biome": "Tropical forest"}, {"id": "himalayas", "name": "Himalayas", "latitude": 28, "longitude": 85, "biome": "Mountain"}, {"id": "atacama", "name": "Atacama Desert", "latitude": -24, "longitude": -69.5, "biome": "Desert"}, {"id": "ganges", "name": "Ganges Delta", "latitude": 22.5, "longitude": 89, "biome": "River delta"}, {"id": "los-angeles", "name": "Los Angeles", "latitude": 34.05, "longitude": -118.25, "biome": "Urban coast"}, {"id": "reef", "name": "Great Barrier Reef", "latitude": -18.3, "longitude": 147.7, "biome": "Coral reef"}, {"id": "marrakech", "name": "Marrakech", "latitude": 31.63, "longitude": -8, "biome": "Semi-arid city"}], "sources": [{"id": "power", "provider": "NASA", "name": "POWER", "status": "FULLY INTEGRATED", "kind": "Reanalysis / satellite-derived", "topics": ["Climate", "Hydrology", "Radiation"], "coverage": "Global · 1981–present", "resolution": "0.5° latitude × 0.625° longitude", "auth": "None", "api": "POWER Monthly Point API", "url": "https://power.larc.nasa.gov/"}, {"id": "giovanni", "provider": "NASA GES DISC", "name": "Giovanni", "status": "FULLY INTEGRATED", "kind": "Time-series service (GPM IMERG precipitation, GLDAS)", "topics": ["Climate", "Hydrology", "Atmosphere"], "coverage": "Global · product-dependent", "resolution": "0.1° (IMERG) – 0.25° (GLDAS)", "auth": "Earthdata token on the server (EARTHDATA_TOKEN)", "api": "Giovanni in the Cloud: Time Series", "url": "https://giovanni.gsfc.nasa.gov/giovanni/"}, {"id": "appeears", "provider": "NASA LP DAAC / ORNL DAAC", "name": "MODIS land products", "status": "FULLY INTEGRATED", "kind": "Satellite observations (MOD13Q1 NDVI/EVI, MOD15A2H LAI, MOD11A2 LST)", "topics": ["Vegetation", "Land surface", "Ecosystems"], "coverage": "Global land · 2000–present", "resolution": "250 m–1 km", "auth": "None", "api": "ORNL DAAC MODIS web service (same MODIS products as AppEEARS, served instantly instead of as a queued AppEEARS task)", "url": "https://modis.ornl.gov/data/modis_webservice.html"}, {"id": "gldas", "provider": "NASA GES DISC", "name": "GLDAS", "status": "FULLY INTEGRATED", "kind": "Land data assimilation model (GLDAS-2.1 Noah)", "topics": ["Hydrology", "Land surface"], "coverage": "Global land · 2000–present", "resolution": "0.25°", "auth": "Earthdata token on the server (EARTHDATA_TOKEN)", "api": "Giovanni in the Cloud: Time Series (replaces Hydrology Data Rods)", "url": "https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_3H_2.1/summary"}, {"id": "noaa", "provider": "NOAA NCEI", "name": "Climate Data Online", "status": "FULLY INTEGRATED", "kind": "Ground station observations (Global Summary of the Month)", "topics": ["Climate"], "coverage": "Station-dependent", "resolution": "Nearest station point", "auth": "None (NOAA_CDO_TOKEN optional for the CDO v2 fallback)", "api": "NCEI Access Data Service, with Climate Data Online v2 as fallback", "url": "https://www.ncei.noaa.gov/cdo-web/webservices/v2"}, {"id": "swot", "provider": "NASA / CNES / CSA / UKSA", "name": "SWOT", "status": "FULLY INTEGRATED", "kind": "Satellite radar altimetry (river reaches and lakes)", "topics": ["Hydrology", "Ocean"], "coverage": "Near-global · 2023–present", "resolution": "River reach (~10 km) or lake", "auth": "None; analysis needs a SWOT reach or lake ID", "api": "PO.DAAC Hydrocron", "url": "https://podaac.github.io/hydrocron/"}, {"id": "radarsat", "provider": "Canadian Space Agency", "name": "RADARSAT Constellation Mission", "status": "EXTERNAL TOOL / MANUAL WORKFLOW", "kind": "Synthetic aperture radar imagery (no public time-series API)", "topics": ["Radar observations", "Ecosystems", "Ocean"], "coverage": "Global acquisitions", "resolution": "Mode-dependent", "auth": "EODMS account; access and licensing vary", "api": "Imagery ordered through EODMS; no point time-series service to connect", "url": "https://donnees-data.asc-csa.gc.ca/en/dataset/rcm"}, {"id": "geo", "provider": "Government of Canada", "name": "GEO.CA", "status": "EXTERNAL TOOL / MANUAL WORKFLOW", "kind": "Geospatial catalogue (maps and datasets, not time series)", "topics": ["Land surface", "Ecosystems", "Hydrology"], "coverage": "Canada", "resolution": "Dataset-dependent", "auth": "Dataset-dependent", "api": "Catalogue of layers; no point time-series service to connect", "url": "https://geo.ca/"}]};
  const ICONS = {"arrow-right": "<path d=\"M5 12h14\" /><path d=\"m12 5 7 7-7 7\" />", "arrow-up-right": "<path d=\"M7 7h10v10\" /><path d=\"M7 17 17 7\" />", "chart-column": "<path d=\"M3 3v16a2 2 0 0 0 2 2h16\" /><path d=\"M18 17V9\" /><path d=\"M13 17V5\" /><path d=\"M8 17v-3\" />", "book-open": "<path d=\"M12 5v16\" /><path d=\"M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z\" />", "check": "<path d=\"M20 6 9 17l-5-5\" />", "circle-check": "<circle cx=\"12\" cy=\"12\" r=\"10\" /><path d=\"m16 9-5.5 5.5L8 12\" />", "code-xml": "<path d=\"m18 16 4-4-4-4\" /><path d=\"m6 8-4 4 4 4\" /><path d=\"m14.5 4-5 16\" />", "crosshair": "<circle cx=\"12\" cy=\"12\" r=\"10\" /><line x1=\"22\" x2=\"18\" y1=\"12\" y2=\"12\" /><line x1=\"6\" x2=\"2\" y1=\"12\" y2=\"12\" /><line x1=\"12\" x2=\"12\" y1=\"6\" y2=\"2\" /><line x1=\"12\" x2=\"12\" y1=\"22\" y2=\"18\" />", "database": "<ellipse cx=\"12\" cy=\"5\" rx=\"9\" ry=\"3\" /><path d=\"M3 5V19A9 3 0 0 0 21 19V5\" /><path d=\"M3 12A9 3 0 0 0 21 12\" />", "download": "<path d=\"M12 15V3\" /><path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\" /><path d=\"m7 10 5 5 5-5\" />", "earth": "<path d=\"M21.54 15H17a2 2 0 0 0-2 2v4.54\" /><path d=\"M7 3.34V5a3 3 0 0 0 3 3a2 2 0 0 1 2 2c0 1.1.9 2 2 2a2 2 0 0 0 2-2c0-1.1.9-2 2-2h3.17\" /><path d=\"M11 21.95V18a2 2 0 0 0-2-2a2 2 0 0 1-2-2v-1a2 2 0 0 0-2-2H2.05\" /><circle cx=\"12\" cy=\"12\" r=\"10\" />", "external-link": "<path d=\"M15 3h6v6\" /><path d=\"M10 14 21 3\" /><path d=\"M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6\" />", "filter": "<path d=\"M10 20a1 1 0 0 0 .553.895l2 1A1 1 0 0 0 14 21v-7a2 2 0 0 1 .517-1.341L21.74 4.67A1 1 0 0 0 21 3H3a1 1 0 0 0-.742 1.67l7.225 7.989A2 2 0 0 1 10 14z\" />", "flask-conical": "<path d=\"M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2\" /><path d=\"M6.453 15h11.094\" /><path d=\"M8.5 2h7\" />", "heart-handshake": "<path d=\"M19.414 14.414C21 12.828 22 11.5 22 9.5a5.5 5.5 0 0 0-9.591-3.676.6.6 0 0 1-.818.001A5.5 5.5 0 0 0 2 9.5c0 2.3 1.5 4 3 5.5l5.535 5.362a2 2 0 0 0 2.879.052 2.12 2.12 0 0 0-.004-3 2.124 2.124 0 1 0 3-3 2.124 2.124 0 0 0 3.004 0 2 2 0 0 0 0-2.828l-1.881-1.882a2.41 2.41 0 0 0-3.409 0l-1.71 1.71a2 2 0 0 1-2.828 0 2 2 0 0 1 0-2.828l2.823-2.762\" />", "loader-circle": "<path d=\"M21 12a9 9 0 1 1-6.219-8.56\" />", "map-pin": "<path d=\"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0\" /><circle cx=\"12\" cy=\"10\" r=\"3\" />", "menu": "<path d=\"M4 5h16\" /><path d=\"M4 12h16\" /><path d=\"M4 19h16\" />", "microscope": "<path d=\"M6 18h8\" /><path d=\"M3 22h18\" /><path d=\"M14 22a7 7 0 1 0 0-14h-1\" /><path d=\"M9 14h2\" /><path d=\"M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z\" /><path d=\"M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3\" />", "moon": "<path d=\"M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401\" />", "orbit": "<path d=\"M20.341 6.484A10 10 0 0 1 10.266 21.85\" /><path d=\"M3.659 17.516A10 10 0 0 1 13.74 2.152\" /><circle cx=\"12\" cy=\"12\" r=\"3\" /><circle cx=\"19\" cy=\"5\" r=\"2\" /><circle cx=\"5\" cy=\"19\" r=\"2\" />", "play": "<path d=\"M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z\" />", "rotate-ccw": "<path d=\"M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8\" /><path d=\"M3 3v5h5\" />", "satellite": "<path d=\"m13.5 6.5-3.148-3.148a1.205 1.205 0 0 0-1.704 0L6.352 5.648a1.205 1.205 0 0 0 0 1.704L9.5 10.5\" /><path d=\"M16.5 7.5 19 5\" /><path d=\"m17.5 10.5 3.148 3.148a1.205 1.205 0 0 1 0 1.704l-2.296 2.296a1.205 1.205 0 0 1-1.704 0L13.5 14.5\" /><path d=\"M9 21a6 6 0 0 0-6-6\" /><path d=\"M9.352 10.648a1.205 1.205 0 0 0 0 1.704l2.296 2.296a1.205 1.205 0 0 0 1.704 0l4.296-4.296a1.205 1.205 0 0 0 0-1.704l-2.296-2.296a1.205 1.205 0 0 0-1.704 0z\" />", "scale": "<path d=\"M12 3v18\" /><path d=\"m19 8 3 8a5 5 0 0 1-6 0zV7\" /><path d=\"M3 7h1a17 17 0 0 0 8-2 17 17 0 0 0 8 2h1\" /><path d=\"m5 8 3 8a5 5 0 0 1-6 0zV7\" /><path d=\"M7 21h10\" />", "search": "<path d=\"m21 21-4.34-4.34\" /><circle cx=\"11\" cy=\"11\" r=\"8\" />", "shield-alert": "<path d=\"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z\" /><path d=\"M12 8v4\" /><path d=\"M12 16h.01\" />", "shield-check": "<path d=\"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z\" /><path d=\"m9 12 2 2 4-4\" />", "sigma": "<path d=\"M18 7V5a1 1 0 0 0-1-1H6.5a.5.5 0 0 0-.4.8l4.5 6a2 2 0 0 1 0 2.4l-4.5 6a.5.5 0 0 0 .4.8H17a1 1 0 0 0 1-1v-2\" />", "sparkles": "<path d=\"M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z\" /><path d=\"M20 2v4\" /><path d=\"M22 4h-4\" /><circle cx=\"4\" cy=\"20\" r=\"2\" />", "sun": "<circle cx=\"12\" cy=\"12\" r=\"4\" /><path d=\"M12 2v2\" /><path d=\"M12 20v2\" /><path d=\"m4.93 4.93 1.41 1.41\" /><path d=\"m17.66 17.66 1.41 1.41\" /><path d=\"M2 12h2\" /><path d=\"M20 12h2\" /><path d=\"m6.34 17.66-1.41 1.41\" /><path d=\"m19.07 4.93-1.41 1.41\" />", "trending-up": "<path d=\"M16 7h6v6\" /><path d=\"m22 7-8.5 8.5-5-5L2 17\" />", "triangle-alert": "<path d=\"m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3\" /><path d=\"M12 9v4\" /><path d=\"M12 17h.01\" />", "x": "<path d=\"M18 6 6 18\" /><path d=\"m6 6 12 12\" />", "linkedin": "<path d=\"M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z\" /><rect width=\"4\" height=\"12\" x=\"2\" y=\"9\" /><circle cx=\"4\" cy=\"4\" r=\"2\" />", "instagram": "<rect width=\"20\" height=\"20\" x=\"2\" y=\"2\" rx=\"5\" ry=\"5\" /><path d=\"M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z\" /><line x1=\"17.5\" x2=\"17.51\" y1=\"6.5\" y2=\"6.5\" />", "facebook": "<path d=\"M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z\" />"};
  const STORAGE_KEY = 'td-theme-v2';

  function escapeHtml(value) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return String(value ?? '').replace(/[&<>"']/g, (ch) => map[ch]);
  }

  function icon(name, opts) {
    const options = opts || {};
    const size = options.size || 24;
    const cls = options.className ? ` class="${options.className}"` : '';
    const fill = options.fill || 'none';
    const body = ICONS[name] || '';
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="${fill}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"${cls}>${body}</svg>`;
  }

  // --- Theme Management ---
  function isLightTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY) !== 'dark';
    } catch (_e) {
      return document.documentElement.dataset.theme !== 'dark';
    }
  }

  function setTheme(nextLight) {
    const theme = nextLight ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (_e) {}
  }

  function initThemeAndHeader() {
    document.documentElement.dataset.theme = 'light';
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (_e) {}

    const header = document.getElementById('site-header');
    if (!header) return;

    const nav = header.querySelector('.main-nav');
    const menuBtn = header.querySelector('[data-role="menu-toggle"]');
    let open = false;

    menuBtn?.addEventListener('click', () => {
      open = !open;
      nav?.classList.toggle('is-open', open);
      menuBtn.innerHTML = open ? icon('x', { size: 19 }) : icon('menu', { size: 19 });
    });

    window.addEventListener(
      'scroll',
      () => {
        header.classList.toggle('is-scrolled', window.scrollY > 12);
      },
      { passive: true }
    );

    document.querySelectorAll('[data-action="scroll-top"]').forEach((btn) => {
      btn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    });
  }

  // --- Route Resolution Helper ---
  function resolvePageHref(routeWithQuery) {
    const isFile = window.location.protocol === 'file:';
    const inPages = window.location.pathname.replace(/\\/g, '/').includes('/pages/');
    const [routePath, query] = routeWithQuery.split('?');
    const q = query ? `?${query}` : '';
    const clean = routePath.replace(/^\//, '') || 'index';
    if (isFile) {
      if (inPages) {
        return `./${clean}.html${q}`;
      }
      return clean === 'index' ? `./index.html${q}` : `./pages/${clean}.html${q}`;
    }
    return routeWithQuery;
  }

  // --- Client-Side Statistical & Risk Engine (Exact Port of Python Backend) ---
  function mean(values) {
    return values.reduce((s, v) => s + v, 0) / values.length;
  }

  function logGamma(value) {
    const coeffs = [
      676.5203681218851, -1259.1392167224028, 771.3234287776531, -176.6150291621406,
      12.507343278686905, -0.13857109526572012, 9.984369578019572e-6, 1.5056327351493116e-7,
    ];
    if (value < 0.5) {
      return Math.log(Math.PI) - Math.log(Math.sin(Math.PI * value)) - logGamma(1 - value);
    }
    let x = 0.9999999999998099;
    const z = value - 1;
    coeffs.forEach((c, i) => {
      x += c / (z + i + 1);
    });
    const t = z + coeffs.length - 0.5;
    return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x);
  }

  function betaFraction(a, b, x) {
    const maxIterations = 200;
    const epsilon = 3e-12;
    const tiny = 1e-30;
    const qab = a + b;
    const qap = a + 1;
    const qam = a - 1;
    let c = 1;
    let d = 1 - (qab * x) / qap;
    if (Math.abs(d) < tiny) d = tiny;
    d = 1 / d;
    let h = d;
    for (let m = 1; m <= maxIterations; m += 1) {
      const m2 = 2 * m;
      let aa = (m * (b - m) * x) / ((qam + m2) * (a + m2));
      d = 1 + aa * d;
      if (Math.abs(d) < tiny) d = tiny;
      c = 1 + aa / c;
      if (Math.abs(c) < tiny) c = tiny;
      d = 1 / d;
      h *= d * c;
      aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2));
      d = 1 + aa * d;
      if (Math.abs(d) < tiny) d = tiny;
      c = 1 + aa / c;
      if (Math.abs(c) < tiny) c = tiny;
      d = 1 / d;
      const delta = d * c;
      h *= delta;
      if (Math.abs(delta - 1) < epsilon) break;
    }
    return h;
  }

  function regularizedBeta(x, a, b) {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    const bt = Math.exp(
      logGamma(a + b) - logGamma(a) - logGamma(b) + a * Math.log(x) + b * Math.log(1 - x)
    );
    return x < (a + 1) / (a + b + 2)
      ? (bt * betaFraction(a, b, x)) / a
      : 1 - (bt * betaFraction(b, a, 1 - x)) / b;
  }

  function studentTPValue(t, df) {
    const x = df / (df + t * t);
    return regularizedBeta(x, df / 2, 0.5);
  }

  function normalCdf(x) {
    const sign = x < 0 ? -1 : 1;
    const z = Math.abs(x) / Math.sqrt(2);
    const t = 1 / (1 + 0.3275911 * z);
    const erf =
      sign *
      (1 -
        ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) *
          t *
          Math.exp(-z * z));
    return 0.5 * (1 + erf);
  }

  function linearRegression(values, xs) {
    if (values.length < 3) throw new Error('At least three observations are required.');
    const x = xs || values.map((_, i) => i);
    const xMean = mean(x);
    const yMean = mean(values);
    const sxx = x.reduce((s, v) => s + (v - xMean) ** 2, 0);
    const sxy = x.reduce((s, v, i) => s + (v - xMean) * (values[i] - yMean), 0);
    const slope = sxy / sxx;
    const intercept = yMean - slope * xMean;
    const fitted = x.map((v) => intercept + slope * v);
    const residualSS = values.reduce((s, v, i) => s + (v - fitted[i]) ** 2, 0);
    const totalSS = values.reduce((s, v) => s + (v - yMean) ** 2, 0);
    const df = values.length - 2;
    const se = Math.sqrt(residualSS / df / sxx);
    const tStat = se === 0 ? Number.POSITIVE_INFINITY : slope / se;
    const pValue = Number.isFinite(tStat) ? studentTPValue(Math.abs(tStat), df) : 0;
    const critical = df >= 30 ? 1.96 : df >= 10 ? 2.228 : 2.776;
    return {
      slope,
      intercept,
      standardError: se,
      tStatistic: tStat,
      degreesFreedom: df,
      pValue,
      confidenceInterval: [slope - critical * se, slope + critical * se],
      rSquared: totalSS === 0 ? 1 : 1 - residualSS / totalSS,
      fitted,
    };
  }

  function mannKendall(values, alpha = 0.05) {
    if (values.length < 3) throw new Error('At least three observations are required.');
    let s = 0;
    for (let i = 0; i < values.length - 1; i += 1) {
      for (let j = i + 1; j < values.length; j += 1) {
        s += Math.sign(values[j] - values[i]);
      }
    }
    const ties = new Map();
    values.forEach((v) => ties.set(v, (ties.get(v) ?? 0) + 1));
    let tieCorrection = 0;
    ties.forEach((count) => {
      if (count > 1) tieCorrection += count * (count - 1) * (2 * count + 5);
    });
    const n = values.length;
    const variance = (n * (n - 1) * (2 * n + 5) - tieCorrection) / 18;
    const z =
      variance === 0 ? 0 : s > 0 ? (s - 1) / Math.sqrt(variance) : s < 0 ? (s + 1) / Math.sqrt(variance) : 0;
    const pValue = 2 * (1 - normalCdf(Math.abs(z)));
    const tau = s / (0.5 * n * (n - 1));
    return { s, variance, z, pValue, tau, significant: pValue < alpha };
  }

  function sensSlope(values, xs) {
    const x = xs || values.map((_, i) => i);
    const slopes = [];
    for (let i = 0; i < values.length - 1; i += 1) {
      for (let j = i + 1; j < values.length; j += 1) {
        if (x[j] !== x[i]) slopes.push((values[j] - values[i]) / (x[j] - x[i]));
      }
    }
    slopes.sort((a, b) => a - b);
    const mid = Math.floor(slopes.length / 2);
    return slopes.length % 2 ? slopes[mid] : (slopes[mid - 1] + slopes[mid]) / 2;
  }

  function transformSeries(points, mode) {
    if (mode === 'raw') return points;
    if (mode === 'annual') {
      const byYear = new Map();
      points.forEach((p) => {
        const year = p.date.slice(0, 4);
        const list = byYear.get(year) || [];
        list.push(p.value);
        byYear.set(year, list);
      });
      const fullest = Math.max(0, ...Array.from(byYear.values(), (vals) => vals.length));
      return Array.from(byYear.entries())
        .filter(([, vals]) => vals.length >= 0.75 * fullest)
        .map(([date, vals]) => ({ date, value: mean(vals) }));
    }
    if (mode === 'anomaly') {
      const byMonth = new Map();
      points.forEach((p) => {
        const month = p.date.slice(5, 7);
        const list = byMonth.get(month) || [];
        list.push(p.value);
        byMonth.set(month, list);
      });
      return points.map((p) => ({
        date: p.date,
        value: p.value - mean(byMonth.get(p.date.slice(5, 7)) || [p.value]),
      }));
    }
    return points;
  }

  const RISK_PROFILES = {
    T2M: { phenomenon: 'Warming and heat stress', adverseDirection: 1, interpretation: 'Higher mean air temperatures increase the screening signal.' },
    T2M_MAX: { phenomenon: 'Extreme heat exposure', adverseDirection: 1, interpretation: 'Rising maximum temperatures increase the screening signal.' },
    T2M_MIN: { phenomenon: 'Night-time warming', adverseDirection: 1, interpretation: 'Rising minimum temperatures increase the screening signal.' },
    TS: { phenomenon: 'Surface heat stress', adverseDirection: 1, interpretation: 'Rising land or ocean skin temperature increases the screening signal.' },
    PRECTOTCORR: { phenomenon: 'Drying and rainfall deficit', adverseDirection: -1, interpretation: 'Declining precipitation increases the drying screening signal.' },
    RH2M: { phenomenon: 'Atmospheric dryness', adverseDirection: -1, interpretation: 'Declining relative humidity increases the dryness screening signal.' },
    QV2M: { phenomenon: 'Atmospheric moisture deficit', adverseDirection: -1, interpretation: 'Declining specific humidity increases the moisture-deficit signal.' },
    GWETROOT: { phenomenon: 'Root-zone drought stress', adverseDirection: -1, interpretation: 'Declining root-zone wetness increases the drought-stress signal.' },
    ALLSKY_SFC_SW_DWN: { phenomenon: 'Solar and evaporative stress', adverseDirection: 1, interpretation: 'Increasing surface radiation raises the evaporative-stress signal.' },
    CLOUD_AMT: { phenomenon: 'Reduced cloud cover', adverseDirection: -1, interpretation: 'Declining cloud amount raises the reduced-cloud-cover signal.' },
    WS10M: { phenomenon: 'Elevated wind exposure', adverseDirection: 1, interpretation: 'Increasing wind speed raises the wind-exposure signal.' },
    PS: { phenomenon: 'Surface pressure regime shift', adverseDirection: 0, interpretation: 'A large pressure trend in either direction raises the regime-shift signal.' },
  };

  function assessRiskClient(points, parameter, analysis, horizonYears = 5) {
    const values = points.map((p) => p.value).filter((v) => Number.isFinite(v));
    const profile = RISK_PROFILES[parameter] || {
      phenomenon: 'Environmental trend shift',
      adverseDirection: 0,
      interpretation: 'A large trend in either direction raises the screening signal.',
    };
    const avg = mean(values);
    const std =
      values.length < 2
        ? 1
        : Math.sqrt(values.reduce((s, v) => s + (v - avg) ** 2, 0) / (values.length - 1)) || 1;
    const dir = profile.adverseDirection;
    const directed = (v) => (dir === 0 ? Math.abs(v) : dir * v);
    const recentCount = Math.max(3, Math.min(values.length, Math.round(values.length * 0.2)));
    const recentMean = mean(values.slice(-recentCount));
    const baseMean = mean(values.slice(0, recentCount));
    const clamp = (v, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, v));
    const trendSignal = directed(analysis.trendPerDecade) / std;
    const recentSignal = directed(recentMean - baseMean) / std;
    const trendComponent = clamp(Math.max(0, trendSignal) / 1.5);
    const recentComponent = clamp(Math.max(0, recentSignal) / 1.5);
    const evidenceConfidence = 1 - clamp((analysis.regression.pValue + analysis.mannKendall.pValue) / 2);
    const completeness = clamp(values.length / 20);
    const combined = 0.62 * trendComponent + 0.38 * recentComponent;
    const horizon = Math.max(1, Math.min(30, Number(horizonYears) || 5));
    const horizonScale = horizon === 5 ? 1.0 : clamp(0.85 + 0.03 * horizon, 0.75, 1.35);
    const score = Math.min(
      100,
      Math.max(0, Math.round(100 * combined * (0.7 + 0.3 * evidenceConfidence) * completeness * horizonScale))
    );
    const uncertainty = Math.round(
      8 + 18 * (1 - evidenceConfidence) + 10 * (1 - completeness) + Math.max(0, horizon - 5) * 0.6
    );
    const projected = Number.isFinite(analysis.slopePerYear)
      ? analysis.slopePerYear * horizon
      : analysis.regression.slope * (points.some((p) => p.date.length >= 7) ? 12 * horizon : horizon);
    const level = score < 25 ? 'Low' : score < 50 ? 'Moderate' : score < 75 ? 'High' : 'Very high';
    return {
      phenomenon: profile.phenomenon,
      score,
      level,
      uncertainty,
      horizonYears: horizon,
      projectedChange: projected,
      trendComponent: Math.round(trendComponent * 100),
      recentComponent: Math.round(recentComponent * 100),
      evidenceConfidence: Math.round(evidenceConfidence * 100),
      interpretation: profile.interpretation,
      method:
        'Screening score combining standardized adverse trend (62%), recent-versus-baseline shift (38%), statistical evidence, and data completeness.',
      disclaimer:
        'This is a statistical screening indicator, not a calibrated probability that a hazardous event will occur. It does not include exposure, vulnerability, local impacts, or causal drivers.',
    };
  }

  function analyzeClient(points, parameter = 'T2M', alpha = 0.05, horizonYears = 5) {
    const valid = points.filter((p) => Number.isFinite(p.value));
    const values = valid.map((p) => p.value);
    // Real time in decimal years, so gaps keep their spacing (same as the server).
    const times = valid.map(
      (p) => Number(p.date.slice(0, 4)) + (p.date.length >= 7 ? (Number(p.date.slice(5, 7)) - 1) / 12 : 0)
    );
    const regression = linearRegression(values, times);
    const mk = mannKendall(values, alpha);
    const sen = sensSlope(values, times);
    const factor = 10;
    const slope = regression.slope;
    const direction = slope > 0 ? 'increasing' : slope < 0 ? 'decreasing' : 'stable';
    let verdict = 'No statistically significant trend detected';
    if (regression.pValue < alpha && mk.significant) {
      verdict = `Significant ${direction} trend`;
    } else if (regression.pValue < alpha || mk.significant) {
      verdict = 'Mixed statistical evidence';
    }
    const core = {
      regression,
      mannKendall: mk,
      senSlope: sen,
      trendPerDecade: slope * factor,
      senPerDecade: sen * factor,
      slopePerYear: slope,
      alpha,
      verdict,
      validObservations: values.length,
    };
    return { ...core, risk: assessRiskClient(points, parameter, core, horizonYears) };
  }

  async function fetchPowerDirect({ parameter, latitude, longitude, start, end, mode, alpha = 0.05, horizon = 5 }) {
    const def = CATALOG.variables.find((v) => v.code === parameter && v.selectable);
    if (!def) throw new Error('Unsupported NASA POWER parameter.');
    const url = new URL('https://power.larc.nasa.gov/api/temporal/monthly/point');
    url.searchParams.set('parameters', parameter);
    url.searchParams.set('community', 'AG');
    url.searchParams.set('longitude', String(longitude));
    url.searchParams.set('latitude', String(latitude));
    url.searchParams.set('start', String(start));
    url.searchParams.set('end', String(end));
    url.searchParams.set('format', 'JSON');

    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`NASA POWER request failed with status ${res.status}.`);
    const payload = await res.json();
    const series = payload?.properties?.parameter?.[parameter];
    if (!series) throw new Error('NASA POWER returned no observations for this parameter.');
    const rawPoints = Object.entries(series)
      .filter(([k, v]) => /^\d{6}$/.test(k) && k.slice(4) !== '13' && Number.isFinite(v) && v !== -999)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => ({ date: `${k.slice(0, 4)}-${k.slice(4, 6)}`, value: Number(v) }));
    if (rawPoints.length < 3) throw new Error('NASA POWER returned too few valid observations.');
    const points = transformSeries(rawPoints, mode);
    const metadata = {
      provider: 'NASA Prediction Of Worldwide Energy Resources',
      product: 'POWER Monthly Point API',
      parameter,
      unit: def.unit,
      latitude: Number(latitude),
      longitude: Number(longitude),
      temporalResolution: 'Monthly',
      spatialResolution: '0.5° latitude × 0.625° longitude (parameter-dependent gridded cell)',
      coverage: `${rawPoints[0].date} to ${rawPoints[rawPoints.length - 1].date}`,
      retrievalDate: new Date().toISOString(),
      processing: `Invalid -999 values and annual month-13 entries removed. Analysis mode: ${mode}.`,
      quality: 'Gridded, model- and satellite-derived data; not a direct measurement at the selected point.',
      documentation: 'https://power.larc.nasa.gov/docs/services/api/',
      simulated: false,
    };
    return {
      points,
      metadata,
      analysis: analyzeClient(points, parameter, Number(alpha), Number(horizon)),
      mode,
    };
  }

  async function fetchScanDirect({ latitude, longitude, start, end, mode = 'annual', alpha = 0.05, horizon = 5 }) {
    // Only NASA POWER can be fetched directly by the browser; other sources need the server.
    const selectable = CATALOG.variables.filter((v) => v.selectable && v.provider === 'power');
    const codes = selectable.map((v) => v.code);
    const batches = [codes.slice(0, 6), codes.slice(6, 12)];
    const rawByCode = {};

    await Promise.all(
      batches.map(async (batch) => {
        if (!batch.length) return;
        const url = new URL('https://power.larc.nasa.gov/api/temporal/monthly/point');
        url.searchParams.set('parameters', batch.join(','));
        url.searchParams.set('community', 'AG');
        url.searchParams.set('longitude', String(longitude));
        url.searchParams.set('latitude', String(latitude));
        url.searchParams.set('start', String(start));
        url.searchParams.set('end', String(end));
        url.searchParams.set('format', 'JSON');
        const res = await fetch(url.toString());
        if (!res.ok) throw new Error(`NASA POWER request failed with status ${res.status}.`);
        const payload = await res.json();
        const paramMap = payload?.properties?.parameter || {};
        Object.assign(rawByCode, paramMap);
      })
    );

    const alphaNum = Number(alpha) || 0.05;
    const horizonNum = Number(horizon) || 5;
    const items = [];

    for (const def of selectable) {
      const series = rawByCode[def.code];
      if (!series) continue;
      const rawPoints = Object.entries(series)
        .filter(([k, v]) => /^\d{6}$/.test(k) && k.slice(4) !== '13' && Number.isFinite(v) && v !== -999)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([k, v]) => ({ date: `${k.slice(0, 4)}-${k.slice(4, 6)}`, value: Number(v) }));
      if (rawPoints.length < 3) continue;
      const points = transformSeries(rawPoints, mode);
      const analysis = analyzeClient(points, def.code, alphaNum, horizonNum);
      const reg = analysis.regression;
      const mk = analysis.mannKendall;
      const isSig = Boolean(reg.pValue < alphaNum || mk.significant);
      items.push({
        code: def.code,
        name: def.name,
        category: def.category,
        unit: def.unit,
        significant: isSig,
        bothSignificant: Boolean(reg.pValue < alphaNum && mk.significant),
        verdict: analysis.verdict,
        trendPerDecade: analysis.trendPerDecade,
        senPerDecade: analysis.senPerDecade,
        pValue: reg.pValue,
        mkPValue: mk.pValue,
        rSquared: reg.rSquared,
        firstValue: points[0].value,
        lastValue: points[points.length - 1].value,
        firstDate: points[0].date,
        lastDate: points[points.length - 1].date,
        source: def.source,
        provider: def.provider,
        risk: analysis.risk,
        points,
        analysis,
      });
    }

    if (!items.length) throw new Error('NASA POWER returned no valid observations for this region.');

    items.sort((a, b) => {
      if (a.significant !== b.significant) return a.significant ? -1 : 1;
      if (b.risk.score !== a.risk.score) return b.risk.score - a.risk.score;
      return a.pValue - b.pValue;
    });

    const significantItems = items.filter((i) => i.significant);
    const phenomena = [...items].sort((a, b) => b.risk.score - a.risk.score);

    return {
      latitude: Number(latitude),
      longitude: Number(longitude),
      start: Number(start),
      end: Number(end),
      mode,
      alpha: alphaNum,
      horizon: horizonNum,
      totalScanned: items.length,
      significantCount: significantItems.length,
      items,
      significantItems,
      phenomena,
    };
  }

  // --- API Client with Automatic FastAPI -> Direct NASA Fallback ---
  async function apiHazards(params, sources) {
    const q = new URLSearchParams({
      latitude: String(params.latitude),
      longitude: String(params.longitude),
      start: String(params.start),
      end: String(params.end),
      sources,
    });
    const bases = window.location.protocol === 'file:' ? ['http://127.0.0.1:8000'] : ['', 'http://127.0.0.1:8000'];
    for (const base of bases) {
      try {
        const res = await fetch(`${base}/api/hazards?${q}`);
        const data = await res.json();
        if (res.ok && data && data.hazards) return data.hazards;
        if (data && data.error) throw new Error(data.error);
      } catch (err) {
        if (err instanceof Error && !err.message.includes('Failed to fetch') && !err.message.includes('NetworkError')) {
          throw err;
        }
      }
    }
    throw new Error('Start the Trend Detective server to detect heat waves, extreme rainfall and droughts.');
  }

  async function apiScanRegion(params) {
    const q = new URLSearchParams({
      latitude: String(params.latitude),
      longitude: String(params.longitude),
      start: String(params.start),
      end: String(params.end),
      mode: String(params.mode),
      alpha: String(params.alpha ?? '0.05'),
      horizon: String(params.horizon ?? '5'),
    });
    if (params.sources) q.set('sources', params.sources);
    const bases = window.location.protocol === 'file:' ? ['http://127.0.0.1:8000'] : ['', 'http://127.0.0.1:8000'];
    for (const base of bases) {
      try {
        const res = await fetch(`${base}/api/scan?${q}`);
        const data = await res.json();
        if (res.ok && data && Array.isArray(data.items)) return data;
        if (!res.ok && data && data.error) throw new Error(data.error);
      } catch (err) {
        if (err instanceof Error && !err.message.includes('Failed to fetch') && !err.message.includes('NetworkError')) {
          throw err;
        }
      }
    }
    if (params.sources && params.sources !== 'power') {
      throw new Error(
        'The Trend Detective server is not running, so only NASA POWER could be scanned. Start the server (see README) to add MODIS, GLDAS, GPM IMERG and NOAA.'
      );
    }
    return fetchScanDirect(params);
  }

  // Combine a fast NASA POWER scan with the slower scan of the other sources.
  function mergeScans(first, second) {
    const seen = new Set(first.items.map((i) => i.code));
    const items = [...first.items, ...second.items.filter((i) => !seen.has(i.code))];
    items.sort((a, b) => {
      if (a.significant !== b.significant) return a.significant ? -1 : 1;
      if (b.risk.score !== a.risk.score) return b.risk.score - a.risk.score;
      return a.pValue - b.pValue;
    });
    const significantItems = items.filter((i) => i.significant);
    return {
      ...first,
      items,
      significantItems,
      phenomena: [...items].sort((a, b) => b.risk.score - a.risk.score),
      totalScanned: items.length,
      significantCount: significantItems.length,
      skipped: [...(first.skipped || []), ...(second.skipped || [])],
    };
  }

  async function apiAnalysis(params) {
    const q = new URLSearchParams({
      parameter: String(params.parameter),
      latitude: String(params.latitude),
      longitude: String(params.longitude),
      start: String(params.start),
      end: String(params.end),
      mode: String(params.mode),
      alpha: String(params.alpha ?? '0.05'),
      horizon: String(params.horizon ?? '5'),
    });
    const bases = window.location.protocol === 'file:' ? ['http://127.0.0.1:8000'] : ['', 'http://127.0.0.1:8000'];
    for (const base of bases) {
      try {
        const res = await fetch(`${base}/api/analysis?${q}`);
        const data = await res.json();
        if (res.ok && data && data.points) return data;
        if (!res.ok && data && data.error) throw new Error(data.error);
      } catch (err) {
        if (err instanceof Error && !err.message.includes('Failed to fetch') && !err.message.includes('NetworkError')) {
          throw err;
        }
      }
    }
    return fetchPowerDirect(params);
  }

  async function apiComparison(payload) {
    const bases = window.location.protocol === 'file:' ? ['http://127.0.0.1:8000'] : ['', 'http://127.0.0.1:8000'];
    for (const base of bases) {
      try {
        const res = await fetch(`${base}/api/comparison`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (res.ok && data && data.regionA) return data;
        if (!res.ok && data && data.error) throw new Error(data.error);
      } catch (err) {
        if (err instanceof Error && !err.message.includes('Failed to fetch') && !err.message.includes('NetworkError')) {
          throw err;
        }
      }
    }
    const [first, second] = await Promise.all([
      fetchPowerDirect({
        parameter: payload.parameter,
        latitude: payload.regionA.latitude,
        longitude: payload.regionA.longitude,
        start: payload.start,
        end: payload.end,
        mode: payload.mode,
      }),
      fetchPowerDirect({
        parameter: payload.parameter,
        latitude: payload.regionB.latitude,
        longitude: payload.regionB.longitude,
        start: payload.start,
        end: payload.end,
        mode: payload.mode,
      }),
    ]);
    return {
      regionA: first,
      regionB: second,
      differencePerDecade: first.analysis.trendPerDecade - second.analysis.trendPerDecade,
      interpretation:
        'Different regional trends can coexist; this comparison does not establish a shared or distinct cause.',
    };
  }

  async function apiGeocode(query) {
    const bases = window.location.protocol === 'file:' ? ['http://127.0.0.1:8000'] : ['', 'http://127.0.0.1:8000'];
    for (const base of bases) {
      try {
        const res = await fetch(`${base}/api/geocode?q=${encodeURIComponent(query)}`);
        if (res.ok) return await res.json();
      } catch (_e) {}
    }
    const url = `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&q=${encodeURIComponent(query)}`;
    const res = await fetch(url);
    const items = await res.json();
    return {
      results: Array.isArray(items)
        ? items.slice(0, 5).map((i) => ({ lat: i.lat, lon: i.lon, display_name: i.display_name }))
        : [],
    };
  }

  // --- Chart.js Wrapper ---
  const PALETTES = {
    light: {
      observed: '#0B3D91',
      observedFill: 'rgba(11,61,145,.14)',
      trend: '#FC3D21',
      text: '#3b5378',
      title: '#0B3D91',
      grid: 'rgba(11,61,145,.12)',
    },
    dark: {
      observed: '#0B3D91',
      observedFill: 'rgba(11,61,145,.22)',
      trend: '#FC3D21',
      text: '#a6bddb',
      title: '#f2f6fc',
      grid: 'rgba(11,61,145,.18)',
    },
  };

  function createTrendChart(canvas, { points, fitted, unit, title }) {
    const ChartLib = window.Chart;
    if (!ChartLib) return null;
    const getPalette = () => (document.documentElement.dataset.theme === 'dark' ? PALETTES.dark : PALETTES.light);

    function buildCfg(pal) {
      const datasets = [
        {
          label: 'Observed',
          data: points.map((p) => p.value),
          borderColor: pal.observed,
          backgroundColor: pal.observedFill,
          pointRadius: points.length > 80 ? 0 : 2.5,
          borderWidth: 2.5,
          tension: 0.18,
          fill: true,
        },
      ];
      if (Array.isArray(fitted)) {
        datasets.push({
          label: 'OLS trend',
          data: fitted,
          borderColor: pal.trend,
          backgroundColor: 'transparent',
          pointRadius: 0,
          borderDash: [7, 6],
          borderWidth: 2.2,
        });
      }
      return {
        type: 'line',
        data: { labels: points.map((p) => p.date), datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { labels: { color: pal.text, font: { family: 'DM Mono', size: 12 } } },
            title: title ? { display: true, text: title, color: pal.title } : { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.parsed.y).toFixed(2)} ${unit}`,
              },
            },
          },
          scales: {
            x: { ticks: { color: pal.text, maxTicksLimit: 10, font: { size: 12 } }, grid: { color: pal.grid } },
            y: {
              ticks: { color: pal.text, font: { size: 12 } },
              title: { display: true, text: unit, color: pal.text, font: { size: 12 } },
              grid: { color: pal.grid },
            },
          },
        },
      };
    }

    const chart = new ChartLib(canvas, buildCfg(getPalette()));
    const obs = new MutationObserver(() => {
      const next = buildCfg(getPalette());
      chart.data = next.data;
      chart.options = next.options;
      chart.update('none');
    });
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return {
      toBase64Image: () => chart.toBase64Image(),
      destroy: () => {
        obs.disconnect();
        chart.destroy();
      },
    };
  }

  // --- Explorer Page Controller (Map-First Multi-Variable Scanner) ---
  function initExplorerPage() {
    const root = document.getElementById('explorer-root');
    if (!root) return;

    const available = CATALOG.variables.filter((v) => v.selectable);
    const regions = CATALOG.regions;
    const params = new URLSearchParams(window.location.search);
    const paramCode = params.get('parameter');
    const validParam = available.some((v) => v.code === paramCode) ? paramCode : 'T2M';
    const regionId = params.get('region') || 'svalbard';
    const matchedRegion = regions.find((r) => r.id === regionId) || regions[0];
    const latParam = params.get('latitude') ?? params.get('lat');
    const lonParam = params.get('longitude') ?? params.get('lon');
    const hasCustomCoords = latParam !== null && lonParam !== null && !Number.isNaN(Number(latParam)) && !Number.isNaN(Number(lonParam));

    const state = {
      parameter: validParam,
      regionId: hasCustomCoords ? 'custom' : matchedRegion.id,
      regionName: hasCustomCoords ? 'Selected Grid Point' : matchedRegion.name,
      biome: hasCustomCoords ? 'Custom coordinate' : matchedRegion.biome,
      latitude: hasCustomCoords ? Number(latParam) : matchedRegion.latitude,
      longitude: hasCustomCoords ? Number(lonParam) : matchedRegion.longitude,
      start: Number(params.get('start')) || 1990,
      end: Number(params.get('end')) || 2024,
      mode: ['annual', 'anomaly', 'raw'].includes(params.get('mode')) ? params.get('mode') : 'annual',
      alpha: ['0.01', '0.05', '0.10'].includes(params.get('alpha')) ? params.get('alpha') : '0.05',
      horizon: ['5', '10', '15', '20'].includes(params.get('horizon')) ? params.get('horizon') : '5',
      showAllVars: false,
      loading: false,
      error: '',
      scanResult: null,
      extraLoading: false,
      extraError: '',
      hazards: null,
      hazardsPending: [],
      hazardsError: '',
    };

    let activeChart = null;
    let map = null;
    let marker = null;

    const paramSelect = root.querySelector('[data-field="parameter"]');
    if (paramSelect && !paramSelect.options.length) {
      available.forEach((v) => {
        const o = document.createElement('option');
        o.value = v.code;
        o.textContent = `${v.name} · ${v.code}`;
        paramSelect.appendChild(o);
      });
      paramSelect.value = state.parameter;
    }
    const regionSelect = root.querySelector('[data-field="region"]');
    const latInput = root.querySelector('[data-field="latitude"]');
    const lonInput = root.querySelector('[data-field="longitude"]');
    const startInput = root.querySelector('[data-field="start"]');
    const endInput = root.querySelector('[data-field="end"]');
    const modeSelect = root.querySelector('[data-field="mode"]');
    const alphaSelect = root.querySelector('[data-field="alpha"]');
    const horizonSelect = root.querySelector('[data-field="horizon"]');
    const launchBtn = root.querySelector('[data-action="investigate"]');
    const resultsPanel = root.querySelector('#results-panel');
    const regionNameEl = root.querySelector('#scanner-region-name');
    const coordsLabelEl = root.querySelector('#scanner-coords-label');
    const kpiTotalEl = root.querySelector('#kpi-total-scanned');
    const kpiSigEl = root.querySelector('#kpi-sig-count');
    const kpiRiskEl = root.querySelector('#kpi-top-risk');
    const placeQueryIn = root.querySelector('#scanner-place-query');
    const placeSearchBtn = root.querySelector('#scanner-place-btn');
    const mapEl = root.querySelector('#explorer-map');

    function syncHeaderSummary() {
      if (regionNameEl) regionNameEl.textContent = state.regionName;
      if (coordsLabelEl) {
        const la = Number(state.latitude), lo = Number(state.longitude);
        coordsLabelEl.textContent = `${Math.abs(la).toFixed(2)}° ${la >= 0 ? 'N' : 'S'}, ${Math.abs(lo).toFixed(2)}° ${lo >= 0 ? 'E' : 'W'} · ${state.biome}`;
      }
      if (latInput) latInput.value = String(state.latitude);
      if (lonInput) lonInput.value = String(state.longitude);
      if (regionSelect) {
        const customOpt = regionSelect.querySelector('[data-custom-option]');
        if (state.regionId === 'custom') {
          if (customOpt) {
            customOpt.hidden = false;
            customOpt.textContent = state.regionName;
          }
          regionSelect.value = 'custom';
        } else {
          if (customOpt) customOpt.hidden = true;
          regionSelect.value = state.regionId;
        }
      }
      if (paramSelect) paramSelect.value = state.parameter;
      root.querySelectorAll('[data-region-pill]').forEach((btn) => {
        btn.classList.toggle('active', btn.getAttribute('data-region-pill') === state.regionId);
      });
    }

    if (startInput) startInput.value = String(state.start);
    if (endInput) endInput.value = String(state.end);
    if (modeSelect) modeSelect.value = state.mode;
    if (alphaSelect) alphaSelect.value = state.alpha;
    if (horizonSelect) horizonSelect.value = state.horizon;
    syncHeaderSummary();

    let gridCellRect = null;
    const hudCoordsEl = root.querySelector('#earth-hud-coords');
    const hudZoomEl = root.querySelector('#earth-hud-zoom');
    const mapCardEl = root.querySelector('#scanner-map-card');

    function formatHudCoords(lat, lon) {
      const ns = lat >= 0 ? 'N' : 'S';
      const ew = lon >= 0 ? 'E' : 'W';
      return `LAT ${Math.abs(lat).toFixed(4)}° ${ns} · LON ${Math.abs(lon).toFixed(4)}° ${ew}`;
    }

    function updateGridBounds(lat, lon) {
      const half = 0.25;
      return [
        [lat - half, lon - half],
        [lat + half, lon + half],
      ];
    }

    function selectLocation(lat, lon, name, regionIdVal = 'custom', biomeVal = 'Selected grid cell', triggerScan = true) {
      state.latitude = Number(Number(lat).toFixed(4));
      state.longitude = Number(Number(lon).toFixed(4));
      state.regionName = name;
      state.regionId = regionIdVal;
      state.biome = biomeVal;
      syncHeaderSummary();
      if (hudCoordsEl) hudCoordsEl.textContent = formatHudCoords(state.latitude, state.longitude);
      if (map && marker) {
        map.flyTo([state.latitude, state.longitude], Math.max(map.getZoom(), 5), {
          duration: 1.4,
          easeLinearity: 0.22,
        });
        marker.setLatLng([state.latitude, state.longitude]);
        if (gridCellRect) gridCellRect.setBounds(updateGridBounds(state.latitude, state.longitude));
      }
      if (triggerScan) investigate();
    }

    // Initialize Google Earth Satellite & Hybrid Map
    if (window.L && mapEl) {
      const L = window.L;
      const inPages = window.location.pathname.replace(/\\/g, '/').includes('/pages/');
      L.Icon.Default.imagePath = inPages ? '../assets/vendor/leaflet/images/' : './assets/vendor/leaflet/images/';
      map = L.map(mapEl, {
        zoomControl: false,
        worldCopyJump: true,
        minZoom: 2,
        maxZoom: 18,
      }).setView([state.latitude, state.longitude], 4);

      const esriSat = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
          attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, NASA',
          maxZoom: 18,
        }
      );
      const esriLabels = L.tileLayer(
        'https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
        {
          maxZoom: 18,
          opacity: 0.88,
        }
      );
      const nasaBlueMarble = L.tileLayer(
        'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_NextGeneration/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg',
        {
          attribution: 'Imagery &copy; NASA EOSDIS GIBS',
          maxNativeZoom: 8,
          maxZoom: 18,
        }
      );
      const esriTerrain = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        {
          attribution: 'Tiles &copy; Esri &mdash; USGS, NOAA',
          maxZoom: 18,
        }
      );
      const osmTileTemplate =
        window.location.protocol === 'file:'
          ? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
          : '/api/tiles/{z}/{x}/{y}';
      const streetLayer = L.tileLayer(osmTileTemplate, {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18,
      });

      const layerGroups = {
        satellite: L.layerGroup([esriSat, esriLabels]),
        nasa: L.layerGroup([nasaBlueMarble, esriLabels]),
        terrain: L.layerGroup([esriTerrain]),
        street: L.layerGroup([streetLayer]),
      };

      let activeLayerGroup = layerGroups.satellite;
      activeLayerGroup.addTo(map);

      root.querySelectorAll('[data-map-layer]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const modeKey = btn.getAttribute('data-map-layer') || 'satellite';
          const nextGroup = layerGroups[modeKey] || layerGroups.satellite;
          if (activeLayerGroup !== nextGroup) {
            map.removeLayer(activeLayerGroup);
            nextGroup.addTo(map);
            activeLayerGroup = nextGroup;
          }
          root.querySelectorAll('[data-map-layer]').forEach((b) =>
            b.classList.toggle('active', b === btn)
          );
        });
      });

      L.control.zoom({ position: 'bottomright' }).addTo(map);

      // NASA 0.5° × 0.5° grid cell footprint
      gridCellRect = L.rectangle(updateGridBounds(state.latitude, state.longitude), {
        color: '#FC3D21',
        weight: 2,
        fillColor: '#FC3D21',
        fillOpacity: 0.16,
        dashArray: '6, 4',
      }).addTo(map);

      // Custom pulsing Google Earth satellite target reticle
      const reticleIcon = L.divIcon({
        className: 'earth-reticle-marker',
        html: '<div class="reticle-ring"></div><div class="reticle-core"></div>',
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      });
      marker = L.marker([state.latitude, state.longitude], { icon: reticleIcon }).addTo(map);

      // Benchmark region pins on globe
      regions.forEach((r) => {
        const pinIcon = L.divIcon({
          className: 'earth-preset-pin',
          html: `<span title="${escapeHtml(r.name)}"></span>`,
          iconSize: [12, 12],
          iconAnchor: [6, 6],
        });
        const rMarker = L.marker([r.latitude, r.longitude], { icon: pinIcon }).addTo(map);
        rMarker.on('click', () => {
          selectLocation(r.latitude, r.longitude, r.name, r.id, r.biome, true);
        });
      });

      function updateZoomAltitude() {
        if (!hudZoomEl) return;
        const z = map.getZoom();
        const approxKm = Math.max(2, Math.round(38000 / Math.pow(1.9, z)));
        hudZoomEl.textContent = `ALT ${approxKm.toLocaleString()} KM · ZOOM ${z}x`;
      }
      updateZoomAltitude();

      map.on('mousemove', (ev) => {
        if (hudCoordsEl) hudCoordsEl.textContent = formatHudCoords(ev.latlng.lat, ev.latlng.lng);
      });
      map.on('mouseout', () => {
        if (hudCoordsEl) hudCoordsEl.textContent = formatHudCoords(state.latitude, state.longitude);
      });
      map.on('zoomend', updateZoomAltitude);

      map.on('click', (ev) => {
        selectLocation(ev.latlng.lat, ev.latlng.lng, 'Custom Satellite Point', 'custom', 'NASA 0.5°×0.5° grid cell', true);
      });

      root.querySelector('#earth-reset-globe')?.addEventListener('click', () => {
        map.flyTo([20, 0], 2, { duration: 1.4 });
      });
      root.querySelector('#earth-fly-target')?.addEventListener('click', () => {
        map.flyTo([state.latitude, state.longitude], 7, { duration: 1.4 });
      });
      root.querySelector('#earth-fullscreen-btn')?.addEventListener('click', () => {
        mapCardEl?.classList.toggle('is-fullscreen');
        setTimeout(() => map?.invalidateSize(), 260);
      });
    }

    // Region pills
    root.querySelectorAll('[data-region-pill]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const r = regions.find((item) => item.id === btn.getAttribute('data-region-pill'));
        if (r) selectLocation(r.latitude, r.longitude, r.name, r.id, r.biome, true);
      });
    });

    // Place search
    // Broad regions that a place search can't find as a single place.
    const BROAD_REGIONS = [
      { keys: ['midwest', 'middle west'], name: 'USA Midwest', lat: 41.5, lon: -91.0 },
      { keys: ['great plains'], name: 'Great Plains, USA', lat: 40.0, lon: -100.0 },
      { keys: ['corn belt'], name: 'US Corn Belt', lat: 41.8, lon: -92.0 },
      { keys: ['southwest usa', 'us southwest', 'american southwest'], name: 'US Southwest', lat: 34.5, lon: -111.0 },
      { keys: ['new england'], name: 'New England, USA', lat: 43.5, lon: -71.5 },
      { keys: ['pacific northwest'], name: 'Pacific Northwest', lat: 46.5, lon: -121.5 },
      { keys: ['sahel'], name: 'Sahel', lat: 14.0, lon: 2.0 },
      { keys: ['maghreb'], name: 'Maghreb', lat: 32.0, lon: 0.0 },
      { keys: ['middle east'], name: 'Middle East', lat: 29.0, lon: 45.0 },
      { keys: ['siberia'], name: 'Siberia', lat: 62.0, lon: 100.0 },
      { keys: ['patagonia'], name: 'Patagonia', lat: -45.0, lon: -69.0 },
      { keys: ['horn of africa'], name: 'Horn of Africa', lat: 8.0, lon: 45.0 },
      { keys: ['mediterranean'], name: 'Mediterranean', lat: 38.0, lon: 15.0 },
    ];
    const placeStatusEl = root.querySelector('#scanner-place-status');
    function setPlaceStatus(text, isError = false) {
      if (!placeStatusEl) return;
      placeStatusEl.textContent = text || '';
      placeStatusEl.classList.toggle('is-error', Boolean(isError));
      clearTimeout(setPlaceStatus.timer);
      if (text && !isError) setPlaceStatus.timer = setTimeout(() => setPlaceStatus(''), 6000);
    }

    async function handlePlaceSearch() {
      const q = placeQueryIn?.value?.trim();
      if (!q) return;
      setPlaceStatus('');
      const coordMatch = q.match(/^\s*(-?\d+(?:[.,]\d+)?)\s*[,;\s]\s*(-?\d+(?:[.,]\d+)?)\s*$/);
      if (coordMatch) {
        const lat = Number(coordMatch[1].replace(',', '.'));
        const lon = Number(coordMatch[2].replace(',', '.'));
        if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
          selectLocation(lat, lon, `${lat.toFixed(2)}°, ${lon.toFixed(2)}°`, 'custom', 'Entered coordinates', true);
        } else {
          setPlaceStatus('Latitude must be between -90 and 90, longitude between -180 and 180.', true);
        }
        return;
      }
      const lower = q.toLowerCase();
      const broad = BROAD_REGIONS.find((r) => r.keys.some((k) => lower.includes(k)));
      if (broad) {
        selectLocation(broad.lat, broad.lon, broad.name, 'custom', 'Region centre point', true);
        setPlaceStatus(`Using the centre of ${broad.name}. Click the map to pick another point.`);
        return;
      }
      if (placeSearchBtn) placeSearchBtn.textContent = '…';
      try {
        const data = await apiGeocode(q);
        if (data?.results?.[0]) {
          const hit = data.results[0];
          const shortName = String(hit.display_name).split(',').slice(0, 2).join(', ');
          selectLocation(Number(hit.lat), Number(hit.lon), shortName, 'custom', 'Geocoded location', true);
        } else {
          setPlaceStatus(`No place found for "${q}". Try a city, state or country, e.g. "Iowa".`, true);
        }
      } catch (_e) {
        setPlaceStatus('Place search is unavailable. Click the map or type coordinates like 41.5, -91.', true);
      }
      if (placeSearchBtn) placeSearchBtn.textContent = 'Fly To';
    }
    placeSearchBtn?.addEventListener('click', handlePlaceSearch);
    placeQueryIn?.addEventListener('keydown', (e) => { if (e.key === 'Enter') handlePlaceSearch(); });

    paramSelect?.addEventListener('change', (e) => {
      state.userVar = true;
      state.parameter = e.target.value;
      if (state.scanResult) renderResults();
    });
    regionSelect?.addEventListener('change', (e) => {
      const r = regions.find((item) => item.id === e.target.value);
      if (r) selectLocation(r.latitude, r.longitude, r.name, r.id, r.biome, true);
    });
    latInput?.addEventListener('input', (e) => { state.latitude = Number(e.target.value); });
    lonInput?.addEventListener('input', (e) => { state.longitude = Number(e.target.value); });
    function applyTypedCoords() {
      const lat = Number(latInput?.value);
      const lon = Number(lonInput?.value);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return;
      selectLocation(lat, lon, `${lat.toFixed(2)}°, ${lon.toFixed(2)}°`, 'custom', 'Entered coordinates', false);
    }
    latInput?.addEventListener('change', applyTypedCoords);
    lonInput?.addEventListener('change', applyTypedCoords);
    startInput?.addEventListener('input', (e) => { state.start = Number(e.target.value); });
    endInput?.addEventListener('input', (e) => { state.end = Number(e.target.value); });
    modeSelect?.addEventListener('change', (e) => {
      state.mode = e.target.value;
      investigate();
    });
    horizonSelect?.addEventListener('change', (e) => {
      state.horizon = e.target.value;
      investigate();
    });

    function getActiveItem() {
      if (!state.scanResult || !Array.isArray(state.scanResult.items)) return null;
      return (
        state.scanResult.items.find((i) => i.code === state.parameter) ||
        state.scanResult.significantItems?.[0] ||
        state.scanResult.items[0]
      );
    }

    function downloadCsv() {
      const item = getActiveItem();
      if (!item) return;
      const csv = [
        `date,${item.code}_${item.unit}`,
        ...item.points.map((p) => `${p.date},${p.value}`),
      ].join('\n');
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
      a.download = `trend-detective-${item.code}-${state.latitude}-${state.longitude}.csv`;
      a.click();
    }

    function downloadPng() {
      const url = activeChart?.toBase64Image();
      if (!url) return;
      const a = document.createElement('a');
      a.href = url;
      a.download = `trend-detective-${state.parameter}.png`;
      a.click();
    }

    function downloadJson() {
      if (!state.scanResult) return;
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([JSON.stringify(state.scanResult, null, 2)], { type: 'application/json' }));
      a.download = `trend-detective-scan-${state.latitude}-${state.longitude}.json`;
      a.click();
    }

    function renderResults() {
      if (!resultsPanel) return;
      if (activeChart) {
        activeChart.destroy();
        activeChart = null;
      }
      if (launchBtn) {
        launchBtn.disabled = state.loading;
        launchBtn.innerHTML = state.loading
          ? `${icon('loader-circle', { size: 18, className: 'spin' })} Analyzing all variables…`
          : `${icon('play', { size: 18, fill: 'currentColor' })} Start Analysis`;
      }

      if (state.loading) {
        resultsPanel.innerHTML = `
          <div class="empty-state">
            ${icon('loader-circle', { size: 44, className: 'spin cyan' })}
            <h2>Scanning NASA POWER variables for ${escapeHtml(state.regionName)}…</h2>
            <p>Computing OLS trends, Mann–Kendall significance, and phenomenon probabilities.</p>
          </div>
        `;
        return;
      }

      if (state.error) {
        resultsPanel.innerHTML = `
          <div class="error-state">
            ${icon('triangle-alert', { size: 34 })}
            <h2>Scan unavailable</h2>
            <p>${escapeHtml(state.error)}</p>
            <button type="button" class="button secondary" data-action="retry">
              ${icon('rotate-ccw', { size: 16 })} Retry Scan
            </button>
          </div>
        `;
        resultsPanel.querySelector('[data-action="retry"]')?.addEventListener('click', investigate);
        return;
      }

      if (!state.scanResult) return;

      const scan = state.scanResult;
      const topPhenomena = (scan.phenomena || scan.items || []).slice(0, 6);
      const sigList = scan.significantItems || [];
      const displayVars = state.showAllVars
        ? scan.items
        : sigList.length > 0
          ? sigList
          : scan.items;

      if (kpiTotalEl) kpiTotalEl.textContent = String(scan.totalScanned || scan.items.length);
      if (kpiSigEl) kpiSigEl.textContent = `${scan.significantCount} / ${scan.totalScanned}`;
      if (kpiRiskEl) {
        const peak = topPhenomena[0];
        kpiRiskEl.textContent = peak ? `${peak.risk.score}%` : '0%';
      }

      const activeItem = getActiveItem();
      if (activeItem && paramSelect) paramSelect.value = activeItem.code;

      // Event-based risks (/api/hazards): one card per hazard, headline from the preferred
      // dataset, the other datasets shown as a cross-check.
      const HAZARD_CARDS = [
        { key: 'heatWave', title: 'Heat wave', code: 'T2M_MAX', what: 'years with a 1-in-5-year heat wave' },
        { key: 'rainDrought', title: 'Severe drought', code: 'PRECTOTCORR', what: 'years with a 1-in-5-year rainfall deficit' },
        { key: 'extremeRain', title: 'Extreme rainfall', code: 'PRECTOTCORR', what: 'years with a 1-in-5-year downpour' },
      ];
      const PENDING_LABELS = { power: 'NASA POWER', 'giovanni,noaa': 'NOAA stations and NASA GPM / GLDAS' };
      const shortReason = (text) => String(text || '').split(/(?<=[.:])\s/)[0].replace(/[.:]$/, '');
      const levelClass = (level) => 'level-' + String(level || '').toLowerCase().replace(/\s+/g, '-');
      const hazardCardHtml = (card) => {
        const results = (state.hazards && state.hazards[card.key] && state.hazards[card.key].results) || [];
        const ok = results.filter((r) => !r.error && Number.isFinite(r.score));
        const failed = results.filter((r) => r.error);
        const head = ok[0];
        const pending = state.hazardsPending.map((p) => PENDING_LABELS[p] || p);
        const selected = state.parameter === card.code ? ' is-selected' : '';
        if (!head) {
          const waiting = pending.length > 0;
          const message = waiting
            ? `Checking ${escapeHtml(pending.join(' and '))}…`
            : escapeHtml(state.hazardsError || (failed[0] ? `${failed[0].sourceLabel}: ${shortReason(failed[0].error)}` : 'No dataset could measure this here.'));
          return `
            <article class="phenomenon-card level-none${selected}" data-select-var="${card.code}">
              <div class="phenomenon-gauge">${waiting ? icon('loader-circle', { size: 30, className: 'spin' }) : '<strong>–</strong>'}</div>
              <div class="phenomenon-info">
                <span class="phenomenon-level-tag">${waiting ? 'Detecting' : 'Unavailable'}</span>
                <h3>${card.title}</h3>
                <p class="phenomenon-detail">${message}</p>
              </div>
            </article>`;
        }
        const events = head.events || [];
        const unitWord = 'years';
        const MAX_SHOWN = 10;
        const shown = events.slice(-MAX_SHOWN).map((e) => e.label).join(', ');
        const hidden = events.length - MAX_SHOWN;
        let detail = head.yearsWithEvents
          ? `<strong>${head.yearsWithEvents} of ${head.yearsAnalysed} ${unitWord}</strong>: ${hidden > 0 ? `${hidden} earlier, then ` : ''}${escapeHtml(shown)}.`
          : `<strong>None</strong> in the ${head.yearsAnalysed} ${unitWord} of this period.`;
        const later = (head.laterEventYears || []).slice(-3);
        if (later.length) detail += ` After ${state.end}: ${later.join(', ')}.`;
        let context = '';
        if (head.baselineScore != null) {
          context = card.key === 'flashDrought'
            ? `Whole record ${escapeHtml(head.baselinePeriod)}: ${head.baselineScore}% of years.`
            : `Normal for ${escapeHtml(head.baselinePeriod)}: ${head.baselineScore}% of years.`;
        }
        if (card.key === 'flashDrought' && head.activeSeason) {
          context += ` Watched: ${escapeHtml(head.activeSeason)} (from the data), ${escapeHtml(head.resolution || 'monthly')}.`;
        }
        let trendText = '';
        if (head.trend && Number.isFinite(head.trend.perDecade)) {
          const t = head.trend;
          trendText = Math.abs(t.perDecade) < 0.05
            ? `${escapeHtml(t.label)}: no clear trend.`
            : `${escapeHtml(t.label)}: ${t.perDecade > 0 ? '+' : ''}${t.perDecade}${t.unitShort ? ' ' + escapeHtml(t.unitShort) : ''} per decade${t.pValue < 0.05 ? ' (significant)' : ''}.`;
        }
        const trend = context || trendText ? `<p class="phenomenon-trend">${[context, trendText].filter(Boolean).join(' ')}</p>` : '';
        const agree = ok.slice(1).map((r) => `${escapeHtml(r.sourceLabel)}: <strong>${r.score}%</strong>`);
        const agreeHtml = agree.length ? `<p class="phenomenon-agree">Also measured by ${agree.join(' · ')}</p>` : '';
        const missing = failed.map((r) => `${escapeHtml(r.sourceLabel)} (${escapeHtml(shortReason(r.error))})`);
        const pendingHtml = pending.length ? `<p class="phenomenon-missing">${icon('loader-circle', { size: 12, className: 'spin' })} Checking ${escapeHtml(pending.join(' and '))}…</p>` : '';
        const missingHtml = missing.length && !pending.length ? `<p class="phenomenon-missing">Not included: ${missing.join('; ')}</p>` : '';
        const tooltip = `${head.method || ''} ${head.caveat || ''}`.trim();
        return `
          <article class="phenomenon-card ${levelClass(head.level)}${selected}" data-select-var="${card.code}" title="${escapeHtml(tooltip)}">
            <div class="phenomenon-gauge" aria-label="${head.score} percent">
              <svg viewBox="0 0 42 42" role="img">
                <circle class="gauge-track" cx="21" cy="21" r="15.9"></circle>
                <circle class="gauge-fill" cx="21" cy="21" r="15.9" pathLength="100" stroke-dasharray="${head.score} 100"></circle>
              </svg>
              <strong>${head.score}%</strong>
            </div>
            <div class="phenomenon-info">
              <span class="phenomenon-level-tag">${escapeHtml(head.level)}</span>
              <h3>${card.title}</h3>
              <p class="phenomenon-detail">${detail}</p>
              ${trend}
              ${agreeHtml}
              ${pendingHtml}${missingHtml}
              <p class="phenomenon-source">${escapeHtml(head.sourceLabel)} · ${escapeHtml(head.product || '')} · share of ${card.what}</p>
            </div>
          </article>`;
      };
      const phenomenaHtml = HAZARD_CARDS.map(hazardCardHtml).join('');

      const sigVarsHtml = displayVars
        .map((item) => {
          const isSelected = activeItem && activeItem.code === item.code;
          return `
            <article class="sig-var-card ${item.significant ? 'is-significant' : ''} ${isSelected ? 'is-selected' : ''}" data-select-var="${escapeHtml(item.code)}">
              <span class="sig-var-code">${escapeHtml(item.code)}</span>
              <h3>${escapeHtml(item.name)}</h3>
              <span class="sig-var-pvalue">p = ${Number(item.pValue).toPrecision(2)}${item.source ? ` · ${escapeHtml(item.source)}` : ''}</span>
            </article>
          `;
        })
        .join('');

      const reg = activeItem.analysis.regression;
      const mk = activeItem.analysis.mannKendall;

      // Progress of the second scan pass and datasets that could not be included.
      // Group datasets that failed for the same reason (e.g. GLDAS and GPM without a token).
      const skippedByReason = new Map();
      (scan.skipped || []).forEach((s) => {
        const sources = skippedByReason.get(s.reason) || new Set();
        sources.add(s.source);
        skippedByReason.set(s.reason, sources);
      });
      const scanNotes = [
        state.extraLoading
          ? `${icon('loader-circle', { size: 15, className: 'spin' })} Adding MODIS, GLDAS, GPM IMERG and NOAA results… The first scan of a place can take up to a minute.`
          : '',
        state.extraError ? `${icon('triangle-alert', { size: 15 })} ${escapeHtml(state.extraError)}` : '',
        ...Array.from(skippedByReason, ([reason, sources]) =>
          `${icon('triangle-alert', { size: 15 })} <span><strong>${escapeHtml([...sources].join(', '))}</strong> not included: ${escapeHtml(reason)}</span>`
        ),
      ].filter(Boolean);
      const scanNotesHtml = scanNotes.length
        ? `<div class="scan-notes">${scanNotes.map((n) => `<p>${n}</p>`).join('')}</div>`
        : '';
      const meta = activeItem.metadata || null;
      const alphaNum = Number(state.alpha || 0.05);
      const trendUp = activeItem.trendPerDecade > 0;
      const seemsTrend = reg.pValue < alphaNum || mk.pValue < alphaNum;
      const isSig = reg.pValue < alphaNum && mk.pValue < alphaNum;
      const trendLead = Math.abs(activeItem.trendPerDecade) < 1e-9
        ? 'The series looks flat.'
        : `The series ${seemsTrend ? 'appears to have' : 'does not clearly show'} a ${trendUp ? 'rising' : 'falling'} trend: ${trendUp ? '+' : ''}${activeItem.trendPerDecade.toFixed(3)} ${activeItem.unit} per decade (${state.start}–${state.end}).`;

      resultsPanel.innerHTML = `
        <div class="scanner-workspace" style="display:flex;flex-direction:column;gap:24px">
          <section class="scanner-section" style="order:4">
            <div class="scanner-section-head">
              <div>
                <h2>Potential Risks</h2>
              </div>
            </div>
            <div class="phenomena-grid">
              ${phenomenaHtml}
            </div>
          </section>

          <section class="scanner-section" style="order:3">
            <div class="scanner-section-head">
              <div>
                <h2>Variables with Statistically Significant Change</h2>
              </div>
              <div class="sig-filter-toggle">
                <button type="button" data-filter-vars="sig" class="${!state.showAllVars ? 'active' : ''}">
                  Significant Only
                </button>
                <button type="button" data-filter-vars="all" class="${state.showAllVars ? 'active' : ''}">
                  All Variables
                </button>
              </div>
            </div>
            ${scanNotesHtml}
            <div class="sig-vars-grid">
              ${sigVarsHtml}
            </div>
          </section>

          <div class="chart-card" id="focus-chart-card" style="order:1">
            <div class="chart-title">
              <div>
                <span class="step-tag">Steps 3-4 · Time series</span><h2>${escapeHtml(activeItem.name)} (${escapeHtml(activeItem.unit)})</h2><p class="step-lead">${trendLead}</p>
                <p class="chart-source">
                  ${escapeHtml(activeItem.source || 'NASA POWER')}${meta && meta.product ? ` · ${escapeHtml(meta.product)}` : ''}${meta && meta.station ? ` · station ${escapeHtml(meta.station)} (${escapeHtml(meta.stationDistance || '')})` : ''}
                </p>
              </div>
            </div>
            <div class="chart-wrap">
              <canvas id="trend-canvas"></canvas>
            </div>
          </div>

          <div class="step-verdict ${isSig ? 'is-sig' : ''}" style="order:2">
              <span class="step-tag">Step 5 · Significance (α = ${alphaNum})</span>
              <h3>${escapeHtml(activeItem.verdict || (isSig ? 'Significant trend' : 'No statistically significant trend'))}</h3>
              <p>${isSig ? 'Both the regression and the Mann–Kendall test reject the no-trend hypothesis.' : 'At least one test does not reject the no-trend hypothesis. A non-significant result is not proof that no change exists.'}</p>
            </div>
            <div class="analysis-grid" style="order:2">
            <article class="analysis-card">
              <h3>Linear Regression</h3>
              <dl>
                <div><dt>Trend / decade</dt><dd>${activeItem.trendPerDecade > 0 ? '+' : ''}${activeItem.trendPerDecade.toFixed(3)} ${escapeHtml(activeItem.unit)}</dd></div>
                <div><dt>R² fit</dt><dd>${reg.rSquared.toFixed(3)}</dd></div>
                <div><dt>p-value</dt><dd>${Number(reg.pValue).toPrecision(3)}</dd></div>
                <div><dt>Historical range</dt><dd>${activeItem.firstValue.toFixed(2)} → ${activeItem.lastValue.toFixed(2)} ${escapeHtml(activeItem.unit)}</dd></div>
              </dl>
            </article>
            <article class="analysis-card">
              <h3>Mann–Kendall &amp; Sen’s Slope</h3>
              <dl>
                <div><dt>Kendall’s tau</dt><dd>${mk.tau.toFixed(3)}</dd></div>
                <div><dt>Z statistic</dt><dd>${mk.z.toFixed(3)}</dd></div>
                <div><dt>p-value</dt><dd>${Number(mk.pValue).toPrecision(3)}</dd></div>
                <div><dt>Sen slope / decade</dt><dd>${activeItem.senPerDecade > 0 ? '+' : ''}${activeItem.senPerDecade.toFixed(3)} ${escapeHtml(activeItem.unit)}</dd></div>
              </dl>
            </article>
          </div>
        </div>
      `;

      resultsPanel.querySelectorAll('[data-select-var]').forEach((card) => {
        card.addEventListener('click', () => {
          const code = card.getAttribute('data-select-var');
          if (code) {
            state.parameter = code;
            renderResults();
            document.getElementById('focus-chart-card')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
        });
      });

      resultsPanel.querySelectorAll('[data-filter-vars]').forEach((btn) => {
        btn.addEventListener('click', () => {
          state.showAllVars = btn.getAttribute('data-filter-vars') === 'all';
          renderResults();
        });
      });

      resultsPanel.querySelector('[data-action="csv"]')?.addEventListener('click', downloadCsv);
      resultsPanel.querySelector('[data-action="png"]')?.addEventListener('click', downloadPng);
      resultsPanel.querySelector('[data-action="json"]')?.addEventListener('click', downloadJson);

      const canvas = resultsPanel.querySelector('#trend-canvas');
      if (canvas) {
        activeChart = createTrendChart(canvas, {
          points: activeItem.points,
          fitted: reg.fitted,
          unit: activeItem.unit,
        });
      }
    }

    // Two passes: NASA POWER first (seconds), then the slower sources, merged when they arrive.
    let scanRun = 0;
    function mergeHazards(current, more) {
      const out = current ? JSON.parse(JSON.stringify(current)) : {};
      Object.entries(more || {}).forEach(([key, value]) => {
        const list = [...((out[key] && out[key].results) || []), ...((value && value.results) || [])];
        list.sort((a, b) => (a.priority ?? 9) - (b.priority ?? 9));
        out[key] = { results: list };
      });
      return out;
    }

    function loadHazards(run) {
      state.hazards = null;
      state.hazardsError = '';
      state.hazardsPending = ['power', 'giovanni,noaa'];
      state.hazardsPending.slice().forEach((sources) => {
        apiHazards(state, sources)
          .then((data) => {
            if (run !== scanRun) return;
            state.hazards = mergeHazards(state.hazards, data);
          })
          .catch((err) => {
            if (run !== scanRun) return;
            if (!state.hazardsError) state.hazardsError = err instanceof Error ? err.message : 'Risk detection failed.';
          })
          .finally(() => {
            if (run !== scanRun) return;
            state.hazardsPending = state.hazardsPending.filter((p) => p !== sources);
            if (state.scanResult && !state.loading) renderResults();
          });
      });
    }

    async function investigate() {
      const run = ++scanRun;
      loadHazards(run);
      state.loading = true;
      state.error = '';
      state.extraLoading = false;
      state.extraError = '';
      renderResults();
      try {
        const first = await apiScanRegion({ ...state, sources: 'power' });
        if (run !== scanRun) return;
        state.scanResult = first;
        if (first && first.significantItems?.length > 0 && !params.get('parameter') && !state.userVar) {
          state.parameter = first.significantItems[0].code;
        }
      } catch (err) {
        if (run !== scanRun) return;
        state.error = err instanceof Error ? err.message : 'Regional scan failed.';
      } finally {
        if (run === scanRun) {
          state.loading = false;
          state.extraLoading = !state.error;
          renderResults();
        }
      }
      if (state.error || run !== scanRun) return;
      try {
        const more = await apiScanRegion({ ...state, sources: 'modis,giovanni,noaa' });
        if (run !== scanRun) return;
        state.scanResult = mergeScans(state.scanResult, more);
      } catch (err) {
        if (run !== scanRun) return;
        state.extraError = err instanceof Error ? err.message : 'Other datasets unavailable.';
      } finally {
        if (run === scanRun) {
          state.extraLoading = false;
          renderResults();
        }
      }
    }

    launchBtn?.addEventListener('click', investigate);
    // Auto-run scan on initial visit so the user immediately sees the region analysis
    investigate();
  }

  // --- Variables Page Controller ---
  function initVariablesPage() {
    const root = document.getElementById('variables-root');
    if (!root) return;
    const variables = CATALOG.variables;
    const categories = ['All', ...new Set(variables.map((v) => v.category))];
    let search = '';
    let category = 'All';
    let selected = 'T2M';

    root.innerHTML = `
      <div class="catalogue-tools">
        <div class="search-field">
          ${icon('search', { size: 17 })}
          <input type="text" id="variable-search" placeholder="Search variables or NASA codes" />
        </div>
        <div class="filter-tabs" id="category-tabs"></div>
      </div>
      <div class="variable-grid" id="variable-grid"></div>
    `;

    const searchInput = root.querySelector('#variable-search');
    const catTabs = root.querySelector('#category-tabs');
    const grid = root.querySelector('#variable-grid');

    function renderAll() {
      if (catTabs) {
        catTabs.innerHTML = categories
          .map(
            (c) =>
              `<button type="button" data-cat="${escapeHtml(c)}" class="${category === c ? 'active' : ''}">${escapeHtml(c)}</button>`
          )
          .join('');
        catTabs.querySelectorAll('button[data-cat]').forEach((b) =>
          b.addEventListener('click', () => {
            category = b.getAttribute('data-cat') || 'All';
            renderAll();
          })
        );
      }
      if (grid) {
        const q = search.toLowerCase();
        const filtered = variables.filter(
          (v) =>
            (category === 'All' || v.category === category) &&
            `${v.name} ${v.code} ${v.definition}`.toLowerCase().includes(q)
        );
        grid.innerHTML = filtered
          .map((v) => {
            const isSel = selected === v.code;
            return `
              <article class="${isSel ? 'variable-card selected' : 'variable-card'}" data-var="${v.code}" data-sel="${v.selectable}">
                <div>
                  <span class="code">${escapeHtml(v.code)}</span>
                </div>
                <h3><strong>${escapeHtml(v.name)}</strong></h3>
                <dl>
                  <div><dt>Unit</dt><dd>${escapeHtml(v.unit)}</dd></div>
                  <div><dt>Source</dt><dd>${escapeHtml(v.source)}</dd></div>
                  ${v.access && !v.access.startsWith('Open, no account') ? `<div><dt>Access</dt><dd>${escapeHtml(v.access)}</dd></div>` : ''}
                </dl>
              </article>
            `;
          })
          .join('');

        grid.querySelectorAll('article[data-sel="true"]').forEach((card) =>
          card.addEventListener('click', (e) => {
            if (e.target.closest('a')) return;
            selected = card.getAttribute('data-var') || 'T2M';
            renderAll();
          })
        );
      }
    }

    searchInput?.addEventListener('input', (e) => {
      search = e.target.value;
      renderAll();
    });
    renderAll();
  }

  // --- Regions Page Controller ---
  function initRegionsPage() {
    const root = document.getElementById('regions-root');
    if (!root) return;
    const regions = CATALOG.regions;
    let latitude = 13.5;
    let longitude = 2.1;
    let place = 'Sahel / Niger';
    let map = null;
    let marker = null;

    root.innerHTML = `
      <div class="map-sidebar">
        <div class="map-search">
          ${icon('search', { size: 17 })}
          <input type="text" id="place-query" placeholder="Search a city or place" />
          <button type="button" id="place-search-btn">Go</button>
        </div>
        <h3>Scientific regions</h3>
        <div class="region-list" id="region-list"></div>
      </div>
      <div class="map-stage">
        <div id="leaflet-map" class="leaflet-map"></div>
        <div class="coordinate-card">
          <span>Selected grid point</span>
          <strong id="selected-place">${escapeHtml(place)}</strong>
          <div>
            <label>Latitude<input type="number" id="coord-lat" min="-90" max="90" step=".01" value="${latitude}" /></label>
            <label>Longitude<input type="number" id="coord-lon" min="-180" max="180" step=".01" value="${longitude}" /></label>
            <button type="button" id="coord-update-btn">Update</button>
          </div>
          <p>
            NASA POWER reports the grid cell containing this point, not an exact measurement at the marker.
            <a href="${resolvePageHref(`/explorer?latitude=${latitude}&longitude=${longitude}`)}" id="investigate-point-link" class="text-link" style="margin-left: 8px;">Investigate point &rarr;</a>
          </p>
        </div>
      </div>
    `;

    const listEl = root.querySelector('#region-list');
    const placeEl = root.querySelector('#selected-place');
    const latIn = root.querySelector('#coord-lat');
    const lonIn = root.querySelector('#coord-lon');
    const updBtn = root.querySelector('#coord-update-btn');
    const qIn = root.querySelector('#place-query');
    const goBtn = root.querySelector('#place-search-btn');
    const invLink = root.querySelector('#investigate-point-link');
    const mapEl = root.querySelector('#leaflet-map');

    function renderRegions() {
      if (!listEl) return;
      listEl.innerHTML = regions
        .map(
          (r) => `
            <button type="button" data-id="${r.id}" class="${place === r.name ? 'active' : ''}">
              <span>${icon('crosshair', { size: 15 })}</span>
              <div>
                <strong>${escapeHtml(r.name)}</strong>
                <small>${escapeHtml(r.biome)} · ${r.latitude}, ${r.longitude}</small>
              </div>
            </button>
          `
        )
        .join('');
      listEl.querySelectorAll('button[data-id]').forEach((b) =>
        b.addEventListener('click', () => {
          const r = regions.find((x) => x.id === b.getAttribute('data-id'));
          if (r) select(r.latitude, r.longitude, r.name);
        })
      );
    }

    function select(lat, lng, name = 'Custom point') {
      latitude = Number(Number(lat).toFixed(4));
      longitude = Number(Number(lng).toFixed(4));
      place = name;
      if (placeEl) placeEl.textContent = place;
      if (latIn) latIn.value = String(latitude);
      if (lonIn) lonIn.value = String(longitude);
      if (invLink) invLink.setAttribute('href', resolvePageHref(`/explorer?latitude=${latitude}&longitude=${longitude}`));
      renderRegions();
      if (map && marker) {
        map.flyTo([latitude, longitude], 5, { duration: 1.2 });
        marker.setLatLng([latitude, longitude]);
      }
    }

    async function doSearch() {
      const q = qIn?.value?.trim();
      if (!q) return;
      if (goBtn) goBtn.textContent = '…';
      try {
        const data = await apiGeocode(q);
        if (data?.results?.[0]) {
          select(Number(data.results[0].lat), Number(data.results[0].lon), data.results[0].display_name);
        }
      } catch (_e) {}
      if (goBtn) goBtn.textContent = 'Go';
    }

    goBtn?.addEventListener('click', doSearch);
    qIn?.addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });
    updBtn?.addEventListener('click', () => {
      select(Number(latIn?.value || latitude), Number(lonIn?.value || longitude), 'Custom point');
    });

    renderRegions();

    if (window.L && mapEl) {
      const L = window.L;
      const inPages = window.location.pathname.replace(/\\/g, '/').includes('/pages/');
      L.Icon.Default.imagePath = inPages ? '../assets/vendor/leaflet/images/' : './assets/vendor/leaflet/images/';
      map = L.map(mapEl, { zoomControl: false, worldCopyJump: true }).setView([latitude, longitude], 2);
      const tileTemplate =
        window.location.protocol === 'file:'
          ? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
          : '/api/tiles/{z}/{x}/{y}';
      L.tileLayer(tileTemplate, {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18,
      }).addTo(map);
      L.control.zoom({ position: 'bottomright' }).addTo(map);
      marker = L.marker([latitude, longitude]).addTo(map);
      map.on('click', (ev) => {
        select(ev.latlng.lat, ev.latlng.lng, 'Custom point');
      });
    }
  }

  // --- Comparison Page Controller ---
  function initComparisonPage() {
    const root = document.getElementById('comparison-root');
    if (!root) return;
    const regions = CATALOG.regions;
    const vars = CATALOG.variables.filter((v) => v.selectable);
    let regionA = 'svalbard';
    let regionB = 'amazon';
    let parameter = 'T2M';
    let loading = false;
    let error = '';
    let result = null;
    let charts = [];

    root.innerHTML = `
      <div class="comparison-controls">
        <label>Region A<select id="cmp-a">${regions.map((r) => `<option value="${r.id}" ${r.id === regionA ? 'selected' : ''}>${escapeHtml(r.name)}</option>`).join('')}</select></label>
        ${icon('arrow-right', { size: 20 })}
        <label>Region B<select id="cmp-b">${regions.map((r) => `<option value="${r.id}" ${r.id === regionB ? 'selected' : ''}>${escapeHtml(r.name)}</option>`).join('')}</select></label>
        <label>Variable<select id="cmp-v">${vars.map((v) => `<option value="${v.code}" ${v.code === parameter ? 'selected' : ''}>${escapeHtml(v.name)}</option>`).join('')}</select></label>
        <button type="button" class="button primary" id="cmp-btn">${icon('scale', { size: 17 })} Compare regions</button>
      </div>
      <div id="cmp-out"></div>
    `;

    const selA = root.querySelector('#cmp-a');
    const selB = root.querySelector('#cmp-b');
    const selV = root.querySelector('#cmp-v');
    const btn = root.querySelector('#cmp-btn');
    const out = root.querySelector('#cmp-out');

    selA?.addEventListener('change', (e) => { regionA = e.target.value; });
    selB?.addEventListener('change', (e) => { regionB = e.target.value; });
    selV?.addEventListener('change', (e) => { parameter = e.target.value; });

    function render() {
      charts.forEach((c) => c?.destroy());
      charts = [];
      if (btn) {
        btn.disabled = loading;
        btn.innerHTML = loading
          ? `${icon('loader-circle', { size: 17, className: 'spin' })} Compare regions`
          : `${icon('scale', { size: 17 })} Compare regions`;
      }
      const errHtml = error ? `<div class="error-banner">${escapeHtml(error)} No simulated data were substituted.</div>` : '';
      if (!result && !loading) {
        out.innerHTML = `
          ${errHtml}
          <div class="comparison-empty">
            ${icon('scale', { size: 40 })}
            <h2>One variable. Two places. Comparable evidence.</h2>
            <p>Run the same annual trend workflow for both regions to reveal spatial differences without implying causation.</p>
          </div>
        `;
        return;
      }
      if (loading && !result) {
        out.innerHTML = `
          <div class="comparison-empty">
            ${icon('loader-circle', { size: 40, className: 'spin cyan' })}
            <h2>Comparing regions…</h2>
            <p>Retrieving real NASA POWER observations for both locations.</p>
          </div>
        `;
        return;
      }
      if (!result) return;
      const def = vars.find((v) => v.code === parameter) || vars[0];
      const first = regions.find((r) => r.id === regionA) || regions[0];
      const second = regions.find((r) => r.id === regionB) || regions[3];
      const items = [
        ['A', first, result.regionA, 'cmp-c-a'],
        ['B', second, result.regionB, 'cmp-c-b'],
      ];
      out.innerHTML = `
        ${errHtml}
        <div class="comparison-results">
          ${items
            .map(
              ([lbl, reg, d, cid]) => `
                <article class="comparison-region">
                  <div class="comparison-region-title">
                    <span>REGION ${lbl}</span>
                    <h2>${escapeHtml(reg.name)}</h2>
                    <p>${reg.latitude}, ${reg.longitude} · NASA POWER grid cell</p>
                  </div>
                  <div class="mini-stats">
                    <div><small>Trend / decade</small><strong>${d.analysis.trendPerDecade > 0 ? '+' : ''}${d.analysis.trendPerDecade.toFixed(3)} ${escapeHtml(def.unit)}</strong></div>
                    <div><small>OLS p-value</small><strong>${Number(d.analysis.regression.pValue).toPrecision(3)}</strong></div>
                    <div><small>Verdict</small><strong>${escapeHtml(d.analysis.verdict)}</strong></div>
                    <div><small>Risk indicator</small><strong>${d.analysis.risk.score}% · ${escapeHtml(d.analysis.risk.level)}</strong></div>
                  </div>
                  <div class="comparison-chart"><canvas id="${cid}"></canvas></div>
                </article>
              `
            )
            .join('')}
          <div class="comparison-verdict">
            <span>Difference in OLS trends</span>
            <strong>${result.differencePerDecade.toFixed(3)} ${escapeHtml(def.unit)} / decade</strong>
            <p>${escapeHtml(result.interpretation)}</p>
          </div>
        </div>
      `;
      items.forEach(([, , d, cid]) => {
        const c = out.querySelector(`#${cid}`);
        if (c) charts.push(createTrendChart(c, { points: d.points, fitted: d.analysis.regression.fitted, unit: def.unit }));
      });
    }

    btn?.addEventListener('click', async () => {
      loading = true;
      error = '';
      render();
      try {
        const first = regions.find((r) => r.id === regionA) || regions[0];
        const second = regions.find((r) => r.id === regionB) || regions[3];
        result = await apiComparison({
          parameter,
          start: 1990,
          end: 2024,
          mode: 'annual',
          regionA: first,
          regionB: second,
        });
      } catch (err) {
        error = err instanceof Error ? err.message : 'Comparison failed.';
      } finally {
        loading = false;
        render();
      }
    });
    render();
  }

  // --- Sources Page Controller ---
  function initSourcesPage() {
    const root = document.getElementById('sources-root');
    if (!root) return;
    const sources = CATALOG.sources;

    root.innerHTML = `
      <div class="source-grid">
        ${sources
          .map(
            (s) => `
              <article class="source-card">
                <h2>${escapeHtml(s.name)}</h2>
                <p class="source-connection">
                  ${s.status === 'FULLY INTEGRATED'
                    ? `Connected live${s.auth && !s.auth.startsWith('None') ? ` · ${escapeHtml(s.auth)}` : ''}`
                    : 'External workflow · no time-series API'}
                </p>
                <a href="${escapeHtml(s.url)}" target="_blank" rel="noreferrer">
                  Official documentation ${icon('arrow-up-right', { size: 15 })}
                </a>
              </article>
            `
          )
          .join('')}
      </div>
    `;
  }

  function boot() {
    initThemeAndHeader();
    initExplorerPage();
    initVariablesPage();
    initRegionsPage();
    initComparisonPage();
    initSourcesPage();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
