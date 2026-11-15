"""Known-answer unit tests of the model code (no data files, no network). Run:  python test_flash_drought.py"""
import numpy as np, pandas as pd
import flash_drought_model as fd

def test_doy():
    d = pd.to_datetime(["2023-02-28", "2023-03-01", "2024-02-28", "2024-02-29", "2024-03-01", "2024-12-31"])
    assert list(fd.doy365(d)) == [59, 60, 59, 59, 60, 365]

def test_events():
    nan = np.nan; base = [60.0] * 30
    x = np.array(base + [30, 20] + [10.0] * 14 + [50.0] * 30)            # rapid fall, 14 dry days => event
    ev, on = fd.flash_drought_events(x); i = 32
    assert on[i] == 1 and ev[i:i + 14].all() and ev.sum() == 14
    x = np.array(base + [30, 20] + [10.0] * 13 + [50.0] * 30)            # only 13 dry days => none
    assert fd.flash_drought_events(x)[0].sum() == 0
    x = np.array([30.0] * 40 + [10.0] * 20 + [50.0] * 30)                # slow drift, never >=40 => not flash
    assert fd.flash_drought_events(x)[0].sum() == 0
    x = np.array(base + [10.0] * 7 + [nan] + [10.0] * 7 + [50.0] * 30)   # a NaN breaks the run
    assert fd.flash_drought_events(x)[0].sum() == 0
    x = np.array(base + [10.0] * 5)                                      # right-censoring
    assert np.isnan(fd.flash_drought_events(x)[1][-5:]).all()

def test_future_any():
    y = fd.future_any([0, 0, 1, 0, 0, 0], 2)
    assert list(y[:2]) == [1, 1] and y[2] == 0 and np.isnan(y[-2:]).all()

def test_pct_rank():
    samp = np.full((365, 10), np.nan, dtype=np.float32); samp[4, :4] = [1, 2, 3, 4]
    r = fd.pct_rank([0.5, 2.0, 9.0, np.nan], np.array([5, 5, 5, 5]), samp)
    assert r[0] == 0 and r[1] == 37.5 and r[2] == 100 and np.isnan(r[3])

def test_rolling_rule():
    s = pd.Series([1.0] * 10); s[3] = np.nan
    assert not np.isnan(fd.rolling(s, 7, False)[9])          # 6/7 valid >= 80%
    s[4] = np.nan; s[5] = np.nan
    assert np.isnan(fd.rolling(s, 7, False)[9])              # 4/7 valid < 80%

def _day(date, tmax, tmin, rh, ws, rs, ps):
    return pd.DataFrame({"date": pd.to_datetime([date]), "T2M_MAX": [tmax], "T2M_MIN": [tmin], "RH2M": [rh],
                         "WS2M": [ws], "ALLSKY_SFC_SW_DWN": [rs], "PS": [ps]})

def test_fao56_example18():
    """FAO-56 Example 18 (Uccle, Belgium, 6 July, lat 50.80 N, z = 100 m). Published: es 1.997, ea 1.409, VAD 0.589 kPa, ET0 3.88 mm/day.
    The paper gives RHmax/RHmin (ea = 1.4086); we feed the equivalent RHmean = ea/es*100 because POWER has only RH2M (mean)."""
    es = (fd._es(21.5) + fd._es(12.3)) / 2
    r = fd.compute_vad_et0(_day("2019-07-06", 21.5, 12.3, 1.408624 / es * 100, 2.078, 22.07, 100.1), 50.8).iloc[0]
    assert abs(es - 1.997) < 0.002
    assert abs(r["VAD"] - 0.5889) < 0.002, r["VAD"]
    assert abs(r["ET0"] - 3.88) < 0.03, r["ET0"]

def test_et0_extremes_plausible():
    hot = fd.compute_vad_et0(_day("2024-07-01", 40, 24, 15, 4, 29, 100.0), 31.6).iloc[0]
    cold = fd.compute_vad_et0(_day("2024-01-01", 8, 0, 85, 2, 8, 100.0), 31.6).iloc[0]
    assert 7 < hot["ET0"] < 13 and hot["VAD"] > 2.5
    assert cold["ET0"] < 2 and cold["VAD"] < 0.3

def test_radiation_unit_guard():
    d = pd.concat([_day("2024-07-01", 30, 18, 40, 2, 7.5, 100.0)] * 1200, ignore_index=True)          # 1200 days of kWh-like values
    d["date"] = pd.date_range("2020-01-01", periods=1200)
    try: fd.compute_vad_et0(d, 30.0)
    except ValueError as e: assert "kWh" in str(e)
    else: raise AssertionError("kWh/m2/day input must be refused")

def test_missing_columns_message():
    d = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"]), "PRECTOTCORR": [0.0], "GWETROOT": [0.4]})
    try: fd.clean_table(d, 30.0)
    except ValueError as e: assert "missing" in str(e)
    else: raise AssertionError("missing raw columns must raise")

def test_minus999_is_nan_and_vad_nan():
    d = _day("2024-07-01", 30, 18, -999, 2, 25, 100.0); d["PRECTOTCORR"] = 0.0; d["GWETROOT"] = 0.3
    c = fd.clean_table(d, 30.0)
    assert np.isnan(c["VAD"].iloc[0]) and np.isnan(c["ET0"].iloc[0])      # no silent value from a missing RH

if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"): f(); print("ok", k)
