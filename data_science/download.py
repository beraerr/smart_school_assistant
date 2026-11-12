"""UCI Student Performance (id 320) arşivini indirir ve doğrular.

Dosyalar zaten duruyorsa ağa çıkılmaz. CHECKSUMS.txt sonraki çalıştırmalarda
sha256 ile karşılaştırılır; uyuşmazlık hata verir.
"""

from __future__ import annotations

import hashlib
import io
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from data_science.config import RAW_DIR

DATASET_URL = "https://archive.ics.uci.edu/static/public/320/student+performance.zip"
CSV_NAMES = ("student-mat.csv", "student-por.csv")
CHECKSUMS_PATH = RAW_DIR / "CHECKSUMS.txt"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_checksums(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        digest, name = stripped.split(None, 1)
        found[Path(name).name] = digest.lower()
    return found


def write_checksums() -> None:
    lines = [f"{sha256_file(RAW_DIR / name)}  {name}" for name in CSV_NAMES]
    CHECKSUMS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_checksums() -> None:
    if not CHECKSUMS_PATH.is_file():
        raise RuntimeError(f"checksum dosyasi yok: {CHECKSUMS_PATH}")
    expected = _parse_checksums(CHECKSUMS_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    for name in CSV_NAMES:
        path = RAW_DIR / name
        if name not in expected:
            errors.append(f"{name}: checksum kaydi yok")
            continue
        if not path.is_file():
            errors.append(f"{name}: dosya yok")
            continue
        actual = sha256_file(path)
        if actual != expected[name]:
            errors.append(f"{name}: beklenen {expected[name]}, bulunan {actual}")
    if errors:
        raise RuntimeError("checksum uyusmazligi:\n" + "\n".join(errors))


def _csvs_present() -> bool:
    return all((RAW_DIR / name).is_file() for name in CSV_NAMES)


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


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "week08-student-performance/1.0 (educational)"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError(f"bos yanit: {url}")
    return payload


def _download_and_extract() -> None:
    payload = _fetch(DATASET_URL)
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        try:
            archive = zipfile.ZipFile(io.BytesIO(payload))
        except zipfile.BadZipFile as exc:
            raise RuntimeError("indirilen dosya zip degil") from exc
        with archive:
            _extract(archive, dest, depth=0)
        missing = [name for name in CSV_NAMES if not (dest / name).is_file()]
        if missing:
            raise RuntimeError(f"zip icinde eksik csv: {missing}")
        for name in CSV_NAMES:
            (RAW_DIR / name).write_bytes((dest / name).read_bytes())


def ensure_dataset() -> None:
    """CSV'ler duruyorsa indirmez; checksum varsa doğrular, yoksa yazar."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if _csvs_present():
        if CHECKSUMS_PATH.is_file():
            verify_checksums()
            print("raw csv mevcut, checksum dogrulandi")
        else:
            write_checksums()
            print("raw csv mevcut, checksum yazildi")
        return
    _download_and_extract()
    if not _csvs_present():
        raise RuntimeError("student-mat.csv ve student-por.csv yazilamadi")
    if CHECKSUMS_PATH.is_file():
        verify_checksums()
        print("indirildi, checksum dogrulandi")
    else:
        write_checksums()
        print("indirildi, checksum yazildi")


def main() -> None:
    ensure_dataset()


if __name__ == "__main__":
    main()
