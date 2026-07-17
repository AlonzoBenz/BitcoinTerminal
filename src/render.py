"""results.json + frescura -> site/index.html (estatico, autocontenido salvo
CDN de Chart.js y Google Fonts)."""
import csv
import json
import math
import pathlib
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
padding:16px 20px;margin-bottom:14px}
.lbl{font-size:10.5px;letter-spacing:1.6px;color:var(--faint);margin-bottom:8px}
.big{font-family:Fraunces,serif;font-size:30px;font-weight:500}
.star .big{font-size:46px;line-height:1.05;color:var(--btctx)}
.mono{font-family:'IBM Plex Mono',monospace}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;
margin-bottom:14px}
.grid .card,.hero .card,.stack .card,.mini .card,.two .card,.g2x2 .card{margin:0}
.hero{display:grid;grid-template-columns:1.1fr 1fr;gap:16px;align-items:start;
margin-bottom:14px}
.stack{display:grid;gap:16px;align-content:start}
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
.gauge{height:8px;background:#ece4d2;border-radius:99px;position:relative;margin:10px 0}
.gauge i{position:absolute;height:8px;background:var(--btc);border-radius:99px}
.gauge b{position:absolute;left:50%;top:-3px;width:2px;height:14px;background:var(--ink)}
table{border-collapse:collapse;width:100%;font-size:13px}
td,th{padding:6px 10px 6px 0;text-align:left;border-bottom:1px solid var(--line)}
.num{font-family:'IBM Plex Mono',monospace;text-align:right}
.alerta{background:var(--warnbg);border:1px solid #fac775;color:var(--warn);
border-radius:8px;padding:12px 16px;margin-bottom:14px;font-size:13.5px}
.cwrap{position:relative;height:280px}
.cwrap.sm{height:200px}
footer{color:var(--faint);font-size:11.5px;padding:20px 4vw;border-top:1px solid var(--line)}
footer a{color:var(--btctx);text-decoration:none}
@media (max-width:900px){
main{padding:24px 5vw 60px}
.hero,.two,.mini,.g2x2,.grid{grid-template-columns:1fr}
header{flex-wrap:wrap;gap:8px}
nav{gap:10px 12px;font-size:11px}
h1{font-size:26px}
.star .big{font-size:40px}
}
"""

SECCIONES = ["El modelo", "Variables", "Cointegración", "Funciones del dinero",
             "Hechos estilizados", "Mercado", "Datos"]

# paleta para c_vars: naranja para DMB, tonos tierra para el resto
VARS_PALETA = {"DMB": "#f7931a", "MC2": "#a09681", "MC1": "#8a7a5c",
               "RV12": "#6e6656", "UC": "#c9bfa6"}

LECT_VARS = ("DMB", "MC2", "MC1", "RV12", "UC")


def _ancla(s):
    return s.lower().replace(" ", "-").replace("ó", "o")


def _fmt_p(p):
    """p-values diminutos reportados honestamente, no como 0.0000."""
    return "p &lt; 0.0001" if p < 1e-4 else f"p = {p:.4f}"


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
    """Última lectura no-NaN de cada variable + su mes y si ese mes es nowcast
    (m2_published False). -> [(nombre, valor, mes, nowcast_bool)] o None."""
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
    out = []
    for k in LECT_VARS:
        ult = None
        for row in rows:
            v = row.get(k, "")
            if v in ("", None):
                continue
            try:
                fv = float(v)
            except ValueError:
                continue
            now = str(row.get("m2_published", "True")).strip().lower() == "false"
            ult = (k, fv, row["Fecha"][:7], now)
        if ult:
            out.append(ult)
    return out or None


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
    nav = "".join(f'<a href="#{_ancla(s)}">{s}</a>' for s in SECCIONES)
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
    filas_datos = "".join(
        f'<tr><td>{k}</td><td>{v["last"]}</td>'
        f'<td><span class="pill {"ok" if v["status"] == "FRESCO" else "warn" if v["status"] == "STALE" else "bad"}">{v["status"]}</span></td></tr>'
        for k, v in freshness.items())

    # ÚLTIMAS LECTURAS (Variables, columna derecha)
    lecturas = _leer_lecturas(monthly_csv)
    if lecturas:
        filas_lect = "".join(
            f'<tr><td>{k}</td><td class="num">{val:.4f}</td>'
            f'<td class="mono" style="color:var(--dim)">{mes}</td>'
            f'<td>{"<span class=\"pill warn\">NOWCAST</span>" if now else ""}</td></tr>'
            for k, val, mes, now in lecturas)
        card_lect = (f'<div class="card"><div class="lbl">ÚLTIMAS LECTURAS</div>'
                     f'<table><tr><th>Serie</th><th class="num">Valor</th>'
                     f'<th>Mes</th><th></th></tr>{filas_lect}</table>'
                     f'<p class="sub" style="margin:10px 0 0">NOWCAST = M2 aún '
                     f'provisional; no entra a la estimación.</p></div>')
    else:
        card_lect = ('<div class="card"><div class="lbl">ÚLTIMAS LECTURAS</div>'
                     '<p class="sub">Sin lecturas disponibles.</p></div>')

    # DIAGNÓSTICOS (Cointegración, columna derecha)
    card_diag = (
        f'<div class="card"><div class="lbl">DIAGNÓSTICOS</div><table>'
        f'<tr><td>n</td><td class="num">{r["n"]}</td></tr>'
        f'<tr><td>R² ajustada</td><td class="num">{r["r2adj"]:.4f}</td></tr>'
        f'<tr><td>Durbin-Watson</td><td class="num">{r["dw"]:.3f}</td></tr>'
        f'<tr><td>Muestra</td><td class="num">{r["sample"][0][:7]} → {r["sample"][1][:7]}</td></tr>'
        f'</table><p class="sub" style="margin:12px 0 0">Caveat honesto: el RESET '
        f'del 6D rechaza (p=0.008) — posible no linealidad; se reporta como '
        f'limitación, igual que en la tesis.</p></div>')

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
<title>Bitcoin Terminal · ¿Es Bitcoin dinero?</title>
<meta name="description" content="{META_DESC}">
<meta property="og:title" content="Bitcoin Terminal · ¿Es Bitcoin dinero?">
<meta property="og:description" content="{META_DESC}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}">
<link rel="icon" href="{FAVICON}">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header><div class="wordmark">₿<b>itcoin</b> Terminal</div><nav>{nav}</nav></header>
<main>
<section id="{_ancla(SECCIONES[0])}">
<h1>¿Es Bitcoin dinero?</h1>
<p class="sub">Evidencia de cointegración ARDL — Calibrado 6D, {r["sample"][0]} → {r["sample"][1]} (n={r["n"]}) · UNAM, Facultad de Economía</p>
{alertas}
<div class="hero">
<div class="card star"><div class="lbl">BRECHA DE MONETIZACIÓN · {r["gap"]["fecha"]}</div>
<div class="big">{gap_nivel:+.0f}%</div>
<p class="sub">({gap:+.1f} puntos log)</p>
<div class="gauge"><i style="left:{max(2, min(94, 50 + gap / 2)):.0f}%;width:4%"></i><b></b></div>
<p class="sub" style="margin-bottom:0">BTC {lado} vs su equilibrio · corrección {abs(r["ect"]["coef"]) * 100:.0f}%/mes · vida media {r["ect"]["half_life_m"]:.1f} meses</p></div>
<div class="stack">
<div class="card"><div class="lbl">RELACIÓN DE LARGO PLAZO</div>
<p class="mono">DMB* = c + {lr["MC2"]["coef"]:.3f}·MC2{lr["MC2"]["stars"]} + {lr["RV12"]["coef"]:.3f}·RV12{lr["RV12"]["stars"]} + {lr["UC"]["coef"]:.3f}·UC{lr["UC"]["stars"]}</p></div>
<div class="mini">
<div class="card"><div class="lbl">COINTEGRACIÓN</div>
<div class="big mono">F = {r["boundsF"]:.2f}</div>
<span class="pill {"ok" if cointegra else "bad"}">{"SÍ · supera I(1) al 1%" if cointegra else "EN DUDA"}</span></div>
<div class="card"><div class="lbl">VELOCIDAD DE AJUSTE</div>
<div class="big mono">{r["ect"]["coef"]:.4f}</div>
<p class="sub" style="margin-bottom:0">ECT, {_fmt_p(r["ect"]["p"])}</p></div>
</div>
</div>
</div>
<div class="card"><div class="lbl">DMB OBSERVADO VS EQUILIBRIO</div><div class="cwrap"><canvas id="c_gap"></canvas></div>
<p class="sub" style="margin-bottom:0">— tramo ámbar: M2 provisional (nowcast)</p></div>
</section>
<section id="{_ancla(SECCIONES[1])}"><h2>Variables</h2>
<div class="two">
<div class="card"><div class="cwrap"{oculto["vars"]}><canvas id="c_vars"></canvas></div><p class="sub" style="margin-bottom:0">DMB, MC2, MC1, RV12, UC — meses nowcast punteados en ámbar</p></div>
{card_lect}</div></section>
<section id="{_ancla(SECCIONES[2])}"><h2>Cointegración</h2>
<div class="two">
<div class="card"><table><tr><th>Nivel</th><th class="num">I(0)</th><th class="num">I(1)</th><th class="num">F</th></tr>
{"".join(f'<tr><td>{n}</td><td class="num">{c[0]:.3f}</td><td class="num">{c[1]:.3f}</td><td class="num">{r["boundsF"]:.2f}</td></tr>' for n, c in r["crit"].items())}
</table></div>
{card_diag}</div></section>
<section id="{_ancla(SECCIONES[3])}"><h2>Funciones del dinero</h2>
<div class="grid">{cards_fn}</div>
<div class="card half"><table><tr><th>Variable</th><th class="num">Coef. LP</th><th class="num">p</th></tr>{filas_lr}</table></div></section>
<section id="{_ancla(SECCIONES[4])}"><h2>Hechos estilizados</h2>
<div class="g2x2">
<div class="card"><div class="lbl">TRANSACCIONES / MES</div><div class="cwrap sm"{oculto["tx"]}><canvas id="c_tx"></canvas></div></div>
<div class="card"><div class="lbl">OFERTA DE BTC</div><div class="cwrap sm"{oculto["supply"]}><canvas id="c_supply"></canvas></div></div>
<div class="card"><div class="lbl">DIFICULTAD (LOG)</div><div class="cwrap sm"{oculto["difficulty"]}><canvas id="c_difficulty"></canvas></div></div>
<div class="card"><div class="lbl">COMISIONES BTC / MES</div><div class="cwrap sm"{oculto["fees"]}><canvas id="c_fees"></canvas></div></div>
</div>
<div class="card"><div class="lbl">PRECIO BTC (LOG)</div><div class="cwrap"{oculto["price"]}><canvas id="c_price"></canvas></div>
<p class="sub" style="margin-bottom:0">El hecho estilizado más citado de la tesis · escala logarítmica</p></div></section>
<section id="{_ancla(SECCIONES[5])}"><h2>Mercado</h2>
<div class="grid">
<div class="card" id="ticker"><div class="lbl">PRECIO BTC · EN VIVO</div>
<p class="big mono" id="tk_price">{px_init}</p><p class="sub" style="margin-bottom:0">CoinGecko al abrir; si falla, valor del build</p></div>
<div class="card"><div class="lbl">DOMINANCIA BTC · EN VIVO</div>
<p class="big mono" id="tk_dom">{dom_init}</p><p class="sub" style="margin-bottom:0">% del market cap total</p></div>
<div class="card"><div class="lbl">OFERTA EN CIRCULACIÓN · AL BUILD</div>
<p class="big mono">{sup_init}</p><p class="sub" style="margin-bottom:0">BTC minados a {sup_fecha}</p></div>
</div></section>
<section id="{_ancla(SECCIONES[6])}"><h2>Datos</h2>
<div class="two">
<div class="card"><table><tr><th>Serie</th><th>Última fecha</th><th>Estado</th></tr>{filas_datos}</table></div>
<div class="card"><div class="lbl">FUENTES CITABLES</div><p class="sub" style="margin-bottom:0">blockchain.info (on-chain), Stooq / Yahoo Finance (oro), FRED · M2SL, CoinGecko (precio y dominancia vivos), y semilla histórica de dominancia validada en la tesis. Código y datos: <a href="{REPO_URL}">github.com/AlonzoBenz/BitcoinTerminal</a></p></div>
</div></section>
</main>
<footer>Generado {r["generated_at"]} · Modelo re-estimado con muestra {r["sample"][0]} → {r["sample"][1]} · Alonzo Niño Mendoza · Especificación congelada Calibrado 6D · <a href="{REPO_URL}">repositorio</a> · Los meses sin M2 publicado no entran a la estimación.</footer>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js" integrity="{CHARTJS_SRI}" crossorigin="anonymous"></script>
<script>{_script(r, sec)}</script></body></html>"""
    out = pathlib.Path(out)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(html)
    tmp.replace(out)          # publicacion atomica del archivo
    return out


def _script(r, sec):
    """Bloque JS: datos embebidos + charts. String normal (sin f-string) para
    no pelear con las llaves de JS."""
    R = json.dumps(dict(fechas=r["series"]["fechas"], dmb=r["series"]["dmb"],
                        dmb_star=r["series"]["dmb_star"]))
    NOWCAST = json.dumps(r["series"]["nowcast"])
    S = json.dumps(sec)
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
    vars_ds = ",".join(
        '{label:"' + k + '",data:S.vars.' + k + ',borderColor:"' + c
        + '",pointRadius:0,borderWidth:1.2,spanGaps:false}'
        for k, c in VARS_PALETA.items())
    js = """
const R = __R__;
const NOWCAST = __NOWCAST__;
const S = __S__;
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
const _secs = [...document.querySelectorAll("main section[id]")];
const _links = new Map([...document.querySelectorAll("nav a")].map(a => [a.getAttribute("href").slice(1), a]));
const _io = new IntersectionObserver(es => {
  es.forEach(e => { if (e.isIntersecting) {
    _links.forEach(a => a.classList.remove("on"));
    const a = _links.get(e.target.id); if (a) a.classList.add("on");
  }});
}, {rootMargin: "-45% 0px -50% 0px"});
_secs.forEach(s => _io.observe(s));
fetch("https://api.coingecko.com/api/v3/global").then(r => r.json()).then(g => {
  document.getElementById("tk_dom").textContent = g.data.market_cap_percentage.btc.toFixed(1) + "%";
  return fetch("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd");
}).then(r => r.json()).then(p => {
  document.getElementById("tk_price").textContent = "$" + p.bitcoin.usd.toLocaleString("en-US");
}).catch(() => {});
"""
    for tok, val in (("__R__", R), ("__NOWCAST__", NOWCAST), ("__S__", S),
                     ("__EJES__", ejes), ("__EJES_ANIOS__", ejes_anios),
                     ("__EJES_LOG__", ejes_log), ("__VARS_DS__", vars_ds)):
        js = js.replace(tok, val)
    return js
