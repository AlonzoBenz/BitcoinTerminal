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


def fetch_daily(key):
    """Version a 1 punto/dia (ultimo valor observado del dia) de un chart sin
    muestrear. Existe porque, para el chart "total-bitcoins" (btc_supply),
    sampled=false devuelve granularidad de bloque (~925k filas, ~28MB: infla
    el repo sin aportar nada, la oferta crece casi linealmente) en vez de la
    serie diaria que uso la tesis. Bajamos el payload completo (transitorio,
    no se persiste) y solo guardamos el cierre de cada dia -> mismo nivel de
    precision que un fetch diario real, archivo chico."""
    df = fetch(key)
    daily = df.set_index("date")["value"].resample("D").last().dropna()
    return daily.reset_index()


def fetch_sampled(key):
    """Serie con el muestreo por defecto de blockchain.info (1 punto cada 4 dias,
    malla anclada en 2009-01-03). Es la forma en que la tesis descargo los charts:
    la base mensual del Excel se construyo sobre esta malla, no sobre datos diarios
    (ver scripts/descubrir_agregacion.py)."""
    js = http.get(f"https://api.blockchain.info/charts/{CHARTS[key]}",
                  params={"timespan": "all", "format": "json"})
    df = parse(js)
    # la base mensual depende de esta malla: si la API cambia su muestreo por
    # defecto, fallar ruidosamente aqui y no en silencio en la agregacion
    paso = df["date"].diff().dt.days.mode()
    if paso.empty or paso.iloc[0] != 4:
        raise RuntimeError(
            f"chart {CHARTS[key]}: el muestreo por defecto ya no es de 4 dias")
    return df
