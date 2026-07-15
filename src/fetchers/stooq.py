import io
import pandas as pd
from src.fetchers import http


def parse(txt):
    df = pd.read_csv(io.StringIO(txt), parse_dates=["Date"])
    df = df.rename(columns={"Date": "date", "Close": "value"})
    return df[["date", "value"]].dropna()


def fetch():
    txt = http.get("https://stooq.com/q/d/l/", params={"s": "xauusd", "i": "d"},
                   as_json=False)
    return parse(txt)
