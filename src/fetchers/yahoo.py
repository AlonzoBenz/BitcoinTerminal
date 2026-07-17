"""Oro GC=F diario desde la API publica de Yahoo Finance (sin key).
Sustituye a stooq (fetch vivo roto por bot-challenge; ver T8)."""
import pandas as pd
from src.fetchers import http


def parse(js):
    r = js["chart"]["result"][0]
    ts = r["timestamp"]
    close = r["indicators"]["quote"][0]["close"]
    df = pd.DataFrame({"date": pd.to_datetime(ts, unit="s").normalize(),
                       "value": close}).dropna()
    return df.reset_index(drop=True)


def fetch_gold():
    js = http.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F",
                  params={"range": "max", "interval": "1d"})
    return parse(js)
