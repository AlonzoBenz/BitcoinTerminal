# BitcoinTerminal — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard público (GitHub Actions + Pages) que muestra el modelo ARDL "Bitcoin es dinero" (Calibrado 6D congelado) funcionando con datos actualizados semanalmente.

**Architecture:** Fetchers → CSV crudos commiteados (el repo es la base de datos) → base mensual validada contra el Excel de la tesis → estimación con pipeline vendored congelado → `results.json` → HTML estático → Pages. Un entrypoint (`python -m src.build --daily|--weekly`) corre idéntico en local y en Actions.

**Tech Stack:** Python 3.12, statsmodels 0.14.6 (versión validada vs EViews), pandas, requests, pytest; Chart.js por CDN; GitHub Actions cron + Pages.

**Working dir:** `/Users/alonzob/BitcoinTerminal` (repo `AlonzoBenz/BitcoinTerminal`, ya existe con spec commiteado). Secret `FRED_API_KEY` ya configurado. Spec: `docs/superpowers/specs/2026-07-07-bitcoin-terminal-design.md`.

**Regla transversal de seguridad:** ningún log, mensaje de error, test ni HTML imprime jamás la FRED key ni URLs con `api_key`. Los mensajes de error de HTTP truncan la URL en `?`.

---

### Task 1: Andamiaje del repo

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `src/__init__.py`, `src/fetchers/__init__.py`, `src/model/__init__.py`, `tests/__init__.py`, `data/raw/.gitkeep`, `site/.gitkeep`

- [ ] **Step 1: Crear estructura y requirements**

```bash
cd ~/BitcoinTerminal
mkdir -p src/fetchers src/model tests/fixtures data/raw site scripts
touch src/__init__.py src/fetchers/__init__.py src/model/__init__.py tests/__init__.py data/raw/.gitkeep site/.gitkeep
```

`requirements.txt`:
```
statsmodels==0.14.6
pandas==3.0.1
numpy==2.4.3
scipy>=1.14
requests>=2.32
openpyxl>=3.1
pytest>=8.0
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
addopts = -q
```

- [ ] **Step 2: Crear venv e instalar**

```bash
cd ~/BitcoinTerminal && python3.12 -m venv venv && venv/bin/pip install -r requirements.txt
```
Esperado: instala sin errores. Verificar: `venv/bin/python -c "import statsmodels; print(statsmodels.__version__)"` → `0.14.6`.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: andamiaje del repo (deps fijadas, estructura src/tests/data)"
```

---

### Task 2: Fixture congelado y números de referencia exactos

La muestra congelada de la tesis y sus resultados al máximo de precisión, capturados UNA vez desde `~/Tesis_Cap3`. Son la vara de todos los tests.

**Files:**
- Create: `scripts/exportar_fixture.py`, `tests/fixtures/monthly_tesis.csv`, `tests/fixtures/referencia_congelada.json`

- [ ] **Step 1: Escribir el exportador (corre con el venv de la TESIS, no el nuestro)**

`scripts/exportar_fixture.py`:
```python
"""Exporta la base mensual del Excel de la tesis y los resultados exactos
del Calibrado 6D. Correr con: cd ~/Tesis_Cap3 && venv/bin/python \
~/BitcoinTerminal/scripts/exportar_fixture.py"""
import json, sys, pathlib
sys.path.insert(0, "scripts")          # dataload/model de la tesis
from dataload import load
from model import fit

OUT = pathlib.Path.home() / "BitcoinTerminal" / "tests" / "fixtures"
df, v = load()
full = df.join(v[["DMB", "MC2", "MC1", "RV12", "UC"]], rsuffix="_v")
full.to_csv(OUT / "monthly_tesis.csv")

m = fit("6D")
ref = dict(
    boundsF=m["boundsF"], n=m["n"], r2adj=m["r2adj"], dw=m["dw"],
    aic=m["aic"], bic=m["bic"],
    ect=dict(coef=m["ect"]["coef"], p=m["ect"]["p"]),
    lr={k: dict(coef=d["coef"], p=d["p"]) for k, d in m["lr"].items()},
    sample=[str(m["sample"][0].date()), str(m["sample"][1].date())],
)
(OUT / "referencia_congelada.json").write_text(json.dumps(ref, indent=2))
print(json.dumps(ref, indent=2))
```

- [ ] **Step 2: Correrlo y verificar contra los números conocidos**

```bash
cd ~/Tesis_Cap3 && venv/bin/python ~/BitcoinTerminal/scripts/exportar_fixture.py
```
Esperado: imprime JSON con `boundsF≈44.09`, `ect.coef≈-0.2525`, `lr.MC2.coef≈1.114`, `lr.RV12.coef≈1.975`. Si difiere, DETENERSE: el pipeline de la tesis cambió y hay que investigar antes de seguir.

- [ ] **Step 3: Commit**

```bash
cd ~/BitcoinTerminal && git add scripts tests/fixtures && git commit -m "test: fixture congelado de la tesis + referencia exacta del Calibrado 6D"
```

---

### Task 3: Vendorizar el modelo congelado

**Files:**
- Create: `src/model/dataload.py`, `src/model/model.py`, `src/model/FROZEN.md`
- Test: `tests/test_estimate_frozen.py`

- [ ] **Step 1: Escribir el test que falla**

`tests/test_estimate_frozen.py`:
```python
"""Candado del congelado: src/model debe reproducir la tesis exactamente."""
import json, pathlib
import pytest
from src.model.model import fit

FIX = pathlib.Path(__file__).parent / "fixtures"
REF = json.loads((FIX / "referencia_congelada.json").read_text())


def test_calibrado_6d_reproduce_tesis():
    m = fit("6D", path=FIX / "monthly_tesis.csv")
    assert m["n"] == REF["n"]
    assert m["boundsF"] == pytest.approx(REF["boundsF"], abs=1e-4)
    assert m["ect"]["coef"] == pytest.approx(REF["ect"]["coef"], abs=1e-4)
    for x in ("MC2", "RV12", "UC"):
        assert m["lr"][x]["coef"] == pytest.approx(REF["lr"][x]["coef"], abs=1e-4)
        assert m["lr"][x]["p"] == pytest.approx(REF["lr"][x]["p"], abs=1e-4)
```

- [ ] **Step 2: Correr y verificar que falla**

```bash
cd ~/BitcoinTerminal && venv/bin/pytest tests/test_estimate_frozen.py -v
```
Esperado: FAIL (`No module named 'src.model.model'` o similar).

- [ ] **Step 3: Vendorizar**

Copiar y adaptar SOLO la E/S (la especificación no se toca):

```bash
cp ~/Tesis_Cap3/scripts/model.py src/model/model.py
```

`src/model/dataload.py` (reescrito para CSV; dummies idénticas):
```python
"""Carga de la base mensual desde CSV. Vendored de ~/Tesis_Cap3 —
la unica adaptacion permitida vs el original es la E/S (Excel -> CSV)."""
import pandas as pd

DUMMY_DATES = {
    "D1_2021_01": "2021-01-01", "D2_2021_06": "2021-06-01",
    "D3_2022_01": "2022-01-01", "D4_2022_05": "2022-05-01",
    "D5_2022_06": "2022-06-01", "D6_2022_11": "2022-11-01",
    "D7_2025_12": "2025-12-01", "D8_2016_01": "2016-01-01",
}
DUMMIES = ["D1_2021_01", "D2_2021_06", "D3_2022_01",
           "D4_2022_05", "D5_2022_06", "D6_2022_11"]
DUMMIES8 = DUMMIES + ["D7_2025_12", "D8_2016_01"]


def load(path="data/monthly.csv"):
    df = pd.read_csv(path, parse_dates=["Fecha"], index_col="Fecha").sort_index()
    v = df[["DMB", "MC2", "MC1", "RV12", "UC"]].copy()
    for name, fecha in DUMMY_DATES.items():
        v[name] = (v.index == pd.Timestamp(fecha)).astype(float)
    return df, v
```

En `src/model/model.py` hacer exactamente 3 cambios de E/S:
1. `from dataload import load, DUMMIES, DUMMIES8` → `from src.model.dataload import load, DUMMIES, DUMMIES8`
2. `def fit(which="6D"):` → `def fit(which="6D", path="data/monthly.csv"):` y dentro `df, v = load()` → `df, v = load(path)`
3. En `design_matrix(m)`: firma → `def design_matrix(m, path="data/monthly.csv"):` y `df, v = load()` → `df, v = load(path)`

`src/model/FROZEN.md`:
```markdown
# Pipeline congelado — NO TOCAR
Origen: ~/Tesis_Cap3/scripts/{model.py,dataload.py} (Calibrado 6D de la tesis).
Fecha de copia: 2026-07-07.
Adaptaciones permitidas: SOLO E/S (lee CSV en vez de Excel, imports absolutos).
La especificación (ARDL(12,12,1,1), caso 5, 6 dummies, Wald manual, método
delta) es inmutable. El candado es tests/test_estimate_frozen.py: si un cambio
altera resultados al 4º decimal, CI truena y no se publica.
```

- [ ] **Step 4: Correr el test y verificar que pasa**

```bash
venv/bin/pytest tests/test_estimate_frozen.py -v
```
Esperado: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/model tests/test_estimate_frozen.py && git commit -m "feat: modelo Calibrado 6D vendorizado + candado test_estimate_frozen"
```

---

### Task 4: Cliente HTTP con reintentos

**Files:**
- Create: `src/fetchers/http.py`
- Test: `tests/test_http.py`

- [ ] **Step 1: Test que falla**

`tests/test_http.py`:
```python
import pytest
import src.fetchers.http as http


class FakeResp:
    def __init__(self, js): self._js = js
    def raise_for_status(self): pass
    def json(self): return self._js
    @property
    def text(self): return "ok"


def test_reintenta_y_devuelve(monkeypatch):
    calls = {"n": 0}
    def fake_get(url, **kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("boom")
        return FakeResp({"ok": True})
    monkeypatch.setattr(http.requests, "get", fake_get)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    assert http.get("https://x.test/api") == {"ok": True}
    assert calls["n"] == 3


def test_error_no_incluye_query(monkeypatch):
    def fake_get(url, **kw): raise ConnectionError("boom")
    monkeypatch.setattr(http.requests, "get", fake_get)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError) as e:
        http.get("https://x.test/api?api_key=SECRETO")
    assert "SECRETO" not in str(e.value)
```

- [ ] **Step 2: Verificar que falla**

`venv/bin/pytest tests/test_http.py -v` → FAIL (módulo no existe).

- [ ] **Step 3: Implementar**

`src/fetchers/http.py`:
```python
"""GET con reintentos y backoff. Los errores NUNCA incluyen query strings
(ahí viven las API keys)."""
import time
import requests

UA = {"User-Agent": "BitcoinTerminal/1.0 (uso academico)"}
BACKOFF = [2, 8, 30]


def get(url, params=None, as_json=True, timeout=30):
    last = None
    for wait in [0] + BACKOFF:
        if wait:
            time.sleep(wait)
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            r.raise_for_status()
            return r.json() if as_json else r.text
        except Exception as e:
            last = e
    base = url.split("?")[0]
    raise RuntimeError(f"GET {base} fallo tras {len(BACKOFF) + 1} intentos: {type(last).__name__}")
```

- [ ] **Step 4: Verificar que pasa** — `venv/bin/pytest tests/test_http.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add src/fetchers/http.py tests/test_http.py && git commit -m "feat: cliente http con reintentos y errores sin secretos"`

---

### Task 5: Fetchers de histórico completo

Cada fetcher separa `fetch()` (red) de `parse()` (puro, testeable). Todos devuelven `pd.DataFrame` con columnas `date` (datetime64) y `value` (float), y se persisten con `save()`.

**Files:**
- Create: `src/fetchers/base.py`, `src/fetchers/blockchain_info.py`, `src/fetchers/stooq.py`, `src/fetchers/fred.py`, `src/fetchers/coingecko.py`
- Test: `tests/test_fetchers.py`

- [ ] **Step 1: Tests que fallan**

`tests/test_fetchers.py`:
```python
import pandas as pd
from src.fetchers import blockchain_info, stooq, fred, coingecko


def test_parse_blockchain_info():
    js = {"values": [{"x": 1420070400, "y": 263.52}, {"x": 1420156800, "y": 264.1}]}
    df = blockchain_info.parse(js)
    assert list(df.columns) == ["date", "value"]
    assert df.iloc[0]["value"] == 263.52
    assert df.iloc[0]["date"] == pd.Timestamp("2015-01-01")


def test_parse_stooq():
    txt = "Date,Open,High,Low,Close,Volume\n2015-01-02,1184.0,1194.5,1180.0,1189.0,0\n"
    df = stooq.parse(txt)
    assert df.iloc[0]["value"] == 1189.0


def test_parse_fred_ignora_faltantes():
    js = {"observations": [{"date": "2015-01-01", "value": "11805200.0"},
                           {"date": "2015-02-01", "value": "."}]}
    df = fred.parse(js)
    assert len(df) == 1 and df.iloc[0]["value"] == 11805200.0


def test_parse_coingecko_global():
    js = {"data": {"market_cap_percentage": {"btc": 58.3},
                   "total_market_cap": {"usd": 3.1e12}}}
    spot = coingecko.parse_global(js)
    assert spot["dominance_pct"] == 58.3
```

- [ ] **Step 2: Verificar que fallan** — `venv/bin/pytest tests/test_fetchers.py -v` → FAIL.

- [ ] **Step 3: Implementar**

`src/fetchers/base.py`:
```python
import pathlib
import pandas as pd

RAW = pathlib.Path("data/raw")


def save(name, df):
    RAW.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW / f"{name}.csv", index=False)


def load(name):
    p = RAW / f"{name}.csv"
    if not p.exists():
        return None
    return pd.read_csv(p, parse_dates=["date"])
```

`src/fetchers/blockchain_info.py`:
```python
import pandas as pd
from src.fetchers import http

CHARTS = {
    "btc_price": "market-price",
    "btc_supply": "total-bitcoins",
    "tx_volume_usd": "estimated-transaction-volume-usd",
    "tx_count": "n-transactions",
    "difficulty": "difficulty",
    "fees_btc": "transaction-fees",
}


def parse(js):
    df = pd.DataFrame(js["values"]).rename(columns={"x": "date", "y": "value"})
    df["date"] = pd.to_datetime(df["date"], unit="s")
    return df[["date", "value"]]


def fetch(key):
    js = http.get(f"https://api.blockchain.info/charts/{CHARTS[key]}",
                  params={"timespan": "all", "format": "json", "sampled": "false"})
    return parse(js)
```

`src/fetchers/stooq.py`:
```python
import io
import pandas as pd
from src.fetchers import http


def parse(txt):
    df = pd.read_csv(io.StringIO(txt), parse_dates=["Date"])
    df = df.rename(columns={"Date": "date", "Close": "value"})
    return df[["date", "value"]].dropna()


def fetch():
    txt = http.get("https://stooq.com/q/d/l/", params={"s": "xauusd", "i": "d"},
                   as_json=False)
    return parse(txt)
```

`src/fetchers/fred.py`:
```python
import os
import pandas as pd
from src.fetchers import http


def parse(js):
    rows = [(o["date"], float(o["value"]))
            for o in js["observations"] if o["value"] != "."]
    df = pd.DataFrame(rows, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch(series="M2SL"):
    key = os.environ["FRED_API_KEY"]      # nunca se loggea; http.get trunca en '?'
    js = http.get("https://api.stlouisfed.org/fred/series/observations",
                  params={"series_id": series, "api_key": key, "file_type": "json"})
    return parse(js)
```

`src/fetchers/coingecko.py`:
```python
from src.fetchers import http


def parse_global(js):
    d = js["data"]
    return {"dominance_pct": float(d["market_cap_percentage"]["btc"]),
            "total_mcap_usd": float(d["total_market_cap"]["usd"])}


def fetch_global():
    return parse_global(http.get("https://api.coingecko.com/api/v3/global"))
```

- [ ] **Step 4: Verificar que pasan** — `venv/bin/pytest tests/test_fetchers.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add src/fetchers tests/test_fetchers.py && git commit -m "feat: fetchers blockchain.info/stooq/fred/coingecko con parse puro testeable"`

---

### Task 6: Dominancia — semilla histórica + acumulación diaria

Diseño del spec §4: el pasado viene del Excel (validado); el futuro se acumula un renglón diario desde CoinGecko.

**Files:**
- Create: `scripts/exportar_semilla_dominancia.py`, `data/raw/btc_dominance_seed.csv`, `src/fetchers/dominance.py`
- Test: `tests/test_dominance.py`

- [ ] **Step 1: Exportar la semilla (corre con el venv de la tesis)**

`scripts/exportar_semilla_dominancia.py`:
```python
"""Semilla mensual de dominancia desde el Excel de la tesis.
Correr: cd ~/Tesis_Cap3 && venv/bin/python este_script"""
import sys, pathlib
sys.path.insert(0, "scripts")
from dataload import load

df, _ = load()
out = df[["BTC_dominance_pct"]].reset_index()
out.columns = ["date", "value"]
out.to_csv(pathlib.Path.home() / "BitcoinTerminal" / "data" / "raw" / "btc_dominance_seed.csv", index=False)
print(out.tail(3))
```
Correr y verificar que el último renglón es 2026-03-01.

- [ ] **Step 2: Test que falla**

`tests/test_dominance.py`:
```python
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
```

- [ ] **Step 3: Verificar que falla** — `venv/bin/pytest tests/test_dominance.py -v` → FAIL.

- [ ] **Step 4: Implementar**

`src/fetchers/dominance.py`:
```python
"""Dominancia BTC: semilla mensual congelada (Excel de la tesis, 2015-2026M03)
+ acumulacion diaria desde CoinGecko para los meses posteriores."""
import datetime as dt
import pathlib
import pandas as pd
from src.fetchers import coingecko

SEED = pathlib.Path("data/raw/btc_dominance_seed.csv")
DAILY = pathlib.Path("data/raw/btc_dominance_daily.csv")


def hoy_dominancia():
    return coingecko.fetch_global()["dominance_pct"]


def append_today():
    today = dt.date.today().isoformat()
    if DAILY.exists():
        df = pd.read_csv(DAILY, dtype={"date": str})
        if (df["date"] == today).any():
            return False
    else:
        df = pd.DataFrame(columns=["date", "value"])
    df.loc[len(df)] = [today, hoy_dominancia()]
    DAILY.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DAILY, index=False)
    return True


def monthly_series():
    seed = pd.read_csv(SEED, parse_dates=["date"]).set_index("date")["value"]
    seed.index = seed.index.to_period("M").to_timestamp()
    out = seed.copy()
    if DAILY.exists():
        d = pd.read_csv(DAILY, parse_dates=["date"]).set_index("date")["value"]
        m = d.resample("MS").mean()
        m = m[m.index > seed.index.max()]      # la semilla es inmutable
        out = pd.concat([out, m])
    return out.sort_index()
```

- [ ] **Step 5: Verificar que pasa** — `venv/bin/pytest tests/test_dominance.py -v` → PASS.

- [ ] **Step 6: Commit** — `git add scripts/exportar_semilla_dominancia.py data/raw/btc_dominance_seed.csv src/fetchers/dominance.py tests/test_dominance.py && git commit -m "feat: dominancia BTC con semilla congelada + acumulacion diaria"`

---

### Task 7: Puertas de sanidad y contrato de frescura

**Files:**
- Create: `src/sanity.py`
- Test: `tests/test_sanity.py`

- [ ] **Step 1: Tests que fallan**

`tests/test_sanity.py`:
```python
import pandas as pd
import src.sanity as sanity


def _df(vals, start="2020-01-01"):
    return pd.DataFrame({"date": pd.date_range(start, periods=len(vals)), "value": vals})


def test_rechaza_negativos():
    ok, why = sanity.check("btc_price", _df([100.0, -5.0, 101.0]))
    assert not ok and "negativ" in why


def test_rechaza_salto_absurdo_vs_previa():
    prev = _df([100.0] * 10)
    new = _df([100.0] * 9 + [900.0])
    ok, why = sanity.check("btc_price", new, prev)
    assert not ok and "salto" in why


def test_acepta_serie_normal():
    ok, _ = sanity.check("btc_price", _df([100.0, 101.5, 99.8]))
    assert ok


def test_frescura():
    assert sanity.freshness_status("m2sl", age_days=30) == "FRESCO"
    assert sanity.freshness_status("m2sl", age_days=60) == "STALE"
    assert sanity.freshness_status("btc_price", age_days=200) == "DEAD"
```

- [ ] **Step 2: Verificar que fallan** — `venv/bin/pytest tests/test_sanity.py -v` → FAIL.

- [ ] **Step 3: Implementar**

`src/sanity.py`:
```python
"""Puertas de sanidad (spec §6.2) y contrato de frescura (§6.3).
Serie insana => se conserva el ultimo CSV bueno y se marca SUSPECT."""

MAX_JUMP = 4.0          # ratio max ultimo valor vs mediana de los 30 previos
POSITIVE = {"btc_price", "btc_supply", "tx_volume_usd", "tx_count",
            "gold_price", "m2sl", "difficulty", "fees_btc"}
MAX_AGE_DAYS = {"m2sl": 45}          # default 3 para series diarias
DEFAULT_MAX_AGE = 3


def check(name, df, prev=None):
    if df is None or len(df) == 0:
        return False, "serie vacia"
    if df["value"].isna().mean() > 0.05:
        return False, "mas de 5% de NaN"
    if name in POSITIVE and (df["value"].dropna() <= 0).any():
        return False, "valores negativos o cero en serie positiva"
    if prev is not None and len(prev) >= 10:
        base = float(prev["value"].tail(30).median())
        last = float(df["value"].iloc[-1])
        if base > 0 and not (1 / MAX_JUMP <= last / base <= MAX_JUMP):
            return False, f"salto de nivel absurdo vs corrida previa ({last:.4g} vs mediana {base:.4g})"
    return True, "ok"


def freshness_status(name, age_days):
    limit = MAX_AGE_DAYS.get(name, DEFAULT_MAX_AGE)
    if age_days <= limit:
        return "FRESCO"
    if age_days <= 3 * limit:
        return "STALE"
    return "DEAD"
```

- [ ] **Step 4: Verificar que pasan** — `venv/bin/pytest tests/test_sanity.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add src/sanity.py tests/test_sanity.py && git commit -m "feat: puertas de sanidad y contrato de frescura por serie"`

---

### Task 8: Base mensual — descubrir reglas de agregación y validar contra el Excel

El paso más delicado del proyecto (spec §4). Primero arqueología con datos reales, luego se fijan las reglas y el test las protege.

**Files:**
- Create: `scripts/descubrir_agregacion.py`, `src/monthly.py`
- Test: `tests/test_monthly_vs_excel.py`

- [ ] **Step 1: Descargar crudos reales una vez (manual, local)**

```bash
cd ~/BitcoinTerminal && venv/bin/python - <<'EOF'
from src.fetchers import blockchain_info, stooq, fred, base
for k in blockchain_info.CHARTS:
    base.save(k, blockchain_info.fetch(k))
    print("ok", k)
base.save("gold_price", stooq.fetch())
import os
base.save("m2sl", fred.fetch())      # requiere: export FRED_API_KEY=$(grep FRED .env | cut -d= -f2)
print("ok gold, m2sl")
EOF
```
Antes: `export FRED_API_KEY=$(grep FRED_API_KEY .env | cut -d= -f2)`. Esperado: 8 CSV en `data/raw/`.

- [ ] **Step 2: Script de arqueología**

`scripts/descubrir_agregacion.py`:
```python
"""Compara reglas candidatas de agregacion diaria->mensual contra las columnas
del Excel de la tesis. Imprime la regla ganadora y su error relativo maximo."""
import pandas as pd
from src.fetchers import base

FIX = pd.read_csv("tests/fixtures/monthly_tesis.csv", parse_dates=["Fecha"], index_col="Fecha")
PARES = [                     # (serie_cruda, columna_excel)
    ("btc_price", "BTC_price"), ("btc_supply", "BTC_supply"),
    ("tx_volume_usd", None),   # nombre truncado: detectar con startswith
    ("tx_count", "TxTfrCnt_daily_avg"), ("gold_price", "Gold_price"),
]
REGLAS = {"mean": lambda s: s.mean(), "last": lambda s: s.last("D").iloc[-1] if len(s) else float("nan"),
          "sum": lambda s: s.sum(), "first": lambda s: s.iloc[0] if len(s) else float("nan")}

for raw_name, col in PARES:
    if col is None:
        col = [c for c in FIX.columns if c.startswith("TxVolumeUSD")][0]
    raw = base.load(raw_name).set_index("date")["value"]
    print(f"\n== {raw_name} vs {col} ==")
    for regla, fn in REGLAS.items():
        m = raw.resample("MS").apply(fn)
        j = pd.concat([m, FIX[col]], axis=1, join="inner").dropna()
        err = (j.iloc[:, 0] / j.iloc[:, 1] - 1).abs().max()
        print(f"  {regla:6s} err_rel_max = {err:.6%}")
```

Correr: `venv/bin/python scripts/descubrir_agregacion.py`. Anotar la regla ganadora (err mínimo) por serie.

- [ ] **Step 3: Test que falla**

`tests/test_monthly_vs_excel.py`:
```python
"""El test que bloquea todo (spec §7.1): la base reconstruida desde APIs
empata con el Excel de la tesis al 0.1% relativo por celda."""
import pathlib
import pandas as pd
import pytest
from src import monthly

FIX = pathlib.Path(__file__).parent / "fixtures" / "monthly_tesis.csv"
RAW_OK = pathlib.Path("data/raw/btc_price.csv").exists()

# Tolerancias por serie; ampliar SOLO con justificacion escrita aqui (spec §7.1).
TOL = {"DMB": 0.001, "MC2": 0.001, "MC1": 0.001, "RV12": 0.001, "UC": 0.001}


@pytest.mark.skipif(not RAW_OK, reason="requiere data/raw poblado (fetch previo)")
def test_base_reconstruida_empata_con_excel():
    ref = pd.read_csv(FIX, parse_dates=["Fecha"], index_col="Fecha")
    got = monthly.build()
    j = got.join(ref, how="inner", rsuffix="_ref").dropna()
    assert len(j) >= 120, "traslape insuficiente con la muestra de la tesis"
    for col, tol in TOL.items():
        err = (j[col] - j[f"{col}_ref"]).abs().max()
        assert err < tol, f"{col}: error absoluto max {err:.6f} >= {tol}"
```
(Las variables del modelo son logs/logits: comparar en niveles absolutos ≈ error relativo de la serie original; 0.001 en log ≈ 0.1%.)

- [ ] **Step 4: Verificar que falla** — `venv/bin/pytest tests/test_monthly_vs_excel.py -v` → FAIL (no existe `src.monthly`).

- [ ] **Step 5: Implementar con las reglas descubiertas**

`src/monthly.py` (las claves de `AGG` se ajustan con el resultado REAL del Step 2; abajo la hipótesis inicial `mean`):
```python
"""Base mensual del modelo desde los crudos. Reglas de agregacion fijadas por
scripts/descubrir_agregacion.py contra el Excel de la tesis (ver test)."""
import numpy as np
import pandas as pd
from src.fetchers import base, dominance

AGG = {"btc_price": "mean", "btc_supply": "mean", "tx_volume_usd": "mean",
       "tx_count": "mean", "gold_price": "mean"}


def _monthly(name):
    s = base.load(name).set_index("date")["value"]
    return s.resample("MS").agg(AGG[name])


def build(start="2013-01-01"):
    price, supply = _monthly("btc_price"), _monthly("btc_supply")
    txvol, txcnt = _monthly("tx_volume_usd"), _monthly("tx_count")
    gold = _monthly("gold_price")
    m2 = base.load("m2sl").set_index("date")["value"]
    m2.index = m2.index.to_period("M").to_timestamp()
    dom = dominance.monthly_series()

    idx = price.loc[start:].index
    df = pd.DataFrame(index=idx)
    df.index.name = "Fecha"
    df["BTC_price"], df["BTC_supply"] = price, supply
    df["MarketCapBTC_USD"] = price * supply
    df["M2SL_USD"] = m2 * 1e6            # FRED reporta en miles de millones? -> VERIFICAR
    df["m2_published"] = df["M2SL_USD"].notna()
    df["M2SL_USD"] = df["M2SL_USD"].ffill()     # nowcast: ultimo publicado
    df["TxVolumeUSD"], df["TxTfrCnt"], df["Gold_price"] = txvol, txcnt, gold
    df["Dominance_dec"] = (dom / 100.0).clip(1e-6, 1 - 1e-6)

    df["DMB"] = np.log(df["MarketCapBTC_USD"] / df["M2SL_USD"])
    df["MC2"] = np.log(df["TxVolumeUSD"] / df["M2SL_USD"])
    df["MC1"] = np.log(df["TxTfrCnt"] / df["BTC_supply"])
    df["RV12"] = (np.log(df["BTC_price"] / df["BTC_price"].shift(12))
                  - np.log(df["Gold_price"] / df["Gold_price"].shift(12)))
    df["UC"] = np.log(df["Dominance_dec"] / (1 - df["Dominance_dec"]))
    return df.loc["2015-01-01":]


def write(path="data/monthly.csv"):
    df = build()
    df.to_csv(path)
    return df
```

**Nota crítica sobre `M2SL_USD`:** el Excel trae `11805200000000` (11.8 billones USD) para 2015-01; FRED M2SL reporta 11805.2 (miles de millones). El factor es `1e9`, no `1e6` — el Step 2/6 lo confirma empíricamente; ajustar la línea y dejar comentario con la unidad verificada. Igual con `RV12`: si el error excede tolerancia, probar variante con niveles (`log(price/gold)` vs momentum) — la fórmula ganadora se fija aquí y el test la protege.

- [ ] **Step 6: Iterar hasta que el test pase**

```bash
venv/bin/pytest tests/test_monthly_vs_excel.py -v
```
Esperado tras ajustar unidades/reglas con la evidencia del Step 2: PASS. Si una serie no baja de tolerancia por *vintage* (blockchain.info revisa histórico), documentar en `TOL` la ampliación con una línea de justificación (spec §7.1).

- [ ] **Step 7: Commit**

```bash
git add scripts/descubrir_agregacion.py src/monthly.py tests/test_monthly_vs_excel.py data/raw
git commit -m "feat: base mensual validada contra el Excel de la tesis (test bloqueante)"
```

---

### Task 9: Estimación → results.json

**Files:**
- Create: `src/estimate.py`
- Test: `tests/test_estimate_json.py`

- [ ] **Step 1: Test que falla**

`tests/test_estimate_json.py`:
```python
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
```

- [ ] **Step 2: Verificar que falla** — `venv/bin/pytest tests/test_estimate_json.py -v` → FAIL.

- [ ] **Step 3: Implementar**

`src/estimate.py`:
```python
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

    r = dict(
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        n=m["n"], r2adj=m["r2adj"], dw=m["dw"], boundsF=m["boundsF"], crit=CRIT,
        sample=[str(m["sample"][0].date()), str(m["sample"][1].date())],
        ect=dict(coef=m["ect"]["coef"], p=m["ect"]["p"],
                 half_life_m=float(np.log(0.5) / np.log(1 + m["ect"]["coef"]))),
        lr={k: dict(coef=d["coef"], p=d["p"], stars=stars(d["p"])) for k, d in m["lr"].items()},
        gap=dict(hoy=float(gap.iloc[-1]), fecha=str(df.index[-1].date())),
        series=dict(fechas=[str(d.date()) for d in df.index],
                    dmb=[round(x, 4) for x in df["DMB"]],
                    dmb_star=[round(float(x), 4) for x in dmb_star],
                    nowcast=[bool(not v) for v in df.get("m2_published", pd.Series(True, index=df.index))]),
        alertas=alertas,
    )
    pathlib.Path(out).write_text(json.dumps(r, indent=1))
    return r
```

- [ ] **Step 4: Verificar que pasa** — `venv/bin/pytest tests/test_estimate_json.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add src/estimate.py tests/test_estimate_json.py && git commit -m "feat: estimacion semanal -> results.json con brecha, alertas y series"`

---

### Task 10: Render del dashboard

v1 funcional con la identidad del spec §5 (crema `#faf6ec`, naranja `#f7931a`, Fraunces + IBM Plex Mono + Inter, nav superior, 7 secciones apiladas con anclas). El refinamiento fino es iteración posterior (spec §8).

**Files:**
- Create: `src/render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Test que falla**

`tests/test_render.py`:
```python
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
                 "id=\"ticker\"", "El modelo", "Funciones del dinero"):
        assert frag in html, frag
```
Generar el fixture una vez: `venv/bin/python -c "from src import estimate; estimate.run('tests/fixtures/monthly_tesis.csv','tests/fixtures/results_demo.json')"`.

- [ ] **Step 2: Verificar que falla** — `venv/bin/pytest tests/test_render.py -v` → FAIL.

- [ ] **Step 3: Implementar**

`src/render.py` (completo; plantilla f-string, un archivo, sin dependencias):
```python
"""results.json + frescura -> site/index.html (estatico, autocontenido salvo
CDN de Chart.js y Google Fonts)."""
import json
import pathlib

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


def _ancla(s):
    return s.lower().replace(" ", "-").replace("ó", "o")


def render(r, freshness, out="site/index.html", monthly_csv="data/monthly.csv"):
    gap = r["gap"]["hoy"]
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
<div class="big">{gap:+.1f}%</div>
<div class="gauge"><i style="left:{max(2, min(94, 50 + gap / 2)):.0f}%;width:4%"></i><b></b></div>
<p class="sub">BTC {lado} vs su equilibrio · corrección {abs(r["ect"]["coef"]) * 100:.0f}%/mes · vida media {r["ect"]["half_life_m"]:.1f} meses</p></div>
<div class="card"><div class="lbl">COINTEGRACIÓN</div>
<div class="big mono">F = {r["boundsF"]:.2f}</div>
<span class="pill {"ok" if cointegra else "bad"}">{"SÍ · supera I(1) al 1%" if cointegra else "EN DUDA"}</span></div>
<div class="card"><div class="lbl">VELOCIDAD DE AJUSTE</div>
<div class="big mono">{r["ect"]["coef"]:.4f}</div>
<p class="sub">ECT, p = {r["ect"]["p"]:.4f}</p></div>
</div>
<div class="card"><div class="lbl">DMB OBSERVADO VS EQUILIBRIO</div><canvas id="c_gap"></canvas></div>
</section>
<section id="{_ancla(SECCIONES[1])}"><h2>Variables</h2>
<div class="card"><canvas id="c_vars"></canvas><p class="sub">DMB, MC2, MC1, RV12, UC — meses nowcast punteados en ámbar</p></div></section>
<section id="{_ancla(SECCIONES[2])}"><h2>Cointegración</h2>
<div class="card"><table><tr><th>Nivel</th><th class="num">I(0)</th><th class="num">I(1)</th><th class="num">F</th></tr>
{"".join(f'<tr><td>{n}</td><td class="num">{c[0]:.3f}</td><td class="num">{c[1]:.3f}</td><td class="num">{r["boundsF"]:.2f}</td></tr>' for n, c in r["crit"].items())}
</table><p class="sub">Caveat honesto: el RESET del 6D rechaza (p=0.008) — posible no linealidad; se reporta como limitación, igual que en la tesis.</p></div></section>
<section id="{_ancla(SECCIONES[3])}"><h2>Funciones del dinero</h2>
<div class="grid">{cards_fn}</div>
<div class="card"><table><tr><th>Variable</th><th class="num">Coef. LP</th><th class="num">p</th></tr>{filas_lr}</table></div></section>
<section id="{_ancla(SECCIONES[4])}"><h2>Hechos estilizados</h2>
<div class="grid"><div class="card"><div class="lbl">TRANSACCIONES / MES</div><canvas id="c_tx"></canvas></div>
<div class="card"><div class="lbl">OFERTA DE BTC</div><canvas id="c_supply"></canvas></div></div></section>
<section id="{_ancla(SECCIONES[5])}"><h2>Mercado</h2>
<div class="card" id="ticker"><div class="lbl">EN VIVO (navegador → CoinGecko)</div>
<p class="big mono" id="tk_price">—</p><p class="sub" id="tk_dom">al cargar esta página; si falla, últimos valores del build</p></div></section>
<section id="{_ancla(SECCIONES[6])}"><h2>Datos</h2>
<div class="card"><table><tr><th>Serie</th><th>Última fecha</th><th>Estado</th></tr>{filas_datos}</table>
<p class="sub">Fuentes: blockchain.info, Stooq, FRED (M2SL), CoinGecko, y semilla histórica de dominancia validada en la tesis. Código y datos: github.com/AlonzoBenz/BitcoinTerminal</p></div></section>
</main>
<footer>Generado {r["generated_at"]} · Modelo re-estimado con muestra {r["sample"][0]} → {r["sample"][1]} · Alonzo Niño Mendoza · Los meses sin M2 publicado no entran a la estimación.</footer>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js" integrity="{CHARTJS_SRI}" crossorigin="anonymous"></script>
<script>
const R = {json.dumps(dict(fechas=r["series"]["fechas"], dmb=r["series"]["dmb"], dmb_star=r["series"]["dmb_star"], nowcast=r["series"]["nowcast"]))};
new Chart(document.getElementById("c_gap"), {{type: "line", data: {{labels: R.fechas,
 datasets: [{{label: "DMB observado", data: R.dmb, borderColor: "#f7931a", pointRadius: 0, borderWidth: 2}},
            {{label: "DMB* equilibrio", data: R.dmb_star, borderColor: "#a09681", borderDash: [5, 4], pointRadius: 0, borderWidth: 1.5}}]}},
 options: {{plugins: {{legend: {{labels: {{color: "#6e6656"}}}}}}, scales: {{x: {{ticks: {{maxTicksLimit: 8, color: "#a09681"}}}}, y: {{ticks: {{color: "#a09681"}}}}}}}}}});
fetch("https://api.coingecko.com/api/v3/global").then(r => r.json()).then(g => {{
  document.getElementById("tk_dom").textContent = "Dominancia BTC: " + g.data.market_cap_percentage.btc.toFixed(1) + "% · actualizado ahora";
  return fetch("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd");
}}).then(r => r.json()).then(p => {{
  document.getElementById("tk_price").textContent = "$" + p.bitcoin.usd.toLocaleString("en-US");
}}).catch(() => {{}});
</script></body></html>"""
    out = pathlib.Path(out)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(html)
    tmp.replace(out)          # publicacion atomica del archivo
    return out
```
(Las gráficas `c_vars`, `c_tx`, `c_supply` se alimentan igual que `c_gap` — al implementar, añadir sus datasets desde `monthly.csv` y `data/raw/` en el mismo bloque `<script>`; si en v1 quedan vacías, dejar los `canvas` ocultos con `style="display:none"` y anotarlo como iteración de diseño, spec §8.)

**SRI obligatorio (seguridad):** `{CHARTJS_SRI}` es una constante en `render.py` con el hash real de la versión fijada. Calcularlo una vez al implementar:
```bash
curl -s https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js | openssl dgst -sha384 -binary | openssl base64 -A
# -> pegar como CHARTJS_SRI = "sha384-<salida>"
```
y añadir al test de render: `assert 'integrity="sha384-' in html`. Sin SRI, un CDN comprometido podría inyectar JS en la página de la defensa. (Google Fonts queda sin SRI: sus CSS varían por navegador y no lo permiten; riesgo aceptado y documentado aquí.)

- [ ] **Step 4: Verificar que pasa** — `venv/bin/pytest tests/test_render.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add src/render.py tests/test_render.py tests/fixtures/results_demo.json && git commit -m "feat: dashboard v1 estilo papel crema/naranja con ticker en vivo"`

---

### Task 11: Entrypoint `build.py` (atómico, tolerante a fallas)

**Files:**
- Create: `src/build.py`, `src/__main__.py` no — se invoca `python -m src.build`
- Test: `tests/test_build.py`

- [ ] **Step 1: Test que falla**

`tests/test_build.py`:
```python
import src.build as build


def test_fetch_con_falla_conserva_csv_previo(tmp_path, monkeypatch):
    import pandas as pd
    from src.fetchers import base
    monkeypatch.setattr(base, "RAW", tmp_path)
    prev = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=40),
                         "value": [100.0] * 40})
    base.save("btc_price", prev)

    def boom(key): raise RuntimeError("api caida")
    monkeypatch.setitem(build.FETCHES, "btc_price", boom)
    fresh = build.fetch_all()
    assert fresh["btc_price"]["status"] in ("STALE", "SUSPECT", "DEAD", "FRESCO")
    assert len(base.load("btc_price")) == 40          # el CSV previo sobrevive
```

- [ ] **Step 2: Verificar que falla** — `venv/bin/pytest tests/test_build.py -v` → FAIL.

- [ ] **Step 3: Implementar**

`src/build.py`:
```python
"""Entrypoint unico (spec §3): python -m src.build --daily | --weekly.
--daily  : fetch + frescura + re-render (sin re-estimar)
--weekly : lo anterior + re-estimacion Calibrado 6D
Regla madre: nunca publicar pagina rota; mejor vieja con fecha honesta."""
import argparse
import datetime as dt
import json
import pathlib
import sys
from src import sanity, monthly, estimate, render
from src.fetchers import base, blockchain_info, stooq, fred, dominance

FETCHES = {k: (lambda k=k: blockchain_info.fetch(k)) for k in blockchain_info.CHARTS}
FETCHES["gold_price"] = stooq.fetch
FETCHES["m2sl"] = fred.fetch
FRESH_PATH = pathlib.Path("data/freshness.json")


def fetch_all():
    fresh = {}
    for name, fn in FETCHES.items():
        prev = base.load(name)
        status = None
        try:
            df = fn()
            ok, why = sanity.check(name, df, prev)
            if ok:
                base.save(name, df)
            else:
                print(f"[sanity] {name}: {why} -> se conserva CSV previo", file=sys.stderr)
                status = "SUSPECT"
        except Exception as e:
            print(f"[fetch] {name}: {e} -> se conserva CSV previo", file=sys.stderr)
        cur = base.load(name)
        if cur is None or len(cur) == 0:
            fresh[name] = {"status": "DEAD", "last": "—"}
            continue
        last = cur["date"].max()
        age = (dt.datetime.now() - last).days
        fresh[name] = {"status": status or sanity.freshness_status(name, age),
                       "last": str(last.date())}
    try:
        dominance.append_today()
        fresh["btc_dominance"] = {"status": "FRESCO", "last": dt.date.today().isoformat()}
    except Exception as e:
        print(f"[fetch] dominancia: {e}", file=sys.stderr)
        fresh["btc_dominance"] = {"status": "STALE", "last": "ver daily csv"}
    FRESH_PATH.write_text(json.dumps(fresh, indent=1))
    return fresh


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--daily", action="store_true")
    g.add_argument("--weekly", action="store_true")
    args = ap.parse_args()

    fresh = fetch_all()
    monthly.write()
    res_path = pathlib.Path("data/results.json")
    if args.weekly:
        try:
            estimate.run()
        except Exception as e:
            print(f"[estimate] fallo ({e}); se conserva results.json previo (spec §6.4)", file=sys.stderr)
    if not res_path.exists():
        print("sin results.json previo ni estimacion nueva: no hay nada que publicar", file=sys.stderr)
        sys.exit(1)
    r = json.loads(res_path.read_text())
    render.render(r, fresh)
    print("build ok ->", "weekly" if args.weekly else "daily")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verificar test + corrida local completa**

```bash
venv/bin/pytest tests/test_build.py -v          # PASS
export FRED_API_KEY=$(grep FRED_API_KEY .env | cut -d= -f2)
venv/bin/python -m src.build --weekly           # corrida real completa
open site/index.html                            # inspección visual
```
Esperado: `build ok -> weekly`, dashboard abre con brecha, F, ECT y gráfica.

- [ ] **Step 5: Commit** — `git add src/build.py tests/test_build.py data && git commit -m "feat: entrypoint build --daily/--weekly con degradacion honesta"`

---

### Task 12: GitHub Actions + Pages + README + auditoría final

**Files:**
- Create: `.github/workflows/build.yml`, `README.md`

- [ ] **Step 1: Workflow**

`.github/workflows/build.yml`:
```yaml
name: build
on:
  schedule:
    - cron: "0 13 * * *"        # diario 13:00 UTC ~ 7am CDMX
  workflow_dispatch:
    inputs:
      mode:
        description: "daily o weekly"
        default: "weekly"
permissions:
  contents: write
  pages: write
  id-token: write
concurrency:
  group: build
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements.txt
      - id: mode
        run: |
          if [ "${{ github.event.inputs.mode }}" = "weekly" ] || [ "$(date -u +%u)" = "1" ]; then
            echo "mode=weekly" >> "$GITHUB_OUTPUT"
          else
            echo "mode=daily" >> "$GITHUB_OUTPUT"
          fi
      - run: python -m src.build --${{ steps.mode.outputs.mode }}
      - run: pytest
      - name: Commit datos y sitio
        run: |
          git config user.name "bitcoin-terminal-bot"
          git config user.email "actions@users.noreply.github.com"
          git add data site
          git diff --staged --quiet || git commit -m "data: corrida ${{ steps.mode.outputs.mode }} $(date -u +%F)"
          git push
      - uses: actions/upload-pages-artifact@v3
        with: { path: site }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```
Nota del orden: `build` corre ANTES de `pytest` para que `test_monthly_vs_excel` valide los datos recién descargados; si cualquier test falla, NO hay commit ni deploy (spec §6.6 — dos fases).

- [ ] **Step 2: README breve**

`README.md`:
```markdown
# Bitcoin Terminal — ¿Es Bitcoin dinero?

Dashboard público del modelo ARDL-Bounds (Calibrado 6D) del trabajo
"El Bitcoin ¿es dinero?" (UNAM, Facultad de Economía). Se re-estima cada
lunes con datos actualizados; los datos crudos y cada estimación quedan
versionados en este repo (procedencia auditable por commit).

- Especificación congelada: `src/model/FROZEN.md`
- Diseño: `docs/superpowers/specs/2026-07-07-bitcoin-terminal-design.md`
- Correr local: `pip install -r requirements.txt && FRED_API_KEY=... python -m src.build --weekly`
```

- [ ] **Step 3: Habilitar Pages y primer deploy**

```bash
cd ~/BitcoinTerminal
gh api -X POST repos/AlonzoBenz/BitcoinTerminal/pages -f build_type=workflow 2>/dev/null || echo "Pages ya estaba habilitado"
git add .github README.md && git commit -m "ci: workflow diario/semanal + deploy a Pages" && git push
gh workflow run build -f mode=weekly
gh run watch --exit-status          # esperar verde
open "https://alonzobenz.github.io/BitcoinTerminal/"
```
Esperado: workflow verde, página pública sirviendo el dashboard.

- [ ] **Step 4: Auditoría final de seguridad**

```bash
cd ~/BitcoinTerminal
git log --all -p | grep -c "4ce45992" && echo "FALLO: key en historia" || echo "ok historia limpia"
grep -rn "api_key=" site/ data/ && echo "FALLO: key en artefactos" || echo "ok artefactos limpios"
gh run view --log 2>/dev/null | grep -c "4ce45992" || echo "ok logs limpios"
```
Esperado: los tres "ok". Además, recomendar al usuario regenerar la FRED key (circuló en chat).

- [ ] **Step 5: Commit final** — ya incluido en Step 3.

---

## Verificación contra el spec (autochequeo)

- §2 decisiones: 6D congelado (T3), solo M2 publicado (T9 `m2_published`), semanal/diario (T12 cron), Actions+Pages (T12), repo=BD (T12 commit de `data/`), tablas HTML (T10), español (T10) ✓
- §4 fuentes: blockchain.info/stooq/fred (T5), dominancia semilla+viva (T6), agregación descubierta y testeada (T8) ✓
- §5 secciones 1–7 (T10), ticker con fallback (T10 JS `catch`), nowcast ámbar (v1: flag en series; punteado fino = iteración §8) ✓
- §6 errores: reintentos (T4), sanidad (T7), frescura (T7/T11), FRED falla→previo (T11), guardarraíl veredicto (T9 alertas), atómico (T10 replace + T12 orden test→commit→deploy), secretos (T4 + auditoría T12) ✓
- §7 pruebas 1–4: T8, T3, T10, T5 ✓
