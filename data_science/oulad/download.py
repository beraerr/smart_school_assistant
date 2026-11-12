"""OULAD (UCI id 349) arşivini indirir ve data/raw/oulad altına açar.

Dosyalar zaten duruyorsa ağa çıkılmaz. ZIP_SHA256 boş ise sha256 yazdırılır;
dolu ise oulad.zip ile karşılaştırılır, uyuşmazlık hata verir.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from data_science.oulad import RAW_OULAD_DIR

DATASET_URL = (
    "https://archive.ics.uci.edu/static/public/349/"
    "open+university+learning+analytics+dataset.zip"
)
CSV_NAMES = (
    "courses.csv",
    "assessments.csv",
    "vle.csv",
    "studentInfo.csv",
    "studentRegistration.csv",
    "studentAssessment.csv",
    "studentVle.csv",
)
ZIP_NAME = "oulad.zip"

# İlk indirmede hesaplanan oulad.zip sha256. Boşsa yazdırılır.
# Hex (veya "hex  oulad.zip" satırı) sabitlenince doğrulanır.
ZIP_SHA256 = "f2ed1902616c1fe8d2824d872c0b7d2d72be435bf0124d077044fe4be2c6d3e4"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pinned_digest() -> str:
    text = ZIP_SHA256.strip().lower()
    if not text:
        return ""
    return text.split()[0]


def verify_sha256(path: Path, expected: str) -> None:
    wanted = str(expected).strip().lower().split()[0] if str(expected).strip() else ""
    if not wanted:
        raise RuntimeError("beklenen sha256 bos")
    errors: list[str] = []
    if not path.is_file():
        errors.append(f"{path.name}: dosya yok")
    else:
        actual = sha256_file(path)
        if actual != wanted:
            errors.append(f"{path.name}: beklenen {wanted}, bulunan {actual}")
    if errors:
        raise RuntimeError("checksum uyusmazligi:\n" + "\n".join(errors))


def _csvs_present() -> bool:
    return all((RAW_OULAD_DIR / name).is_file() for name in CSV_NAMES)


def _extract(archive: zipfile.ZipFile, dest: Path, depth: int) -> None:
    nested: list[zipfile.ZipInfo] = []
    for info in archive.infolist():
        if info.is_dir():
            continue
        base = Path(info.filename).name
        if base in CSV_NAMES and not (dest / base).is_file():
            (dest / base).write_bytes(archive.read(info))
        elif base.lower().endswith(".zip"):
            nested.append(info)
    if depth >= 1:
        return
    for info in nested:
        with zipfile.ZipFile(io.BytesIO(archive.read(info))) as inner:
            _extract(inner, dest, depth + 1)


def _extract_zip(path: Path) -> None:
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise RuntimeError("indirilen dosya zip degil") from exc
    with archive:
        _extract(archive, RAW_OULAD_DIR, depth=0)
    missing = [name for name in CSV_NAMES if not (RAW_OULAD_DIR / name).is_file()]
    if missing:
        raise RuntimeError(f"zip icinde eksik csv: {missing}")


def _stream_download(dest: Path) -> None:
    request = urllib.request.Request(
        DATASET_URL,
        headers={"User-Agent": "week09-oulad/1.0 (educational)"},
    )
    empty = True
    with urllib.request.urlopen(request, timeout=300) as response, dest.open("wb") as handle:
        while True:
            chunk = response.read(1 << 16)
            if not chunk:
                break
            empty = False
            handle.write(chunk)
    if empty:
        raise RuntimeError(f"bos yanit: {DATASET_URL}")


def _report_existing() -> None:
    zip_path = RAW_OULAD_DIR / ZIP_NAME
    pinned = _pinned_digest()
    if pinned:
        verify_sha256(zip_path, pinned)
        print("raw csv mevcut, checksum dogrulandi")
        return
    if zip_path.is_file():
        print(f"{sha256_file(zip_path)}  {ZIP_NAME}")
        print("raw csv mevcut, sha256 yazdirildi")
        return
    print("raw csv mevcut")


def _download_and_extract() -> None:
    RAW_OULAD_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="oulad-", suffix=".zip", dir=RAW_OULAD_DIR)
    os.close(fd)
    tmp_path = Path(tmp_name)
    zip_path = RAW_OULAD_DIR / ZIP_NAME
    try:
        _stream_download(tmp_path)
        pinned = _pinned_digest()
        if pinned:
            verify_sha256(tmp_path, pinned)
        else:
            print(f"{sha256_file(tmp_path)}  {ZIP_NAME}")
        os.replace(tmp_path, zip_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    for name in CSV_NAMES:
        csv_path = RAW_OULAD_DIR / name
        if csv_path.is_file():
            csv_path.unlink()
    _extract_zip(zip_path)
    if not _csvs_present():
        raise RuntimeError("oulad csv dosyalari yazilamadi")
    if _pinned_digest():
        print("indirildi, checksum dogrulandi")
    else:
        print("indirildi, sha256 yazdirildi")


def ensure_dataset(force: bool = False) -> None:
    """CSV'ler duruyorsa indirmez. Hash sabitliyse doğrular, değilse yazdırır."""
    RAW_OULAD_DIR.mkdir(parents=True, exist_ok=True)
    if _csvs_present() and not force:
        _report_existing()
        return
    _download_and_extract()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="OULAD arsivini indirir")
    parser.add_argument("--force", action="store_true", help="varsa da yeniden indir")
    args = parser.parse_args(argv)
    ensure_dataset(force=args.force)


if __name__ == "__main__":
    main()
