import json, pathlib
from src import render

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_html_contiene_lo_esencial(tmp_path):
    results = json.loads((FIX / "results_demo.json").read_text()) \
        if (FIX / "results_demo.json").exists() else None
    assert results is not None, "generar fixtures/results_demo.json con estimate.run sobre el fixture (ver Task 9)"
    out = tmp_path / "index.html"
    render.render(results, freshness={"btc_price": {"status": "FRESCO", "last": "2026-07-07"}}, out=out)
    html = out.read_text()
    for frag in ("Fraunces", "chart.js", "BRECHA", f"{results['boundsF']:.2f}",
                 "id=\"ticker\"", "El modelo", "Funciones del dinero",
                 'integrity="sha384-', "puntos log", "spanGaps",
                 "og:title", 'rel="icon"', "c_price", "setInterval",
                 "Percentil", "EQUILIBRIO IMPLÍCITO", "BRECHA HISTÓRICA",
                 "No es pronóstico", "ROBUSTEZ DE LA ESPECIFICACIÓN",
                 "Último publicado", "Pesaran"):
        assert frag in html, frag


def test_degradacion_sin_datos(tmp_path):
    """Si monthly.csv (y por tanto data/raw junto a el) no existe, el grafico
    de Variables se degrada a oculto en vez de tronar (T10 review)."""
    results = json.loads((FIX / "results_demo.json").read_text())
    out = tmp_path / "index.html"
    render.render(results, {"btc_price": {"status": "FRESCO", "last": "2026-07-16"}},
                  out=out, monthly_csv=tmp_path / "no_existe.csv")
    html = out.read_text()
    assert 'style="display:none"><canvas id="c_vars"></canvas>' in html
