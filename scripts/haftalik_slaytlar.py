"""Haftalık sunumları (docs/sunumlar/*.pptx) slayt PNG'lerine ve PDF'e çevirir.

Ad kuralı tam olarak `hafta<NN>_<tr|en>.pptx` (NN iki hane). Kurala uymayan bir dosya varsa
hiçbir şey silinmeden betik hata verip durur; dosya atlanmaz.

Her dosya için `soffice --headless --convert-to pdf`, ardından `pdftoppm -png -r 110` çalışır.
Çıktı (frontend/assets/haftalik/ her çalıştırmada sıfırdan kurulur):
    hafta<NN>/<tr|en>/sunum.pdf
    hafta<NN>/<tr|en>/slayt_<NN>.png
    haftalik.json   (her hafta için dil başına PDF yolu ve sıralı slayt listesi; yollar
                     haftalik/ klasörüne görelidir)

Dış komut başarısız olursa hata yutulmaz; betik hata koduyla durur.

Proje kökünden:
    python scripts/haftalik_slaytlar.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

_KOK = Path(__file__).resolve().parents[1]
SUNUM_DIZINI = _KOK / "docs" / "sunumlar"
CIKTI_DIZINI = _KOK / "frontend" / "assets" / "haftalik"
_AD = re.compile(r"hafta(\d{2})_(tr|en)\.pptx")
_SAYFA_PNG = re.compile(r"sayfa-(\d+)\.png")
_COZUNURLUK = "110"


def sunum_adi_ayristir(ad: str) -> tuple[int, str]:
    """`hafta11_tr.pptx` -> (11, "tr"). Kurala uymayan ad ValueError verir."""
    eslesme = _AD.fullmatch(ad)
    if eslesme is None:
        raise ValueError(f"Sunum adı 'hafta<NN>_<tr|en>.pptx' kuralına uymuyor: {ad!r}")
    return int(eslesme.group(1)), eslesme.group(2)


def sunumlari_bul(dizin: Path) -> list[tuple[int, str, Path]]:
    """Dizindeki bütün .pptx dosyalarını (hafta, dil, yol) olarak sıralı döndürür; uymayan ad hata verir."""
    kayitlar = []
    gorulen: set[tuple[int, str]] = set()
    for yol in sorted(dizin.glob("*.pptx")):
        hafta, dil = sunum_adi_ayristir(yol.name)
        if (hafta, dil) in gorulen:
            raise ValueError(f"Aynı hafta ve dil birden fazla kez var: {yol.name}")
        gorulen.add((hafta, dil))
        kayitlar.append((hafta, dil, yol))
    return sorted(kayitlar, key=lambda kayit: (kayit[0], kayit[1]))


def _calistir(komut: list[str]) -> None:
    subprocess.run(komut, check=True)


def _donustur(pptx: Path, hedef: Path) -> dict:
    """Tek sunumu hedef klasöre çevirir; manifest girdisini (PDF yolu, slayt adları) döndürür."""
    hedef.mkdir(parents=True)
    _calistir(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(hedef), str(pptx)])
    uretilen = hedef / f"{pptx.stem}.pdf"
    if not uretilen.is_file():
        raise RuntimeError(f"soffice PDF üretmedi: {uretilen}")
    pdf = hedef / "sunum.pdf"
    uretilen.replace(pdf)

    _calistir(["pdftoppm", "-png", "-r", _COZUNURLUK, str(pdf), str(hedef / "sayfa")])
    sayfalar = []
    for png in hedef.glob("sayfa-*.png"):
        eslesme = _SAYFA_PNG.fullmatch(png.name)
        if eslesme is None:
            raise RuntimeError(f"Beklenmeyen pdftoppm çıktısı: {png.name}")
        sayfalar.append((int(eslesme.group(1)), png))
    sayfalar.sort()
    if not sayfalar:
        raise RuntimeError(f"pdftoppm slayt üretmedi: {pdf}")
    if [no for no, _ in sayfalar] != list(range(1, len(sayfalar) + 1)):
        raise RuntimeError(f"pdftoppm sayfa numaraları ardışık değil: {pdf}")

    adlar = []
    for sira, (_, png) in enumerate(sayfalar, start=1):
        ad = f"slayt_{sira:02d}.png"
        png.replace(hedef / ad)
        adlar.append(ad)
    return {"pdf": "sunum.pdf", "slaytlar": adlar}


def _goreli(kok: Path, yol: str, hedef: Path) -> str:
    return (hedef.relative_to(kok) / yol).as_posix()


def kur(sunum_dizini: Path = SUNUM_DIZINI, cikti: Path = CIKTI_DIZINI) -> dict:
    """Çıktı klasörünü sıfırdan kurar ve manifesti yazıp döndürür."""
    sunumlar = sunumlari_bul(sunum_dizini)  # Ad hatası, hiçbir şey silinmeden önce durdurur.
    if cikti.exists():
        shutil.rmtree(cikti)
    cikti.mkdir(parents=True)

    haftalar: dict[int, dict] = {}
    for hafta, dil, pptx in sunumlar:
        hedef = cikti / f"hafta{hafta:02d}" / dil
        girdi = _donustur(pptx, hedef)
        haftalar.setdefault(hafta, {})[dil] = {
            "pdf": _goreli(cikti, girdi["pdf"], hedef),
            "slaytlar": [_goreli(cikti, ad, hedef) for ad in girdi["slaytlar"]],
        }
    manifest = {
        "haftalar": [{"hafta": hafta, "diller": haftalar[hafta]} for hafta in sorted(haftalar)]
    }
    (cikti / "haftalik.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    manifest = kur()
    adet = sum(len(hafta["diller"]) for hafta in manifest["haftalar"])
    print(f"{adet} sunum işlendi: {CIKTI_DIZINI / 'haftalik.json'}")


if __name__ == "__main__":
    main()
