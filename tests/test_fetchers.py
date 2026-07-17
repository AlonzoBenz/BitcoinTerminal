import pandas as pd
from src.fetchers import blockchain_info, stooq, fred, coingecko, yahoo


def test_parse_blockchain_info():
    js = {"values": [{"x": 1420070400, "y": 263.52}, {"x": 1420156800, "y": 264.1}]}
    df = blockchain_info.parse(js)
    assert list(df.columns) == ["date", "value"]
    assert df.iloc[0]["value"] == 263.52
    assert df.iloc[0]["date"] == pd.Timestamp("2015-01-01")


def test_parse_stooq():
    txt = "Date,Open,High,Low,Close,Volume\n2015-01-02,1184.0,1194.5,1180.0,1189.0,0\n"
    df = stooq.parse(txt)
    assert df.iloc[0]["value"] == 1189.0


def test_parse_fred_ignora_faltantes():
    js = {"observations": [{"date": "2015-01-01", "value": "11805200.0"},
                           {"date": "2015-02-01", "value": "."}]}
    df = fred.parse(js)
    assert len(df) == 1 and df.iloc[0]["value"] == 11805200.0


def test_parse_coingecko_global():
    js = {"data": {"market_cap_percentage": {"btc": 58.3},
                   "total_market_cap": {"usd": 3.1e12}}}
    spot = coingecko.parse_global(js)
    assert spot["dominance_pct"] == 58.3


def test_fetch_daily_colapsa_a_un_punto_por_dia(monkeypatch):
    """btc_supply con sampled=false viene a granularidad de bloque (T11): nos
    quedamos con el ultimo valor de cada dia calendario."""
    js = {"values": [
        {"x": 1420070400, "y": 100.0},        # 2015-01-01 00:00
        {"x": 1420102800, "y": 105.0},        # 2015-01-01 09:00 (mismo dia, mas nuevo)
        {"x": 1420156800, "y": 200.0},        # 2015-01-02 00:00
    ]}
    monkeypatch.setattr(blockchain_info.http, "get", lambda *a, **kw: js)
    df = blockchain_info.fetch_daily("btc_supply")
    assert len(df) == 2
    assert df.iloc[0]["value"] == 105.0     # el ultimo del 2015-01-01, no el primero
    assert df.iloc[1]["value"] == 200.0


def test_parse_yahoo_gold():
    js = {"chart": {"result": [{
        "timestamp": [1420070400, 1420156800],
        "indicators": {"quote": [{"close": [1184.0, 1189.0]}]},
    }]}}
    df = yahoo.parse(js)
    assert list(df.columns) == ["date", "value"]
    assert df.iloc[0]["value"] == 1184.0
    assert df.iloc[0]["date"] == pd.Timestamp("2015-01-01")


def test_parse_yahoo_gold_ignora_huecos():
    js = {"chart": {"result": [{
        "timestamp": [1420070400, 1420156800],
        "indicators": {"quote": [{"close": [1184.0, None]}]},
    }]}}
    df = yahoo.parse(js)
    assert len(df) == 1 and df.iloc[0]["value"] == 1184.0


def test_save_load_roundtrip(tmp_path, monkeypatch):
    from src.fetchers import base
    monkeypatch.setattr(base, "RAW", tmp_path)
    df = pd.DataFrame({"date": pd.to_datetime(["2015-01-01", "2015-01-02"]),
                       "value": [263.52, 264.1]})
    base.save("btc_price", df)
    back = base.load("btc_price")
    assert list(back.columns) == ["date", "value"]
    assert back["date"].dtype.kind == "M"          # datetime64 sobrevive el CSV
    assert back["value"].tolist() == [263.52, 264.1]
    assert base.load("no_existe") is None
