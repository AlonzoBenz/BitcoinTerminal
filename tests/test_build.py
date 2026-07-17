"""Candado de tolerancia a fallas del entrypoint (spec §6, T11): un fetch que
truena nunca debe tirar el CSV previo -- se conserva y se marca el estado en
la frescura."""
import pandas as pd
import src.build as build
from src.fetchers import base


def test_fetch_con_falla_conserva_csv_previo(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "RAW", tmp_path)
    # FRESH_PATH es relativo a data/freshness.json: sin este monkeypatch,
    # fetch_all() pisaria el freshness.json real del repo con datos de prueba.
    monkeypatch.setattr(build, "FRESH_PATH", tmp_path / "freshness.json")
    prev = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=40),
                         "value": [100.0] * 40})
    base.save("btc_price_sampled", prev)

    def boom():
        raise RuntimeError("api caida")

    # Aislar la prueba de red: solo la serie bajo prueba entra a FETCHES, y la
    # acumulacion diaria de dominancia (tambien via red) se stubea.
    monkeypatch.setattr(build, "FETCHES", {"btc_price_sampled": boom})
    monkeypatch.setattr(build.dominance, "append_today", lambda: True)

    fresh = build.fetch_all()
    assert fresh["btc_price_sampled"]["status"] in ("STALE", "SUSPECT", "DEAD", "FRESCO")
    assert len(base.load("btc_price_sampled")) == 40          # el CSV previo sobrevive
