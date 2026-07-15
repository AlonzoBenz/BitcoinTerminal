"""
Estimacion ARDL-Bounds del Cap.3 y extraccion de todo lo necesario para los
cuadros estilo EViews. Maneja las correcciones validadas:
  - dummies de impulso reconstruidas desde fechas (dataload)
  - Bounds F via Wald manual (statsmodels ignora regresores 'fixed')
  - SE de largo plazo via metodo delta
"""
import numpy as np
import pandas as pd
from scipy import stats as sps
from statsmodels.tsa.ardl import ARDL, UECM
from src.model.dataload import load, DUMMIES, DUMMIES8

EXOG_COLS = ["MC2", "RV12", "UC"]
ORDER = {"MC2": 12, "RV12": 1, "UC": 1}
LAGS = 12
LEVEL_TERMS = ["DMB.L1", "MC2.L1", "RV12.L1", "UC.L1"]

# valores criticos Pesaran (caso 5, k=3) — de la salida de statsmodels bounds_test
CRIT = {  # nivel: (I0, I1)
    "10%": (3.2196, 4.0466), "5%": (3.6494, 4.5276),
    "1%": (4.6076, 5.6687),
}


def stars(p):
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .10 else ""


def fit(which="6D", path="data/monthly.csv"):
    """which in {'base','6D','8D'} -> dict con ardl, uecm y resultados clave."""
    df, v = load(path)
    fixed_cols = {"base": [], "6D": DUMMIES, "8D": DUMMIES8}[which]
    endog = v["DMB"]; exog = v[EXOG_COLS]
    fx = v[fixed_cols] if fixed_cols else None

    ardl = ARDL(endog, lags=LAGS, exog=exog, order=ORDER, fixed=fx, trend="ct").fit()
    uecm = UECM(endog, lags=LAGS, exog=exog, order=ORDER, fixed=fx, trend="ct").fit()

    resid = ardl.resid; y = endog.loc[resid.index]
    n = int(ardl.nobs); k = ardl.params.shape[0]
    ssr = float((resid ** 2).sum()); sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ssr / sst; r2adj = 1 - (1 - r2) * (n - 1) / (n - k)
    dw = float((np.diff(resid) ** 2).sum() / ssr)

    # Bounds F manual (Wald sobre los niveles rezagados)
    wald = uecm.wald_test([f"{t} = 0" for t in LEVEL_TERMS], scalar=True)
    Fb = float(wald.statistic)

    # Largo plazo + SE por metodo delta
    p = uecm.params; cov = uecm.cov_params()
    by = p["DMB.L1"]
    lr = {}
    for x in EXOG_COLS:
        bx = p[f"{x}.L1"]
        beta = -bx / by
        # gradiente respecto a (by, bx)
        g = {"DMB.L1": bx / by ** 2, f"{x}.L1": -1.0 / by}
        var = 0.0
        for a in g:
            for b in g:
                var += g[a] * g[b] * cov.loc[a, b]
        se = np.sqrt(var); t = beta / se
        pv = 2 * sps.t.sf(abs(t), df=n - k)
        lr[x] = dict(coef=beta, se=se, t=t, p=pv)

    ect = dict(coef=p["DMB.L1"], se=uecm.bse["DMB.L1"],
               t=uecm.tvalues["DMB.L1"], p=uecm.pvalues["DMB.L1"])

    return dict(which=which, ardl=ardl, uecm=uecm, fixed=fixed_cols,
                n=n, k=k, r2=r2, r2adj=r2adj, dw=dw, ssr=ssr,
                aic=float(ardl.aic), bic=float(ardl.bic),
                boundsF=Fb, lr=lr, ect=ect,
                sample=(resid.index.min(), resid.index.max()))


def design_matrix(m, path="data/monthly.csv"):
    """Matriz de diseno completa (const, trend, rezagos, dummies) + y,
    alineadas a la muestra de estimacion. Reproduce el ARDL exactamente."""
    df, v = load(path)
    full = pd.DataFrame(index=v.index)
    full["const"] = 1.0
    full["trend"] = np.arange(1, len(v) + 1, dtype=float)
    for i in range(1, 13): full[f"DMB.L{i}"] = v["DMB"].shift(i)
    for i in range(0, 13): full[f"MC2.L{i}"] = v["MC2"].shift(i)
    for i in range(0, 2):  full[f"RV12.L{i}"] = v["RV12"].shift(i)
    for i in range(0, 2):  full[f"UC.L{i}"] = v["UC"].shift(i)
    for d in m["fixed"]:   full[d] = v[d]
    idx = m["ardl"].resid.index
    return full.loc[idx], v["DMB"].loc[idx]


if __name__ == "__main__":
    for w in ["base", "6D", "8D"]:
        r = fit(w)
        print(f"{w:5s} n={r['n']} AIC={r['aic']:.2f} DW={r['dw']:.3f} "
              f"F={r['boundsF']:.2f} ECT={r['ect']['coef']:.4f} "
              f"LR: MC2={r['lr']['MC2']['coef']:.3f} RV12={r['lr']['RV12']['coef']:.3f} UC={r['lr']['UC']['coef']:.3f}")
