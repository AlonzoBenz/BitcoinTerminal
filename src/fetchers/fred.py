import os
import pandas as pd
from src.fetchers import http


def parse(js):
    rows = [(o["date"], float(o["value"]))
            for o in js["observations"] if o["value"] != "."]
    df = pd.DataFrame(rows, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch(series="M2SL"):
    key = os.environ["FRED_API_KEY"]      # nunca se loggea; http.get trunca en '?'
    js = http.get("https://api.stlouisfed.org/fred/series/observations",
                  params={"series_id": series, "api_key": key, "file_type": "json"})
    return parse(js)
