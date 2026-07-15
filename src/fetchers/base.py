import pathlib
import pandas as pd

RAW = pathlib.Path("data/raw")


def save(name, df):
    RAW.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW / f"{name}.csv", index=False)


def load(name):
    p = RAW / f"{name}.csv"
    if not p.exists():
        return None
    return pd.read_csv(p, parse_dates=["date"])
