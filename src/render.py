"""results.json + frescura -> site/index.html (estatico, autocontenido salvo
CDN de Chart.js y Google Fonts)."""
import csv
import json
import math
import pathlib
import unicodedata
import urllib.parse

# SRI de chart.js@4.4.1 (jsdelivr), calculado el 2026-07-16:
#   curl -s https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js \
#     | openssl dgst -sha384 -binary | openssl base64 -A
CHARTJS_SRI = "sha384-9nhczxUqK87bcKHh20fSQcTGD4qq5GhayNYSYWqwBkINBhOfQLg/P5HG5lF1urn4"

# favicon inline: ₿ naranja sobre crema, URL-encoded para caber en un data:URI
_FAVSVG = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
           "<rect width='32' height='32' rx='6' fill='#faf6ec'/>"
           "<text x='16' y='24' font-size='22' text-anchor='middle' "
           "font-family='Georgia,serif' fill='#f7931a'>&#8383;</text></svg>")
FAVICON = "data:image/svg+xml," + urllib.parse.quote(_FAVSVG)

REPO_URL = "https://github.com/AlonzoBenz/BitcoinTerminal"
SITE_URL = "https://alonzobenz.github.io/BitcoinTerminal/"
META_DESC = ("Evidencia viva de cointegración ARDL: ¿es Bitcoin dinero? "
             "Modelo Calibrado 6D, UNAM.")

CSS = """
:root{--paper:#faf6ec;--card:#fffdf6;--line:#e0d7c2;--ink:#211d14;--dim:#6e6656;
--faint:#a09681;--btc:#f7931a;--btctx:#c46f0a;--ok:#3b6d11;--okbg:#eaf3de;
--warn:#854f0b;--warnbg:#faeeda;--bad:#a32d2d}
*{box-sizing:border-box;margin:0}
body{background:var(--paper);color:var(--ink);font:15px/1.6 Inter,sans-serif}
header{display:flex;justify-content:space-between;align-items:center;
padding:14px 4vw;border-bottom:1px solid var(--line);position:sticky;top:0;
background:var(--paper);z-index:9}
.wordmark{font-family:Fraunces,serif;font-size:20px;font-weight:600}
.wordmark b{color:var(--btctx);font-weight:600}
nav{display:flex;gap:16px;font-size:12px;flex-wrap:wrap}
nav a{color:var(--dim);text-decoration:none;padding-bottom:3px;
border-bottom:2px solid transparent}
nav a:hover{color:var(--ink);border-bottom-color:var(--btc)}
nav a.on{color:var(--ink);border-bottom-color:var(--btc)}
main{max-width:1320px;margin:0 auto;padding:30px 4vw 80px}
h1{font-family:Fraunces,serif;font-size:30px;font-weight:500;margin:8px 0 4px}
h2{font-family:Fraunces,serif;font-size:21px;font-weight:500;margin:44px 0 14px;
padding-top:14px;border-top:1px solid var(--line)}
.sub{color:var(--dim);font-size:13px;margin-bottom:22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:16px 20px;margin-bottom:14px;transition:border-color .15s,box-shadow .15s}
.card:hover{border-color:#d8cbb0;box-shadow:0 1px 8px rgba(33,29,20,.05)}
.lbl{font-size:10.5px;letter-spacing:1.6px;color:var(--faint);margin-bottom:8px}
.big{font-family:Fraunces,serif;font-size:30px;font-weight:500;
font-variant-numeric:tabular-nums}
.star .big{font-size:46px;line-height:1.05;color:var(--btctx)}
.mono{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;
margin-bottom:14px}
.grid .card,.hero .card,.stack .card,.mini .card,.two .card,.g2x2 .card{margin:0}
.hero{display:grid;grid-template-columns:1.1fr 1fr;gap:16px;align-items:stretch;
margin-bottom:14px}
.stack{display:grid;grid-template-rows:auto 1fr;gap:16px;align-content:stretch}
.stack > .card:last-child{display:flex;flex-direction:column;justify-content:center}
.mini{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.two{display:grid;grid-template-columns:2fr 1fr;gap:16px;align-items:start;
margin-bottom:14px}
.g2x2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:14px}
.half{max-width:680px}
.pill{font-size:10.5px;border-radius:99px;padding:2px 10px;border:1px solid;
white-space:nowrap}
.pill.ok{color:var(--ok);background:var(--okbg);border-color:#c0dd97}
.pill.warn{color:var(--warn);background:var(--warnbg);border-color:#fac775}
.pill.bad{color:var(--bad);background:#fcebeb;border-color:#f7c1c1}
.pill.neu{color:var(--dim);background:#f2ede1;border-color:var(--line)}
.ref{font-family:'IBM Plex Mono',monospace;font-size:9.5px;color:var(--faint);
border:1px solid var(--line);border-radius:99px;padding:1px 7px;margin-left:8px;
vertical-align:2px;letter-spacing:0;white-space:nowrap;text-transform:none}
tr.hi td{background:#fdf4e6}
td.alta{color:var(--btctx)}
.eqs{font-family:'IBM Plex Mono',monospace;font-size:12.5px;line-height:2.1;
overflow-x:auto}
.eqs div{white-space:nowrap}
.eqs b{color:var(--faint);font-weight:400;margin-right:12px}
.quote{font-style:italic;color:var(--dim);font-size:13px;
border-left:2px solid var(--line);padding-left:14px;margin:16px 0 0}
.tw{overflow-x:auto}
.gauge{height:8px;background:#ece4d2;border-radius:99px;position:relative;margin:10px 0}
.gauge i{position:absolute;height:8px;background:var(--btc);border-radius:99px}
.gauge b{position:absolute;left:50%;top:-3px;width:2px;height:14px;background:var(--ink)}
table{border-collapse:collapse;width:100%;font-size:13px}
td,th{padding:6px 10px 6px 0;text-align:left;border-bottom:1px solid var(--line)}
td{font-variant-numeric:tabular-nums}
.num{font-family:'IBM Plex Mono',monospace;text-align:right}
.alerta{background:var(--warnbg);border:1px solid #fac775;color:var(--warn);
border-radius:8px;padding:12px 16px;margin-bottom:14px;font-size:13.5px}
.cwrap{position:relative;height:280px}
.cwrap.sm{height:200px}
.cwrap.spark{height:72px;margin-top:12px}
section{scroll-margin-top:90px}
.statusbar{display:flex;justify-content:space-between;align-items:center;gap:10px;
background:#f2ede1;border-bottom:1px solid var(--line);padding:6px 4vw;flex-wrap:wrap}
.live{display:flex;align-items:center;gap:7px;font-family:'IBM Plex Mono',monospace;
font-size:10px;letter-spacing:2px;color:var(--dim)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--ok);
animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(59,109,17,.5)}
70%{box-shadow:0 0 0 6px rgba(59,109,17,0)}100%{box-shadow:0 0 0 0 rgba(59,109,17,0)}}
.statusbar .meta{font-family:'IBM Plex Mono',monospace;color:var(--dim);
font-size:11px;text-align:right}
.verdict{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:6px 0 22px}
.verdict .lead{color:var(--dim);font-size:13px}
.chip{font-family:'IBM Plex Mono',monospace;font-size:11px;border-radius:99px;
padding:3px 12px;border:1px solid;white-space:nowrap;
font-variant-numeric:tabular-nums}
.chip.yes{background:#eaf3de;border-color:#c0dd97;color:#3b6d11}
.chip.no{background:#f2ede1;border-color:var(--line);color:var(--dim)}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);padding:0;overflow:hidden}
.kpi{padding:14px 18px;border-left:1px solid var(--line)}
.kpi:first-child{border-left:0}
.kpi .kl{font-size:9.5px;letter-spacing:1.6px;color:var(--faint);
text-transform:uppercase;margin-bottom:6px}
.kpi .kv{font-family:'IBM Plex Mono',monospace;font-size:18px;color:var(--ink);
font-variant-numeric:tabular-nums}
.kpi .kv.ok{color:var(--ok)}
.kpi .kv.warn{color:var(--warn)}
.kpi .ksub{font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:var(--dim);
margin-top:3px;font-variant-numeric:tabular-nums}
.idx{font-family:'IBM Plex Mono',monospace;font-size:.55em;color:var(--faint);
font-weight:400;margin-right:10px;vertical-align:middle;
font-variant-numeric:tabular-nums}
footer{color:var(--faint);font-size:11.5px;padding:20px 4vw;border-top:1px solid var(--line)}
footer a{color:var(--btctx);text-decoration:none}
@media (max-width:900px){
main{padding:24px 5vw 60px}
.hero,.two,.mini,.g2x2,.grid{grid-template-columns:1fr}
header{flex-wrap:wrap;gap:8px}
nav{gap:10px 12px;font-size:11px}
h1{font-size:26px}
.star .big{font-size:40px}
.kpis{grid-template-columns:1fr 1fr 1fr}
.kpi{border-top:1px solid var(--line)}
.kpi:nth-child(-n+3){border-top:0}
.kpi:nth-child(3n+1){border-left:0}
}
@media (max-width:560px){
.kpis{grid-template-columns:1fr 1fr}
.kpi:nth-child(-n+2){border-top:0}
.kpi:nth-child(3){border-top:1px solid var(--line)}
.kpi:nth-child(odd){border-left:0}
.kpi:nth-child(even){border-left:1px solid var(--line)}
}
"""

SECCIONES = ["El modelo", "Variables", "Raíz unitaria", "Cointegración",
             "Funciones del dinero", "Hechos estilizados", "Mercado", "Datos"]

# secciones que sólo existen si su bloque llegó en results.json
SEC_OPCIONALES = {"Raíz unitaria": "raiz_unitaria"}

# paleta para c_vars: naranja para DMB, tonos tierra para el resto
VARS_PALETA = {"DMB": "#f7931a", "MC2": "#a09681", "MC1": "#8a7a5c",
               "RV12": "#6e6656", "UC": "#c9bfa6"}

LECT_VARS = ("DMB", "MC2", "MC1", "RV12", "UC")

# glosario para tooltips nativos (title="…") sobre las etiquetas de variables
GLOSARIO = {
    "DMB": "log(MarketCap BTC / M2): monetización de Bitcoin",
    "MC2": "log(Volumen tx USD / M2): medio de cambio",
    "MC1": "log(tx / oferta): frecuencia transaccional",
    "RV12": "momentum 12m de BTC vs oro: reserva de valor",
    "UC": "logit(dominancia BTC): unidad de cuenta",
    "ECT": "término de corrección de error: velocidad de ajuste al equilibrio",
}


def _ancla(s):
    """'Cointegración' -> 'cointegracion'. Sin acentos para que el ancla del
    nav y el id de la sección coincidan siempre."""
    plano = unicodedata.normalize("NFKD", s.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return plano.replace(" ", "-")


def _fmt_p(p):
    """p-values diminutos reportados honestamente, no como 0.0000."""
    return "p &lt; 0.0001" if p < 1e-4 else f"p = {p:.4f}"


def _p_corto(p):
    """p para celdas de tabla: los diminutos no se redondean a 0.0000."""
    return "&lt; 0.001" if p < 1e-3 else f"{p:.4f}"


def _p_kpss(p):
    """El p de KPSS sale de una tabla acotada: en los extremos se reporta como
    cota, no como si fuera un valor exacto."""
    if p <= 0.01:
        return "≤ 0.010"
    if p >= 0.10:
        return "≥ 0.100"
    return f"{p:.3f}"


def _ref(cuadro):
    """Badge de referencia cruzada al Capítulo 3 del documento."""
    return f'<span class="ref">≡ {cuadro}</span>'


def _pill_p(p):
    """Veredicto de una prueba por su p: no rechazar la nula al 5% = OK."""
    if p is None:
        return ""
    return ('<span class="pill ok">OK</span>' if p >= 0.05
            else '<span class="pill warn">reparo</span>')


def _card_raiz(r):
    """Cuadro 3.3: ADF/KPSS en nivel y ADF en diferencias. '' si no hay bloque."""
    ru = r.get("raiz_unitaria")
    if not ru:
        return ""
    filas = "".join(
        f'<tr{" class=\"hi\"" if f["var"] == "MC1" else ""}>'
        f'<td title="{GLOSARIO.get(f["var"], "")}">{f["var"]}</td>'
        f'<td class="num">{f["adf_nivel"]:.3f}</td>'
        f'<td class="num">{_p_corto(f["adf_p"])}</td>'
        f'<td class="num">{f["kpss_nivel"]:.3f}</td>'
        f'<td class="num">{_p_kpss(f["kpss_p"])}</td>'
        f'<td class="num">{f["adf_dif"]:.3f}</td>'
        f'<td class="num">{_p_corto(f["adf_dif_p"])}</td>'
        f'<td><span class="pill {"ok" if f["orden"] == "I(0)" else "neu"}">'
        f'{f["orden"]}</span></td></tr>'
        for f in ru)
    return (
        '<div class="card"><div class="lbl">ORDEN DE INTEGRACIÓN'
        f'{_ref("Cuadro 3.3")}</div><div class="tw"><table>'
        '<tr><th>Variable</th><th class="num">ADF (nivel)</th><th class="num">p</th>'
        '<th class="num">KPSS</th><th class="num">p</th>'
        '<th class="num">ADF (Δ)</th><th class="num">p</th><th>Orden</th></tr>'
        f'{filas}</table></div>'
        '<p class="sub" style="margin:12px 0 0">ADF: la nula es raíz unitaria '
        '(p &lt; 0.05 = estacionaria). KPSS: la nula es estacionariedad '
        '(valor alto = se rechaza). Ambas con constante.</p></div>')


def _nota_raiz(r):
    """Lectura honesta del Cuadro 3.3: se adapta a lo que salga en la muestra
    viva en vez de afirmar la mezcla I(0)/I(1) de la muestra congelada."""
    ru = r.get("raiz_unitaria")
    if not ru:
        return ""
    if any(f["orden"].startswith("≥") for f in ru):
        return ("Alguna serie no alcanza estacionariedad ni en primeras "
                "diferencias en esta muestra: el Bounds exige que ninguna sea "
                "I(2), así que conviene leerlo con reservas.")
    if any(f["orden"] == "I(0)" for f in ru):
        return ("Ninguna serie es I(2) y hay mezcla de I(0)/I(1) — exactamente "
                "el caso que justifica ARDL-Bounds en lugar de Johansen.")
    mc1 = next((f for f in ru if f["var"] == "MC1"), None)
    filo = f" — MC1 se queda al filo (ADF p = {mc1['adf_p']:.4f})" if mc1 else ""
    return ("Ninguna serie es I(2), que es el requisito del Bounds. En esta "
            f"muestra viva todas resultan I(1){filo}. En la muestra congelada "
            "de la tesis MC1 sale I(0), y esa mezcla I(0)/I(1) es la que "
            "justifica ARDL-Bounds frente a Johansen.")


def _card_correlacion(r):
    """Cuadro 3.10: matriz 5x5, |r| > 0.9 en naranja."""
    c = r.get("correlacion")
    if not c:
        return ""
    vs, M = c["vars"], c["m"]
    cab = "".join(f'<th class="num">{v}</th>' for v in vs)
    filas = "".join(
        f'<tr><td title="{GLOSARIO.get(v, "")}">{v}</td>' + "".join(
            f'<td class="num{" alta" if i != j and abs(x) > 0.9 else ""}">{x:.3f}</td>'
            for j, x in enumerate(M[i])) + '</tr>'
        for i, v in enumerate(vs))
    return (
        f'<div class="card"><div class="lbl">CORRELACIÓN{_ref("Cuadro 3.10")}</div>'
        f'<div class="tw"><table><tr><th></th>{cab}</tr>{filas}</table></div>'
        '<p class="sub" style="margin:10px 0 0">DMB y MC2 comparten casi toda '
        'su variación (naranja): por eso la colinealidad se vigila con el VIF '
        'de los regresores, no con esta matriz.</p></div>')


def _card_vif(r):
    """Cuadro 3.11: VIF de los tres regresores del largo plazo."""
    v = r.get("vif")
    if not v:
        return ""
    filas = "".join(
        f'<tr><td title="{GLOSARIO.get(k, "")}">{k}</td>'
        f'<td class="num">{val:.4f}</td>'
        f'<td><span class="pill {"ok" if val < 5 else "warn"}">'
        f'{"&lt; 5 OK" if val < 5 else "alto"}</span></td></tr>'
        for k, val in v.items())
    return (
        f'<div class="card"><div class="lbl">VIF{_ref("Cuadro 3.11")}</div>'
        f'<table><tr><th>Regresor</th><th class="num">VIF</th><th>Veredicto</th></tr>'
        f'{filas}</table>'
        '<p class="sub" style="margin:10px 0 0">Factor de inflación de la '
        'varianza. Por debajo de 5 no hay multicolinealidad preocupante.</p></div>')


def _card_hac(r):
    """Cuadro 3.12: errores estándar robustos Newey-West."""
    h = r.get("hac")
    if not h:
        return ""
    filas = "".join(
        f'<tr><td title="{GLOSARIO.get(k, "")}">{k}</td>'
        f'<td class="num">{d["coef"]:+.4f}</td>'
        f'<td class="num">{_p_corto(d["p"])}</td>'
        f'<td>{_pill_p(d["p"])}</td></tr>'
        for k, d in h.items())
    return (
        f'<div class="card"><div class="lbl">ERRORES ROBUSTOS HAC{_ref("Cuadro 3.12")}</div>'
        f'<table><tr><th>Término en nivel</th><th class="num">Coef.</th>'
        f'<th class="num">p</th><th>Al 5%</th></tr>{filas}</table>'
        '<p class="sub" style="margin:10px 0 0">Errores robustos HAC '
        '(Newey-West, 12 rezagos): la significancia de MC2 y RV12 se '
        'mantiene.</p></div>')


CAVEAT_RESET = ('Caveat honesto: el RESET del 6D rechaza (p=0.008) — posible no '
                'linealidad; se reporta como limitación, igual que en la tesis.')


def _card_diagnosticos(r):
    """Cuadro 3.9: pruebas sobre los residuos de la UECM. Si no llegó el bloque
    se degrada a la tarjeta mínima de siempre (n, R², DW, muestra)."""
    d = r.get("diagnosticos") or {}
    muestra = (f'<tr><td>Muestra</td><td class="num" colspan="2">'
               f'{r["sample"][0][:7]} → {r["sample"][1][:7]}</td></tr>')
    if not d:
        return (
            f'<div class="card"><div class="lbl">DIAGNÓSTICOS{_ref("Cuadro 3.9")}</div><table>'
            f'<tr><td>n</td><td class="num" colspan="2">{r["n"]}</td></tr>'
            f'<tr><td title="ARDL en niveles; en la UECM en diferencias de la tesis ronda 0.89">'
            f'R² ajustada (niveles)</td><td class="num" colspan="2">{r["r2adj"]:.4f}</td></tr>'
            f'<tr><td>Durbin-Watson</td><td class="num" colspan="2">{r["dw"]:.3f}</td></tr>'
            f'{muestra}</table>'
            f'<p class="sub" style="margin:12px 0 0">{CAVEAT_RESET}</p></div>')

    def fila(nombre, valor, p=None, title=""):
        t = f' title="{title}"' if title else ""
        return (f'<tr><td{t}>{nombre}</td><td class="num">{valor}</td>'
                f'<td>{_pill_p(p)}</td></tr>')

    def val(clave, fmt="{:.4f}"):
        v = d.get(clave)
        return "—" if v is None else fmt.format(v)

    dw = d.get("dw", r["dw"])
    r2u = d.get("r2adj_uecm")
    filas = (
        fila("Durbin-Watson", f"{dw:.3f}" if dw is not None else "—",
             title="Autocorrelación de primer orden; cerca de 2 es lo deseable")
        + fila("Breusch-Pagan (p)", val("bp_p"), d.get("bp_p"),
               title="Nula: homocedasticidad")
        + fila("ARCH LM (p)", val("arch_p"), d.get("arch_p"),
               title="Nula: sin heterocedasticidad condicional (12 rezagos)")
        + fila("Ljung-Box(12) (p)", val("lb12_p"), d.get("lb12_p"),
               title="Nula: residuos sin autocorrelación hasta el rezago 12")
        + fila("Jarque-Bera (p)", val("jb_p"), d.get("jb_p"),
               title="Nula: residuos normales")
        + fila("RESET (p)", val("reset_p"), d.get("reset_p"),
               title="Nula: forma funcional lineal correcta (ecuación en niveles)")
        + fila("R² ajustada UECM", "—" if r2u is None else f"{r2u:.4f}",
               title="La misma que reporta la tesis: ecuación (3.3), en diferencias")
        + fila("n", str(r["n"]))
        + muestra)

    rp = d.get("reset_p")
    if rp is None:
        caveat = CAVEAT_RESET
    elif rp < 0.05:
        caveat = (f'El RESET rechaza (p={rp:.4f}): posible no linealidad. La '
                  f'tesis lo reporta como limitación y línea de investigación '
                  f'futura.')
    else:
        caveat = (f'El RESET no rechaza (p={rp:.4f}): en esta muestra no hay '
                  f'evidencia de error de forma funcional.')
    return (
        f'<div class="card"><div class="lbl">DIAGNÓSTICOS{_ref("Cuadro 3.9")}</div>'
        f'<table>{filas}</table>'
        f'<p class="sub" style="margin:12px 0 0">{caveat}</p></div>')


CARD_ESPEC = (
    '<div class="card"><div class="lbl">ESPECIFICACIÓN (§3.3 DE LA TESIS)</div>'
    '<div class="eqs">'
    '<div><b>(3.1)</b>DMB<sub>t</sub> = β₀ + β₁·MC2<sub>t</sub> + β₂·RV12<sub>t</sub>'
    ' + β₃·UC<sub>t</sub> + u<sub>t</sub></div>'
    '<div><b>(3.3)</b>ΔDMB<sub>t</sub> = α + δt + θ₀·DMB<sub>t−1</sub> + θ′·X<sub>t−1</sub>'
    ' + Σγ<sub>i</sub>·ΔDMB<sub>t−i</sub> + Σλ<sub>j</sub>′·ΔX<sub>t−j</sub>'
    ' + ε<sub>t</sub></div>'
    '</div>'
    '<p class="sub" style="margin:12px 0 0">(3.1) es la relación de largo plazo '
    'que se busca; (3.3) es la UECM que efectivamente se estima y de la que '
    'salen el Bounds F, el ECT y los coeficientes de largo plazo.</p></div>')


def _leer_vars(monthly_csv):
    """monthly.csv -> {fechas, DMB, MC2, MC1, RV12, UC} o None si no existe."""
    p = pathlib.Path(monthly_csv)
    if not p.exists():
        return None
    fechas, series = [], {k: [] for k in VARS_PALETA}
    try:
        with open(p, newline="") as f:
            for row in csv.DictReader(f):
                fechas.append(row["Fecha"][:7])
                for k in series:
                    v = row.get(k, "")
                    series[k].append(round(float(v), 4) if v not in ("", None) else None)
    except (KeyError, ValueError, OSError):
        return None
    if not fechas:
        return None
    return dict(fechas=fechas, **series)


def _leer_lecturas(monthly_csv):
    """Último publicado (última fila con m2_published True) vs Nowcast (última
    fila con datos, si su mes difiere del publicado). -> dict con pub_mes/pub
    y now_mes/now (None si no hay nowcast activo), o None si no hay datos."""
    p = pathlib.Path(monthly_csv)
    if not p.exists():
        return None
    try:
        with open(p, newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None
    if not rows:
        return None

    def tiene_datos(row):
        return any(row.get(k, "") not in ("", None) for k in LECT_VARS)

    def valores(row):
        out = {}
        for k in LECT_VARS:
            v = row.get(k, "")
            try:
                out[k] = round(float(v), 4) if v not in ("", None) else None
            except ValueError:
                out[k] = None
        return out

    ultimo = next((row for row in reversed(rows) if tiene_datos(row)), None)
    if ultimo is None:
        return None
    publicado = next(
        (row for row in reversed(rows)
         if tiene_datos(row)
         and str(row.get("m2_published", "True")).strip().lower() != "false"),
        None)
    if publicado is None:
        publicado = ultimo

    nowcast = ultimo if publicado["Fecha"][:7] != ultimo["Fecha"][:7] else None
    return dict(pub_mes=publicado["Fecha"][:7], pub=valores(publicado),
                now_mes=(nowcast["Fecha"][:7] if nowcast else None),
                now=(valores(nowcast) if nowcast else None))


def _tabla_robustez(r):
    """Card ROBUSTEZ DE LA ESPECIFICACIÓN: Base (0D) / Calibrado 6D / 8D, una
    fila por especificación, con los mismos estadísticos. '' si no hay datos
    de robustez (degradación T15)."""
    rob = r.get("robustez") or {}
    if not rob:
        return ""
    especs = []
    if "base" in rob:
        especs.append(("Base (0D)", rob["base"], False))
    especs.append(("Calibrado 6D",
                    dict(boundsF=r["boundsF"], ect=r["ect"], lr=r["lr"],
                         n=r["n"], aic=None), True))
    if "8D" in rob:
        especs.append(("8D", rob["8D"], False))
    if len(especs) < 2:
        return ""

    crit1 = r["crit"]["1%"][1]
    cointegran = all(d["boundsF"] > crit1 for _, d, _ in especs)
    ect_neg = all(d["ect"]["coef"] < 0 for _, d, _ in especs)
    nota = ("La conclusión no depende de las dummies: la cointegración y los "
            "signos se sostienen en las tres especificaciones (robustez del "
            "Cap. 3).") if (cointegran and ect_neg) else \
           "Comparación de especificaciones re-estimada semanalmente."

    filas = "".join(
        f'<tr><td>{"<b>" + nombre + "</b>" if bold else nombre}</td>'
        f'<td class="num">{d["boundsF"]:.2f}</td>'
        f'<td class="num">{d["ect"]["coef"]:.4f}</td>'
        f'<td class="num">{d["lr"]["MC2"]["coef"]:.3f}{d["lr"]["MC2"]["stars"]}</td>'
        f'<td class="num">{d["lr"]["RV12"]["coef"]:.3f}{d["lr"]["RV12"]["stars"]}</td>'
        f'<td class="num">{d["lr"]["UC"]["coef"]:.3f}{d["lr"]["UC"]["stars"]}</td>'
        f'<td class="num">{d["n"]}</td>'
        f'<td class="num">{f"{d['aic']:.2f}" if d.get("aic") is not None else "—"}</td></tr>'
        for nombre, d, bold in especs)
    return (
        '<div class="card"><div class="lbl">ROBUSTEZ DE LA ESPECIFICACIÓN'
        f'{_ref("Cuadro 3.4")}</div>'
        '<div class="tw"><table><tr><th>Especificación</th><th class="num">Bounds F</th>'
        '<th class="num">ECT</th><th class="num">MC2</th><th class="num">RV12</th>'
        '<th class="num">UC</th><th class="num">n</th><th class="num">AIC</th></tr>'
        f'{filas}</table></div>'
        f'<p class="sub" style="margin:10px 0 0">{nota}</p></div>')


def _leer_mercado(monthly_csv):
    """Última fila de monthly.csv -> valores 'al build' para la sección Mercado."""
    p = pathlib.Path(monthly_csv)
    if not p.exists():
        return None
    try:
        with open(p, newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None
    if not rows:
        return None
    last = rows[-1]
    try:
        return dict(
            fecha=last["Fecha"][:10],
            price=float(last["BTC_price"]),
            supply=float(last["BTC_supply"]),
            dom=float(last["Dominance_dec"]) * 100,
        )
    except (KeyError, ValueError):
        return None


def _brecha_stats(r):
    """Serie histórica de la brecha (DMB-DMB*)*100 + percentil/z de hoy y
    trayectoria de convergencia implícita por el ECT. None si no hay serie
    utilizable (degradación T14)."""
    series = r.get("series") or {}
    fechas = series.get("fechas") or []
    dmb = series.get("dmb") or []
    dmb_star = series.get("dmb_star") or []
    pares = [(f, (a - b) * 100) for f, a, b in zip(fechas, dmb, dmb_star)
             if a is not None and b is not None]
    if not pares:
        return None
    fechas_g = [f for f, _ in pares]
    gap_series = [g for _, g in pares]
    n = len(gap_series)
    media = sum(gap_series) / n
    sd = (sum((x - media) ** 2 for x in gap_series) / n) ** 0.5
    gap_hoy = r["gap"]["hoy"]
    pct = sum(1 for x in gap_series if x < gap_hoy) / n * 100
    z = (gap_hoy - media) / sd if sd > 0 else 0.0
    ect = r["ect"]["coef"]
    conv = {k: gap_hoy * (1 + ect) ** k for k in (3, 6, 12)}
    return dict(fechas=fechas_g, gap_series=gap_series, n=n, media=media,
                sd=sd, pct=pct, z=z, conv=conv)


def _leer_equilibrio(monthly_csv, gap_hoy):
    """Última fila de monthly.csv con DMB no nulo -> nivel de equilibrio
    implícito (market cap y precio), dado el gap de hoy. None si faltan
    columnas o el archivo no existe."""
    p = pathlib.Path(monthly_csv)
    if not p.exists():
        return None
    try:
        with open(p, newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None
    ult = None
    for row in rows:
        v = row.get("DMB", "")
        if v not in ("", None):
            ult = row
    if ult is None:
        return None
    try:
        dmb = float(ult["DMB"])
        m2 = float(ult["M2SL_USD"])
        supply = float(ult["BTC_supply"])
        price_obs = float(ult["BTC_price"])
    except (KeyError, ValueError):
        return None
    if supply <= 0:
        return None
    dmb_star_hoy = dmb - gap_hoy / 100
    mcap_eq = math.exp(dmb_star_hoy) * m2
    return dict(mcap_eq=mcap_eq, price_eq=mcap_eq / supply, price_obs=price_obs,
                fecha=ult["Fecha"][:10])


def _fmt_usd_abbrev(v):
    """$X.XXe12 abreviado a $B/$T, convención del sitio."""
    if v >= 1e12:
        return f"${v / 1e12:.2f}T"
    if v >= 1e9:
        return f"${v / 1e9:.1f}B"
    if v >= 1e6:
        return f"${v / 1e6:.1f}M"
    return f"${v:,.0f}"


def _leer_raw_mensual(path, agg, drop_nonpos=False):
    """CSV diario (date,value) -> mensual. agg='sum' (flujo) o 'last' (nivel).
    drop_nonpos: valores <=0 se vuelven None (para ejes logarítmicos)."""
    p = pathlib.Path(path)
    if not p.exists():
        return None
    buckets = {}
    try:
        with open(p, newline="") as f:
            for row in csv.DictReader(f):
                try:
                    v = float(row["value"])
                except (KeyError, ValueError, TypeError):
                    continue
                buckets.setdefault(row["date"][:7], []).append(v)
    except OSError:
        return None
    if not buckets:
        return None
    meses = sorted(buckets)
    if agg == "sum":
        vals = [round(sum(buckets[m])) for m in meses]
    else:
        vals = [round(buckets[m][-1]) for m in meses]
    if drop_nonpos:
        vals = [v if v > 0 else None for v in vals]
    return dict(fechas=meses, valores=vals)


def render(r, freshness, out="site/index.html", monthly_csv="data/monthly.csv"):
    gap = r["gap"]["hoy"]                                  # puntos log
    gap_nivel = (math.exp(gap / 100) - 1) * 100            # equivalente en nivel
    lado = "SUB-monetizado" if gap < 0 else "SOBRE-monetizado"
    cointegra = r["boundsF"] > r["crit"]["1%"][1]
    # las secciones opcionales desaparecen del nav y del índice si su bloque no
    # llegó en results.json, de modo que la numeración 01..0N siempre cuadre
    secciones = [s for s in SECCIONES
                 if s not in SEC_OPCIONALES or r.get(SEC_OPCIONALES[s])]
    idx = {s: f"{i:02d}" for i, s in enumerate(secciones, 1)}
    nav = "".join(f'<a href="#{_ancla(s)}">{s}</a>' for s in secciones)
    alertas = "".join(f'<div class="alerta">⚠ {a}</div>' for a in r["alertas"])
    lr = r["lr"]
    filas_lr = "".join(
        f'<tr><td>{k}</td><td class="num">{d["coef"]:.4f}{d["stars"]}</td>'
        f'<td class="num">{"&lt; 0.0001" if d["p"] < 1e-4 else f"{d['p']:.4f}"}</td></tr>'
        for k, d in lr.items())
    funciones = [
        ("Reserva de valor", "RV12", lr["RV12"]["p"] < 0.05),
        ("Medio de cambio", "MC2", lr["MC2"]["p"] < 0.05),
        ("Unidad de cuenta", "UC", lr["UC"]["p"] < 0.05),
    ]
    cards_fn = "".join(
        f'<div class="card"><div class="lbl">{n} · {v}</div>'
        f'<span class="pill {"ok" if sig else "bad"}">{"CUMPLE" if sig else "NO SIGNIFICATIVA"}</span></div>'
        for n, v, sig in funciones)

    # VERDICTO (chips bajo el subtítulo del H1): reutiliza `funciones`
    verdict_chips = "".join(
        f'<span class="chip {"yes" if sig else "no"}">{n} {"✓" if sig else "n.s."}</span>'
        for n, _v, sig in funciones)

    # PANEL DE INSTRUMENTOS (KPI strip) al inicio de la sección El modelo
    sample_yrs = f'{r["sample"][0][:4]}–{r["sample"][1][:4]}'
    # El R² que reporta la tesis es el de la UECM en diferencias; el del ARDL en
    # niveles va inflado por la tendencia. Se prefiere el primero si llegó.
    r2u = (r.get("diagnosticos") or {}).get("r2adj_uecm")
    if r2u is None:
        kpi_r2 = (f'<div class="kpi"><div class="kl" title="R² del ARDL en niveles;'
                  f' las series con tendencia lo inflan. En la ecuación UECM'
                  f' (diferencias) de la tesis ronda 0.89.">R² aj. (niveles)</div>'
                  f'<div class="kv">{r["r2adj"]:.3f}</div></div>')
    else:
        kpi_r2 = (f'<div class="kpi"><div class="kl" title="Igual que la tesis'
                  f' (ec. 3.3 en diferencias). El R² del ARDL en niveles'
                  f' ({r["r2adj"]:.3f}) está inflado por la tendencia.">'
                  f'R² aj. (UECM)</div>'
                  f'<div class="kv">{r2u:.3f}</div></div>')
    kpis_html = (
        '<div class="card kpis">'
        f'<div class="kpi"><div class="kl">Veredicto</div>'
        f'<div class="kv {"ok" if cointegra else "warn"}">'
        f'{"SÍ cointegra" if cointegra else "en duda"}</div></div>'
        f'<div class="kpi"><div class="kl">Bounds F</div>'
        f'<div class="kv">{r["boundsF"]:.2f}</div></div>'
        f'<div class="kpi"><div class="kl" title="{GLOSARIO["ECT"]}">ECT'
        f'{_ref("Cuadro 3.8")}</div>'
        f'<div class="kv">{r["ect"]["coef"]:.3f}</div>'
        f'<div class="ksub">vida media {r["ect"]["half_life_m"]:.1f} m</div></div>'
        f'<div class="kpi"><div class="kl">Muestra</div>'
        f'<div class="kv">{sample_yrs}</div></div>'
        f'<div class="kpi"><div class="kl">Observaciones</div>'
        f'<div class="kv">n = {r["n"]}</div></div>'
        f'{kpi_r2}'
        '</div>')

    trend_glyph = "▲" if gap > 0 else "▼"
    filas_datos = "".join(
        f'<tr><td>{k}</td><td>{v["last"]}</td>'
        f'<td><span class="pill {"ok" if v["status"] == "FRESCO" else "warn" if v["status"] == "STALE" else "bad"}">{v["status"]}</span></td></tr>'
        for k, v in freshness.items())

    # ÚLTIMAS LECTURAS (Variables, columna derecha): publicado vs nowcast
    lect = _leer_lecturas(monthly_csv)
    if lect:
        con_nowcast = lect["now"] is not None
        cab_now = (f'<th class="num">Nowcast <span class="pill warn">NOWCAST</span>'
                   f'<br><span class="mono" style="font-weight:400;color:var(--dim)">'
                   f'{lect["now_mes"]}</span></th>') if con_nowcast else ""
        filas_lect = "".join(
            f'<tr><td title="{GLOSARIO.get(k, "")}">{k}</td><td class="num mono">'
            f'{f"{lect['pub'][k]:.4f}" if lect["pub"][k] is not None else "—"}</td>'
            + (f'<td class="num mono">'
               f'{f"{lect['now'][k]:.4f}" if con_nowcast and lect["now"][k] is not None else "—"}</td>'
               if con_nowcast else "")
            + '</tr>'
            for k in LECT_VARS)
        card_lect = (
            '<div class="card"><div class="lbl">ÚLTIMAS LECTURAS</div>'
            f'<table><tr><th>Serie</th><th class="num">Último publicado'
            f'<br><span class="mono" style="font-weight:400;color:var(--dim)">'
            f'{lect["pub_mes"]}</span></th>{cab_now}</tr>{filas_lect}</table>'
            '<p class="sub" style="margin:10px 0 0">NOWCAST = M2 aún '
            'provisional; no entra a la estimación.</p></div>')
    else:
        card_lect = ('<div class="card"><div class="lbl">ÚLTIMAS LECTURAS</div>'
                     '<p class="sub">Sin lecturas disponibles.</p></div>')

    # DIAGNÓSTICOS (Cointegración, columna derecha) — Cuadro 3.9 sobre la UECM
    card_diag = _card_diagnosticos(r)

    # BRECHA: contexto histórico (percentil/z), trayectoria del ECT y
    # equilibrio implícito en niveles (T14, todo derivado de r + monthly.csv)
    brecha = _brecha_stats(r)
    equilibrio = _leer_equilibrio(monthly_csv, gap)
    if brecha:
        contexto_brecha = (
            f'<p class="sub">Percentil {brecha["pct"]:.0f} de la historia '
            f'(z {brecha["z"]:+.1f})</p>'
            f'<p class="sub mono" style="margin-bottom:0">Trayectoria implícita '
            f'del ECT: {brecha["conv"][3]:+.0f} (3m) · {brecha["conv"][6]:+.0f} '
            f'(6m) · {brecha["conv"][12]:+.0f} (12m) pts log '
            f'<span style="font-style:italic">(ceteris paribus las demás '
            f'variables)</span></p>')
    else:
        contexto_brecha = ""
    if equilibrio:
        mcap_str = _fmt_usd_abbrev(equilibrio["mcap_eq"])
        precio_linea = (f'Precio implícito: ${equilibrio["price_eq"]:,.0f} · '
                         f'observado: ${equilibrio["price_obs"]:,.0f}')
    else:
        mcap_str = "—"
        precio_linea = "Precio implícito: — · observado: —"
    # bloques nuevos del Cap.3 (T17); "" si su bloque no llegó
    card_raiz = _card_raiz(r)
    nota_raiz = _nota_raiz(r)
    card_corr = _card_correlacion(r)
    card_vif = _card_vif(r)
    card_hac = _card_hac(r)
    if card_corr and card_vif:
        fila_corr_vif = f'<div class="g2x2">{card_corr}{card_vif}</div>'
    else:
        fila_corr_vif = card_corr or card_vif
    seccion_raiz = (
        f'<section id="{_ancla("Raíz unitaria")}">'
        f'<h2><span class="idx">{idx.get("Raíz unitaria", "")}</span>Raíz unitaria</h2>'
        f'<p class="sub">{nota_raiz}</p>{card_raiz}</section>'
    ) if card_raiz else ""

    card_equilibrio = (
        '<div class="card"><div class="lbl">EQUILIBRIO IMPLÍCITO (NIVELES)</div>'
        f'<div class="big mono">{mcap_str}</div>'
        f'<p class="sub mono" style="margin-bottom:0">{precio_linea}</p>'
        '<p class="sub" style="margin:6px 0 0">No es pronóstico de precio: el '
        'ajuste puede venir por DMB o por crecimiento de las funciones del '
        'dinero (MC2, RV12), que elevan el equilibrio.</p></div>')
    oculto_brecha = "" if brecha else ' style="display:none"'
    card_robustez = _tabla_robustez(r)

    # datos secundarios; si faltan archivos se degradan a canvas oculto
    raw_dir = pathlib.Path(monthly_csv).parent / "raw"
    sec = dict(
        vars=_leer_vars(monthly_csv),
        tx=_leer_raw_mensual(raw_dir / "tx_count.csv", "sum"),
        supply=_leer_raw_mensual(raw_dir / "btc_supply.csv", "last"),
        difficulty=_leer_raw_mensual(raw_dir / "difficulty.csv", "last", drop_nonpos=True),
        fees=_leer_raw_mensual(raw_dir / "fees_btc.csv", "sum"),
        price=_leer_raw_mensual(raw_dir / "btc_price_sampled.csv", "last", drop_nonpos=True),
    )
    oculto = {k: "" if sec[k] else ' style="display:none"' for k in sec}

    # Mercado: valores estáticos al build (la vista viva los sobreescribe via JS)
    mkt = _leer_mercado(monthly_csv)
    if mkt:
        px_init = f"${mkt['price']:,.0f}"
        dom_init = f"{mkt['dom']:.1f}%"
        sup_init = f"{mkt['supply']:,.0f}"
        sup_fecha = mkt["fecha"]
    else:
        px_init = dom_init = sup_init = "—"
        sup_fecha = "—"

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>El Bitcoin ¿es dinero? · Bitcoin Terminal</title>
<meta name="description" content="{META_DESC}">
<meta property="og:title" content="El Bitcoin ¿es dinero? · Bitcoin Terminal">
<meta property="og:description" content="{META_DESC}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}">
<link rel="icon" href="{FAVICON}">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header><div class="wordmark">₿<b>itcoin</b> Terminal</div><nav>{nav}</nav></header>
<div class="statusbar"><span class="live"><span class="dot"></span>EN VIVO</span>
<span class="meta">Modelo re-estimado {r["generated_at"][:10]} · muestra {r["sample"][0]} → {r["sample"][1]} · n={r["n"]} · datos frescos</span></div>
<main>
<section id="{_ancla("El modelo")}">
<h1><span class="idx">{idx["El modelo"]}</span>El Bitcoin ¿es dinero?</h1>
<p class="sub" style="margin-bottom:4px">Evidencia de cointegración ARDL — Calibrado 6D, {r["sample"][0]} → {r["sample"][1]} (n={r["n"]})</p>
<p class="sub" style="margin-bottom:10px;color:var(--faint)">Alonzo Niño Mendoza · Asesora: Dra. Nancy Ivonne Muller Duran · Facultad de Economía, UNAM</p>
<div class="verdict"><span class="lead">El modelo responde:</span>{verdict_chips}</div>
{alertas}
{kpis_html}
<div class="hero">
<div class="card star"><div class="lbl">BRECHA DE MONETIZACIÓN · {r["gap"]["fecha"]}</div>
<div class="big"><span style="color:#c46f0a">{trend_glyph}</span> {gap_nivel:+.0f}%</div>
<p class="sub">({gap:+.1f} puntos log)</p>
<div class="gauge"><i style="left:{max(2, min(94, 50 + gap / 2)):.0f}%;width:4%"></i><b></b></div>
<p class="sub" style="margin-bottom:0">BTC {lado} vs su equilibrio · corrección {abs(r["ect"]["coef"]) * 100:.0f}%/mes · vida media {r["ect"]["half_life_m"]:.1f} meses</p>
{contexto_brecha}
<div class="cwrap spark"{oculto_brecha}><canvas id="c_gap_spark"></canvas></div></div>
<div class="stack">
<div class="card"><div class="lbl">RELACIÓN DE LARGO PLAZO</div>
<p class="mono">DMB* = c + {lr["MC2"]["coef"]:.3f}·MC2{lr["MC2"]["stars"]} + {lr["RV12"]["coef"]:.3f}·RV12{lr["RV12"]["stars"]} + {lr["UC"]["coef"]:.3f}·UC{lr["UC"]["stars"]}</p></div>
{card_equilibrio}
</div>
</div>
{CARD_ESPEC}
<div class="card"><div class="lbl">DMB OBSERVADO VS EQUILIBRIO</div><div class="cwrap"><canvas id="c_gap"></canvas></div>
<p class="sub" style="margin-bottom:0">— tramo ámbar: M2 provisional (nowcast)</p></div>
</section>
<section id="{_ancla("Variables")}"><h2><span class="idx">{idx["Variables"]}</span>Variables</h2>
<p class="sub">Las cinco variables del modelo. DMB es la monetización de BTC frente a M2; MC2, MC1, RV12 y UC son las funciones del dinero.</p>
<div class="two">
<div class="card"><div class="lbl">SERIES DEL MODELO (2015–HOY){_ref("Figura 3.1")}</div><div class="cwrap"{oculto["vars"]}><canvas id="c_vars"></canvas></div><p class="sub" style="margin-bottom:0">DMB, MC2, MC1, RV12, UC — meses nowcast punteados en ámbar</p></div>
{card_lect}</div></section>
{seccion_raiz}
<section id="{_ancla("Cointegración")}"><h2><span class="idx">{idx["Cointegración"]}</span>Cointegración</h2>
<p class="sub">¿Hay una relación de equilibrio estable de largo plazo? El test de límites lo decide: F por encima del valor crítico I(1) = sí.</p>
<div class="two">
<div class="card"><div class="lbl">PRUEBA DE COINTEGRACIÓN (BOUNDS){_ref("Cuadro 3.6")}</div><table><tr><th>Nivel</th><th class="num">I(0)</th><th class="num">I(1)</th><th class="num">F</th></tr>
{"".join(f'<tr><td>{n}</td><td class="num">{c[0]:.3f}</td><td class="num">{c[1]:.3f}</td><td class="num">{r["boundsF"]:.2f}</td></tr>' for n, c in r["crit"].items())}
</table></div>
{card_diag}</div>
{card_robustez}
{fila_corr_vif}
{card_hac}
<div class="card"><div class="lbl">BRECHA HISTÓRICA (PTS LOG)</div><div class="cwrap"{oculto_brecha}><canvas id="c_brecha"></canvas></div>
<p class="sub" style="margin-bottom:0">DMB − DMB* a lo largo de la muestra · línea cero y banda ±1σ sobre la media histórica</p></div>
</section>
<section id="{_ancla("Funciones del dinero")}"><h2><span class="idx">{idx["Funciones del dinero"]}</span>Funciones del dinero</h2>
<p class="sub">Cada coeficiente de largo plazo dice si BTC cumple esa función del dinero de forma estadísticamente significativa.</p>
<div class="grid">{cards_fn}</div>
<p class="quote">«Existe evidencia de que Bitcoin se comporta a largo plazo como medio de cambio y reserva de valor; el modelo no favorece su comportamiento como unidad de cuenta.» — Conclusiones, Cap. 3</p>
<div class="card half" style="margin-top:16px"><div class="lbl">COEFICIENTES DE LARGO PLAZO{_ref("Cuadro 3.7")}</div><table><tr><th>Variable</th><th class="num">Coef. LP</th><th class="num">p</th></tr>{filas_lr}</table></div></section>
<section id="{_ancla("Hechos estilizados")}"><h2><span class="idx">{idx["Hechos estilizados"]}</span>Hechos estilizados</h2>
<p class="sub">Los hechos del Capítulo 1, en vivo: adopción, escasez y costos de la red.</p>
<div class="g2x2">
<div class="card"><div class="lbl">TRANSACCIONES / MES</div><div class="cwrap sm"{oculto["tx"]}><canvas id="c_tx"></canvas></div></div>
<div class="card"><div class="lbl">OFERTA DE BTC</div><div class="cwrap sm"{oculto["supply"]}><canvas id="c_supply"></canvas></div></div>
<div class="card"><div class="lbl">DIFICULTAD (LOG)</div><div class="cwrap sm"{oculto["difficulty"]}><canvas id="c_difficulty"></canvas></div></div>
<div class="card"><div class="lbl">COMISIONES BTC / MES</div><div class="cwrap sm"{oculto["fees"]}><canvas id="c_fees"></canvas></div></div>
</div>
<div class="card"><div class="lbl">PRECIO BTC (LOG)</div><div class="cwrap"{oculto["price"]}><canvas id="c_price"></canvas></div>
<p class="sub" style="margin-bottom:0">El hecho estilizado más citado de la tesis · escala logarítmica</p></div></section>
<section id="{_ancla("Mercado")}"><h2><span class="idx">{idx["Mercado"]}</span>Mercado</h2>
<p class="sub">Precio y dominancia en tiempo real; tu navegador consulta CoinGecko directamente.</p>
<div class="grid">
<div class="card" id="ticker"><div class="lbl">PRECIO BTC · EN VIVO</div>
<p class="big mono" id="tk_price">{px_init}</p><p class="sub" style="margin-bottom:0">CoinGecko al abrir; si falla, valor del build</p></div>
<div class="card"><div class="lbl">DOMINANCIA BTC · EN VIVO</div>
<p class="big mono" id="tk_dom">{dom_init}</p><p class="sub" style="margin-bottom:0">% del market cap total</p></div>
<div class="card"><div class="lbl">OFERTA EN CIRCULACIÓN · AL BUILD</div>
<p class="big mono">{sup_init}</p><p class="sub" style="margin-bottom:0">BTC minados a {sup_fecha}</p></div>
</div></section>
<section id="{_ancla("Datos")}"><h2><span class="idx">{idx["Datos"]}</span>Datos</h2>
<p class="sub">De dónde viene cada serie y qué tan fresca está.</p>
<div class="two">
<div class="card"><div class="lbl">FRESCURA POR SERIE</div><table><tr><th>Serie</th><th>Última fecha</th><th>Estado</th></tr>{filas_datos}</table></div>
<div class="card"><div class="lbl">FUENTES CITABLES{_ref("Cuadro 3.13")}</div><p class="sub" style="margin-bottom:0">blockchain.info (on-chain), Stooq / Yahoo Finance (oro), FRED · M2SL, CoinGecko (precio y dominancia vivos), y semilla histórica de dominancia validada en la tesis. Código y datos: <a href="{REPO_URL}">github.com/AlonzoBenz/BitcoinTerminal</a><br>Metodología: ARDL-Bounds (Pesaran, Shin &amp; Smith, 2001), caso 5. Especificación y diseño: docs/superpowers/specs/ en el repositorio.</p></div>
</div></section>
</main>
<footer>Generado {r["generated_at"]} · Modelo re-estimado con muestra {r["sample"][0]} → {r["sample"][1]} · Alonzo Niño Mendoza · Especificación congelada Calibrado 6D · <a href="{REPO_URL}">repositorio</a> · Los meses sin M2 publicado no entran a la estimación.</footer>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js" integrity="{CHARTJS_SRI}" crossorigin="anonymous"></script>
<script>{_script(r, sec, brecha)}</script></body></html>"""
    out = pathlib.Path(out)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(html)
    tmp.replace(out)          # publicacion atomica del archivo
    return out


def _script(r, sec, brecha=None):
    """Bloque JS: datos embebidos + charts. String normal (sin f-string) para
    no pelear con las llaves de JS."""
    R = json.dumps(dict(fechas=r["series"]["fechas"], dmb=r["series"]["dmb"],
                        dmb_star=r["series"]["dmb_star"]))
    NOWCAST = json.dumps(r["series"]["nowcast"])
    S = json.dumps(sec)
    BR = json.dumps(dict(fechas=brecha["fechas"],
                          valores=[round(x, 2) for x in brecha["gap_series"]],
                          media=round(brecha["media"], 2),
                          sd=round(brecha["sd"], 2))) if brecha else "null"
    ejes = ('{responsive:true,maintainAspectRatio:false,'
            'plugins:{legend:{labels:{color:"#6e6656"}}},'
            'scales:{x:{ticks:{maxTicksLimit:8,color:"#a09681"}},'
            'y:{ticks:{color:"#a09681"}}}}')
    ejes_anios = ('{responsive:true,maintainAspectRatio:false,'
                  'plugins:{legend:{display:false}},'
                  'scales:{x:{ticks:{maxTicksLimit:8,color:"#a09681",'
                  'callback:function(v){return this.getLabelForValue(v).slice(0,4);}}},'
                  'y:{ticks:{color:"#a09681"}}}}')
    ejes_log = ('{responsive:true,maintainAspectRatio:false,'
                'plugins:{legend:{display:false}},'
                'scales:{x:{ticks:{maxTicksLimit:8,color:"#a09681",'
                'callback:function(v){return this.getLabelForValue(v).slice(0,4);}}},'
                'y:{type:"logarithmic",ticks:{color:"#a09681"}}}}')
    ejes_spark = ('{responsive:true,maintainAspectRatio:false,'
                  'plugins:{legend:{display:false},tooltip:{enabled:false}},'
                  'scales:{x:{display:false},y:{display:false}}}')
    vars_ds = ",".join(
        '{label:"' + k + '",data:S.vars.' + k + ',borderColor:"' + c
        + '",pointRadius:0,borderWidth:1.2,spanGaps:false}'
        for k, c in VARS_PALETA.items())
    js = """
const R = __R__;
const NOWCAST = __NOWCAST__;
const S = __S__;
const BR = __BR__;
new Chart(document.getElementById("c_gap"), {type: "line", data: {labels: R.fechas,
 datasets: [{label: "DMB observado", data: R.dmb, borderColor: "#f7931a", pointRadius: 0, borderWidth: 2, spanGaps: false,
             segment: {borderColor: ctx => NOWCAST[ctx.p1DataIndex] ? "#e6b56a" : "#f7931a",
                       borderDash: ctx => NOWCAST[ctx.p1DataIndex] ? [4,3] : undefined}},
            {label: "DMB* equilibrio", data: R.dmb_star, borderColor: "#a09681", borderDash: [5, 4], pointRadius: 0, borderWidth: 1.5, spanGaps: false}]},
 options: __EJES__});
if (S.vars) new Chart(document.getElementById("c_vars"), {type: "line",
 data: {labels: S.vars.fechas, datasets: [__VARS_DS__]}, options: __EJES__});
if (S.tx) new Chart(document.getElementById("c_tx"), {type: "line",
 data: {labels: S.tx.fechas, datasets: [{label: "tx/mes", data: S.tx.valores, borderColor: "#f7931a", pointRadius: 0, borderWidth: 1.5}]},
 options: __EJES_ANIOS__});
if (S.supply) new Chart(document.getElementById("c_supply"), {type: "line",
 data: {labels: S.supply.fechas, datasets: [{label: "BTC en circulación", data: S.supply.valores, borderColor: "#8a7a5c", pointRadius: 0, borderWidth: 1.5}]},
 options: __EJES_ANIOS__});
if (S.difficulty) new Chart(document.getElementById("c_difficulty"), {type: "line",
 data: {labels: S.difficulty.fechas, datasets: [{label: "dificultad", data: S.difficulty.valores, borderColor: "#8a7a5c", pointRadius: 0, borderWidth: 1.5, spanGaps: true}]},
 options: __EJES_LOG__});
if (S.fees) new Chart(document.getElementById("c_fees"), {type: "line",
 data: {labels: S.fees.fechas, datasets: [{label: "comisiones BTC/mes", data: S.fees.valores, borderColor: "#c46f0a", pointRadius: 0, borderWidth: 1.5}]},
 options: __EJES_ANIOS__});
if (S.price) new Chart(document.getElementById("c_price"), {type: "line",
 data: {labels: S.price.fechas, datasets: [{label: "precio BTC", data: S.price.valores, borderColor: "#f7931a", pointRadius: 0, borderWidth: 1.8, spanGaps: true}]},
 options: __EJES_LOG__});
if (BR) new Chart(document.getElementById("c_brecha"), {type: "line",
 data: {labels: BR.fechas, datasets: [
   {label: "brecha", data: BR.valores, borderColor: "#f7931a", pointRadius: 0, borderWidth: 1.8, spanGaps: false},
   {label: "cero", data: BR.valores.map(() => 0), borderColor: "#211d14", borderWidth: 1, pointRadius: 0, borderDash: [2, 2]},
   {label: "+1s", data: BR.valores.map(() => BR.media + BR.sd), borderColor: "#a09681", borderWidth: 1, pointRadius: 0, borderDash: [5, 4]},
   {label: "-1s", data: BR.valores.map(() => BR.media - BR.sd), borderColor: "#a09681", borderWidth: 1, pointRadius: 0, borderDash: [5, 4]}]},
 options: __EJES_ANIOS__});
if (BR) new Chart(document.getElementById("c_gap_spark"), {type: "line",
 data: {labels: BR.fechas, datasets: [
   {label: "brecha", data: BR.valores, borderColor: "#f7931a", pointRadius: 0, borderWidth: 1.2, spanGaps: false},
   {label: "cero", data: BR.valores.map(() => 0), borderColor: "#a09681", borderWidth: 1, pointRadius: 0, borderDash: [3, 3]}]},
 options: __EJES_SPARK__});
const _secs = [...document.querySelectorAll("main section[id]")];
const _links = new Map([...document.querySelectorAll("nav a")].map(a => [a.getAttribute("href").slice(1), a]));
const _io = new IntersectionObserver(es => {
  es.forEach(e => { if (e.isIntersecting) {
    _links.forEach(a => a.classList.remove("on"));
    const a = _links.get(e.target.id); if (a) a.classList.add("on");
  }});
}, {rootMargin: "-45% 0px -50% 0px"});
_secs.forEach(s => _io.observe(s));
function actualizarTicker() {
  fetch("https://api.coingecko.com/api/v3/global").then(r => r.json()).then(g => {
    document.getElementById("tk_dom").textContent = g.data.market_cap_percentage.btc.toFixed(1) + "%";
    return fetch("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd");
  }).then(r => r.json()).then(p => {
    document.getElementById("tk_price").textContent = "$" + p.bitcoin.usd.toLocaleString("en-US");
  }).catch(() => {});
}
actualizarTicker();
setInterval(actualizarTicker, 60000);  // spec §5.6: refresco cada 60s (limite libre de CoinGecko)
"""
    for tok, val in (("__R__", R), ("__NOWCAST__", NOWCAST), ("__S__", S),
                     ("__BR__", BR), ("__EJES__", ejes), ("__EJES_ANIOS__", ejes_anios),
                     ("__EJES_LOG__", ejes_log), ("__EJES_SPARK__", ejes_spark),
                     ("__VARS_DS__", vars_ds)):
        js = js.replace(tok, val)
    return js
