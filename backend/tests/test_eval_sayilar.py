"""Cevaptaki sayı denetimi satır başı liste işaretlerini sayı saymaz."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from eval.run_eval import _sayi_dayanakli


def test_liste_isaretleri_sayi_sayilmaz() -> None:
    cevap = "\n".join(
        [
            "Sınıfta 4 öğrenci var:",
            "1. Ali Yılmaz",
            "2) Kerem Güneş",
            "  3) Mehmet Kaya",
            "- Zeynep Demir",
            "• Elif Şahin",
            "1.5 satır başında ondalık kalsın",
            "Ortalama 62,53.",
        ]
    )
    eksik = _sayi_dayanakli(cevap, {4.0, 62.53})
    assert eksik == ["1.5"]
