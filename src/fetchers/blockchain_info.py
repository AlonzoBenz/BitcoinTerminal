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


def fetch_sampled(key):
    """Serie con el muestreo por defecto de blockchain.info (1 punto cada 4 dias,
    malla anclada en 2009-01-03). Es la forma en que la tesis descargo los charts:
    la base mensual del Excel se construyo sobre esta malla, no sobre datos diarios
    (ver scripts/descubrir_agregacion.py)."""
    js = http.get(f"https://api.blockchain.info/charts/{CHARTS[key]}",
                  params={"timespan": "all", "format": "json"})
    return parse(js)
