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
