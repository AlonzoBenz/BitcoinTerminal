"""Backfill de dominancia BTC para el hueco 2026-04..06 entre la semilla
(Excel de la tesis, congelada hasta 2026-03-01) y la acumulacion diaria via
CoinGecko `/global` (arranca el 2026-07-15, ver src/fetchers/dominance.py).

Investigacion empirica (2026-07-15, ~15 min con curl) de fuentes gratuitas/
sin-key para dominancia BTC HISTORICA (o btc_mcap + total_mcap historicos)
cubriendo 2026-04-01 -> hoy. Ninguna funciono:

  1. CoinStats  openapiv1.coinstats.app/insights/btc-dominance?type=all|1y
     -> 401 Unauthorized (requiere API key; ya no es gratis sin key,
        pese a ser la fuente original de la tesis).
  2. Coinpaprika api.coinpaprika.com/v1/global
     -> 200 pero solo snapshot ACTUAL (bitcoin_dominance_percentage=55.61
        el 2026-07-15). No existe endpoint /v1/global/history (404).
  3. CoinCap api.coincap.io/v2/... -> NXDOMAIN (v2 fue dado de baja).
     rest.coincap.io/v3/... -> 401 Unauthorized (requiere API key).
  4. CoinGecko api.coingecko.com/api/v3/global/market_cap_chart
     -> error_code 10005 "This request is limited to PRO API subscribers".
     El market_chart POR MONEDA (coins/bitcoin/market_chart) si es gratis
     y da el market cap historico de BTC solo, pero sin el market cap TOTAL
     del mercado no se puede reconstruir dominancia = btc_mcap/total_mcap.
  5. Coinlore api.coinlore.net/api/global/ -> 200 pero solo snapshot actual
     (btc_d=58.33 el 2026-07-15). /api/global/history -> 404.
  6. Messari data.messari.io/api/v1/assets/bitcoin/metrics/marketcap/...
     -> 404 (API publica descontinuada/migrada).
  7. CoinCodex coincodex.com/api/coincodex/get_all_dominance/1M -> 404.
  8. CoinMarketCap api.coinmarketcap.com/data-api/v3/... (endpoint interno
     no documentado del frontend, no una API publica) -> HTTP 200 pero
     payload de error ("The system is busy") en el momento de la prueba;
     ademas usar un endpoint interno no soportado para un script permanente
     es fragil y de dudosa legitimidad (no es "keyless API" en el sentido
     del criterio de busqueda). Descartado.
  9. cryptorank.io -> timeout.

Conclusion: no hay fuente real, gratuita y sin key que cubra el hueco.
Se aplica IMPUTACION TRANSPARENTE: interpolacion lineal entre el ultimo
punto de la semilla (55.832258064516125 @ 2026-03-01) y el valor EN VIVO
de CoinGecko `/global` obtenido una sola vez en el momento de correr este
script (fuente: src.fetchers.coingecko.fetch_global(), la misma que ya usa
dominance.py para la acumulacion diaria real). Los puntos interpolados se
anclan al primer dia de cada mes faltante (2026-04-01, 2026-05-01,
2026-06-01) y se appendean a data/raw/btc_dominance_daily.csv -- el mismo
archivo y formato (date,value) que escribe dominance.append_today(). La
semilla (data/raw/btc_dominance_seed.csv) NO se toca.

Ver tambien data/raw/btc_dominance_backfill_NOTA.md para el detalle
completo de la imputacion y su impacto (bajo: el coeficiente de UC
-unidad de cuenta, la variable que usa esta serie- es estadisticamente
no significativo en el modelo, ver docs/superpowers/specs/
2026-07-07-bitcoin-terminal-design.md linea 106).

Correr: cd ~/BitcoinTerminal && venv/bin/python scripts/backfill_dominancia.py
"""
import datetime as dt
import pathlib
import sys

import pandas as pd

sys.path.insert(0, ".")
from src.fetchers import coingecko, dominance

SEED = dominance.SEED
DAILY = dominance.DAILY


def _puntos_faltantes(seed_last_date, hoy):
    """Primeros de mes estrictamente despues del ultimo mes de la semilla
    y antes del mes actual (el mes actual ya lo cubre la acumulacion diaria
    real que arranca hoy)."""
    inicio_mes_actual = pd.Timestamp(hoy.year, hoy.month, 1)
    faltantes = pd.date_range(
        seed_last_date + pd.DateOffset(months=1), inicio_mes_actual, freq="MS"
    )
    return faltantes[faltantes < inicio_mes_actual]


def calcular_interpolacion():
    seed = pd.read_csv(SEED, parse_dates=["date"]).set_index("date")["value"]
    seed_last_date = seed.index.max()
    seed_last_value = float(seed.loc[seed_last_date])

    hoy = dt.date.today()
    hoy_ts = pd.Timestamp(hoy)
    hoy_valor = coingecko.fetch_global()["dominance_pct"]

    faltantes = _puntos_faltantes(seed_last_date, hoy)
    total_dias = (hoy_ts - seed_last_date).days

    filas = []
    for fecha in faltantes:
        frac = (fecha - seed_last_date).days / total_dias
        valor = seed_last_value + frac * (hoy_valor - seed_last_value)
        filas.append((fecha.date().isoformat(), valor))
    return filas, seed_last_date, seed_last_value, hoy, hoy_valor


def escribir_daily(filas):
    if DAILY.exists():
        df = pd.read_csv(DAILY, dtype={"date": str})
    else:
        df = pd.DataFrame(columns=["date", "value"])
    existentes = set(df["date"])
    nuevas = 0
    for fecha, valor in filas:
        if fecha in existentes:
            continue
        df.loc[len(df)] = [fecha, valor]
        nuevas += 1
    df = df.sort_values("date").reset_index(drop=True)
    DAILY.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DAILY, index=False)
    return nuevas, df


def escribir_nota(seed_last_date, seed_last_value, hoy, hoy_valor, filas):
    nota = DAILY.parent / "btc_dominance_backfill_NOTA.md"
    filas_txt = "\n".join(f"- {f}: {v:.6f}" for f, v in filas)
    contenido = f"""# Backfill de dominancia BTC 2026-04..06 (imputacion transparente)

## Que se imputo

Tres puntos mensuales de dominancia BTC que no tenian fuente real disponible:

{filas_txt}

## Por que

La semilla historica (`data/raw/btc_dominance_seed.csv`, del Excel validado
de la tesis) termina en {seed_last_date.date().isoformat()}
({seed_last_value:.6f}). La acumulacion diaria via CoinGecko `/global`
(`src/fetchers/dominance.py`) arranca el {hoy.isoformat()}. Los meses
2026-04, 2026-05 y 2026-06 (y la primera quincena de 2026-07) quedan sin
ninguna muestra real. El modelo ARDL necesita una serie mensual contigua
-- un hueco permanente rompe cualquier estimacion futura.

Se investigaron 9 fuentes gratuitas/sin-key para dominancia BTC historica
(o btc_mcap + total_mcap historicos) que cubrieran ese rango: CoinStats,
Coinpaprika, CoinCap v2/v3, CoinGecko `/global/market_cap_chart`, Coinlore,
Messari, CoinCodex y el endpoint interno de CoinMarketCap. Ninguna ofrece
datos historicos reales sin llave de pago; el detalle completo (URLs,
respuestas de curl, veredicto de cada una) esta documentado en el docstring
de `scripts/backfill_dominancia.py`.

## Metodo

Interpolacion lineal (ponderada por dias calendario) entre:
- el ultimo punto de la semilla: {seed_last_value:.6f} @ {seed_last_date.date().isoformat()}
- el valor EN VIVO de CoinGecko `/global` obtenido una sola vez el
  {hoy.isoformat()}: {hoy_valor:.6f}
  (fuente: `src.fetchers.coingecko.fetch_global()`, la misma fuente que ya
  usa `dominance.py` para la acumulacion diaria real -- no se introduce
  ninguna fuente nueva).

Los puntos interpolados se anclan al primer dia de cada mes faltante y se
guardan en `data/raw/btc_dominance_daily.csv` (mismo formato que escribe
`dominance.append_today()`: columnas `date,value`). La semilla no se toca.

## Impacto / limitacion

Estos tres valores mensuales son estimados, no observados. El impacto en
el modelo se considera bajo porque la variable que consume esta serie,
UC (unidad de cuenta, `log(Dominance / (1 - Dominance))`), tiene un
coeficiente estadisticamente NO significativo en la regresion de largo
plazo (ver `docs/superpowers/specs/2026-07-07-bitcoin-terminal-design.md`,
linea 106: "unidad de cuenta X (UC ns)"). Aun asi, esto se debe reportar
como limitacion metodologica del panel de datos: 3 de los ~138 meses de
la serie (2015-01 a 2026-06) son imputados por interpolacion lineal en
vez de observados.

Cuando una fuente real y gratuita para dominancia BTC historica este
disponible, estos 3 puntos deberian reemplazarse por datos observados.
"""
    nota.write_text(contenido)
    return nota


def main():
    filas, seed_last_date, seed_last_value, hoy, hoy_valor = calcular_interpolacion()
    if not filas:
        print("No hay meses faltantes que rellenar.")
        return
    nuevas, df = escribir_daily(filas)
    nota = escribir_nota(seed_last_date, seed_last_value, hoy, hoy_valor, filas)
    print(f"Semilla hasta {seed_last_date.date().isoformat()} ({seed_last_value:.6f})")
    print(f"CoinGecko en vivo {hoy.isoformat()}: {hoy_valor:.6f}")
    print(f"{nuevas} filas nuevas escritas en {DAILY}")
    print(df.tail(len(filas) + 2))
    print(f"Nota escrita en {nota}")


if __name__ == "__main__":
    main()
