"""
simulate_test_data.py  --  TEST ONLY.  SYNTHETIC data to check that the pipeline RUNS end to end.
NOT part of the model, never imported by it, and its results mean NOTHING scientifically (the "weather" is random numbers).

Writes the SAME layout the data team delivers:
    <folder>/points.csv            name,lat,lon
    <folder>/<name>.csv            date + 8 raw POWER columns (+T2M), -999 for gaps, 2005-01-01..2024-12-31
    <folder>/demo_baseline.csv     2005-2014 of ONE extra point that is NOT in points.csv   (to test prediction on an unseen place)
    <folder>/demo_window.csv       2024-04-11..2024-07-15 of that same point               (the "last days" window)
The last region has a deliberate 10-day gap in its dates: the pipeline must EXCLUDE it (that is part of the test).

Usage:   python simulate_test_data.py /content/sim_data 24        (CSV files, for the CSV route)
         client = power_client.NasaPowerClient(fetch=simulate_test_data.mock_fetch)    (a stand-in for the NASA POWER API, no network)
"""
import os, sys, numpy as np, pandas as pd
import flash_drought_model as fd            # only for compute_vad_et0 (to make the fake soil respond to fake ET0)

BASE_START, BASE_END = fd.BASE_START, fd.BASE_END
compute_vad_et0 = fd.compute_vad_et0

def _fake_region(lat, lon, seed, wetness, spells_per_year=2.2):
    """Physically coupled fake NASA-POWER-like daily table with RAW POWER columns (ET0/VAD are computed later by the same
    code used for real data). A slow wet/dry regime plus random multi-week DRY SPELLS (hot, sunny, no rain) drive a soil bucket,
    so soil moisture sometimes collapses fast and stays low = flash droughts, with the weather signals (rain, VAD, ET0, heat) leading it."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2005-01-01", "2024-12-31"); n = len(dates); doy = dates.dayofyear.values
    hemi = 1.0 if lat >= 0 else -1.0
    season = hemi * np.sin(2 * np.pi * (doy - 172) / 365)                         # +1 = local summer
    amp = 2 + 0.28 * abs(lat)
    regime = np.zeros(n); r = 0.0
    for i in range(n): r = 0.97 * r + rng.normal(0, 0.15); regime[i] = r           # slow wet(+)/dry(-) tendency, sd ~0.6
    spell = np.zeros(n)                                                             # random dry spells, 15-45 days
    for _ in range(rng.poisson(spells_per_year * 20)):
        a0 = rng.integers(0, n - 50); spell[a0:a0 + rng.integers(15, 46)] = 1.0
    tmean = 28 - 0.33 * abs(lat) + amp * season - 0.8 * regime + 4.0 * spell + rng.normal(0, 1.8, n)
    dtr = np.clip(9 + 3 * spell + rng.normal(0, 1.5, n), 3, 18)
    tmax, tmin = tmean + dtr / 2, tmean - dtr / 2
    pwet = np.clip(wetness - 0.10 * season + 0.15 * regime, 0.02, 0.85) * (1 - 0.95 * spell)
    rain = (rng.random(n) < pwet) * rng.gamma(0.8, 7.0, n)
    rh = np.clip(62 - 1.3 * (tmax - 25) + 22 * (rain > 0) + 8 * regime - 12 * spell + rng.normal(0, 6, n), 8, 98)
    ws = np.clip(rng.gamma(4, 0.65, n) * (1 + 0.25 * spell), 0.3, 12)
    z = rng.uniform(0, 1500); ps = 101.3 * np.exp(-z / 8400) * np.ones(n)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365); dec = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39); phi = np.deg2rad(lat)
    wsa = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1, 1))
    ra = (24 * 60 / np.pi) * 0.0820 * dr * (wsa * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(wsa))
    sw = np.clip(ra * (0.75 + 2e-5 * z) * (0.80 - 0.45 * (rain > 0) + 0.05 * spell), 1.0, None)
    d = pd.DataFrame({"date": dates, "PRECTOTCORR": rain, "GWETROOT": 0.5, "T2M_MAX": tmax, "T2M_MIN": tmin, "T2M": tmean,
                      "RH2M": rh, "WS2M": ws, "ALLSKY_SFC_SW_DWN": sw, "PS": ps})
    et0 = compute_vad_et0(d, lat)["ET0"].values
    cap = rng.uniform(150, 260); s_ = 0.5; soil = np.zeros(n)                       # soil bucket (mm), loss rises with wetness
    for i in range(n):
        s_ = min(max(s_ + (rain[i] - et0[i] * (0.15 + 0.85 * s_)) / cap, 0.03), 0.97); soil[i] = s_
    d["GWETROOT"] = soil
    return d

def simulate(folder: str, n_regions: int = 24, seed: int = 0, with_bad_region: bool = True):
    """Writes <folder>/<name>.csv (raw POWER columns, -999 for gaps) + points.csv -- the SAME layout download_power.py produces --
    plus demo_window.csv / demo_baseline.csv for ONE extra point that is NOT in points.csv (to test prediction on an unseen place)."""
    os.makedirs(folder, exist_ok=True); rng = np.random.default_rng(seed); rows = []
    for i in range(n_regions):
        lat = float(np.round(rng.uniform(-45, 55), 2)); lon = float(np.round(rng.uniform(-120, 140), 2))
        d = _fake_region(lat, lon, seed * 1000 + i, wetness=rng.uniform(0.15, 0.45))
        num = [c for c in d.columns if c != "date"]
        mask = rng.random(d[num].shape) < 0.002                                   # 0.2% missing as -999 (like NASA)
        d2 = d.copy(); d2[num] = d[num].mask(mask, -999.0)
        if with_bad_region and i == n_regions - 1: d2 = d2.drop(index=range(1000, 1010))   # a gap in dates -> must be EXCLUDED
        name = f"fake_{i:02d}"; d2.to_csv(os.path.join(folder, f"{name}.csv"), index=False); rows.append((name, lat, lon))
    pd.DataFrame(rows, columns=["name", "lat", "lon"]).to_csv(os.path.join(folder, "points.csv"), index=False)
    d = _fake_region(33.3, -7.5, seed * 1000 + 999, wetness=0.25)
    d[(d["date"] >= BASE_START) & (d["date"] <= BASE_END)].to_csv(os.path.join(folder, "demo_baseline.csv"), index=False)
    d[(d["date"] > "2024-04-10") & (d["date"] <= "2024-07-15")].to_csv(os.path.join(folder, "demo_window.csv"), index=False)
    return folder


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "sim_data"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    simulate(folder, n_regions=n); print("synthetic test data written to", folder)


# ---- stand-in for the NASA POWER API (test only): same call signature as a real `fetch` ------------------------------------
_MOCK_CACHE = {}
def mock_fetch(lat, lon, start, end, parameters):
    """Synthetic replacement for the API: returns date + the requested columns for (lat, lon), -999 for a few gaps, and only
    days up to 2024-12-31 (like a real source that has no data after its last day). Deterministic per coordinate."""
    key = (round(float(lat), 2), round(float(lon), 2))
    if key not in _MOCK_CACHE:
        seed = int(abs(hash(key)) % 100000)
        rng = np.random.default_rng(seed)
        d = _fake_region(key[0], key[1], seed, wetness=float(rng.uniform(0.15, 0.45)))
        num = [c for c in d.columns if c != "date"]
        d[num] = d[num].mask(rng.random(d[num].shape) < 0.002, -999.0)
        _MOCK_CACHE[key] = d
    d = _MOCK_CACHE[key]
    return d[(d["date"] >= pd.Timestamp(start)) & (d["date"] <= pd.Timestamp(end))][["date"] + list(parameters)].reset_index(drop=True)
