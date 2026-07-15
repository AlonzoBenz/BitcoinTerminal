"""Semilla mensual de dominancia desde el Excel de la tesis.
Correr: cd ~/Tesis_Cap3 && venv/bin/python este_script"""
import sys, pathlib
sys.path.insert(0, "scripts")
from dataload import load

df, _ = load()
out = df[["BTC_dominance_pct"]].reset_index()
out.columns = ["date", "value"]
out.to_csv(pathlib.Path.home() / "BitcoinTerminal" / "data" / "raw" / "btc_dominance_seed.csv", index=False)
print(out.tail(3))
