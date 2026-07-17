"""results.json + frescura -> site/index.html (estatico, autocontenido salvo
CDN de Chart.js y Google Fonts)."""
import csv
import json
import math
import pathlib

# SRI de chart.js@4.4.1 (jsdelivr), calculado el 2026-07-16:
#   curl -s https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js \
#     | openssl dgst -sha384 -binary | openssl base64 -A
CHARTJS_SRI = "sha384-9nhczxUqK87bcKHh20fSQcTGD4qq5GhayNYSYWqwBkINBhOfQLg/P5HG5lF1urn4"

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
nav{display:flex;gap:16px;font-size:12px}
nav a{color:var(--dim);text-decoration:none;padding-bottom:3px}
nav a:hover{color:var(--ink);border-bottom:2px solid var(--btc)}
main{max-width:1040px;margin:0 auto;padding:30px 4vw 80px}
h1{font-family:Fraunces,serif;font-size:30px;font-weight:500;margin:8px 0 4px}
h2{font-family:Fraunces,serif;font-size:21px;font-weight:500;margin:44px 0 14px;
padding-top:14px;border-top:1px solid var(--line)}
.sub{color:var(--dim);font-size:13px;margin-bottom:22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:16px 20px;margin-bottom:14px}
.lbl{font-size:10.5px;letter-spacing:1.6px;color:var(--faint);margin-bottom:8px}
.big{font-family:Fraunces,serif;font-size:30px;font-weight:500}
.mono{font-family:'IBM Plex Mono',monospace}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.grid .card{margin:0}
.pill{font-size:10.5px;border-radius:99px;padding:2px 10px;border:1px solid}
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
canvas{max-height:280px}
footer{color:var(--faint);font-size:11.5px;padding:20px 4vw;border-top:1px solid var(--line)}
"""

SECCIONES = ["El modelo", "Variables", "Cointegración", "Funciones del dinero",
             "Hechos estilizados", "Mercado", "Datos"]

# paleta para c_vars: naranja para DMB, tonos tierra para el resto
VARS_PALETA = {"DMB": "#f7931a", "MC2": "#a09681", "MC1": "#8a7a5c",
               "RV12": "#6e6656", "UC": "#c9bfa6"}


def _ancla(s):
    return s.lower().replace(" ", "-").replace("ó", "o")


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


def _leer_raw_mensual(path, agg):
    """CSV diario (date,value) -> mensual. agg='sum' (tx) o 'last' (supply)."""
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
        f'<td class="num">{d["p"]:.4f}</td></tr>' for k, d in lr.items())
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

    # datos secundarios; si faltan archivos se degradan a canvas oculto
    raw_dir = pathlib.Path(monthly_csv).parent / "raw"
    sec = dict(
        vars=_leer_vars(monthly_csv),
        tx=_leer_raw_mensual(raw_dir / "tx_count.csv", "sum"),
        supply=_leer_raw_mensual(raw_dir / "btc_supply.csv", "last"),
    )
    oculto = {k: "" if sec[k] else ' style="display:none"' for k in sec}

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bitcoin Terminal · ¿Es Bitcoin dinero?</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header><div class="wordmark">₿<b>itcoin</b> Terminal</div><nav>{nav}</nav></header>
<main>
<section id="{_ancla(SECCIONES[0])}">
<h1>¿Es Bitcoin dinero?</h1>
<p class="sub">Evidencia de cointegración ARDL — Calibrado 6D, {r["sample"][0]} → {r["sample"][1]} (n={r["n"]}) · UNAM, Facultad de Economía</p>
{alertas}
<div class="card"><div class="lbl">RELACIÓN DE LARGO PLAZO</div>
<p class="mono">DMB* = c + {lr["MC2"]["coef"]:.3f}·MC2{lr["MC2"]["stars"]} + {lr["RV12"]["coef"]:.3f}·RV12{lr["RV12"]["stars"]} + {lr["UC"]["coef"]:.3f}·UC{lr["UC"]["stars"]}</p></div>
<div class="grid">
<div class="card"><div class="lbl">BRECHA DE MONETIZACIÓN · {r["gap"]["fecha"]}</div>
<div class="big">{gap_nivel:+.0f}%</div>
<p class="sub">({gap:+.1f} puntos log)</p>
<div class="gauge"><i style="left:{max(2, min(94, 50 + gap / 2)):.0f}%;width:4%"></i><b></b></div>
<p class="sub">BTC {lado} vs su equilibrio · corrección {abs(r["ect"]["coef"]) * 100:.0f}%/mes · vida media {r["ect"]["half_life_m"]:.1f} meses</p></div>
<div class="card"><div class="lbl">COINTEGRACIÓN</div>
<div class="big mono">F = {r["boundsF"]:.2f}</div>
<span class="pill {"ok" if cointegra else "bad"}">{"SÍ · supera I(1) al 1%" if cointegra else "EN DUDA"}</span></div>
<div class="card"><div class="lbl">VELOCIDAD DE AJUSTE</div>
<div class="big mono">{r["ect"]["coef"]:.4f}</div>
<p class="sub">ECT, p = {r["ect"]["p"]:.4f}</p></div>
</div>
<div class="card"><div class="lbl">DMB OBSERVADO VS EQUILIBRIO</div><canvas id="c_gap"></canvas>
<p class="sub">— tramo ámbar: M2 provisional (nowcast)</p></div>
</section>
<section id="{_ancla(SECCIONES[1])}"><h2>Variables</h2>
<div class="card"><canvas id="c_vars"{oculto["vars"]}></canvas><p class="sub">DMB, MC2, MC1, RV12, UC — meses nowcast punteados en ámbar</p></div></section>
<section id="{_ancla(SECCIONES[2])}"><h2>Cointegración</h2>
<div class="card"><table><tr><th>Nivel</th><th class="num">I(0)</th><th class="num">I(1)</th><th class="num">F</th></tr>
{"".join(f'<tr><td>{n}</td><td class="num">{c[0]:.3f}</td><td class="num">{c[1]:.3f}</td><td class="num">{r["boundsF"]:.2f}</td></tr>' for n, c in r["crit"].items())}
</table><p class="sub">Caveat honesto: el RESET del 6D rechaza (p=0.008) — posible no linealidad; se reporta como limitación, igual que en la tesis.</p></div></section>
<section id="{_ancla(SECCIONES[3])}"><h2>Funciones del dinero</h2>
<div class="grid">{cards_fn}</div>
<div class="card"><table><tr><th>Variable</th><th class="num">Coef. LP</th><th class="num">p</th></tr>{filas_lr}</table></div></section>
<section id="{_ancla(SECCIONES[4])}"><h2>Hechos estilizados</h2>
<div class="grid"><div class="card"><div class="lbl">TRANSACCIONES / MES</div><canvas id="c_tx"{oculto["tx"]}></canvas></div>
<div class="card"><div class="lbl">OFERTA DE BTC</div><canvas id="c_supply"{oculto["supply"]}></canvas></div></div></section>
<section id="{_ancla(SECCIONES[5])}"><h2>Mercado</h2>
<div class="card" id="ticker"><div class="lbl">EN VIVO (navegador → CoinGecko)</div>
<p class="big mono" id="tk_price">—</p><p class="sub" id="tk_dom">al cargar esta página; si falla, últimos valores del build</p></div></section>
<section id="{_ancla(SECCIONES[6])}"><h2>Datos</h2>
<div class="card"><table><tr><th>Serie</th><th>Última fecha</th><th>Estado</th></tr>{filas_datos}</table>
<p class="sub">Fuentes: blockchain.info, Stooq, FRED (M2SL), CoinGecko, y semilla histórica de dominancia validada en la tesis. Código y datos: github.com/AlonzoBenz/BitcoinTerminal</p></div></section>
</main>
<footer>Generado {r["generated_at"]} · Modelo re-estimado con muestra {r["sample"][0]} → {r["sample"][1]} · Alonzo Niño Mendoza · Los meses sin M2 publicado no entran a la estimación.</footer>
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
    ejes = ('{plugins:{legend:{labels:{color:"#6e6656"}}},'
            'scales:{x:{ticks:{maxTicksLimit:8,color:"#a09681"}},'
            'y:{ticks:{color:"#a09681"}}}}')
    ejes_anios = ('{plugins:{legend:{display:false}},'
                  'scales:{x:{ticks:{maxTicksLimit:8,color:"#a09681",'
                  'callback:function(v){return this.getLabelForValue(v).slice(0,4);}}},'
                  'y:{ticks:{color:"#a09681"}}}}')
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
fetch("https://api.coingecko.com/api/v3/global").then(r => r.json()).then(g => {
  document.getElementById("tk_dom").textContent = "Dominancia BTC: " + g.data.market_cap_percentage.btc.toFixed(1) + "% · actualizado ahora";
  return fetch("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd");
}).then(r => r.json()).then(p => {
  document.getElementById("tk_price").textContent = "$" + p.bitcoin.usd.toLocaleString("en-US");
}).catch(() => {});
"""
    for tok, val in (("__R__", R), ("__NOWCAST__", NOWCAST), ("__S__", S),
                     ("__EJES__", ejes), ("__EJES_ANIOS__", ejes_anios),
                     ("__VARS_DS__", vars_ds)):
        js = js.replace(tok, val)
    return js
