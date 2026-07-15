import pandas as pd
from src.fetchers import dominance


def test_append_es_idempotente(tmp_path, monkeypatch):
    daily = tmp_path / "btc_dominance_daily.csv"
    monkeypatch.setattr(dominance, "DAILY", daily)
    monkeypatch.setattr(dominance, "hoy_dominancia", lambda: 58.3)
    dominance.append_today()
    dominance.append_today()      # segunda vez el mismo dia: no duplica
    df = pd.read_csv(daily)
    assert len(df) == 1


def test_monthly_series_une_semilla_y_diario(tmp_path, monkeypatch):
    seed = tmp_path / "seed.csv"
    daily = tmp_path / "daily.csv"
    pd.DataFrame({"date": ["2026-02-01", "2026-03-01"], "value": [57.0, 58.0]}).to_csv(seed, index=False)
    pd.DataFrame({"date": ["2026-04-02", "2026-04-15"], "value": [60.0, 62.0]}).to_csv(daily, index=False)
    monkeypatch.setattr(dominance, "SEED", seed)
    monkeypatch.setattr(dominance, "DAILY", daily)
    s = dominance.monthly_series()
    assert s.loc["2026-03-01"] == 58.0          # la semilla manda en su periodo
    assert s.loc["2026-04-01"] == 61.0          # promedio de muestras diarias


def test_monthly_series_sin_huecos():
    s = dominance.monthly_series()
    completo = s.loc[:"2026-06-01"]
    assert not completo.isna().any()
    idx = pd.date_range("2015-01-01", completo.index.max(), freq="MS")
    assert completo.index.equals(idx), "huecos en la serie mensual de dominancia"
