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
