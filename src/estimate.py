"""Corre el Calibrado 6D congelado sobre la muestra con M2 publicado y emite
results.json para el dashboard. El guardarrail del veredicto (spec §6.5)
genera 'alertas' en vez de esconder cambios de conclusion."""
import datetime as dt
import json
import pathlib
import numpy as np
import pandas as pd
from src.model.model import fit, CRIT, stars


def run(monthly_csv="data/monthly.csv", out="data/results.json"):
    df = pd.read_csv(monthly_csv, parse_dates=["Fecha"], index_col="Fecha")
    if "m2_published" in df.columns:
        est = df[df["m2_published"].astype(bool)]
        assert est.index.equals(df.index[:len(est)]), \
            "m2_published debe ser un prefijo contiguo: el trend de dmb_star se desalinearia"
    else:                                   # fixture de la tesis: todo publicado
        est = df
    est_path = pathlib.Path(out).parent / "monthly_est.csv"
    est.to_csv(est_path)
    m = fit("6D", path=est_path)

    p = m["uecm"].params
    by = p["DMB.L1"]
    t = np.arange(1, len(df) + 1, dtype=float)
    dmb_star = -(p["const"] + p["trend"] * t
                 + p["MC2.L1"] * df["MC2"] + p["RV12.L1"] * df["RV12"]
                 + p["UC.L1"] * df["UC"]) / by
    gap = (df["DMB"] - dmb_star) * 100.0          # puntos log ~ %

    alertas = []
    if m["boundsF"] < CRIT["5%"][1]:
        alertas.append("Bounds F cayo bajo el critico I(1) al 5%: la evidencia de cointegracion se debilito")
    if m["ect"]["coef"] >= 0:
        alertas.append("ECT no negativo: se perdio la correccion al equilibrio")
    elif m["ect"]["p"] > 0.05:
        alertas.append("ECT perdio significancia al 5%")

    g = gap.dropna()
    gap_hoy = float(g.iloc[-1])
    gap_fecha = str(g.index[-1].date())

    r = dict(
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        n=m["n"], r2adj=m["r2adj"], dw=m["dw"], boundsF=m["boundsF"], crit=CRIT,
        sample=[str(m["sample"][0].date()), str(m["sample"][1].date())],
        ect=dict(coef=m["ect"]["coef"], p=m["ect"]["p"],
                 half_life_m=(float(np.log(0.5) / np.log(1 + m["ect"]["coef"]))
                              if -1 < m["ect"]["coef"] < 0 else None)),
        lr={k: dict(coef=d["coef"], p=d["p"], stars=stars(d["p"])) for k, d in m["lr"].items()},
        gap=dict(hoy=gap_hoy, fecha=gap_fecha),
        series=dict(fechas=[str(d.date()) for d in df.index],
                    dmb=[round(x, 4) for x in df["DMB"]],
                    dmb_star=[round(float(x), 4) if pd.notna(x) else None for x in dmb_star],
                    nowcast=[bool(not v) for v in df.get("m2_published", pd.Series(True, index=df.index))]),
        alertas=alertas,
    )
    pathlib.Path(out).write_text(json.dumps(r, indent=1))
    return r
