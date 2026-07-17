"""Entrypoint unico (spec §3): python -m src.build --daily | --weekly.
--daily  : fetch + frescura + re-render (sin re-estimar)
--weekly : lo anterior + re-estimacion Calibrado 6D
Regla madre: nunca publicar pagina rota; mejor vieja con fecha honesta.

FETCHES cubre exactamente lo que src/monthly.py consume de data/raw (ver
docstring de monthly.py): las series *_sampled (malla de 4 dias de
blockchain.info, la misma que uso la tesis), gold_price diario (Yahoo
Finance -- stooq quedo roto por bot-challenge, ver T8) y m2sl de FRED.
difficulty/fees_btc no las usa monthly.py todavia, pero se mantienen
frescas aqui porque son baratas y las usaran las graficas de "Hechos
estilizados" a futuro. btc_dominance se acumula aparte (T6) y no pasa por
este dict, pero su estado entra igual al reporte de frescura.

btc_supply se trae con fetch_daily (no fetch a secas): se descubrio
corriendo el build real que blockchain.info, con sampled=false, devuelve
el chart "total-bitcoins" a granularidad de bloque (~925k filas, ~28MB) en
vez de diario -- infla el repo sin aportar nada. fetch_daily baja el mismo
payload pero solo persiste el ultimo valor de cada dia (precision diaria
real, como espera monthly.py y protege test_monthly_vs_excel; usar la
malla de 4 dias en su lugar corre el error de DMB justo por encima de la
tolerancia). El nombre del CSV sigue siendo btc_supply.csv."""
import argparse
import datetime as dt
import json
import pathlib
import sys
from src import sanity, monthly, estimate, render
from src.fetchers import base, blockchain_info, fred, yahoo, dominance

FETCHES = {
    "btc_price_sampled": lambda: blockchain_info.fetch_sampled("btc_price"),
    "tx_count_sampled": lambda: blockchain_info.fetch_sampled("tx_count"),
    "tx_volume_usd_sampled": lambda: blockchain_info.fetch_sampled("tx_volume_usd"),
    "btc_supply": lambda: blockchain_info.fetch_daily("btc_supply"),
    "difficulty": lambda: blockchain_info.fetch("difficulty"),
    "fees_btc": lambda: blockchain_info.fetch("fees_btc"),
    "gold_price": yahoo.fetch_gold,
    "m2sl": fred.fetch,
}
FRESH_PATH = pathlib.Path("data/freshness.json")


def fetch_all():
    fresh = {}
    for name, fn in FETCHES.items():
        prev = base.load(name)
        status = None
        try:
            df = fn()
            ok, why = sanity.check(name, df, prev)
            if ok:
                base.save(name, df)
            else:
                print(f"[sanity] {name}: {why} -> se conserva CSV previo", file=sys.stderr)
                status = "SUSPECT"
        except Exception as e:
            print(f"[fetch] {name}: {e} -> se conserva CSV previo", file=sys.stderr)
        cur = base.load(name)
        if cur is None or len(cur) == 0:
            fresh[name] = {"status": "DEAD", "last": "—"}
            continue
        last = cur["date"].max()
        age = (dt.datetime.now() - last).days
        fresh[name] = {"status": status or sanity.freshness_status(name, age),
                       "last": str(last.date())}
    try:
        dominance.append_today()
        fresh["btc_dominance"] = {"status": "FRESCO", "last": dt.date.today().isoformat()}
    except Exception as e:
        print(f"[fetch] dominancia: {e}", file=sys.stderr)
        fresh["btc_dominance"] = {"status": "STALE", "last": "ver daily csv"}
    FRESH_PATH.write_text(json.dumps(fresh, indent=1))
    return fresh


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--daily", action="store_true")
    g.add_argument("--weekly", action="store_true")
    args = ap.parse_args()

    fresh = fetch_all()
    monthly.write()
    res_path = pathlib.Path("data/results.json")
    if args.weekly:
        try:
            estimate.run()
        except Exception as e:
            print(f"[estimate] fallo ({e}); se conserva results.json previo (spec §6.4)", file=sys.stderr)
    if not res_path.exists():
        print("sin results.json previo ni estimacion nueva: no hay nada que publicar", file=sys.stderr)
        sys.exit(1)
    r = json.loads(res_path.read_text())
    render.render(r, fresh)
    print("build ok ->", "weekly" if args.weekly else "daily")


if __name__ == "__main__":
    main()
