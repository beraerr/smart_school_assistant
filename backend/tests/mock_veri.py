"""database/mock_data.json'dan beklenen değerleri hesaplayan test yardımcıları.

Testler mock rakamlarını elle yazmaz; sayım, ortalama, sıra ve risk beklentisi
buradan, sabit bir "bugün" verilerek üretilir. Veritabanı bu dosyadan
yüklenmiş olmalıdır (database/seed_mock.py).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.services.risk import assess_risk
from backend.app.services.takvim import risk_penceresi

MOCK_YOLU = _PROJECT_ROOT / "database" / "mock_data.json"


@lru_cache(maxsize=1)
def yukle() -> dict[str, Any]:
    return json.loads(MOCK_YOLU.read_text(encoding="utf-8"))


def ogrenciler(sinif: str | None = None) -> list[dict[str, Any]]:
    return [r for r in yukle()["students"] if sinif is None or r["class_name"] == sinif]


def siniflar() -> list[str]:
    return sorted({r["class_name"] for r in yukle()["students"]})


def ogrenci_sayisi(sinif: str | None = None) -> int:
    return len(ogrenciler(sinif))


def ogrenci_sinifi(student_id: int) -> str:
    return next(r["class_name"] for r in yukle()["students"] if r["id"] == student_id)


def ogrenci_adi(student_id: int) -> str:
    return next(r["name"] for r in yukle()["students"] if r["id"] == student_id)


def gune_kadar(gun: date) -> tuple[list[dict], list[dict]]:
    """gun (dahil) tarihine kadarki not ve devamsızlık satırları."""
    sinir = gun.isoformat()
    veri = yukle()
    return (
        [r for r in veri["grades"] if r["date"] <= sinir],
        [r for r in veri["attendance"] if r["date"] <= sinir],
    )


def gelecek_kayitlar(gun: date) -> tuple[list[dict], list[dict]]:
    """gun tarihinden sonraki (hariç) not ve devamsızlık satırları."""
    sinir = gun.isoformat()
    veri = yukle()
    return (
        [r for r in veri["grades"] if r["date"] > sinir],
        [r for r in veri["attendance"] if r["date"] > sinir],
    )


def pencere_kayitlari(gun: date) -> tuple[list[dict], list[dict]]:
    """Risk penceresindeki satırlar. Pencere yoksa boş listeler."""
    pencere = risk_penceresi(gun)
    if pencere is None:
        return [], []
    bas, bit = pencere[0].isoformat(), pencere[1].isoformat()
    veri = yukle()
    return (
        [r for r in veri["grades"] if bas <= r["date"] <= bit],
        [r for r in veri["attendance"] if bas <= r["date"] <= bit],
    )


def risk_beklenen(gun: date, sinif: str | None = None) -> list[dict[str, Any]]:
    """Mock ve sabit günden beklenen /risk satırları. Pencere yoksa boş liste."""
    if risk_penceresi(gun) is None:
        return []
    notlar, devam = pencere_kayitlari(gun)
    return assess_risk(ogrenciler(sinif), notlar, devam, lang="tr")


def ortalamalar(gun: date, ders: str | None = None) -> dict[int, float | None]:
    """Her öğrencinin gun (dahil) tarihine kadarki not ortalaması; notsuz None."""
    notlar, _ = gune_kadar(gun)
    toplam: dict[int, list[float]] = {r["id"]: [] for r in yukle()["students"]}
    for r in notlar:
        if ders is None or r["subject"].lower() == ders.lower():
            toplam[r["student_id"]].append(r["grade"])
    return {sid: (sum(v) / len(v) if v else None) for sid, v in toplam.items()}


def sira_beklenen(
    student_id: int, kapsam: str, gun: date, ders: str | None = None
) -> dict[str, Any]:
    """student_rank'in beklenen satırı: rank, total_students, student_avg, group_avg.

    Notsuz öğrenciler sıralamada sona düşer ve grup ortalamasına girmez.
    """
    sinif = ogrenci_sinifi(student_id)
    kapsamdakiler = [
        r["id"]
        for r in yukle()["students"]
        if kapsam == "school" or r["class_name"] == sinif
    ]
    ort = ortalamalar(gun, ders)
    benim = ort[student_id]
    dolu = [ort[sid] for sid in kapsamdakiler if ort[sid] is not None]
    if benim is None:
        sira = len(dolu) + 1
    else:
        sira = 1 + sum(1 for deger in dolu if deger > benim)
    return {
        "rank": sira,
        "total_students": len(kapsamdakiler),
        "student_avg": benim,
        "group_avg": (sum(dolu) / len(dolu)) if dolu else None,
    }
