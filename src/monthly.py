"""Base mensual del modelo desde los crudos de data/raw.

Reglas de agregacion fijadas empiricamente contra el Excel de la tesis con
scripts/descubrir_agregacion.py (protegidas por tests/test_monthly_vs_excel.py):

  BTC_price   last del mes sobre *_sampled (malla blockchain.info de 4 dias)
  BTC_supply  last del mes sobre serie diaria
  TxVolumeUSD mean del mes sobre *_sampled x dias del mes (estimado mensual)
  TxTfrCnt    mean del mes sobre *_sampled (promedio diario)
  Gold_price  semilla mensual congelada (cierre de futuros, base de la tesis)
              extendida con last del mes de gold_price diario para meses nuevos
  M2SL        FRED M2SL x 1e9, con ffill como nowcast del ultimo publicado
  Dominance   src.fetchers.dominance.monthly_series (semilla + acumulacion)

Las FORMULAS de las variables (DMB, MC2, MC1, RV12, UC) las fija la tesis y no
se tocan."""
import numpy as np
import pandas as pd
from src.fetchers import base, dominance

M2_FACTOR = 1e9   # FRED M2SL en miles de millones de USD -> USD (verificado)


def _serie(name):
    return base.load(name).set_index("date")["value"].sort_index()


def _gold_monthly():
    seed = _serie("gold_price_monthly_seed")
    seed.index = seed.index.to_period("M").to_timestamp()
    out = seed.copy()
    daily = base.load("gold_price")
    if daily is not None:
        m = daily.set_index("date")["value"].sort_index().resample("MS").last()
        out = pd.concat([out, m[m.index > seed.index.max()]])  # semilla inmutable
    return out.sort_index()


def build(start="2013-01-01"):
    # start=2013: warm-up holgado para el shift(12) de RV12 antes de 2015
    price = _serie("btc_price_sampled").resample("MS").last()
    supply = _serie("btc_supply").resample("MS").last()
    txcnt = _serie("tx_count_sampled").resample("MS").mean()
    txvol = _serie("tx_volume_usd_sampled").resample("MS").mean()
    txvol = txvol * pd.Series(txvol.index.days_in_month, index=txvol.index)
    gold = _gold_monthly()
    m2 = _serie("m2sl") * M2_FACTOR
    m2.index = m2.index.to_period("M").to_timestamp()
    dom = dominance.monthly_series()

    idx = price.loc[start:].index
    df = pd.DataFrame(index=idx)
    df.index.name = "Fecha"
    df["BTC_price"], df["BTC_supply"] = price, supply
    df["MarketCapBTC_USD"] = price * supply
    df["M2SL_USD"] = m2
    df["m2_published"] = df["M2SL_USD"].notna()
    df["M2SL_USD"] = df["M2SL_USD"].ffill()     # nowcast: ultimo publicado
    df["TxVolumeUSD"], df["TxTfrCnt"], df["Gold_price"] = txvol, txcnt, gold
    df["Dominance_dec"] = (dom / 100.0).clip(1e-6, 1 - 1e-6)

    df["DMB"] = np.log(df["MarketCapBTC_USD"] / df["M2SL_USD"])
    df["MC2"] = np.log(df["TxVolumeUSD"] / df["M2SL_USD"])
    df["MC1"] = np.log(df["TxTfrCnt"] / df["BTC_supply"])
    df["RV12"] = (np.log(df["BTC_price"] / df["BTC_price"].shift(12))
                  - np.log(df["Gold_price"] / df["Gold_price"].shift(12)))
    df["UC"] = np.log(df["Dominance_dec"] / (1 - df["Dominance_dec"]))
    return df.loc["2015-01-01":]   # inicio de la muestra de la tesis


def write(path="data/monthly.csv"):
    df = build()
    df.to_csv(path)
    return df
