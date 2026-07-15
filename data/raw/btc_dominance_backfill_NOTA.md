# Backfill de dominancia BTC 2026-04..06 (imputacion transparente)

## Que se imputo

Tres puntos mensuales de dominancia BTC que no tenian fuente real disponible:

- 2026-04-01: 55.950758
- 2026-05-01: 56.065435
- 2026-06-01: 56.183935

## Por que

La semilla historica (`data/raw/btc_dominance_seed.csv`, del Excel validado
de la tesis) termina en 2026-03-01
(55.832258). La acumulacion diaria via CoinGecko `/global`
(`src/fetchers/dominance.py`) arranca el 2026-07-15. Los meses
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
- el ultimo punto de la semilla: 55.832258 @ 2026-03-01
- el valor EN VIVO de CoinGecko `/global` obtenido una sola vez el
  2026-07-15: 56.352128
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
