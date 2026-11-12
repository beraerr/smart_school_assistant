"""build_explanation: dört rol, iki dil, metinde sayı yok."""

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.services.explain_service import build_explanation

_ROLLER = ("teacher", "principal", "parent", "student")
_DILLER = ("tr", "en")


@pytest.mark.parametrize("role", _ROLLER)
@pytest.mark.parametrize("lang", _DILLER)
def test_rol_ve_dil_sayi_icermez(role: str, lang: str) -> None:
    metin = build_explanation(role, "9-A", lang)
    assert metin.strip()
    assert "9-A" not in metin
    assert not any(karakter.isdigit() for karakter in metin)
    assert "öğrenci sayısı" not in metin.casefold()
    assert "student count" not in metin.casefold()
    assert "row count" not in metin.casefold()


def test_sekiz_metin_birbirinden_farkli() -> None:
    metinler = [build_explanation(role, "9-A", lang) for role in _ROLLER for lang in _DILLER]
    assert len(set(metinler)) == 8


def test_dil_ayrimi_ve_sinif_parametresi() -> None:
    assert "kayıt" in build_explanation("student", None, "tr")
    assert "record" in build_explanation("student", None, "en").casefold()
    assert build_explanation("teacher", "9-A", "tr") != build_explanation("teacher", None, "tr")
    assert not any(karakter.isdigit() for karakter in build_explanation("teacher", None, "en"))
