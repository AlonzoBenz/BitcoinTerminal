"""Carga de la base mensual desde CSV. Vendored de ~/Tesis_Cap3 —
la unica adaptacion permitida vs el original es la E/S (Excel -> CSV)."""
import pandas as pd

DUMMY_DATES = {
    "D1_2021_01": "2021-01-01", "D2_2021_06": "2021-06-01",
    "D3_2022_01": "2022-01-01", "D4_2022_05": "2022-05-01",
    "D5_2022_06": "2022-06-01", "D6_2022_11": "2022-11-01",
    "D7_2025_12": "2025-12-01", "D8_2016_01": "2016-01-01",
}
DUMMIES = ["D1_2021_01", "D2_2021_06", "D3_2022_01",
           "D4_2022_05", "D5_2022_06", "D6_2022_11"]
DUMMIES8 = DUMMIES + ["D7_2025_12", "D8_2016_01"]


def load(path="data/monthly.csv"):
    df = pd.read_csv(path, parse_dates=["Fecha"], index_col="Fecha").sort_index()
    v = df[["DMB", "MC2", "MC1", "RV12", "UC"]].copy()
    for name, fecha in DUMMY_DATES.items():
        v[name] = (v.index == pd.Timestamp(fecha)).astype(float)
    return df, v
