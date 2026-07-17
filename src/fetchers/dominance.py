"""Dominancia BTC: semilla mensual congelada (Excel de la tesis, 2015-2026M03)
+ acumulacion diaria desde CoinGecko para los meses posteriores."""
import datetime as dt
import pathlib
import pandas as pd
from src.fetchers import coingecko

SEED = pathlib.Path("data/raw/btc_dominance_seed.csv")
DAILY = pathlib.Path("data/raw/btc_dominance_daily.csv")


def hoy_dominancia():
    return coingecko.fetch_global()["dominance_pct"]


def append_today():
    today = dt.date.today().isoformat()
    if DAILY.exists():
        df = pd.read_csv(DAILY, dtype={"date": str})
        if (df["date"] == today).any():
            return False
    else:
        df = pd.DataFrame(columns=["date", "value"])
    val = hoy_dominancia()
    # puerta de sanidad: toda la historia de la dominancia BTC cae dentro de
    # este rango con margen enorme; fuera de el la API respondio basura y
    # build.py degrada a STALE sin escribir nada
    if not (20.0 <= val <= 95.0):
        raise ValueError(f"dominancia fuera de rango plausible: {val}")
    df.loc[len(df)] = [today, val]
    DAILY.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DAILY, index=False)
    return True


def monthly_series():
    seed = pd.read_csv(SEED, parse_dates=["date"]).set_index("date")["value"]
    seed.index = seed.index.to_period("M").to_timestamp()
    out = seed.copy()
    if DAILY.exists():
        d = pd.read_csv(DAILY, parse_dates=["date"]).set_index("date")["value"]
        m = d.resample("MS").mean()
        m = m[m.index > seed.index.max()]      # la semilla es inmutable
        out = pd.concat([out, m])
    return out.sort_index()
