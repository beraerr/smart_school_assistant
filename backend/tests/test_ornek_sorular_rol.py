"""Rol bazlı örnek sorular: roller ayrışır, kapsam dışı soru yoktur. Veritabanı gerekmez."""

import re
import sys
from itertools import combinations
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.services.assistant_examples import example_questions, questions

_ROLLER = ("principal", "teacher", "parent", "student")
_DILLER = ("tr", "en")

# Başka bir sınıfı ya da sınıf adını soran ifade: "9-A", "10 - B" ...
_SINIF_ADI = re.compile(r"\b\d{1,2}\s*-\s*[a-z]\b", re.IGNORECASE)

# Okul geneli ya da başka sınıf kapsamı. "okulda" / "at school" gibi çocuğun kendi
# okulunu anan ifadeler kapsam dışı sayılmaz; kalıplar bilerek dar tutuldu.
_GENEL_KAPSAM = {
    "tr": (
        r"\bokul(un|u)?\b",
        r"sınıfların",
        r"\bdiğer\b",
        r"hangi sınıf",
    ),
    "en": (
        r"\bthe school\b",
        r"school's",
        r"\bclasses\b",
        r"\bother\b",
        r"which class",
    ),
}
# Yalnız tek kayıt görenler (veli, öğrenci) için: çoğul öğrenci sorusu kapsam dışıdır.
# Öğretmen kendi sınıfındaki öğrencileri çoğul sorabilir.
_COGUL_OGRENCI = {"tr": r"öğrenciler\b", "en": r"\bstudents\b"}


def _genel_kapsam_var(soru: str, dil: str, cogul_ogrenci: bool = False) -> bool:
    metin = soru.casefold()
    kaliplar = list(_GENEL_KAPSAM[dil])
    if cogul_ogrenci:
        kaliplar.append(_COGUL_OGRENCI[dil])
    return any(re.search(kalip, metin) for kalip in kaliplar)


@pytest.mark.parametrize("dil", _DILLER)
def test_dort_rolun_listesi_birbirinden_farkli(dil: str) -> None:
    listeler = {rol: questions(rol, dil) for rol in _ROLLER}
    for rol, liste in listeler.items():
        assert liste, rol
        assert len(set(liste)) == len(liste), rol  # kendi içinde tekrar yok
    for a, b in combinations(_ROLLER, 2):
        assert listeler[a] != listeler[b], (a, b)
        assert set(listeler[a]) != set(listeler[b]), (a, b)
    # Her rolün yalnız ona özgü en az bir sorusu vardır.
    for rol in _ROLLER:
        digerleri = set().union(*(set(listeler[d]) for d in _ROLLER if d != rol))
        assert set(listeler[rol]) - digerleri, rol


@pytest.mark.parametrize("dil", _DILLER)
@pytest.mark.parametrize("rol", ["parent", "student"])
def test_veli_ve_ogrenci_listesinde_okul_geneli_ya_da_baska_sinif_yok(
    rol: str, dil: str
) -> None:
    for soru in questions(rol, dil):
        assert not _SINIF_ADI.search(soru), (rol, soru)
        assert not _genel_kapsam_var(soru, dil, cogul_ogrenci=True), (rol, soru)


@pytest.mark.parametrize("dil", _DILLER)
def test_ogretmen_listesinde_baska_sinifi_soran_soru_yok(dil: str) -> None:
    sahip = {"tr": ("sınıfım",), "en": ("my class",)}[dil]
    sinif_kelimesi = {"tr": "sınıf", "en": "class"}[dil]
    for soru in questions("teacher", dil):
        metin = soru.casefold()
        assert not _SINIF_ADI.search(soru), soru
        assert not _genel_kapsam_var(soru, dil), soru
        # Sınıftan söz eden her soru yalnız öğretmenin kendi sınıfını (iyelikle) anar.
        if sinif_kelimesi in metin:
            assert any(ek in metin for ek in sahip), soru


@pytest.mark.parametrize("dil", _DILLER)
def test_her_rolde_en_az_bir_donem_sorusu_var(dil: str) -> None:
    kelime = {"tr": "dönem", "en": "term"}[dil]
    for rol in _ROLLER:
        assert any(kelime in soru.casefold() for soru in questions(rol, dil)), rol


def test_bilinmeyen_rol_bos_liste() -> None:
    assert example_questions("admin", "tr") == []
    assert example_questions("", "en") == []
