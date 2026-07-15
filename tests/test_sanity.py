import pandas as pd
import src.sanity as sanity


def _df(vals, start="2020-01-01"):
    return pd.DataFrame({"date": pd.date_range(start, periods=len(vals)), "value": vals})


def test_rechaza_negativos():
    ok, why = sanity.check("btc_price", _df([100.0, -5.0, 101.0]))
    assert not ok and "negativ" in why


def test_rechaza_salto_absurdo_vs_previa():
    prev = _df([100.0] * 10)
    new = _df([100.0] * 9 + [900.0])
    ok, why = sanity.check("btc_price", new, prev)
    assert not ok and "salto" in why


def test_acepta_serie_normal():
    ok, _ = sanity.check("btc_price", _df([100.0, 101.5, 99.8]))
    assert ok


def test_frescura():
    assert sanity.freshness_status("m2sl", age_days=30) == "FRESCO"
    assert sanity.freshness_status("m2sl", age_days=60) == "STALE"
    assert sanity.freshness_status("btc_price", age_days=200) == "DEAD"
