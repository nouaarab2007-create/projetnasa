# Trend Detective — NASA Earth Science Investigation Platform

Trend Detective is a multi-page scientific web application built for the **NASA International Space Apps Challenge**. It reproduces the Figma design in pure **HTML5, CSS3, and Vanilla JavaScript (ES6 modules)** on the frontend, powered by a **Python FastAPI** REST backend.

## Architecture

```
Trend_Detective_NASA/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI server (mounts /assets, /api, and multi-page HTML routes)
│   │   ├── config.py             # Runtime settings and upstream endpoints
│   │   ├── api/
│   │   │   ├── router.py         # Central /api router
│   │   │   └── routes/
│   │   │       ├── analysis.py   # GET /api/analysis (one variable) and GET /api/scan (all variables at a place)
│   │   │       ├── data.py       # GET /api/data (validated observations from any source)
│   │   │       ├── catalog.py    # GET /api/variables, /api/regions, /api/sources
│   │   │       ├── comparison.py # POST /api/comparison (two-region comparative analysis)
│   │   │       ├── geocode.py    # GET /api/geocode (Nominatim place search proxy)
│   │   │       ├── tiles.py      # GET /api/tiles/{z}/{x}/{y} (OSM raster tile proxy)
│   │   │       └── health.py     # GET /api/health (+ which tokens are set, never their values)
│   │   ├── science/
│   │   │   ├── statistics.py     # OLS regression, Student t-test, Mann-Kendall, Sen's slope
│   │   │   ├── extremes.py       # Heat-wave, extreme-rainfall and drought detection
│   │   │   ├── flash_drought_daily.py  # Flash drought from daily soil moisture (main)
│   │   │   ├── flash_drought.py  # Flash drought, monthly fallback
│   │   │   ├── risk.py           # Phenomenon risk screening indicator (0-100%)
│   │   │   ├── transform.py      # Annual aggregation & monthly anomalies
│   │   │   └── catalog.py        # Scientific variables, regions, and data sources
│   │   └── services/
│   │       ├── datasets.py       # Routes each variable to its connector (+ 24 h cache)
│   │       ├── nasa_power.py     # NASA POWER Monthly Point API client + TTL cache
│   │       ├── daily.py          # Daily series: POWER daily, NOAA GHCN-Daily, GPM IMERG daily
│   │       ├── hazards.py        # Heat wave / drought / extreme rain from every dataset
│   │       ├── modis.py          # MODIS NDVI / EVI / LAI / land temperature (ORNL DAAC)
│   │       ├── giovanni.py       # GLDAS + GPM IMERG via Giovanni time-series API
│   │       ├── noaa.py           # NOAA NCEI station data (Access Data Service, CDO v2 fallback)
│   │       ├── swot.py           # SWOT water-surface elevation (PO.DAAC Hydrocron)
│   │       ├── series.py         # Shared validation, monthly averaging, provenance
│   │       ├── geocoding.py      # OpenStreetMap Nominatim proxy
│   │       └── tiles.py          # OpenStreetMap tile cache proxy
│   ├── tests/                    # Automated pytest suite (all upstream services mocked)
│   └── requirements.txt
└── frontend/
    ├── index.html                # Root entry point (Home page)
    ├── pages/                    # Multi-page HTML5 views
    │   ├── index.html            # /            — Home & 5-step framework
    │   ├── explorer.html         # /explorer    — 5-step investigation + Risk % gauge
    │   ├── analysis.html         # /analysis    — Statistical testing workspace
    │   ├── variables.html        # /variables   — Scientific variable explorer
    │   ├── regions.html          # /regions     — Interactive Leaflet map & region selector
    │   ├── comparison.html       # /comparison  — Two-region synchronized comparison
    │   ├── sources.html          # /sources     — Data sources & mission status catalogue
    │   ├── methodology.html      # /methodology — Statistical formulas & bibliography
    │   ├── about.html            # /about       — Mission statement & values
    │   └── 404.html              # 404 Not Found
    └── assets/
        ├── css/                  # Modular CSS3 reproducing the Figma design tokens
        ├── js/                   # Modular Vanilla JS (core, components, page controllers)
        ├── images/               # Earth, Arctic, Sahel, Forest imagery & favicon
        └── vendor/               # Bundled Chart.js and Leaflet
```

## Trained flash-drought model (AI early warning)

The LightGBM + SHAP models (horizons 7, 14, 30 days) exported from the training notebook live in `backend/models/fd_bundle` and are served by `GET /api/flash-forecast?latitude=..&longitude=..[&date=YYYY-MM-DD][&horizon=7|14|30]` (code in `backend/app/ml` and `backend/app/services/flash_forecast.py`). `GET /api/flash-forecast/model` returns the test scores. The Explorer page shows the result in an *AI early warning* card (`frontend/assets/js/flash-forecast.js`). Install the scientific packages first: `pip install -r backend/requirements.txt` (numpy, pandas, scipy, scikit-learn, lightgbm, shap, joblib). Override the bundle location with `TD_FD_BUNDLE_DIR`.

## Running the Application

Run these from the project folder (the one that contains `backend` and `frontend`).

1. With the bundled Python (`.python` folder present):
   ```powershell
   .\.python\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```
   Or with your own Python (install the libraries once first):
   ```powershell
   py -m pip install -r backend/requirements.txt
   py -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```
2. Open `http://127.0.0.1:8000` in your browser.

## Running Automated Tests

```powershell
.\.python\python.exe -m pytest backend/tests
```

## Connected datasets

Every variable in `backend/app/science/catalog.py` names the connector that retrieves it.
All of them go through the same `/api/data`, `/api/analysis`, `/api/scan` and `/api/comparison` endpoints.

The Investigate page scans a place in two passes: NASA POWER first (a few seconds), then MODIS,
GLDAS, GPM IMERG and NOAA, merged in when they arrive. Datasets that cannot be used (for example
GLDAS without a token) are listed on the page with the reason. `/api/scan` accepts an optional
`sources=power,modis,giovanni,noaa` filter.

| Source | Variables | Service | Account |
|---|---|---|---|
| NASA POWER | T2M, T2M_MAX, T2M_MIN, TS, PRECTOTCORR, RH2M, QV2M, GWETROOT, ALLSKY_SFC_SW_DWN, CLOUD_AMT, WS10M, PS | POWER Monthly Point API | none |
| NASA MODIS (AppEEARS products) | MOD13Q1_NDVI, MOD13Q1_EVI, MOD15A2H_LAI, MOD11A2_LST_DAY | ORNL DAAC MODIS web service | none |
| NASA GLDAS | GLDAS_SOILM_0_10, GLDAS_ROOT_ZONE_SM, GLDAS_EVAP, GLDAS_SWE | Giovanni time-series API (replaces Hydrology Data Rods) | `EARTHDATA_TOKEN` |
| NASA Giovanni | GPM_IMERG_PRECIP | Giovanni time-series API | `EARTHDATA_TOKEN` |
| NOAA NCEI | NOAA_TAVG, NOAA_TMAX, NOAA_TMIN, NOAA_PRCP (nearest station) | NCEI Access Data Service; Climate Data Online v2 fallback | none (`NOAA_CDO_TOKEN` optional) |
| NASA SWOT | SWOT_WSE (river reach or lake) | PO.DAAC Hydrocron | none; pass `featureId` |
| RADARSAT, GEO.CA | — | No point time-series API: listed as external workflows | — |

Notes:
- Series are averaged per calendar month, then processed by the selected mode. In annual mode, years with fewer than 75 % of the best-covered year's months (e.g. the unfinished current year) are left out.
- Trends are fitted against real time in years, so missing months keep their true spacing. Rates are reported per year and per decade.
- If a start year is earlier than a dataset begins (MODIS/GLDAS 2000, SWOT 2023), it is moved forward and the provenance says so.
- First requests can take up to a minute (MODIS sends 10 composites per request; Giovanni returns 3-hourly data). Results are cached in memory for 24 h.
- SWOT is identified by an ID, not coordinates: river reach = 11 digits (e.g. `78340600051`, find them on https://www.swordexplorer.com), lake = 10 digits. Use monthly modes: the record starts in 2023.

### Tokens

Tokens are read from environment variables when the server starts and are never sent to the browser.

1. Create a free Earthdata account at https://urs.earthdata.nasa.gov, then **Generate Token**.
2. Start the server with it (PowerShell):
   ```powershell
   $env:EARTHDATA_TOKEN = "paste-your-token"
   # optional: $env:NOAA_CDO_TOKEN = "your-noaa-token"   (https://www.ncdc.noaa.gov/cdo-web/token)
   .\.python\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```
3. Check `http://127.0.0.1:8000/api/health`: `credentials.EARTHDATA_TOKEN` should be `true`.

### Potential risks (event detection)

The four "Potential Risks" cards count **events**, not long-term trends. Each one is computed from
every dataset that can measure it. The first available source is the headline; the others are
shown as a cross-check ("Also measured by ...") or listed under "Not included" with the reason.

| Risk | Event definition | Datasets |
|---|---|---|
| Heat wave | Year whose hottest 3-day spell in the 5 warmest months *of that place* (found in the data; all year where there is no seasonal cycle) beats the 1-in-5-year value of 1981-2010. Heat-wave days (3+ days above the 95th percentile, Perkins & Alexander 2013) and their trend are shown too. | NASA POWER daily T2M_MAX · NOAA GHCN-Daily TMAX (nearest good station) |
| Flash drought | Daily root-zone soil moisture in 5-day means falls from at or above the 40th to at or below the 20th percentile (same time of year) within 20 days and stays there at least 20 days (Ford & Labosier 2017; Otkin et al. 2018). Watched part of the year comes from the data: 5-day periods with a normal daily maximum below 10 °C, or soil moisture that never varies, are skipped. Monthly data only as a fallback. | NASA POWER daily GWETROOT · NASA GLDAS 3-hourly root-zone soil moisture, averaged per day (Giovanni) |
| Severe drought | Year whose driest 3-month rainfall is a 1-in-5-year deficit and reaches SPI-3 <= -1.5 (6.7th percentile, McKee et al. 1993, empirical). Months that normally get under 10 mm in 3 months (dry seasons, deserts) are skipped. | NASA POWER daily rain · NASA GPM IMERG daily (Giovanni) · NOAA GHCN-Daily PRCP |
| Extreme rainfall | Year whose wettest day beats the 1-in-5-year daily total of 1981-2010 (Rx1day, ETCCDI) | same three rainfall sources |

Score = share of years (seasons for flash drought) in the chosen period with at least one event.
Heat wave, severe drought and extreme rainfall are calibrated against 1981-2010 (or the whole record
when a dataset starts later, e.g. GPM IMERG 2001): in a stable climate about 20 % of years qualify,
so a higher score means the event has become more frequent. Levels: Low < 20 %, Moderate 20-39 %,
High 40-59 %, Very high >= 60 % (flash drought: 10 / 20 / 35 %). Events after the chosen end year
are listed so a period that stops just before a big event (e.g. 2011 vs the 2012 US flash drought)
is not misleading.

No detector uses a region, a hemisphere or fixed months: every threshold and season comes from
the record at the selected point. `backend/tests/test_validation_climates.py` checks every detector
in eight simulated climates (Great Plains, Mediterranean, southern Australia, Indian monsoon,
equatorial Congo, boreal Canada, Sahel, Pampas) with events inserted at random dates: flash
droughts found, heat waves found, wet-season droughts found, no drought reported for a normal dry
season, slow drying not reported as a flash drought, frozen months ignored.

Direct call: `/api/hazards?latitude=39.1&longitude=-94.58&start=2000&end=2024`
(add `&sources=power` or `&sources=giovanni,noaa` to limit the datasets).
GPM IMERG and GLDAS need `EARTHDATA_TOKEN`; NASA POWER and NOAA need no account.

### Quick checks (server running)

```
/api/scan?latitude=31.63&longitude=-8&start=2001&end=2024&mode=annual
/api/hazards?latitude=39.1&longitude=-94.58&start=2000&end=2024
/api/analysis?parameter=MOD13Q1_NDVI&latitude=31.63&longitude=-8&start=2001&end=2024&mode=annual
/api/analysis?parameter=NOAA_TAVG&latitude=31.63&longitude=-8&start=1990&end=2024&mode=annual
/api/analysis?parameter=GLDAS_SOILM_0_10&latitude=31.63&longitude=-8&start=2001&end=2024&mode=annual
/api/analysis?parameter=SWOT_WSE&featureId=78340600051&start=2023&end=2025&mode=raw
```

## Editing the frontend

`scripts/generate_site.py` generates every page in `frontend/pages`, `frontend/index.html`,
`frontend/assets/css/main.css` and `frontend/assets/js/app.bundle.js` (it embeds the catalogue).
Edit the generator, then run:

```powershell
.\.python\python.exe scripts/generate_site.py
```

