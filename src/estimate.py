"""Corre el Calibrado 6D congelado sobre la muestra con M2 publicado y emite
results.json para el dashboard. El guardarrail del veredicto (spec §6.5)
genera 'alertas' en vez de esconder cambios de conclusion."""
import datetime as dt
import json
import pathlib
import sys
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as sps
from statsmodels.stats.diagnostic import (acorr_ljungbox, het_arch,
                                          het_breuschpagan, het_white)
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.stattools import adfuller, kpss
from src.model.model import fit, design_matrix, CRIT, stars

# variables del Cap.3 en el orden de los cuadros 3.3 y 3.10
VARS_CAP3 = ("DMB", "MC2", "MC1", "RV12", "UC")


def _partes_uecm(m, est_path):
    """(X, y_uecm, resid) de la ecuacion UECM ya estimada.

    OJO: m["uecm"].resid NO es el residual de la regresion UECM — statsmodels
    resta los ajustados en diferencias al DMB en NIVELES (media -4.3, sd 1.46).
    El residual correcto es el del ARDL: es la misma regresion reparametrizada,
    asi que comparte residuales, n y k. Se usa design_matrix() del modulo
    congelado (misma envolvente lineal, 123x37) como exog de las pruebas.
    """
    Xd, y_niveles = design_matrix(m, path=est_path)
    X = np.asarray(Xd, dtype=float)
    resid = np.asarray(m["ardl"].resid, dtype=float)
    y_uecm = np.asarray(m["uecm"].fittedvalues, dtype=float) + resid
    return X, y_uecm, resid, np.asarray(y_niveles, dtype=float)


def _reset_p(y_niveles, X, fitted_niveles):
    """RESET de Ramsey con y^2 e y^3 sobre la ecuacion en NIVELES.

    Es la version que reproduce el p=0.008 reportado en la tesis (aqui 0.0084).
    El mismo test sobre la UECM en diferencias da p=0.64: la sospecha de no
    linealidad viene de la ecuacion en niveles, no de la de corto plazo.
    """
    yh = np.asarray(fitted_niveles, dtype=float)
    Xr = np.column_stack([X, yh ** 2, yh ** 3])
    res = sm.OLS(y_niveles, Xr).fit()
    R = np.zeros((2, Xr.shape[1]))
    R[0, X.shape[1]] = 1.0
    R[1, X.shape[1] + 1] = 1.0
    return float(res.f_test(R).pvalue)


def _diagnosticos(m, est_path):
    """Cuadro 3.9: residuos de la UECM. Cada prueba falla por separado."""
    X, y_uecm, resid, y_niveles = _partes_uecm(m, est_path)
    n, k = X.shape
    d = {}

    def probar(clave, fn):
        try:
            d[clave] = float(fn())
        except Exception as e:
            print(f"[diag] {clave} fallo: {type(e).__name__}", file=sys.stderr)
            d[clave] = None

    probar("dw", lambda: durbin_watson(resid))
    # het_breuschpagan devuelve (lm, lm_p, f, f_p); la tesis reporta el LM
    probar("bp_p", lambda: het_breuschpagan(resid, X)[1])
    probar("arch_p", lambda: het_arch(resid, nlags=12)[1])
    probar("lb12_p",
           lambda: acorr_ljungbox(resid, lags=[12], return_df=True)["lb_pvalue"].iloc[0])
    probar("jb_p", lambda: sps.jarque_bera(resid).pvalue)
    probar("reset_p",
           lambda: _reset_p(y_niveles, X, m["ardl"].fittedvalues))
    # White con 37 regresores sobre n=123 queda sobreparametrizado (740 terminos
    # cruzados): se exporta por completitud pero no se publica en el cuadro.
    probar("white_p", lambda: het_white(resid, X)[1])
    ssr = float((resid ** 2).sum())
    sst = float(((y_uecm - y_uecm.mean()) ** 2).sum())
    r2 = 1 - ssr / sst
    d["r2adj_uecm"] = float(1 - (1 - r2) * (n - 1) / (n - k))
    return d


def _raiz_unitaria(est):
    """Cuadro 3.3: ADF y KPSS en nivel + ADF en primeras diferencias sobre la
    muestra de estimacion (la misma que se publica)."""
    filas = []
    for v in VARS_CAP3:
        s = est[v].dropna().astype(float)
        ad = adfuller(s, regression="c", autolag="AIC")
        adif = adfuller(s.diff().dropna(), regression="c", autolag="AIC")
        with warnings.catch_warnings():
            # InterpolationWarning: el p de KPSS sale de la tabla (queda en 0.01/0.10)
            warnings.simplefilter("ignore")
            kp = kpss(s, regression="c", nlags="auto")
        orden = "I(0)" if ad[1] < .05 else ("I(1)" if adif[1] < .05 else "≥I(2)?")
        filas.append(dict(var=v, adf_nivel=float(ad[0]), adf_p=float(ad[1]),
                          kpss_nivel=float(kp[0]), kpss_p=float(kp[1]),
                          adf_dif=float(adif[0]), adf_dif_p=float(adif[1]),
                          orden=orden))
    return filas


def _vif(est):
    """Cuadro 3.11: VIF de los tres regresores (la constante no se publica)."""
    X = est[["MC2", "RV12", "UC"]].dropna().astype(float).copy()
    X.insert(0, "const", 1.0)
    A = np.asarray(X, dtype=float)
    return {c: float(variance_inflation_factor(A, i))
            for i, c in enumerate(X.columns) if c != "const"}


def _correlacion(est):
    """Cuadro 3.10: matriz de correlacion 5x5."""
    C = est[list(VARS_CAP3)].astype(float).corr().round(4)
    return dict(vars=list(VARS_CAP3),
                m=[[float(x) for x in fila] for fila in C.to_numpy()])


def _hac(m):
    """Cuadro 3.12: Newey-West (12 rezagos) sobre los terminos en nivel.

    UECMResults no expone get_robustcov_results, asi que se re-estima la misma
    regresion por OLS con la matriz de diseno de la UECM y se verifica que
    reproduce los coeficientes antes de confiar en ella."""
    u = m["uecm"]
    X = np.asarray(u.model._x, dtype=float)      # privado en statsmodels
    nombres = list(u.model.exog_names)
    y = np.asarray(u.fittedvalues, dtype=float) + np.asarray(m["ardl"].resid, dtype=float)
    if not np.allclose(sm.OLS(y, X).fit().params, u.params.to_numpy(), atol=1e-8):
        raise ValueError("la matriz UECM no reproduce los coeficientes publicados")
    h = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    return {x: dict(coef=float(h.params[nombres.index(f"{x}.L1")]),
                    p=float(h.pvalues[nombres.index(f"{x}.L1")]))
            for x in ("MC2", "RV12", "UC")}


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

    robustez = {}
    for which in ("base", "8D"):
        try:
            rm = fit(which, path=est_path)
            robustez[which] = dict(
                boundsF=rm["boundsF"],
                ect=dict(coef=rm["ect"]["coef"], p=rm["ect"]["p"]),
                lr={k: dict(coef=d["coef"], p=d["p"], stars=stars(d["p"])) for k, d in rm["lr"].items()},
                n=rm["n"], aic=rm["aic"],
            )
        except Exception as e:
            print(f"[robustez] {which} fallo: {type(e).__name__}", file=sys.stderr)

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
    r["robustez"] = robustez

    # Bloques del Cap.3 (T17). Todo se deriva del modelo ya estimado; si algo
    # falla el bloque queda en None y el portal lo degrada, nunca rompe el build.
    for clave, calcular in (("diagnosticos", lambda: _diagnosticos(m, est_path)),
                            ("raiz_unitaria", lambda: _raiz_unitaria(est)),
                            ("vif", lambda: _vif(est)),
                            ("correlacion", lambda: _correlacion(est)),
                            ("hac", lambda: _hac(m))):
        try:
            r[clave] = calcular()
        except Exception as e:
            print(f"[diag] {clave} fallo: {type(e).__name__}: {e}", file=sys.stderr)
            r[clave] = None

    pathlib.Path(out).write_text(json.dumps(r, indent=1))
    return r
