"""
power_client.py  --  the ONLY file that talks to NASA POWER.  The model (flash_drought_model.py) never touches the network.

What it does
  1. NasaPowerClient.get(lat, lon, start, end)  -> daily table with the 8 raw variables the model needs (nothing else is requested;
     VAD and ET0 are computed inside the model with FAO-56).
  2. build_points(step)                          -> a global grid of LAND points (what "all regions" means in practice).
  3. fetch_all(lib, client, points)              -> asks the API for every point, stores it in the library. Resumable.
  4. predict_live(lib, client, lat, lon, date)   -> for ANY place and date: pulls the last days (+ the 2005-2014 baseline the first
     time that place is seen) from the API and returns the risk JSON. This is what the interface backend calls.

If your team's API is a wrapper (not the public POWER URL), pass your own function:
    client = NasaPowerClient(fetch=my_fetch)      # my_fetch(lat, lon, start, end, parameters) -> DataFrame: date + one column per parameter

Safety checks built in: units are read from the API answer (the AG community must give MJ/m2/day, kPa, m/s, mm/day, %, degC);
a wrong unit stops the run instead of silently corrupting ET0.
"""
from __future__ import annotations
import os, json, time, warnings
import numpy as np, pandas as pd
from app.ml import flash_drought_model as fd

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = list(fd.POWER_RAW_COLS)                 # the 8 raw variables, kept in sync with the model's data contract
COMMUNITY = "AG"                                 # AG gives MJ/m2/day for radiation (RE/SB give kWh/m2/day): do not change

# accepted spellings of the units (compared after normalisation); GWETROOT is dimensionless -> not checked
EXPECTED_UNITS = {"PRECTOTCORR": {"mm/day"}, "T2M_MAX": {"c", "degc", "degreec", "celsius"}, "T2M_MIN": {"c", "degc", "degreec", "celsius"},
                  "RH2M": {"%", "percent"}, "WS2M": {"m/s"}, "ALLSKY_SFC_SW_DWN": {"mj/m2/day"}, "PS": {"kpa"}}

class PowerError(Exception): """Any problem getting data (network, empty answer, missing variable)."""
class PowerParameterError(PowerError): """HTTP 400/422: the request itself is wrong (parameter name, dates, coordinates). Retrying cannot help."""
class PowerUnitError(PowerError): """The API answered in units the model cannot use."""

def _norm_unit(u) -> str:
    return str(u).strip().lower().replace(" ", "").replace("\u00b2", "2").replace("^", "").replace("\u00b0", "").replace("-", "")

def check_units(js: dict) -> list[str]:
    """Compare the units announced by the API (js['parameters'][name]['units']) with what the model needs. Returns warnings; raises on mismatch."""
    meta = js.get("parameters")
    if not isinstance(meta, dict) or not meta: return ["the answer carries no unit information: units NOT verified (radiation is also checked by value inside the model)"]
    for p, ok in EXPECTED_UNITS.items():
        u = (meta.get(p) or {}).get("units")
        if u is None: continue
        if _norm_unit(u) not in ok: raise PowerUnitError(f"{p}: API says units '{u}', model needs one of {sorted(ok)}. Is community='{COMMUNITY}' used?")
    return []

def _dstr(x) -> str: return pd.Timestamp(x).strftime("%Y%m%d")

class NasaPowerClient:
    def __init__(self, fetch=None, pause: float = 1.0, retries: int = 5, timeout: int = 240, verbose: bool = True):
        """fetch=None -> public NASA POWER REST API. pause = seconds to wait between requests (be polite to the server)."""
        self.fetch, self.pause, self.retries, self.timeout, self.verbose = fetch, pause, retries, timeout, verbose
        self._unit_warned = False

    # ---- one point, one period ------------------------------------------------------------------------------
    def get(self, lat: float, lon: float, start, end) -> pd.DataFrame:
        """Daily raw table: date + PARAMS. Missing values are NaN. Raises PowerError subclasses on problems."""
        if self.fetch is not None: d = self.fetch(float(lat), float(lon), pd.Timestamp(start), pd.Timestamp(end), list(PARAMS))
        else: d = self._http(float(lat), float(lon), start, end)
        miss = [c for c in ["date"] + PARAMS if c not in d.columns]
        if miss: raise PowerError(f"answer lacks variables {miss}")
        d = d[["date"] + PARAMS].copy(); d["date"] = pd.to_datetime(d["date"])
        d[PARAMS] = d[PARAMS].astype(float).replace(-999.0, np.nan)
        return d.sort_values("date").reset_index(drop=True)

    def _http(self, lat, lon, start, end) -> pd.DataFrame:
        import requests
        q = {"parameters": ",".join(PARAMS), "community": COMMUNITY, "longitude": lon, "latitude": lat,
             "start": _dstr(start), "end": _dstr(end), "format": "JSON"}
        last = None
        for k in range(self.retries):
            try:
                r = requests.get(URL, params=q, timeout=self.timeout)
            except Exception as e:                                           # timeout / connection reset: retry
                last = e; time.sleep(10 * (k + 1)); continue
            if r.status_code in (400, 422): raise PowerParameterError(r.text[:500])
            if r.ok:
                try: js = r.json()
                except ValueError as e: last = e; time.sleep(10 * (k + 1)); continue
                break
            last = f"HTTP {r.status_code}"
            if self.verbose: print("  retry", r.status_code)
            time.sleep(10 * (k + 1))
        else: raise PowerError(f"download failed after {self.retries} tries: {last}")
        warns = check_units(js)
        if warns and not self._unit_warned:
            self._unit_warned = True; warnings.warn(warns[0])
        try: par = js["properties"]["parameter"]
        except (KeyError, TypeError): raise PowerError(f"unexpected answer: {str(js)[:300]}")
        d = pd.DataFrame(par); d.index = pd.to_datetime(d.index, format="%Y%m%d"); d.index.name = "date"
        time.sleep(self.pause)
        return d.reset_index()

# =============================================================================
# ALL REGIONS: choose points, download, store
# =============================================================================
def build_points(step: float = 10.0, lat_min=-55, lat_max=65, jitter=True, seed=0) -> pd.DataFrame:
    """Regular global grid (step degrees) restricted to LAND (name, lat, lon). step=10 -> ~127 points, 7 -> ~257, 5 -> ~516.
    Polar regions are skipped (frozen soil). jitter avoids exact cell centres. A point list is only a choice of WHERE to look:
    NASA POWER itself is a 0.5-degree global grid, so any coordinate is valid."""
    from global_land_mask import globe
    rng = np.random.default_rng(seed); rows = []
    for lat in np.arange(lat_min + step / 2, lat_max, step):
        for lon in np.arange(-180 + step / 2, 180, step):
            la = float(np.round(lat + (rng.uniform(-step / 4, step / 4) if jitter else 0), 2))
            lo = float(np.round(lon + (rng.uniform(-step / 4, step / 4) if jitter else 0), 2))
            if globe.is_land(la, lo): rows.append((f"p_{la:+06.2f}_{lo:+07.2f}", la, lo))
    return pd.DataFrame(rows, columns=["name", "lat", "lon"])

def _skip_path(lib): return os.path.join(lib.root, "skipped_points.json")
def _load_skips(lib): return json.load(open(_skip_path(lib))) if os.path.exists(_skip_path(lib)) else {}

def fetch_all(lib: fd.Library, client: NasaPowerClient, points: pd.DataFrame, start="2005-01-01", end="2024-12-31", max_points: int | None = None):
    """Ask the API for every point, check it, store it in the library (raw cache + ET0/VAD computed by the model code).
    RESUMABLE: points already stored, or already known to have no soil data, are skipped; failures are listed and retried next call."""
    done = set(lib._load_reg()["regions"]); skips = _load_skips(lib); todo = [r for r in points.itertuples() if r.name not in done and r.name not in skips]
    if max_points: todo = todo[:max_points]
    stats = {"stored": 0, "no_soil_data": 0, "failed": [], "with_problems": {}}
    for i, r in enumerate(todo, 1):
        try:
            d = client.get(r.lat, r.lon, start, end)
            if d["GWETROOT"].isna().mean() > 0.5:                              # sea / ice / no soil data
                skips[r.name] = "no soil moisture data"; json.dump(skips, open(_skip_path(lib), "w"), indent=1)
                stats["no_soil_data"] += 1; print(f"{i}/{len(todo)} {r.name} SKIPPED (no soil data)"); continue
            probs = fd.ingest(lib, r.name, float(r.lat), float(r.lon), d)
            if probs: stats["with_problems"][r.name] = probs
            stats["stored"] += 1; print(f"{i}/{len(todo)} {r.name} stored" + (f"  PROBLEMS: {probs}" if probs else ""))
        except PowerParameterError as e:
            raise SystemExit(f"NASA POWER rejected the request (parameter name / dates / coordinates?):\n{e}")
        except PowerUnitError as e:
            raise SystemExit(f"UNIT PROBLEM, stopped on purpose:\n{e}")
        except Exception as e:                                                  # network hiccup etc.: keep going, run again later
            stats["failed"].append(r.name); print(f"{i}/{len(todo)} {r.name} FAILED: {e}")
    print(f"done. stored now: {stats['stored']}, no soil data: {stats['no_soil_data']}, failed: {len(stats['failed'])}, "
          f"in library: {len(fd.all_regions(lib))}")
    if stats["failed"]: print("Run fetch_all(...) again: only the failed points are retried.")
    return stats

# =============================================================================
# LIVE PREDICTION: any place, any date
# =============================================================================
def _model_L(lib: fd.Library, H: int) -> int:
    mid = lib.active_model_id(H)
    if mid is None: raise PowerError(f"no active model for H={H}; available: {sorted(lib._load_reg()['active'])}")
    return int(json.load(open(os.path.join(lib.model_dir(mid), "meta.json")))["L"])

def predict_live(lib: fd.Library, client: NasaPowerClient, lat: float, lon: float, date, H: int = 14, top: int = 3, extra_days: int = 10):
    """Flash-drought onset risk at (lat, lon) for `date`, pulling everything from the API:
       - the last L (+extra) days ending at `date`
       - the 2005-2014 baseline, only the first time this place is seen (then cached in the library)."""
    date = pd.Timestamp(date).normalize(); L = _model_L(lib, H)
    if date > pd.Timestamp.now().normalize(): return {"status": "future_date", "why": "date is in the future; POWER only has past days"}
    if date < pd.Timestamp("2005-01-01") + pd.Timedelta(days=L): return {"status": "date_too_early", "why": f"needs {L} days of history after 2005-01-01"}
    win = client.get(lat, lon, date - pd.Timedelta(days=L + extra_days - 1), date)
    ok = win.dropna(subset=PARAMS)
    if ok.empty or ok["date"].max() < date:
        return {"status": "data_not_available_yet", "date": str(date.date()), "latest_date_with_data": str(ok["date"].max().date()) if len(ok) else None,
                "why": "NASA POWER has no complete values for this date yet (it lags real time by a few days)"}
    name = f"point_{fd.Library.key(lat, lon)}"
    base = None if lib.has_baseline(name) else client.get(lat, lon, "2005-01-01", "2014-12-31")
    return fd.predict(lib, lat, lon, win, base, H=H, top=top)

