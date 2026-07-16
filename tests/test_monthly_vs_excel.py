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
    j = got.join(ref, how="inner", rsuffix="_ref").dropna(subset=["DMB", "DMB_ref"])
    assert len(j) >= 120, "traslape insuficiente con la muestra de la tesis"
    for col, tol in TOL.items():
        err = (j[col] - j[f"{col}_ref"]).abs().max()
        assert err < tol, f"{col}: error absoluto max {err:.6f} >= {tol}"
