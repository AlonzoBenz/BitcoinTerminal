"""Puertas de sanidad (spec §6.2) y contrato de frescura (§6.3).
Serie insana => se conserva el ultimo CSV bueno y se marca SUSPECT."""

MAX_JUMP = 4.0          # ratio max ultimo valor vs mediana de los 30 previos
POSITIVE = {"btc_price", "btc_supply", "tx_volume_usd", "tx_count",
            "gold_price", "m2sl", "difficulty", "fees_btc",
            "btc_price_sampled", "tx_count_sampled", "tx_volume_usd_sampled"}
POSITIVE_TAIL = 90     # solo se exige positividad en la cola reciente: btc_price,
                       # difficulty y fees_btc traen ceros legitimos en 2009-2010
                       # (pre-mercado / arranque de la red) en el historico completo
MAX_AGE_DAYS = {"m2sl": 45}          # default 3 para series diarias
DEFAULT_MAX_AGE = 3


def check(name, df, prev=None):
    if df is None or len(df) == 0:
        return False, "serie vacia"
    if df["value"].isna().mean() > 0.05:
        return False, "mas de 5% de NaN"
    if name in POSITIVE and (df["value"].dropna().tail(POSITIVE_TAIL) <= 0).any():
        return False, "valores negativos o cero en serie positiva"
    if prev is not None and len(prev) >= 10:
        base = float(prev["value"].tail(30).median())
        last = float(df["value"].iloc[-1])
        if base > 0 and not (1 / MAX_JUMP <= last / base <= MAX_JUMP):
            return False, f"salto de nivel absurdo vs corrida previa ({last:.4g} vs mediana {base:.4g})"
    return True, "ok"


def freshness_status(name, age_days):
    limit = MAX_AGE_DAYS.get(name, DEFAULT_MAX_AGE)
    if age_days <= limit:
        return "FRESCO"
    if age_days <= 3 * limit:
        return "STALE"
    return "DEAD"
