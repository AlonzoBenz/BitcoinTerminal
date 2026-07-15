import pandas as pd
from src.fetchers import http

CHARTS = {
    "btc_price": "market-price",
    "btc_supply": "total-bitcoins",
    "tx_volume_usd": "estimated-transaction-volume-usd",
    "tx_count": "n-transactions",
    "difficulty": "difficulty",
    "fees_btc": "transaction-fees",
}


def parse(js):
    df = pd.DataFrame(js["values"]).rename(columns={"x": "date", "y": "value"})
    df["date"] = pd.to_datetime(df["date"], unit="s")
    return df[["date", "value"]]


def fetch(key):
    js = http.get(f"https://api.blockchain.info/charts/{CHARTS[key]}",
                  params={"timespan": "all", "format": "json", "sampled": "false"})
    return parse(js)
