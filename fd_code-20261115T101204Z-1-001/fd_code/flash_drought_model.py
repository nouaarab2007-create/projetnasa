"""
Flash Drought Early-Warning Model  (model part only)
=====================================================
Data   : NASA POWER daily values supplied as tables (no download code here: you feed DataFrames)
Task   : at date D, using only the previous L days, estimate the probability that a
         FLASH DROUGHT ONSET occurs during the next H days. Explain it with SHAP.
Memory : everything learned/downloaded is kept in a persistent LIBRARY folder
         (raw data cache, baselines, models, metrics, SHAP importance, registry).

Kept from the previous (daily drought/heatwave) design, because it was correct:
  doy365 calendar, +-7-day circular baseline 2005-2014, z-scores, 80% rolling rule,
  run_flag / future_any, L (lookback) and H (horizon) chosen by experiment,
  time split with H-day embargo, NO class re-weighting, Platt calibration,
  climatology baseline, leave-one-region-out, test set used once.

Changed for flash drought: see the DEFINITION block below.

Usage (Colab or local):
    import flash_drought_model as fd, power_client as pc
    lib    = fd.Library("/content/drive/MyDrive/fd_library")
    client = pc.NasaPowerClient()                       # connection to the NASA POWER API (or NasaPowerClient(fetch=your_function))
    points = pc.build_points(step=10)                   # which places: global grid of land points
    pc.fetch_all(lib, client, points)                   # the code ASKS the API for the variables it needs, for every point, 2005-2024
    fd.run_full_pipeline(lib)                           # ALL stored regions: label, choose L/H, train, spatial CV, test 2024 (once)
    fd.export_bundle(lib, "fd_bundle")                  # what the interface backend needs
    pc.predict_live(lib, client, lat, lon, "2024-07-15", H=14)    # any place, any date: pulls its own data, returns the risk JSON

Variables requested from the API (8, raw): PRECTOTCORR (mm/day), GWETROOT (0-1), T2M_MAX (degC), T2M_MIN (degC), RH2M (%),
WS2M (m/s at 2 m), ALLSKY_SFC_SW_DWN (MJ/m2/day), PS (kPa).   VAD and ET0 are NOT requested: they are computed here with FAO-56
(compute_vad_et0), verified against FAO-56 Example 18.
(Offline alternative: fd.ingest_folder(lib, folder) reads points.csv + one CSV per point with the same columns.)
"""
from __future__ import annotations
import os, json, time, math, hashlib, datetime as dt, warnings
import numpy as np
import pandas as pd
import joblib
from scipy.special import logit, expit
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss

# =============================================================================
# 0. CONFIGURATION
# =============================================================================
# Input columns of every daily table (NASA POWER names). -999 is converted to NaN on ingestion.
BASE_VARS = ["PRECTOTCORR", "ET0", "GWETROOT", "T2M_MAX", "VAD"]
DERIVED = {"PMET": "PRECTOTCORR - ET0"}              # climatic water balance (mm/day)
VARS = BASE_VARS + list(DERIVED)                     # PMET = P - ET0
SUM_VARS = {"PRECTOTCORR", "PMET"}                   # rolling SUM (mm); all others rolling MEAN
UNITS = {"PRECTOTCORR": "mm", "ET0": "mm/day", "GWETROOT": "", "T2M_MAX": "°C", "VAD": "kPa", "PMET": "mm"}
NICE = {"PRECTOTCORR": "precipitation total", "ET0": "reference evapotranspiration",
        "GWETROOT": "root-zone soil wetness", "T2M_MAX": "daily maximum temperature",
        "VAD": "vapor-pressure deficit", "PMET": "water balance (precipitation minus ET0)"}

WINDOWS = [1, 7, 14, 30, 60, 90]                     # rolling windows (days); 1 = the day itself
PCT_WINDOWS = [1, 7, 14, 30]                          # GWETROOT windows that also get a percentile feature
DD_KS = [7, 14, 21]                                  # dry-down look-back steps (days)
MIN_VALID = 0.8                                      # rolling value missing if < 80% valid days

BASE_START, BASE_END = pd.Timestamp("2005-01-01"), pd.Timestamp("2014-12-31")

# ---- DEFINITION of a flash drought (soil-moisture based, relative to local 2005-2014 climate) ----
# pct7(t)   = percentile (0-100) of the 7-day mean of GWETROOT versus baseline days within +-7 doy.
# DRY run   : >= DRY_RUN consecutive days with pct7 <= DRY_PCT      (user spec: 14 days below 15th pct)
# RAPID     : within the RAPID_WIN days before the run starts, pct7 was >= START_PCT
#             (i.e. a fall of >= START_PCT-DRY_PCT percentile points in <= RAPID_WIN days)
# EVENT DAY : every day of a DRY run that is RAPID.   ONSET : first day of such a run.
# TARGET y  : 1 if an ONSET occurs in days t+1..t+H, else 0.  Rows already inside an event are not
#             "at risk" and are dropped (they are reported as state 'already in flash drought').
DRY_PCT, DRY_RUN, START_PCT, RAPID_WIN = 15.0, 14, 40.0, 21

H_CANDIDATES = [7, 14, 30]
MIN_ONSETS = 5               # a region with fewer flash-drought onsets (2005-2024) is excluded from training
STRIDE = 3                   # experiments / CV / hyper-parameter search use every 3rd training row (neighbouring days are near-duplicates); final fit uses ALL rows
LR_MAX_ROWS = 400_000
L_CANDIDATES = [14, 30, 60, 90]
TIER_MODE = "relative"      # "relative": cuts = 2x/4x/8x the usual rate (data-driven); "absolute": 30/65/85 %
ABS_TIERS = [0.30, 0.65, 0.85]
REL_TIERS = [2.0, 4.0, 8.0]
TIER_NAMES = ["LOW", "MODERATE", "HIGH", "CRITICAL"]
SPLIT = {"train_end": "2020-12-31", "val_start": "2021-01-01", "val_end": "2023-12-31",
         "test_start": "2024-01-01"}                 # test = 2024, used once
LGB_GRID = [dict(n_estimators=n, num_leaves=l) for n in (150, 400) for l in (7, 15)]
LGB_FIXED = dict(learning_rate=0.05, min_child_samples=300, subsample=0.8, subsample_freq=1,
                 colsample_bytree=0.8, reg_lambda=5.0, verbose=-1, random_state=0, n_jobs=-1)

# 36 training regions: dry, semi-arid, Mediterranean, monsoon, temperate crop belts, humid. (lat, lon)
REGIONS = {
 "sahel_niger": (13.5, 2.1), "ne_brazil": (-9.4, -40.5), "murray_darling": (-34.3, 146.0),
 "marrakech_morocco": (31.6, -8.0), "andalusia_spain": (37.6, -5.0), "california_cv": (36.7, -119.8),
 "east_africa_kenya": (-1.5, 37.3), "punjab_india": (30.9, 75.9), "amazonia_brazil": (-3.1, -60.0),
 "iowa_usa": (42.0, -93.5), "ukraine_central": (49.0, 31.5), "north_china_plain": (36.5, 115.5),
 "texas_panhandle": (35.2, -101.8), "oklahoma_usa": (35.6, -97.5), "kansas_usa": (38.5, -98.0),
 "nebraska_usa": (41.0, -99.0), "illinois_usa": (40.0, -89.0), "georgia_usa": (32.5, -83.5),
 "mississippi_delta": (33.5, -90.8), "saskatchewan_canada": (51.5, -106.0),
 "pampas_argentina": (-34.0, -62.0), "cerrado_brazil": (-15.5, -47.5), "rio_grande_do_sul": (-29.5, -53.5),
 "south_africa_highveld": (-26.5, 28.5), "zimbabwe": (-18.5, 30.0), "ethiopia_highlands": (9.0, 38.8),
 "castilla_spain": (41.5, -4.5), "france_beauce": (48.2, 1.8), "germany_north": (52.5, 10.5),
 "turkey_anatolia": (39.0, 33.0), "iran_zagros": (33.5, 48.5), "maharashtra_india": (19.5, 75.5),
 "indo_gangetic_east": (25.5, 85.0), "thailand_central": (15.0, 100.5), "sichuan_china": (30.5, 104.5),
 "queensland_darling": (-27.5, 150.0),
}

# =============================================================================
# 1. LIBRARY (persistent memory)
# =============================================================================
class Library:
    """Folder-based memory. Nothing is ever recomputed if it is already stored.
        raw/<region>.csv.gz        downloaded POWER data (cache, includes -999 -> NaN)
        baselines/<region>.npz     baseline statistics (means, stds, sorted samples)
        models/<model_id>/         model.joblib, meta.json, shap_importance.csv, reports
        registry.json              list of models, 'active' pointer, region catalogue, test log
    """
    def __init__(self, root: str):
        self.root = root
        for sub in ("raw", "baselines", "models"):
            os.makedirs(os.path.join(root, sub), exist_ok=True)
        self.reg_path = os.path.join(root, "registry.json")
        if not os.path.exists(self.reg_path):
            self._save_reg({"models": {}, "active": {}, "regions": {}, "created": _now()})

    def _load_reg(self): return json.load(open(self.reg_path))
    def _save_reg(self, r):
        tmp = self.reg_path + ".tmp"; json.dump(r, open(tmp, "w"), indent=1); os.replace(tmp, self.reg_path)

    @staticmethod
    def key(lat, lon): return f"{round(float(lat), 2):.2f}_{round(float(lon), 2):.2f}"

    # ---- raw data cache ---------------------------------------------------
    def raw_path(self, name): return os.path.join(self.root, "raw", f"{name}.csv.gz")
    def has_raw(self, name): return os.path.exists(self.raw_path(name))
    def load_raw(self, name): return pd.read_csv(self.raw_path(name), parse_dates=["date"])
    def save_raw(self, name, df, lat, lon):
        df.to_csv(self.raw_path(name), index=False, compression="gzip")
        r = self._load_reg()
        r["regions"][name] = {"lat": lat, "lon": lon, "start": str(df["date"].min().date()),
                              "end": str(df["date"].max().date()), "rows": int(len(df)), "downloaded": _now()}
        self._save_reg(r)

    # ---- baselines ---------------------------------------------------------
    def baseline_path(self, name): return os.path.join(self.root, "baselines", f"{name}.npz")
    def has_baseline(self, name): return os.path.exists(self.baseline_path(name))

    # ---- models ------------------------------------------------------------
    def model_dir(self, mid): return os.path.join(self.root, "models", mid)
    def register_model(self, mid, meta, make_active=True):
        r = self._load_reg(); r["models"][mid] = {k: meta[k] for k in ("H", "L", "created", "val_PR_AUC", "algorithm")}
        if make_active: r["active"][f"H{meta['H']}"] = mid
        self._save_reg(r)
    def active_model_id(self, H):
        return self._load_reg()["active"].get(f"H{H}")
    def log_test(self, mid, res):
        r = self._load_reg(); r["models"][mid]["test_done"] = True; r["models"][mid]["test"] = res; self._save_reg(r)
    def test_done(self, mid): return bool(self._load_reg()["models"].get(mid, {}).get("test_done"))
    def summary(self):
        r = self._load_reg()
        return {"n_regions": len(r["regions"]), "models": r["models"], "active": r["active"]}


def _now(): return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# =============================================================================
# 2. DATA INGESTION (tables in, no network)
# =============================================================================
POWER_RAW_COLS = ["PRECTOTCORR", "GWETROOT", "T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PS"]   # all that ET0/VAD/model need

def _es(t):  # saturation vapour pressure, kPa (FAO-56)
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))

def compute_vad_et0(d: pd.DataFrame, lat: float) -> pd.DataFrame:
    """VAD and ET0 from raw daily weather, exactly as FAO Irrigation & Drainage Paper 56 (Allen et al. 1998), daily step, G = 0.
    Inputs: date, T2M_MAX, T2M_MIN (degC), RH2M (%), WS2M (m/s at 2 m), ALLSKY_SFC_SW_DWN = Rs (MJ/m2/day), PS (kPa).
      e0(T)  = 0.6108 exp(17.27 T / (T + 237.3))                                   [Eq. 11]
      es     = (e0(Tmax) + e0(Tmin)) / 2                                           [Eq. 12]
      ea     = RHmean/100 * es                                                     [Eq. 19, RHmean variant]
      VAD    = es - ea                                                             [kPa]
      Delta  = 4098 e0(Tmean) / (Tmean + 237.3)^2,  Tmean = (Tmax+Tmin)/2          [Eq. 13, 9]
      gamma  = 0.000665 P                                                          [Eq. 8]
      Ra     = 24*60/pi * 0.0820 * dr * (ws sin(phi) sin(dec) + cos(phi) cos(dec) sin(ws))   [Eq. 21]
               dr = 1 + 0.033 cos(2 pi J/365); dec = 0.409 sin(2 pi J/365 - 1.39); ws = arccos(-tan(phi) tan(dec))   [Eq. 23-25]
      Rso    = (0.75 + 2e-5 z) Ra,  z from pressure (barometric formula)           [Eq. 37]
      Rns    = (1 - 0.23) Rs                                                       [Eq. 38]
      Rnl    = 4.903e-9 (Tmax,K^4 + Tmin,K^4)/2 (0.34 - 0.14 sqrt(ea)) (1.35 Rs/Rso - 0.35),  0.3 <= Rs/Rso <= 1   [Eq. 39]
      ET0    = (0.408 Delta (Rn - G) + gamma 900/(Tmean+273) u2 (es - ea)) / (Delta + gamma (1 + 0.34 u2)),  u2 >= 0.5   [Eq. 6]
    Verified against FAO-56 Example 18 in test_flash_drought.py (ET0 = 3.88 mm/day)."""
    d = d.copy(); doy = pd.DatetimeIndex(d["date"]).dayofyear.values
    rs = d["ALLSKY_SFC_SW_DWN"].values.astype(float)
    if np.isfinite(rs).sum() >= 1000 and np.nanpercentile(rs, 99) < 10:      # long series only: a short winter window can legitimately be < 10 MJ
        raise ValueError("ALLSKY_SFC_SW_DWN looks like kWh/m2/day (99th percentile < 10); ET0 needs MJ/m2/day (multiply kWh by 3.6)")
    tmax, tmin = d["T2M_MAX"].values, d["T2M_MIN"].values; tmean = (tmax + tmin) / 2
    es = (_es(tmax) + _es(tmin)) / 2; ea = es * np.clip(d["RH2M"].values, 0, 100) / 100.0
    d["VAD"] = np.clip(es - ea, 0, None)
    P = d["PS"].values; gamma = 0.000665 * P
    delta = 4098 * _es(tmean) / (tmean + 237.3) ** 2
    u2 = np.clip(d["WS2M"].values, 0.5, None)                       # FAO-56 lower bound
    phi = np.deg2rad(lat); dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    dec = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1, 1))
    ra = (24 * 60 / np.pi) * 0.0820 * dr * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))
    z = 44330.0 * (1 - (np.clip(P, 50, 110) / 101.325) ** 0.1903)    # elevation implied by pressure (m)
    rso = np.clip((0.75 + 2e-5 * z) * ra, 0.1, None)
    rnl = 4.903e-9 * (((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2) * (0.34 - 0.14 * np.sqrt(np.clip(ea, 0, None))) \
          * (1.35 * np.clip(rs / rso, 0.3, 1.0) - 0.35)
    rn = 0.77 * rs - rnl
    et0 = (0.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))
    d["ET0"] = np.clip(et0, 0, None)
    return d

def clean_table(d: pd.DataFrame, lat: float | None = None) -> pd.DataFrame:
    """Canonical daily table: date + BASE_VARS + PMET. -999 -> NaN. If ET0/VAD are absent (raw POWER columns),
    they are computed (needs lat). Duplicates refused, sorted."""
    d = d.copy(); d["date"] = pd.to_datetime(d["date"])
    num = [c for c in d.columns if c != "date"]; d[num] = d[num].astype(float).replace(-999.0, np.nan)
    if "ET0" not in d.columns or "VAD" not in d.columns:
        miss = [c for c in POWER_RAW_COLS if c not in d.columns]
        if miss or lat is None: raise ValueError(f"cannot compute ET0/VAD: missing {miss}, lat={lat}")
        d = compute_vad_et0(d, lat)
    miss = [c for c in ["date"] + BASE_VARS if c not in d.columns]
    if miss: raise ValueError(f"missing columns: {miss}")
    d = d[["date"] + BASE_VARS]
    if d["date"].duplicated().any(): raise ValueError("duplicate dates")
    d = d.sort_values("date").reset_index(drop=True)
    d["PMET"] = d["PRECTOTCORR"] - d["ET0"]
    return d

def check_series(d: pd.DataFrame, name="?"):
    """Hard checks; returns a list of problems (a region with problems is excluded, not silently used)."""
    p = []
    if not (d["date"].diff().dropna() == pd.Timedelta(days=1)).all(): p.append("gaps in dates")
    g = d["GWETROOT"].dropna()
    if len(g) and not g.between(0, 1).all(): p.append("GWETROOT outside [0,1]")
    if (d["PRECTOTCORR"].dropna() < 0).any(): p.append("negative precipitation")
    if d["GWETROOT"].isna().mean() > 0.05: p.append(f"GWETROOT missing {d['GWETROOT'].isna().mean():.1%}")
    if d["date"].min() > BASE_START or d["date"].max() < pd.Timestamp("2024-12-31"): p.append("does not cover 2005-01-01..2024-12-31")
    return p

def ingest(lib: Library, name, lat, lon, df_or_csv):
    """Store one region's daily table in the library (done once; later runs reuse it)."""
    d = pd.read_csv(df_or_csv) if isinstance(df_or_csv, (str, os.PathLike)) else df_or_csv
    d = clean_table(d, lat); lib.save_raw(name, d[["date"] + BASE_VARS], lat, lon)
    if lib.has_baseline(name): os.remove(lib.baseline_path(name))        # data changed -> baseline must be rebuilt
    return check_series(d, name)

def ingest_folder(lib: Library, folder: str, verbose=True):
    """Ingest every region listed in <folder>/points.csv (columns name,lat,lon; one <name>.csv per row).
    Already-ingested regions are skipped. Returns {name: problems}."""
    pts = pd.read_csv(os.path.join(folder, "points.csv")); out = {}
    done = set(lib._load_reg()["regions"])
    for r in pts.itertuples():
        path = os.path.join(folder, f"{r.name}.csv")
        if r.name in done or not os.path.exists(path): continue
        try: out[r.name] = ingest(lib, r.name, float(r.lat), float(r.lon), path)
        except Exception as e: out[r.name] = [f"ERROR {e}"]
        if verbose: print(r.name, out[r.name] or "ok")
    return out

def all_regions(lib: Library):
    """Every region stored in the library (prediction-only 'point_*' baselines excluded)."""
    return {n: (r["lat"], r["lon"]) for n, r in lib._load_reg()["regions"].items() if not n.startswith("point_")}

def load_region(lib: Library, name):
    if not lib.has_raw(name): raise FileNotFoundError(f"region '{name}' not ingested; call ingest() first")
    return clean_table(lib.load_raw(name))

# =============================================================================
# 3. CALENDAR, ROLLING FEATURES, BASELINE   (identical code path for training and live prediction)
# =============================================================================
def doy365(dates):
    """Day of year on a fixed 365-day calendar. 29 Feb is treated as 28 Feb."""
    d = pd.DatetimeIndex(dates); doy = d.dayofyear.values
    return np.where(d.is_leap_year & (doy >= 60), doy - 1, doy)

def rolling(s: pd.Series, w: int, is_sum: bool):
    m = s.rolling(w, min_periods=int(math.ceil(MIN_VALID * w))).mean()
    return m * w if is_sum else m                    # sum = mean*w (rescales for <20% missing days)

def roll_frame(d: pd.DataFrame) -> pd.DataFrame:
    """Rolling columns for ONE continuous daily series: {v}_m{w} and dry-down rates GWETROOT_dd{k}.
    d must be sorted by date with consecutive days."""
    out = pd.DataFrame({"date": d["date"].values})
    for v in VARS:
        s = d[v].reset_index(drop=True)
        for w in WINDOWS: out[f"{v}_m{w}"] = rolling(s, w, v in SUM_VARS).values
    m7 = out["GWETROOT_m7"]
    for k in DD_KS: out[f"GWETROOT_dd{k}"] = (m7 - m7.shift(k)) / k        # wetness change per day (negative = drying)
    out["doy"] = doy365(out["date"])
    return out

ROLL_COLS = [f"{v}_m{w}" for v in VARS for w in WINDOWS] + [f"GWETROOT_dd{k}" for k in DD_KS]
PCT_COLS = [f"GWETROOT_m{w}" for w in PCT_WINDOWS]

def compute_baseline(rf: pd.DataFrame, lat: float, half=7):
    """Baseline statistics from the roll_frame of the baseline period (2005-2014).
    mean/std[col] arrays (365,), samples[col] sorted padded arrays (365, nmax) for percentile ranks."""
    X = rf[ROLL_COLS].values.astype(float); doy = rf["doy"].values
    nmax = 11 * (2 * half + 1)
    mean = np.full((365, len(ROLL_COLS)), np.nan); std = mean.copy()
    samp = {c: np.full((365, nmax), np.nan, dtype=np.float32) for c in PCT_COLS}
    ci = {c: ROLL_COLS.index(c) for c in PCT_COLS}
    for d in range(1, 366):
        dist = ((doy - d + 182) % 365) - 182
        S = X[np.abs(dist) <= half]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mean[d - 1] = np.nanmean(S, axis=0); std[d - 1] = np.nanstd(S, axis=0, ddof=1)
        for c in PCT_COLS:
            v = np.sort(S[:, ci[c]][~np.isnan(S[:, ci[c]])])[:nmax]
            samp[c][d - 1, :len(v)] = v
    aridity = float(np.nanmean(rf["PRECTOTCORR_m1"]) / max(float(np.nanmean(rf["ET0_m1"])), 1e-6))   # mean rain / mean ET0
    return {"mean": mean, "std": std, "samples": samp, "static": np.array([aridity, abs(float(lat))])}

def save_baseline(lib: Library, name, bl):
    np.savez_compressed(lib.baseline_path(name), mean=bl["mean"], std=bl["std"], static=bl["static"],
                        **{f"samp_{c}": a for c, a in bl["samples"].items()})

def load_baseline(lib: Library, name):
    z = np.load(lib.baseline_path(name))
    if "static" not in z.files: raise RuntimeError(f"{name}: baseline from an older version; delete the library/baselines folder and re-run")
    return {"mean": z["mean"], "std": z["std"], "static": z["static"], "samples": {c: z[f"samp_{c}"] for c in PCT_COLS}}

def pct_rank(values, doys, samp_c):
    """Percentile (0-100) of each value within the baseline sample set of its doy.
    Ties -> average of left/right rank. NaN stays NaN. (JS must replicate exactly.)"""
    values = np.asarray(values, float); out = np.full(len(values), np.nan)
    for d in np.unique(doys):
        idx = np.where(doys == d)[0]
        arr = samp_c[d - 1]; arr = arr[~np.isnan(arr)]
        if len(arr) == 0: continue
        v = values[idx]; ok = ~np.isnan(v)
        l = np.searchsorted(arr, v[ok], "left"); r = np.searchsorted(arr, v[ok], "right")
        res = np.full(len(v), np.nan); res[ok] = 100.0 * (l + r) / 2.0 / len(arr); out[idx] = res
    return out

# ---- feature catalogue: name -> (minimum lookback L needed, group, kind, spec) ----------
def feature_catalogue():
    cat = {}
    for v in VARS:
        for w in WINDOWS: cat[f"{v}_z{w}"] = dict(need=w, group=v, kind="z", var=v, w=w)
    for w in PCT_WINDOWS: cat[f"GWETROOT_pct{w}"] = dict(need=w, group="GWETROOT", kind="pct", var="GWETROOT", w=w)
    for k in DD_KS:
        cat[f"GWETROOT_pctdrop{k}"] = dict(need=k + 6, group="GWETROOT", kind="pctdrop", var="GWETROOT", k=k)
        cat[f"GWETROOT_ddz{k}"] = dict(need=k + 6, group="GWETROOT", kind="ddz", var="GWETROOT", k=k)
    for k in (7, 14):
        cat[f"gwet_delta_{k}d"] = dict(need=k + 1, group="GWETROOT", kind="delta", var="GWETROOT", k=k)   # GWETROOT_t - GWETROOT_{t-k}
    cat["esi_proxy_14d"] = dict(need=14, group="PMET", kind="ratio", var="PMET", w=14)                   # rain14 / ET0 sum14
    cat["static_aridity"] = dict(need=0, group="climate", kind="static")     # baseline mean rain / mean ET0 of the point
    cat["static_abslat"] = dict(need=0, group="climate", kind="static")      # |latitude|
    cat["doy_sin"] = dict(need=0, group="season", kind="season"); cat["doy_cos"] = dict(need=0, group="season", kind="season")
    return cat
CAT = feature_catalogue()
def feats_for(L): return [f for f, s in CAT.items() if s["need"] <= L]
ALLF = feats_for(max(L_CANDIDATES))

def build_features(rf: pd.DataFrame, bl: dict) -> pd.DataFrame:
    """z-scores, percentiles, percentile drops, dry-down z-scores, season. rf = roll_frame of the series."""
    f = rf.copy(); doy = f["doy"].values; idx = doy - 1
    for i, c in enumerate(ROLL_COLS):
        mu, sd = bl["mean"][idx, i], bl["std"][idx, i]
        sd = np.where(sd > 1e-9, sd, np.nan)
        z = (f[c].values - mu) / sd
        if c.startswith("GWETROOT_dd"): f["GWETROOT_ddz" + c.split("dd")[1]] = z
        else:
            v, w = c.rsplit("_m", 1); f[f"{v}_z{w}"] = z
    for w in PCT_WINDOWS:
        f[f"GWETROOT_pct{w}"] = pct_rank(f[f"GWETROOT_m{w}"].values, doy, bl["samples"][f"GWETROOT_m{w}"]) / 100.0
    pct7 = pd.Series(pct_rank(f["GWETROOT_m7"].values, doy, bl["samples"]["GWETROOT_m7"]))
    f["pct7"] = pct7.values                                           # 0-100, used by the label
    for k in DD_KS: f[f"GWETROOT_pctdrop{k}"] = ((pct7.shift(k) - pct7) / 100.0).values
    m1 = f["GWETROOT_m1"]
    for k in (7, 14): f[f"gwet_delta_{k}d"] = (m1 - m1.shift(k)).values
    et_sum = f["ET0_m14"] * 14.0
    f["esi_proxy_14d"] = np.clip(f["PRECTOTCORR_m14"] / et_sum.where(et_sum > 1e-6), 0, 1.5).values
    f["static_aridity"], f["static_abslat"] = float(bl["static"][0]), float(bl["static"][1])
    f["doy_sin"] = np.sin(2 * np.pi * doy / 365); f["doy_cos"] = np.cos(2 * np.pi * doy / 365)
    return f

# =============================================================================
# 4. LABELS: flash drought events, onsets, target
# =============================================================================
def run_flag(flag, min_len):
    """True for every day that belongs to a run of >= min_len consecutive True values."""
    flag = np.asarray(flag, dtype=bool); out = np.zeros(len(flag), dtype=bool); i = 0
    while i < len(flag):
        if flag[i]:
            j = i
            while j < len(flag) and flag[j]: j += 1
            if j - i >= min_len: out[i:j] = True
            i = j
        else: i += 1
    return out

def flash_drought_events(pct7: np.ndarray):
    """Returns (event_day, onset) arrays for one region. onset is NaN where it cannot be confirmed
    (the last DRY_RUN-1 days of the series: a run that starts there cannot yet be 14 days long)."""
    n = len(pct7); dry = np.where(np.isnan(pct7), False, pct7 <= DRY_PCT)
    ev = np.zeros(n, dtype=bool); onset = np.zeros(n, dtype=float); i = 0
    while i < n:
        if dry[i]:
            j = i
            while j < n and dry[j]: j += 1
            if j - i >= DRY_RUN:
                prev = pct7[max(0, i - RAPID_WIN):i]
                if len(prev) and np.any(prev >= START_PCT):           # NaN comparisons are False
                    ev[i:j] = True; onset[i] = 1.0
            i = j
        else: i += 1
    onset[max(0, n - DRY_RUN + 1):] = np.nan
    return ev.astype(int), onset

def future_any(x, H):
    """1 if any x in days t+1..t+H, else 0. NaN where fewer than H future days exist or x is NaN inside."""
    s = pd.Series(np.asarray(x, dtype=float))
    fw = s[::-1].rolling(H, min_periods=H).max()[::-1]
    return fw.shift(-1).values

def label_region(f: pd.DataFrame, Hs) -> pd.DataFrame:
    f = f.copy(); ev, on = flash_drought_events(f["pct7"].values)
    f["fd_day"] = ev; f["fd_onset"] = on; f["dry_now"] = (f["pct7"] <= DRY_PCT).astype(int)
    for H in Hs: f[f"y_fd_{H}"] = future_any(on, H)
    return f

# =============================================================================
# 5. DATASET ASSEMBLY (shared by training and tests)
# =============================================================================
def prepare_region(lib: Library, name, lat, lon, Hs=H_CANDIDATES, raw: pd.DataFrame | None = None):
    d = raw if raw is not None else load_region(lib, name)
    d = d.sort_values("date").reset_index(drop=True)
    rf_all = roll_frame(d)
    if not lib.has_baseline(name):
        b = rf_all[(rf_all["date"] >= BASE_START) & (rf_all["date"] <= BASE_END)].reset_index(drop=True)
        save_baseline(lib, name, compute_baseline(b, lat))
    bl = load_baseline(lib, name)
    f = build_features(rf_all, bl)
    f = label_region(f, Hs); f.insert(0, "region", name); f["lat"] = lat; f["lon"] = lon
    keep = (["region", "date", "doy", "lat", "lon", "pct7", "fd_day", "dry_now", "fd_onset"] + ALLF + [f"y_fd_{H}" for H in Hs])
    f = f[list(dict.fromkeys(keep))].copy()                            # drop rolling intermediates (memory with many regions)
    fl = f.select_dtypes("float64").columns.difference(["lat", "lon", "fd_onset"] + [f"y_fd_{H}" for H in Hs])
    f[fl] = f[fl].astype("float32")
    return f

def build_dataset(lib: Library, regions: dict, Hs=H_CANDIDATES, verbose=True):
    parts, report = [], []
    for name, (lat, lon) in regions.items():
        if not lib.has_raw(name):
            report.append({"region": name, "status": "NOT INGESTED"}); continue
        d = load_region(lib, name)
        problems = check_series(d, name)
        if problems:
            report.append({"region": name, "status": "EXCLUDED", "why": "; ".join(problems)}); continue
        f = prepare_region(lib, name, lat, lon, Hs, raw=d)
        ev_rate = float(f["fd_day"].mean()); n_ev = int(np.nansum(f["fd_onset"]))
        status = "ok"
        why = ""
        if n_ev < MIN_ONSETS: status, why = "EXCLUDED", f"fewer than {MIN_ONSETS} flash-drought onsets in 20 years (desert / always wet / frozen)"
        elif ev_rate > 0.40: status, why = "EXCLUDED", "event days > 40% of all days (suspicious)"
        report.append({"region": name, "status": status, "event_day_rate": round(ev_rate, 4), "n_onsets": n_ev, "why": why})
        if status == "ok": parts.append(f)
    rep = pd.DataFrame(report)
    if verbose:
        print(rep["status"].value_counts().to_string())
        bad = rep[rep["status"] != "ok"]
        if len(bad): print(bad.head(40).to_string(index=False)); print("(full list: region_report.csv in the library folder)") if len(bad) > 40 else None
    if not parts: raise RuntimeError("no usable region")
    return pd.concat(parts, ignore_index=True), rep

def get_data(df, H):
    """At-risk rows with complete features and a defined target. Same rows for every L (fair comparison)."""
    t = f"y_fd_{H}"
    x = df.dropna(subset=ALLF + [t])
    return x[(x["fd_day"] == 0) & (x["dry_now"] == 0)]   # rows already in / currently in a dry state are not "at risk of onset"

def get_split(data, H):
    d, e = data["date"], pd.Timedelta(days=H)
    tr = data[d <= pd.Timestamp(SPLIT["train_end"]) - e]
    va = data[(d >= SPLIT["val_start"]) & (d <= pd.Timestamp(SPLIT["val_end"]) - e)]
    te = data[d >= SPLIT["test_start"]]
    return tr, va, te

# =============================================================================
# 6. MODELS, METRICS, CALIBRATION
# =============================================================================
def make_gbm(**kw):
    try:
        import lightgbm as lgb
        return lgb.LGBMClassifier(**{**LGB_FIXED, **kw}), "lightgbm"      # no class_weight / scale_pos_weight, on purpose
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        return GradientBoostingClassifier(n_estimators=kw.get("n_estimators", 150), max_depth=3,
                                          learning_rate=0.05, subsample=0.8, min_samples_leaf=300, random_state=0), "sklearn-gbm"

def evaluate(y, p):
    y = np.asarray(y)
    if y.min() == y.max(): return {"event_rate": float(y.mean()), "note": "no variation"}
    return {"event_rate": round(float(y.mean()), 4), "PR_AUC": round(float(average_precision_score(y, p)), 4),
            "ROC_AUC": round(float(roc_auc_score(y, p)), 4), "Brier": round(float(brier_score_loss(y, p)), 5)}

def reliability(y, p, bins=10):
    d = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    d["bin"] = pd.qcut(d["p"], bins, duplicates="drop")
    return d.groupby("bin", observed=True).agg(predicted=("p", "mean"), observed=("y", "mean"), n=("y", "size"))

def fit_gbm(tr, F, target, params):
    m, algo = make_gbm(**params); m.fit(tr[F], tr[target]); return m, algo

def fit_logreg(tr, F, target, C=1.0):
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000)).fit(tr[F], tr[target])

def climatology_table(tr, t):
    """Event rate per (region, day of year), smoothed with a circular 15-day window. Returns dict."""
    tab = {}
    for r, g in tr.groupby("region"):
        raw = g.groupby("doy")[t].mean().reindex(range(1, 366))
        ext = pd.concat([raw.iloc[-7:], raw, raw.iloc[:7]]).interpolate(limit_direction="both")
        sm = ext.rolling(15, center=True, min_periods=1).mean().iloc[7:-7]
        for d, v in zip(range(1, 366), sm.values): tab[(r, d)] = float(v)
    return tab

def climatology_pred(tab, x, default):
    return np.array([tab.get((r, d), default) for r, d in zip(x["region"], x["doy"])])

def baselines(data, H):
    """Models that must be beaten: climatology (per region & day of year) and a physical heuristic
    (lower current soil-moisture percentile = higher risk)."""
    t = f"y_fd_{H}"; tr, va, te = get_split(data, H); out = {}
    tab = climatology_table(tr, t)
    out["climatology"] = evaluate(va[t], climatology_pred(tab, va, tr[t].mean()))
    h = evaluate(va[t], 1 - va["pct7"].values / 100.0); h.pop("Brier", None)   # a score, not a probability
    out["soil_percentile_heuristic"] = h
    return out

def block_bootstrap_ci(df, y_col, p, n_boot=300, seed=0):
    """95% CI of PR-AUC resampling whole (region, year) blocks, because daily rows are strongly autocorrelated."""
    rng = np.random.default_rng(seed); d = df[["region", "date", y_col]].copy(); d["p"] = p; d["blk"] = d["region"] + d["date"].dt.year.astype(str)
    groups = [g for _, g in d.groupby("blk")]; vals = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups)); s = pd.concat([groups[i] for i in pick])
        if s[y_col].nunique() == 2: vals.append(average_precision_score(s[y_col], s["p"]))
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (np.nan, np.nan)

# =============================================================================
# 7. EXPERIMENT: let the data choose L, H, hyper-parameters (validation only)
# =============================================================================
def experiment_L_H(df, Hs=H_CANDIDATES, Ls=L_CANDIDATES, lib: Library | None = None):
    rows = []
    for H in Hs:
        data = get_data(df, H); tr, va, _ = get_split(data, H); t = f"y_fd_{H}"
        base = baselines(data, H)
        for L in Ls:
            F = feats_for(L)
            trs = tr.iloc[::STRIDE]
            lr = fit_logreg(trs.iloc[:: max(1, len(trs) // LR_MAX_ROWS)], F, t); r_lr = evaluate(va[t], lr.predict_proba(va[F])[:, 1])
            m, _ = fit_gbm(trs, F, t, LGB_GRID[0]); r_gb = evaluate(va[t], m.predict_proba(va[F])[:, 1])
            rows.append({"H": H, "L": L, "n_train": len(tr), "n_val": len(va), "val_events": int(va[t].sum()),
                         "LR_PR_AUC": r_lr.get("PR_AUC"), "GBM_PR_AUC": r_gb.get("PR_AUC"), "GBM_Brier": r_gb.get("Brier"),
                         "clim_PR_AUC": base["climatology"].get("PR_AUC"), "heur_PR_AUC": base["soil_percentile_heuristic"].get("PR_AUC")})
    res = pd.DataFrame(rows)
    if lib: res.to_csv(os.path.join(lib.root, "experiment_L_H.csv"), index=False)
    return res

def choose_L(res: pd.DataFrame, H, tol=0.01):
    """Smallest L whose validation PR-AUC is within tol of the best (same rule as before)."""
    r = res[res["H"] == H]; best = r["GBM_PR_AUC"].max()
    return int(r[r["GBM_PR_AUC"] >= best - tol]["L"].min())

# =============================================================================
# 8. TRAIN FINAL MODEL + SHAP + SAVE TO LIBRARY
# =============================================================================
def platt_fit(p_val, y_val):
    pv = np.clip(p_val, 1e-6, 1 - 1e-6)
    cal = LogisticRegression(C=1e6).fit(logit(pv).reshape(-1, 1), y_val)
    return float(cal.coef_[0, 0]), float(cal.intercept_[0])

def calibrate(p, a, c): return expit(a * logit(np.clip(p, 1e-6, 1 - 1e-6)) + c)

def train_model(lib: Library, df, H, L, regions: dict, tag=""):
    t = f"y_fd_{H}"; F = feats_for(L); data = get_data(df, H); tr, va, te = get_split(data, H)
    # 1. choose hyper-parameters on validation PR-AUC
    best = None
    for params in LGB_GRID:
        m, algo = fit_gbm(tr.iloc[::STRIDE], F, t, params); pr = average_precision_score(va[t], m.predict_proba(va[F])[:, 1])
        if best is None or pr > best[0]: best = (pr, params)
    val_pr, params = best
    # 2. calibration (Platt) fitted on validation using the train-only model
    m_val, algo = fit_gbm(tr, F, t, params); p_val = m_val.predict_proba(va[F])[:, 1]
    a, c = platt_fit(p_val, va[t].values)
    p_cal = calibrate(p_val, a, c); rel = reliability(va[t], p_cal)
    val_metrics = {"raw": evaluate(va[t], p_val), "calibrated": evaluate(va[t], p_cal)}
    # 3. final refit on every row with a target up to end of 2023 (test year 2024 stays untouched)
    final_end = pd.Timestamp(SPLIT["val_end"]) - pd.Timedelta(days=H)
    train_final = data[data["date"] <= final_end]
    m_final, _ = fit_gbm(train_final, F, t, params)
    mid = f"fd_H{H}_L{L}_{dt.datetime.now(dt.timezone.utc):%Y%m%d_%H%M%S}{tag}"
    mdir = lib.model_dir(mid); os.makedirs(mdir)
    joblib.dump(m_final, os.path.join(mdir, "model.joblib"))
    # 4. global SHAP importance (memory of what the model learned)
    shap_imp = global_shap(m_final, train_final[F].sample(min(20000, len(train_final)), random_state=0), F, a)
    shap_imp.to_csv(os.path.join(mdir, "shap_importance.csv"))
    rel.to_csv(os.path.join(mdir, "reliability_val.csv"))
    base_rate = float(train_final[t].mean())
    cuts = ABS_TIERS if TIER_MODE == "absolute" else [min(0.95, base_rate * k) for k in REL_TIERS]
    tier_idx = np.digitize(p_cal, cuts)
    tier_report = pd.DataFrame({"tier": [TIER_NAMES[i] for i in tier_idx], "y": va[t].values}).groupby("tier").agg(
        n=("y", "size"), observed_event_rate=("y", "mean")).reindex(TIER_NAMES)
    tier_report.to_csv(os.path.join(mdir, "tier_report_val.csv"))
    if TIER_MODE == "absolute" and p_cal.max() < cuts[0]:
        warnings.warn("absolute tiers: no validation probability reaches 30% -> every output would be LOW. Use TIER_MODE='relative'.")
    meta = {"model_id": mid, "phenomenon": "flash_drought_onset", "H": H, "L": L, "features": F, "algorithm": algo,
            "params": params, "calibration": {"a": a, "c": c}, "base_rate": float(train_final[t].mean()),
            "definition": {"DRY_PCT": DRY_PCT, "DRY_RUN": DRY_RUN, "START_PCT": START_PCT, "RAPID_WIN": RAPID_WIN},
            "windows": [w for w in WINDOWS if w <= L], "baseline": [str(BASE_START.date()), str(BASE_END.date())],
            "half_window_days": 7, "split": SPLIT, "train_rows": int(len(train_final)), "n_regions": int(df["region"].nunique()),
            "regions": sorted(df["region"].unique().tolist()), "train_period": ["2005-01-01", str(final_end.date())],
            "val_metrics": val_metrics, "val_PR_AUC": float(val_pr), "created": _now(),
            "tiers": {"mode": TIER_MODE, "cuts": cuts, "names": TIER_NAMES, "validation_observed_rate": tier_report["observed_event_rate"].to_dict()}}
    json.dump(meta, open(os.path.join(mdir, "meta.json"), "w"), indent=1)
    lib.register_model(mid, meta)
    return mid, meta, (tr, va, te)

def load_model(lib: Library, mid):
    mdir = lib.model_dir(mid)
    return joblib.load(os.path.join(mdir, "model.joblib")), json.load(open(os.path.join(mdir, "meta.json")))

# =============================================================================
# 9. SHAP: TreeExplainer -> human-readable risk drivers
# =============================================================================
def _shap_values(model, X):
    import shap
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ex = shap.TreeExplainer(model); sv = ex.shap_values(X)
    if isinstance(sv, list): sv = sv[1]                                 # older shap: [class0, class1]
    sv = np.asarray(sv)
    if sv.ndim == 3: sv = sv[:, :, 1]
    base = ex.expected_value; base = float(np.ravel(base)[-1])
    return sv, base

def global_shap(model, X, F, a=1.0):
    sv, _ = _shap_values(model, X)
    s = pd.DataFrame({"mean_abs_shap": np.abs(sv).mean(0) * abs(a)}, index=F)
    s["group"] = [CAT[f]["group"] for f in F]; return s.sort_values("mean_abs_shap", ascending=False)

def risk_level(p, meta):
    return meta["tiers"]["names"][int(np.digitize(p, meta["tiers"]["cuts"]))]

def display_name(f):
    """Readable feature name used in the JSON output."""
    sp = CAT[f]; k = sp["kind"]
    if k == "z":
        w = sp["w"]; tag = {"PRECTOTCORR": f"rain_{w}d_sum", "ET0": f"et0_{w}d_mean", "GWETROOT": f"gwet_{w}d_mean",
                            "T2M_MAX": f"tmax_{w}d_mean", "VAD": f"vad_{w}d_mean", "PMET": f"water_balance_{w}d"}[sp["var"]]
        return tag if w > 1 else tag.replace("_1d", "_daily").replace("_sum", "").replace("_mean", "")
    if k == "pct": return "gwet_percentile" if sp["w"] == 1 else f"gwet_percentile_{sp['w']}d"
    if k == "pctdrop": return f"gwet_percentile_drop_{sp['k']}d"
    if k == "ddz": return f"gwet_dry_down_rate_z_{sp['k']}d"
    if k == "static": return "aridity_index" if f == "static_aridity" else "abs_latitude"
    return f  # gwet_delta_7d, gwet_delta_14d, esi_proxy_14d, doy_sin, doy_cos

def _driver(f, x, roll_row, bl, doy):
    """-> (display value, plain-language reason) for one feature at the target date."""
    s = CAT[f]; k = s["kind"]
    if k == "z":
        v, w = s["var"], s["w"]; R = float(roll_row[f"{v}_m{w}"]); i = ROLL_COLS.index(f"{v}_m{w}")
        B = float(bl["mean"][doy - 1, i]); z = float(x[f]); u = UNITS[v]
        what = "totalled" if v in SUM_VARS else "averaged"; span = "On the day" if w == 1 else f"Over the last {w} days"
        return R, (f"{span}, {NICE[v]} {what} {R:.2f} {u}, {R - B:+.2f} {u} versus the usual {B:.2f} {u} "
                   f"for this time of year ({z:+.1f} standard deviations).")
    if k == "pct":
        return float(x[f]) * 100, f"Root-zone soil wetness ({'daily' if s['w']==1 else str(s['w'])+'-day mean'}) is at the {x[f]*100:.0f}th percentile for this time of year."
    if k == "pctdrop":
        return float(x[f]) * 100, f"Soil-wetness percentile fell {x[f]*100:.0f} points over {s['k']} days (rapid dry-down)."
    if k == "ddz":
        return float(x[f]), f"Soil is drying faster than usual over {s['k']} days ({x[f]:+.1f} standard deviations of the typical rate)."
    if k == "delta":
        d = float(x[f]); return d, f"Root-zone soil wetness changed by {d:+.2f} ({d*100:+.0f} percentage points) over {s['k']} days."
    if k == "ratio":
        r = float(x[f]); return r, f"Rain supplied only {r*100:.0f}% of evaporative demand over the last 14 days (proxy for moisture stress)."
    if k == "static":
        return float(x[f]), ("This location's climate (mean rain relative to evaporative demand) shapes how easily soil dries rapidly."
                             if f == "static_aridity" else "This latitude's typical climate regime shapes the risk.")
    return float(x[f]), "Time of year makes this season more (or less) prone to rapid drying."

def explain_row(model, meta, x: pd.Series, roll_row: pd.Series, bl, doy, top=3):
    """x: features of the target day; roll_row: raw rolling columns. Returns the probability, tier and SHAP drivers.
    SHAP is computed on the raw model (log-odds); Platt is affine in logit, so contributions are scaled by a.
    'impact_score' = a driver group's share of all risk-increasing SHAP mass (log-odds), NOT percentage points of probability."""
    F = meta["features"]; a, c = meta["calibration"]["a"], meta["calibration"]["c"]
    X = pd.DataFrame([x[F].values.astype(float)], columns=F)
    p_raw = float(model.predict_proba(X)[:, 1][0]); p = float(calibrate(np.array([p_raw]), a, c)[0])
    sv, base = _shap_values(model, X); contrib = pd.Series(sv[0] * a, index=F)
    grp = contrib.groupby([CAT[f]["group"] for f in F]).sum().sort_values(ascending=False)
    pos_total = float(grp[grp > 0].sum()) or 1.0
    drivers, relief = [], []
    for g, tot in grp.items():
        fs = contrib[[f for f in F if CAT[f]["group"] == g]]; fb = fs.abs().idxmax()
        val, text = _driver(fb, x, roll_row, bl, doy)
        share = 100 * float(tot) / pos_total
        item = {"feature": display_name(fb), "value": round(float(val), 4),
                "impact_score": f"{share:+.1f}%", "impact_logodds": round(float(tot), 4), "reason": text}
        (drivers if tot > 0 else relief).append(item)
    return {"risk_percentage": round(100 * p, 1), "risk_level": risk_level(p, meta), "horizon_days": meta["H"],
            "top_drivers": drivers[:top], "relief_factors": relief[-1:] if relief else [],
            "usual_percentage": round(100 * meta["base_rate"], 1), "risk_ratio_vs_usual": round(p / meta["base_rate"], 1),
            "risk_percentage_uncalibrated": round(100 * p_raw, 1)}

# =============================================================================
# 10. LEAVE-ONE-REGION-OUT and FINAL TEST (once)
# =============================================================================
def leave_one_region_out(df, H, L, params):
    t = f"y_fd_{H}"; F = feats_for(L); data = get_data(df, H); out = []
    for r in data["region"].unique():
        tr = data[(data["region"] != r) & (data["date"] <= pd.Timestamp(SPLIT["train_end"]) - pd.Timedelta(days=H))]
        va = data[(data["region"] == r) & (data["date"] >= SPLIT["val_start"]) &
                  (data["date"] <= pd.Timestamp(SPLIT["val_end"]) - pd.Timedelta(days=H))]
        if va[t].nunique() < 2: out.append({"region": r, "note": "no variation in validation"}); continue
        m, _ = fit_gbm(tr, F, t, params); ev = evaluate(va[t], m.predict_proba(va[F])[:, 1])
        clim = va[t].mean()                                                # PR-AUC of a no-skill model == event rate
        out.append({"region": r, **ev, "no_skill_PR_AUC": round(float(clim), 4), "beats_no_skill": ev["PR_AUC"] > clim})
    return pd.DataFrame(out)

def spatial_block_cv(df, H, L, params, block_deg=20, n_folds=5, seed=0):
    """Neighbouring grid points are correlated, so leave-ONE-region-out is too optimistic for a dense global set.
    Whole block_deg x block_deg geographic blocks are held out (n_folds folds, validation years only).
    Also fits the model WITHOUT the 2 static location features: if PR_AUC_no_static is close to PR_AUC, the model
    generalises to unseen places from the weather signal itself and is not just memorising locations."""
    t = f"y_fd_{H}"; F = feats_for(L); Fns = [f for f in F if not f.startswith("static_")]
    data = get_data(df, H).copy()
    data["blk"] = (np.floor((data["lat"] + 90) / block_deg).astype(int) * 1000 + np.floor((data["lon"] + 180) / block_deg).astype(int))
    ub = data["blk"].unique(); rng = np.random.default_rng(seed); rng.shuffle(ub)
    data["fold"] = data["blk"].map({b: i % n_folds for i, b in enumerate(ub)}); out = []; e = pd.Timedelta(days=H)
    for k in range(n_folds):
        tr = data[(data["fold"] != k) & (data["date"] <= pd.Timestamp(SPLIT["train_end"]) - e)].iloc[::STRIDE]
        va = data[(data["fold"] == k) & (data["date"] >= SPLIT["val_start"]) & (data["date"] <= pd.Timestamp(SPLIT["val_end"]) - e)]
        if va[t].nunique() < 2 or tr[t].nunique() < 2: out.append({"fold": k, "note": "no variation"}); continue
        m, _ = fit_gbm(tr, F, t, params); ev = evaluate(va[t], m.predict_proba(va[F])[:, 1])
        m2, _ = fit_gbm(tr, Fns, t, params); ev2 = evaluate(va[t], m2.predict_proba(va[Fns])[:, 1])
        base = float(va[t].mean())
        out.append({"fold": k, "n_regions": int(va["region"].nunique()), **ev, "PR_AUC_no_static": ev2["PR_AUC"],
                    "no_skill_PR_AUC": round(base, 4), "beats_no_skill": ev["PR_AUC"] > base})
    return pd.DataFrame(out)

def final_test(lib: Library, df, mid, force=False):
    """Evaluate on 2024. Logged in the library: the test can only be run once per model unless force=True."""
    if lib.test_done(mid) and not force:
        raise RuntimeError("Test already done for this model; refusing to re-run (use force=True knowingly).")
    model, meta = load_model(lib, mid); H, L = meta["H"], meta["L"]; F = meta["features"]; t = f"y_fd_{H}"
    te = get_data(df, H); te = te[te["date"] >= SPLIT["test_start"]]
    p = calibrate(model.predict_proba(te[F])[:, 1], meta["calibration"]["a"], meta["calibration"]["c"])
    res = evaluate(te[t], p); lo, hi = block_bootstrap_ci(te, t, p); res["PR_AUC_95CI"] = [round(lo, 4), round(hi, 4)]
    res["n_rows"] = int(len(te)); res["n_positive_rows"] = int(te[t].sum())
    full = get_data(df, H); tr_ = full[full["date"] <= pd.Timestamp(SPLIT["val_end"]) - pd.Timedelta(days=H)]
    pc = climatology_pred(climatology_table(tr_, t), te, tr_[t].mean())
    res["climatology"] = evaluate(te[t], pc); res["soil_percentile_heuristic"] = {k: v for k, v in evaluate(te[t], 1 - te["pct7"].values / 100).items() if k != "Brier"}
    tp = te.assign(p=p); rows = {}
    for r_, g in tp.groupby("region"): rows[r_] = evaluate(g[t], g["p"].values) if g[t].nunique() > 1 else {"note": "no variation"}
    per_region = pd.DataFrame.from_dict(rows, orient="index")
    per_region.to_csv(os.path.join(lib.model_dir(mid), "test_2024_per_region.csv"))
    reliability(te[t], p).to_csv(os.path.join(lib.model_dir(mid), "reliability_test.csv"))
    json.dump(res, open(os.path.join(lib.model_dir(mid), "test_2024.json"), "w"), indent=1)
    lib.log_test(mid, res); return res

# =============================================================================
# 11. PIPELINES
# =============================================================================
def run_full_pipeline(lib: Library, regions: dict | None = None, run_test=True, cv=True):
    """regions=None -> EVERY region ingested in the library (the 'all regions' mode)."""
    regions = regions or all_regions(lib)
    print(f"== 1. data, features, labels ({len(regions)} regions in the library) ==")
    df, rep = build_dataset(lib, regions); rep.to_csv(os.path.join(lib.root, "region_report.csv"), index=False)
    print(f"   used: {df['region'].nunique()} regions, {len(df):,} daily rows")
    print("== 2. choose L and H on validation ==")
    res = experiment_L_H(df, lib=lib); print(res.to_string(index=False))
    out = {}
    for H in H_CANDIDATES:
        L = choose_L(res, H); print(f"-> H={H}: smallest L within 0.01 of best = {L}")
        mid, meta, _ = train_model(lib, df, H, L, regions)
        if cv:
            cvr = spatial_block_cv(df, H, L, meta["params"]); cvr.to_csv(os.path.join(lib.model_dir(mid), "spatial_block_cv.csv"), index=False)
            print(cvr.to_string(index=False))
        out[H] = mid; print("validation:", meta["val_metrics"])
    if run_test:
        print("== 3. final test on 2024 (once) ==")
        for H, mid in out.items(): print(f"H={H}", json.dumps(final_test(lib, df, mid), indent=1))
    return out

def add_regions(lib: Library, new_tables: dict, retrain=True):
    """new_tables: {name: (lat, lon, DataFrame_or_csv)}. Stores them (once) then retrains on ALL stored regions."""
    for n, (lat, lon, t) in new_tables.items():
        probs = ingest(lib, n, lat, lon, t)
        if probs: warnings.warn(f"{n}: {probs}")
    return run_full_pipeline(lib) if retrain else all_regions(lib)

# =============================================================================
# 12. PREDICTION FOR ANY POINT AND DATE  (same feature code as training)
# =============================================================================
def predict(lib: Library, lat, lon, window_df: pd.DataFrame, baseline_df: pd.DataFrame | None = None, H=None, top=3):
    """Flash-drought onset risk for the LAST date of window_df.
    window_df  : raw POWER columns (or the 5 model variables) with >= L consecutive days ending at the target date.
    baseline_df: daily table 2005-01-01..2014-12-31 for this point; needed only the first time a point is seen
                 (then cached in the library under the point key)."""
    act = lib._load_reg()["active"]
    if not act: return {"status": "no_model", "why": "train a model first (run_full_pipeline)"}
    H = int(H) if H else int(sorted(act, key=lambda k: int(k[1:]))[0][1:])
    mid = lib.active_model_id(H)
    if mid is None: return {"status": "no_model", "why": f"no active model for H={H}; available: {sorted(act)}"}
    model, meta = load_model(lib, mid); L = meta["L"]
    name = f"point_{Library.key(lat, lon)}"
    if not lib.has_baseline(name):
        if baseline_df is None: return {"status": "baseline_required", "why": "first time this point is seen: pass baseline_df (2005-2014 daily)"}
        b = clean_table(baseline_df, lat); b = b[(b["date"] >= BASE_START) & (b["date"] <= BASE_END)].reset_index(drop=True)
        if len(b) < 3000: return {"status": "baseline_required", "why": f"baseline has only {len(b)} days"}
        save_baseline(lib, name, compute_baseline(roll_frame(b), lat))
        r = lib._load_reg(); r["regions"][name] = {"lat": lat, "lon": lon, "baseline_only": True, "created": _now()}; lib._save_reg(r)
    bl = load_baseline(lib, name)
    w = clean_table(window_df, lat); D = w["date"].iloc[-1]
    w = w[w["date"] > D - pd.Timedelta(days=L)].reset_index(drop=True)
    if len(w) < L or not (w["date"].diff().dropna() == pd.Timedelta(days=1)).all():
        return {"status": "insufficient_data", "why": f"need {L} consecutive days ending {D.date()}"}
    rf = roll_frame(w); f = build_features(rf, bl); x = f.iloc[-1]; F = meta["features"]
    if x[F].isna().any(): return {"status": "insufficient_data", "why": f"missing: {list(x[F].index[x[F].isna()])}"}
    res = explain_row(model, meta, x, rf.iloc[-1], bl, int(rf["doy"].iloc[-1]), top=top)
    state = ("ALREADY_DRY: soil is at/below the 15th percentile; onset risk does not apply, check ongoing-drought status"
             if x["pct7"] <= DRY_PCT else "AT_RISK_SET")
    return {"location": {"lat": lat, "lon": lon}, "date": str(D.date()), **res, "state": state, "status": "ok",
            "model": {"id": mid, "L": L, "H": H, "validated_on": "2021-2023", "tiers": meta["tiers"]["mode"]},
            "note": "Statistical association from past data, not a weather forecast; drivers are not proven causes."}

# =============================================================================
# 13. EXPORT FOR THE INTERFACE
# =============================================================================
def export_bundle(lib: Library, dest: str, include_point_baselines=True):
    """Copy what the interface needs to run predict(): registry (active models only), the active models' files, and the
    cached baselines. NOT copied: raw/ (the big training data). The interface backend then does
        lib = Library(dest); predict(lib, lat, lon, window_df, baseline_df)
    together with flash_drought_model.py and requirements (numpy pandas scipy scikit-learn lightgbm shap joblib)."""
    import shutil
    reg = lib._load_reg(); active = reg["active"]
    if not active: raise RuntimeError("no active model: run run_full_pipeline first")
    os.makedirs(dest, exist_ok=True)
    keep = set(active.values())
    for sub in ("raw", "baselines", "models"): os.makedirs(os.path.join(dest, sub), exist_ok=True)
    for mid in keep: shutil.copytree(lib.model_dir(mid), os.path.join(dest, "models", mid), dirs_exist_ok=True)
    if include_point_baselines:
        for n in os.listdir(os.path.join(lib.root, "baselines")): shutil.copy2(os.path.join(lib.root, "baselines", n), os.path.join(dest, "baselines", n))
    out = {"models": {m: v for m, v in reg["models"].items() if m in keep}, "active": active,
           "regions": {n: v for n, v in reg["regions"].items() if n.startswith("point_")}, "created": _now(), "exported_from": reg.get("created")}
    json.dump(out, open(os.path.join(dest, "registry.json"), "w"), indent=1)
    return {"dest": dest, "active": active}

if __name__ == "__main__":
    print(__doc__)
