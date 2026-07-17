# Bitcoin Terminal — ¿Es Bitcoin dinero?

Dashboard público del modelo ARDL-Bounds (Calibrado 6D) del trabajo
"El Bitcoin ¿es dinero?" (UNAM, Facultad de Economía). Se re-estima cada
lunes con datos actualizados; los datos crudos y cada estimación quedan
versionados en este repo (procedencia auditable por commit).

**Dashboard:** https://alonzobenz.github.io/BitcoinTerminal/

- Especificación congelada: `src/model/FROZEN.md`
- Diseño: `docs/superpowers/specs/2026-07-07-bitcoin-terminal-design.md`
- Correr local: `pip install -r requirements.txt && FRED_API_KEY=... python -m src.build --weekly`
