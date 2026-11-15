"""Tests of the API connection code with a stand-in for the server (no network). Run:  python test_power_client.py"""
import tempfile, warnings
import numpy as np, pandas as pd
import requests
import flash_drought_model as fd, power_client as pc

class Resp:
    def __init__(self, code, js=None, text="x"): self.status_code = code; self.ok = code < 300; self._js = js; self.text = text
    def json(self):
        if self._js is None: raise ValueError("no json")
        return self._js

def power_json(n=5, units=None, gw=0.4):
    idx = pd.date_range("2024-01-01", periods=n).strftime("%Y%m%d")
    par = {p: {d: (-999.0 if (p == "PRECTOTCORR" and i == 1) else (gw if p == "GWETROOT" else 1.0)) for i, d in enumerate(idx)} for p in pc.PARAMS}
    meta = {p: {"units": u} for p, u in (units or {}).items()}
    js = {"properties": {"parameter": par}}
    if meta: js["parameters"] = meta
    return js

GOOD_UNITS = {"PRECTOTCORR": "mm/day", "GWETROOT": "1", "T2M_MAX": "C", "T2M_MIN": "C", "RH2M": "%", "WS2M": "m/s",
              "ALLSKY_SFC_SW_DWN": "MJ/m^2/day", "PS": "kPa"}

def with_server(responses):
    calls = []
    def fake_get(url, params=None, timeout=None):
        calls.append(params); return responses[min(len(calls) - 1, len(responses) - 1)]
    requests.get = fake_get; pc.time.sleep = lambda s: None
    return calls

def client(): return pc.NasaPowerClient(verbose=False)

def test_request_asks_only_for_the_8_variables_in_AG():
    calls = with_server([Resp(200, power_json(units=GOOD_UNITS))])
    d = client().get(31.6, -8.0, "2024-01-01", "2024-01-05")
    q = calls[0]
    assert q["community"] == "AG" and q["start"] == "20240101" and q["end"] == "20240105" and q["latitude"] == 31.6 and q["longitude"] == -8.0
    assert q["parameters"].split(",") == ["PRECTOTCORR", "GWETROOT", "T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PS"]
    assert list(d.columns) == ["date"] + pc.PARAMS and len(d) == 5
    assert np.isnan(d["PRECTOTCORR"].iloc[1]) and d["PRECTOTCORR"].iloc[0] == 1.0      # -999 -> NaN

def test_422_is_not_retried():
    calls = with_server([Resp(422, text="bad parameter")])
    try: client().get(1, 1, "2024-01-01", "2024-01-05")
    except pc.PowerParameterError: pass
    else: raise AssertionError("422 must raise PowerParameterError")
    assert len(calls) == 1

def test_server_errors_are_retried_then_succeed():
    calls = with_server([Resp(503), Resp(429), Resp(200, power_json(units=GOOD_UNITS))])
    assert len(client().get(1, 1, "2024-01-01", "2024-01-05")) == 5 and len(calls) == 3

def test_gives_up_after_retries():
    with_server([Resp(500)])
    try: pc.NasaPowerClient(retries=3, verbose=False).get(1, 1, "2024-01-01", "2024-01-05")
    except pc.PowerError: pass
    else: raise AssertionError("must raise after retries")

def test_wrong_radiation_unit_stops():
    bad = dict(GOOD_UNITS, ALLSKY_SFC_SW_DWN="kW-hr/m^2/day")
    with_server([Resp(200, power_json(units=bad))])
    try: client().get(1, 1, "2024-01-01", "2024-01-05")
    except pc.PowerUnitError as e: assert "ALLSKY_SFC_SW_DWN" in str(e)
    else: raise AssertionError("kWh radiation must be refused")

def test_missing_unit_info_only_warns():
    with_server([Resp(200, power_json())])
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always"); client().get(1, 1, "2024-01-01", "2024-01-05")
    assert any("units NOT verified" in str(x.message) for x in w)

def test_missing_variable_in_answer_is_an_error():
    js = power_json(units=GOOD_UNITS); del js["properties"]["parameter"]["PS"]
    with_server([Resp(200, js)])
    try: client().get(1, 1, "2024-01-01", "2024-01-05")
    except pc.PowerError as e: assert "PS" in str(e)
    else: raise AssertionError("a missing variable must raise")

def test_custom_fetch_hook():
    def my_fetch(lat, lon, start, end, parameters):
        return pd.DataFrame({"date": pd.date_range(start, end), **{p: 1.0 for p in parameters}})
    d = pc.NasaPowerClient(fetch=my_fetch).get(1, 2, "2024-01-01", "2024-01-03")
    assert len(d) == 3 and list(d.columns) == ["date"] + pc.PARAMS

def test_build_points_are_land_and_in_range():
    from global_land_mask import globe
    p = pc.build_points(step=40)
    assert len(p) > 3 and p["name"].is_unique and all(globe.is_land(a, b) for a, b in zip(p["lat"], p["lon"]))
    assert p["lat"].between(-55, 65).all() and p["lon"].between(-180, 180).all()

def test_fetch_all_is_resumable_and_skips_no_soil():
    n = {"calls": 0}
    def my_fetch(lat, lon, start, end, parameters):
        n["calls"] += 1; idx = pd.date_range(start, end)
        d = pd.DataFrame({"date": idx, "PRECTOTCORR": 1.0, "GWETROOT": (np.nan if lat < 0 else 0.4), "T2M_MAX": 30.0, "T2M_MIN": 18.0,
                          "RH2M": 40.0, "WS2M": 2.0, "ALLSKY_SFC_SW_DWN": 22.0, "PS": 100.0})
        return d[["date"] + list(parameters)]
    pts = pd.DataFrame({"name": ["a", "b", "c"], "lat": [10.0, -10.0, 20.0], "lon": [0.0, 0.0, 5.0]})
    lib = fd.Library(tempfile.mkdtemp()); c = pc.NasaPowerClient(fetch=my_fetch)
    s = pc.fetch_all(lib, c, pts)
    assert s["stored"] == 2 and s["no_soil_data"] == 1 and set(fd.all_regions(lib)) == {"a", "c"} and n["calls"] == 3
    s2 = pc.fetch_all(lib, c, pts)
    assert n["calls"] == 3 and s2["stored"] == 0                          # nothing asked twice (stored AND no-soil points remembered)

if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"): f(); print("ok", k)
