"""Exporta la base mensual del Excel de la tesis y los resultados exactos
del Calibrado 6D. Correr con: cd ~/Tesis_Cap3 && venv/bin/python \
~/BitcoinTerminal/scripts/exportar_fixture.py"""
import json, sys, pathlib
sys.path.insert(0, "scripts")          # dataload/model de la tesis
from dataload import load
from model import fit

OUT = pathlib.Path.home() / "BitcoinTerminal" / "tests" / "fixtures"
df, v = load()
full = df.join(v[["DMB", "MC2", "MC1", "RV12", "UC"]], rsuffix="_v")
full.to_csv(OUT / "monthly_tesis.csv")

m = fit("6D")
ref = dict(
    boundsF=m["boundsF"], n=m["n"], r2adj=m["r2adj"], dw=m["dw"],
    aic=m["aic"], bic=m["bic"],
    ect=dict(coef=m["ect"]["coef"], p=m["ect"]["p"]),
    lr={k: dict(coef=d["coef"], p=d["p"]) for k, d in m["lr"].items()},
    sample=[str(m["sample"][0].date()), str(m["sample"][1].date())],
)
(OUT / "referencia_congelada.json").write_text(json.dumps(ref, indent=2))
print(json.dumps(ref, indent=2))
