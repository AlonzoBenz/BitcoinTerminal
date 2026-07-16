"""El test que bloquea todo (spec §7.1): la base reconstruida desde APIs
empata con el Excel de la tesis al 0.1% relativo por celda."""
import pathlib
import pandas as pd
import pytest
from src import monthly

FIX = pathlib.Path(__file__).parent / "fixtures" / "monthly_tesis.csv"
RAW_OK = pathlib.Path("data/raw/btc_price_sampled.csv").exists()

# Tolerancias por serie; ampliar SOLO con justificacion escrita aqui (spec §7.1).
# Las variables son logs/logits: error absoluto en log ~ error relativo del
# nivel; 0.001 ~ 0.1%. Errores observados al fijar las reglas (2026-07-15):
# DMB/MC1 ~4.7e-4 (supply fin de mes diario vs chart 1d-average de la tesis),
# MC2 ~3.3e-5 (vintage FRED), RV12 y UC exactos a precision de float.
TOL = {"DMB": 0.001, "MC2": 0.001, "MC1": 0.001, "RV12": 0.001, "UC": 0.001}


@pytest.mark.skipif(not RAW_OK, reason="requiere data/raw poblado (fetch previo)")
def test_base_reconstruida_empata_con_excel():
    ref = pd.read_csv(FIX, parse_dates=["Fecha"], index_col="Fecha")
    got = monthly.build()
    j = got.join(ref, how="inner", rsuffix="_ref")
    # el fixture esta congelado en 135 meses: el traslape debe cubrirlos TODOS
    assert len(j) == len(ref), \
        f"traslape {len(j)} != {len(ref)} meses del fixture congelado"
    cols = [c for c in j.columns
            if c in TOL or (c.endswith("_ref") and c[:-4] in TOL)]
    assert not j[cols].isna().any().any(), "NaN en columnas comparadas: paso vacuo"
    for col, tol in TOL.items():
        err = (j[col] - j[f"{col}_ref"]).abs().max()
        assert err < tol, f"{col}: error absoluto max {err:.6f} >= {tol}"


GOLD_OK = (pathlib.Path("data/raw/gold_price_monthly_seed.csv").exists()
           and pathlib.Path("data/raw/gold_price.csv").exists())


@pytest.mark.skipif(not GOLD_OK, reason="requiere semilla y diario de oro")
def test_empalme_oro_semilla_vs_diario():
    """Guardia de continuidad del oro: en los meses donde coexisten la semilla
    congelada (cierre investing.com) y el agregado last-del-mes del diario
    (Yahoo GC=F), la divergencia relativa debe ser <= 5% en TODOS los meses
    (medido 2.1% max al fijar reglas; detecta extension rota o cambio de
    moneda/contrato en la fuente diaria)."""
    from src.fetchers import base
    seed = base.load("gold_price_monthly_seed").set_index("date")["value"]
    seed.index = seed.index.to_period("M").to_timestamp()
    daily = base.load("gold_price").set_index("date")["value"].sort_index()
    j = pd.concat([seed, daily.resample("MS").last()], axis=1,
                  join="inner").dropna()
    assert len(j) >= 100, "traslape semilla/diario insuficiente"
    div = (j.iloc[:, 0] / j.iloc[:, 1] - 1).abs()
    assert div.max() <= 0.05, \
        f"empalme de oro divergente: max {div.max():.2%} en {div.idxmax():%Y-%m}"
