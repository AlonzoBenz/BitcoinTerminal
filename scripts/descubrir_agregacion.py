"""Compara reglas candidatas de agregacion contra las columnas del Excel de la
tesis e imprime la regla ganadora y su error relativo maximo por serie.

Hallazgo central (2026-07-15): la tesis NO agrego datos diarios. Descargo los
charts de blockchain.com con el muestreo por defecto (1 punto cada 4 dias,
malla anclada en 2009-01-03, estable entre descargas) y agrego esos puntos:

  BTC_price               = last  del mes sobre la malla de 4 dias  (exacto)
  TxTfrCnt_daily_avg      = mean  del mes sobre la malla de 4 dias  (exacto)
  TxVolumeUSD_monthly_est = mean del mes (malla 4d) x dias del mes  (exacto)
  BTC_supply              = last  del mes sobre serie DIARIA        (~2.5e-6)
  Gold_price              = cierre mensual de futuros de oro (investing.com);
                            congelado como semilla en data/raw (0 exacto)
  M2SL_USD                = FRED M2SL x 1e9 (miles de millones -> USD)

Evidencia adicional: los JSON originales de la tesis (~/Downloads/Datos/) son
byte-identicos a lo que devuelve hoy la API => blockchain.info no revisa
historia y la malla es determinista; el empate se sostiene en el tiempo.

Uso: PYTHONPATH=. venv/bin/python scripts/descubrir_agregacion.py
Requiere data/raw poblado (fetch previo)."""
import pandas as pd
from src.fetchers import base

FIX = pd.read_csv("tests/fixtures/monthly_tesis.csv",
                  parse_dates=["Fecha"], index_col="Fecha")
# (nombre_raw, columna del Excel): se prueban el crudo diario y el muestreado
PARES = [
    ("btc_price", "BTC_price"), ("btc_price_sampled", "BTC_price"),
    ("btc_supply", "BTC_supply"),
    ("tx_volume_usd", "TxVolumeUSD_monthly_est"),
    ("tx_volume_usd_sampled", "TxVolumeUSD_monthly_est"),
    ("tx_count", "TxTfrCnt_daily_avg"), ("tx_count_sampled", "TxTfrCnt_daily_avg"),
    ("gold_price_monthly_seed", "Gold_price"),
]
REGLAS = ["mean", "mean_x_dias", "last", "sum", "first", "median"]


def _mensual(s, regla):
    if regla == "mean_x_dias":
        m = s.resample("MS").mean()
        return m * pd.Series(m.index.days_in_month, index=m.index)
    return s.resample("MS").agg(regla)


def main():
    for raw_name, col in PARES:
        df = base.load(raw_name)
        if df is None:
            print(f"\n== {raw_name}: sin datos en data/raw, saltando ==")
            continue
        raw = df.set_index("date")["value"]
        print(f"\n== {raw_name} vs {col} ==")
        mejor = None
        for nombre in REGLAS:
            m = _mensual(raw, nombre)
            j = pd.concat([m, FIX[col]], axis=1, join="inner").dropna()
            if len(j) == 0:
                print(f"  {nombre:11s} sin traslape")
                continue
            err = (j.iloc[:, 0] / j.iloc[:, 1] - 1).abs().max()
            print(f"  {nombre:11s} err_rel_max = {err:.6%}  (n={len(j)})")
            if mejor is None or err < mejor[1]:
                mejor = (nombre, err)
        if mejor:
            print(f"  -> GANADORA: {mejor[0]} (err_rel_max={mejor[1]:.6%})")

    # M2: unidades. FRED M2SL viene en miles de millones; el Excel esta en USD.
    m2 = base.load("m2sl").set_index("date")["value"]
    m2.index = m2.index.to_period("M").to_timestamp()
    j = pd.concat([m2, FIX["M2SL_USD"]], axis=1, join="inner").dropna()
    factor = (j["M2SL_USD"] / j["value"]).median()
    err = ((j["value"] * factor) / j["M2SL_USD"] - 1).abs().max()
    print(f"\n== m2sl vs M2SL_USD ==")
    print(f"  factor (mediana) = {factor:.6g}"
          f"  err_rel_max con factor = {err:.6%}  (n={len(j)})"
          f"  (residuo = diferencias de vintage FRED)")


if __name__ == "__main__":
    main()
