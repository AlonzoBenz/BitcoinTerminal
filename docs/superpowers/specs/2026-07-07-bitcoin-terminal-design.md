# BitcoinTerminal — Diseño

**Fecha:** 2026-07-07 · **Estado:** aprobado en brainstorming, pendiente de revisión final del usuario

## 1. Propósito

Dashboard público que muestra **el modelo ARDL "Bitcoin es dinero" funcionando** con datos
actualizados. Es la evidencia viva del Capítulo 3 de la tesis (UNAM, Facultad de Economía)
para la defensa ante el sínodo, y secundariamente una herramienta de monitoreo.

La ventana principal es **el modelo**, no el mercado: brecha de monetización (DMB observado
vs DMB* de equilibrio), ecuación de largo plazo con coeficientes vivos, cointegración y
velocidad de ajuste.

## 2. Decisiones fijadas

| Decisión | Valor |
|---|---|
| Especificación econométrica | **Calibrado 6D congelado** (ARDL(12,12,1,1), caso 5, 6 dummies de impulso), vendored desde `~/Tesis_Cap3` — no se re-optimiza |
| Muestra de estimación | **Solo meses con M2 publicado por la Fed.** Meses provisionales (M2 = último publicado) aparecen solo en gráficas, marcados "nowcast" |
| Cadencia | Re-estimación **semanal** (lunes ~7am CDMX = 13:00 UTC); refresh **diario** de datos de mercado/hechos estilizados sin re-estimar |
| Infraestructura | **GitHub Actions** (cron) + **GitHub Pages**. La Mac del usuario no participa en producción |
| Persistencia | **El repo es la base de datos**: CSV crudos + base mensual + results.json commiteados en cada corrida (procedencia auditable por commit) |
| Distribución | URL pública (Pages) + funciona igual en local (`python -m src.build`) |
| Cuadros econométricos | Tablas HTML nativas (los PNG estilo EViews siguen viviendo solo en la tesis) |
| Idioma | Español, etiquetas académicas |

**Nota Pages:** el plan gratuito de GitHub requiere **repo público** para Pages. El código
vendored y los datos serán públicos (son del propio usuario). La FRED key vive solo en
GitHub Secrets; conviene regenerarla al terminar el setup porque circuló en una conversación.

## 3. Arquitectura y estructura del repo

```
BitcoinTerminal/
├── .github/workflows/build.yml   # cron diario 13:00 UTC; el lunes (o manual) corre --weekly
├── src/
│   ├── fetchers/
│   │   ├── coingecko.py          # spot: precio, market cap, dominancia actual
│   │   ├── blockchain_info.py    # Charts API (timespan=all): estimated-transaction-volume-usd,
│   │   │                         #   n-transactions, total-bitcoins, market-price, difficulty, fees
│   │   ├── stooq.py              # oro XAUUSD (histórico completo, CSV gratuito)
│   │   ├── coinstats.py          # dominancia BTC histórica (fuente original de la tesis)
│   │   └── fred.py               # M2SL (env FRED_API_KEY)
│   ├── model/                    # VENDORED congelado de ~/Tesis_Cap3/scripts
│   │   ├── dataload.py           #   adaptado: lee CSV en vez de Excel; dummies desde fechas
│   │   ├── model.py              #   copia 1:1 (incluye Wald manual del Bounds F)
│   │   └── FROZEN.md             #   SHA de origen + fecha + regla: no se toca
│   ├── monthly.py                # agrega crudos a base mensual: DMB, MC2, MC1, RV12, UC + 6 dummies
│   ├── estimate.py               # corre Calibrado 6D → Bounds F, ECT, coefs LP, diagnósticos
│   ├── sanity.py                 # puertas de sanidad por serie (ver §6)
│   ├── render.py                 # monthly.csv + results.json → site/index.html
│   └── build.py                  # entrypoint único: --daily | --weekly
├── data/
│   ├── raw/                      # CSV crudos por fuente (commiteados)
│   ├── monthly.csv               # base mensual reconstruida
│   └── results.json              # salida de estimación + metadatos (fechas, frescura)
├── site/index.html               # dashboard generado (publicado a Pages)
├── tests/                        # ver §7
├── docs/superpowers/specs/       # este documento
├── .env.example                  # FRED_API_KEY=...
└── requirements.txt              # versiones fijadas (statsmodels == la validada vs EViews)
```

**Flujo:** fetchers → `data/raw/*.csv` → `sanity.py` → `monthly.py` → `estimate.py`
(solo `--weekly`) → `render.py` → commit único de datos+HTML → deploy a Pages.
El modo `--daily` es el `--weekly` saltándose `estimate.py`.

## 4. Fuentes de datos

| Serie | Variable | Fuente | Frecuencia | Riesgo |
|---|---|---|---|---|
| Precio BTC | RV12, MarketCap | blockchain.info `market-price` (histórico) + CoinGecko (spot) | diaria | bajo |
| Supply BTC | MarketCap, MC1 | blockchain.info `total-bitcoins` | diaria | bajo |
| TxVolumeUSD | MC2 | blockchain.info `estimated-transaction-volume-usd` | diaria | bajo |
| TxTfrCnt | MC1 | blockchain.info `n-transactions` | diaria | bajo |
| Oro XAUUSD | RV12 | Stooq (CSV histórico gratuito) | diaria | bajo |
| Dominancia BTC | UC | CoinStats OpenAPI (fuente de la tesis) | diaria | **medio — resolver en implementación**: si el endpoint histórico no es viable, evaluar CoinMarketCap u otra; el test vs Excel (§7) valida cualquier sustituto |
| M2SL | denominador DMB, MC2 | FRED API (key en Secrets) | mensual, rezago ~4 sem | bajo |

La agregación diaria→mensual replica la del Excel de la tesis (`TxTfrCnt_daily_avg` ⇒
promedio diario del mes, etc.). **La regla exacta por serie se descubre y fija en la
implementación, verificada por `test_monthly_vs_excel`** — no se adivina.

## 5. Dashboard (frontend)

Un solo `site/index.html` estático generado por `render.py`. Gráficas con Chart.js (CDN).

**Identidad visual — "papel académico, escolar futurista, simple" (estilo anthropic.com + Bitcoin):**
- Fondo crema `#faf6ec`, cards marfil `#fffdf6`, líneas arena `#e0d7c2`, tinta `#211d14`
- Acento único fuerte: naranja Bitcoin `#f7931a` (`#c46f0a` para texto naranja sobre crema)
- Tipografías: **Fraunces** (títulos y cifras protagonistas), **IBM Plex Mono** (datos),
  **Inter** (interfaz) — Google Fonts
- Navegación superior (no sidebar); verde/ámbar/rojo en tonos tinta para señales
- El refinamiento visual fino se itera después del primer deploy (acordado con el usuario)

**Secciones (nav superior, en este orden):**
1. **El modelo** (inicio): ecuación de largo plazo con coeficientes y significancia;
   brecha de monetización hoy (DMB observado vs DMB*, gauge, % sub/sobre-monetizado);
   ECT como velocidad de corrección (25%/mes, vida media ~2.4 meses); badge de
   cointegración (Bounds F vs crítico); serie DMB vs DMB* 2015→hoy; frescura
2. **Variables**: DMB, MC2, MC1, RV12, UC — series completas, última lectura, meses nowcast en ámbar
3. **Cointegración**: Bounds test vs valores críticos, ECT, diagnósticos, incluido el
   caveat honesto del RESET (p=0.008, posible no linealidad)
4. **Funciones del dinero**: coeficientes traducidos a la tesis — reserva de valor ✓
   (RV12***), medio de cambio ✓ (MC2***), unidad de cuenta ✗ (UC ns) — semáforo por función
5. **Hechos estilizados**: gráficas del Cap. 1 en vivo (transacciones, supply, dificultad, fees, precio)
6. **Mercado**: ticker en vivo — `fetch` del navegador a CoinGecko cada 60s con fallback
   silencioso a los valores del build
7. **Datos**: frescura por serie (badges contra el contrato de §6) y fuentes citables

## 6. Manejo de errores

**Regla madre: nunca publicar una página rota; mejor una página vieja con fecha honesta.**

1. **Reintentos**: 3 intentos por petición con backoff exponencial (2s/8s/30s), timeout 30s.
2. **Puertas de sanidad** (`sanity.py`) antes de aceptar cualquier descarga: esquema
   correcto, sin negativos en precios/volúmenes, sin huecos en el índice mensual, sin
   saltos de nivel absurdos vs la última corrida buena. Serie insana ⇒ se descarta la
   descarga, se usa el último CSV commiteado (el repo es el caché) y se marca `SUSPECT`.
3. **Contrato de frescura por serie**: cada fuente declara edad máxima (M2: 45 días;
   diarias: 3 días). Badges FRESCO / STALE / DEAD en la sección Datos se calculan contra
   el contrato.
4. **Fallo de FRED en `--weekly`**: se aborta la re-estimación, se conserva el
   `results.json` anterior; el dashboard muestra la estimación previa con su fecha e
   indicador ámbar.
5. **Guardarraíl del veredicto**: si una estimación válida cambia la conclusión (F cae
   bajo el crítico, ECT cambia de signo o pierde significancia), se **publica con banner
   de alerta** — es información, no error. Errores numéricos reales (p.ej. matriz
   singular) conservan el `results.json` anterior con indicador ámbar.
6. **Publicación atómica en dos fases**: build en directorio temporal; solo si sanidad +
   pruebas pasan se mueve a `site/` y se commitea datos+HTML en un solo commit. Pages
   nunca sirve estados intermedios; si el workflow truena, sigue la última versión buena
   y GitHub notifica por email automáticamente.
7. **Secretos**: FRED key solo por env; los logs nunca imprimen URLs con la key (Actions
   además enmascara secrets). `concurrency` en el workflow evita corridas encimadas;
   `workflow_dispatch` da botón manual.

## 7. Pruebas (corren en el workflow antes de cada build)

1. **`test_monthly_vs_excel`** — la base mensual reconstruida desde APIs empata con
   `Modelo_Calibrado_Cloud.xlsx` en 2015M01–2026M03. Tolerancia relativa inicial: **0.1%
   por celda**; si una serie la excede por diferencias de *vintage* (las APIs revisan
   histórico), la tolerancia de esa serie puede ampliarse solo con justificación
   documentada en el propio test. **Bloquea todo lo demás**; hasta que pase, no se
   publica nada.
2. **`test_estimate_frozen`** — el Calibrado 6D sobre la muestra congelada de la tesis
   reproduce: Bounds F=44.09, ECT=−0.2525, MC2=1.114, RV12=1.975 (tolerancia al 4º
   decimal, igual que la validación Python vs EViews). Es el candado del "congelado":
   cualquier cambio en `src/model/` que altere resultados truena CI antes de publicar.
3. **`test_render`** — humo: el HTML generado contiene los números clave y estructura válida.
4. **Fetchers con fixtures grabados** — los tests de CI no dependen de APIs vivas.

## 8. Fuera de alcance (por ahora)

- Refinamiento visual fino (segunda iteración, tras el primer deploy)
- Señales de trading / predicción de precio (eso es PlanT, otro proyecto)
- Re-optimización de dummies o de la especificación (violaría el congelado)
- Notificaciones más allá del email automático de Actions
- Estimaciones alternativas con M2 nowcast ("dos estimaciones" se descartó)

## 9. Riesgos abiertos

| Riesgo | Mitigación |
|---|---|
| Fuente histórica de dominancia BTC (CoinStats) puede no ser viable sin key | Resolver en implementación; `test_monthly_vs_excel` valida cualquier sustituto |
| Reglas de agregación mensual desconocidas con exactitud | Arqueología contra el Excel + test de tolerancia (§4, §7) |
| GitHub deshabilita crons tras 60 días sin actividad en el repo | Cada corrida commitea ⇒ hay actividad perpetua; el email de fallo avisa si algo se detiene |
| Rate limits de blockchain.info / CoinGecko en CI | Backoff + caché en repo; el build diario tolera series STALE |
