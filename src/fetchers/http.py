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
