# Pipeline congelado — NO TOCAR
Origen: ~/Tesis_Cap3/scripts/{model.py,dataload.py} (Calibrado 6D de la tesis).
Fecha de copia: 2026-07-07.
Adaptaciones permitidas: SOLO E/S (lee CSV en vez de Excel, imports absolutos).
La especificación (ARDL(12,12,1,1), caso 5, 6 dummies, Wald manual, método
delta) es inmutable. El candado es tests/test_estimate_frozen.py: si un cambio
altera resultados al 4º decimal, CI truena y no se publica.

Notas técnicas: requiere statsmodels==0.14.6 (versión con la que se validó vs
EViews; ver requirements.txt). "Caso 5" = intercepto y tendencia irrestrictos
(Pesaran, Shin & Smith, 2001). D7/D8 en dataload.py están reservadas para la
robustez 8D — no son código muerto.
