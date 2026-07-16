import json, pathlib
from src import estimate

FIX = pathlib.Path(__file__).parent / "fixtures" / "monthly_tesis.csv"


def test_results_json_estructura(tmp_path):
    out = tmp_path / "results.json"
    estimate.run(monthly_csv=FIX, out=out)
    r = json.loads(out.read_text())
    for k in ("boundsF", "crit", "ect", "lr", "n", "sample", "gap",
              "series", "generated_at", "alertas"):
        assert k in r, k
    assert r["boundsF"] > r["crit"]["1%"][1]          # cointegra al 1%
    assert r["ect"]["coef"] < 0
    assert len(r["series"]["fechas"]) == len(r["series"]["dmb"]) == len(r["series"]["dmb_star"])
