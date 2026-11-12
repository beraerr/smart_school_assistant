"""İki UCI ders dosyasını okur, birleştirir ve student_key üretir."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from data_science.config import RAW_DIR

UCI_COLUMNS = (
    "school",
    "sex",
    "age",
    "address",
    "famsize",
    "Pstatus",
    "Medu",
    "Fedu",
    "Mjob",
    "Fjob",
    "reason",
    "guardian",
    "traveltime",
    "studytime",
    "failures",
    "schoolsup",
    "famsup",
    "paid",
    "activities",
    "nursery",
    "higher",
    "internet",
    "romantic",
    "famrel",
    "freetime",
    "goout",
    "Dalc",
    "Walc",
    "health",
    "absences",
    "G1",
    "G2",
    "G3",
)

NUMERIC_COLUMNS = (
    "age",
    "Medu",
    "Fedu",
    "traveltime",
    "studytime",
    "failures",
    "famrel",
    "freetime",
    "goout",
    "Dalc",
    "Walc",
    "health",
    "absences",
    "G1",
    "G2",
    "G3",
)

# student_key bu sütunların deterministik özetidir. Sırayı değiştirmek anahtarı değiştirir.
KEY_COLUMNS = (
    "school",
    "sex",
    "age",
    "address",
    "famsize",
    "Pstatus",
    "Medu",
    "Fedu",
    "Mjob",
    "Fjob",
    "reason",
    "nursery",
    "internet",
)

KEY_INTEGER_COLUMNS = ("age", "Medu", "Fedu")

BINARY_CATEGORIES: dict[str, tuple[str, str]] = {
    "school": ("GP", "MS"),
    "sex": ("F", "M"),
    "address": ("U", "R"),
    "famsize": ("LE3", "GT3"),
    "Pstatus": ("T", "A"),
    "schoolsup": ("no", "yes"),
    "famsup": ("no", "yes"),
    "paid": ("no", "yes"),
    "activities": ("no", "yes"),
    "nursery": ("no", "yes"),
    "higher": ("no", "yes"),
    "internet": ("no", "yes"),
    "romantic": ("no", "yes"),
}

NOMINAL_CATEGORIES: dict[str, tuple[str, ...]] = {
    "Mjob": ("teacher", "health", "services", "at_home", "other"),
    "Fjob": ("teacher", "health", "services", "at_home", "other"),
    "reason": ("home", "reputation", "course", "other"),
    "guardian": ("mother", "father", "other"),
    "subject": ("mat", "por"),
}

CATEGORICAL_COLUMNS = tuple(BINARY_CATEGORIES) + tuple(
    column for column in NOMINAL_CATEGORIES if column != "subject"
)


def _read_subject(path: Path, subject: str) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, sep=";", encoding="utf-8")
    frame.columns = [str(column).replace("\ufeff", "").strip() for column in frame.columns]
    frame["subject"] = subject
    return frame


def _require_categories(frame: pd.DataFrame, column: str, allowed: tuple[str, ...]) -> None:
    observed = set(frame[column].dropna().unique())
    unknown = sorted(observed - set(allowed))
    if unknown:
        raise ValueError(f"{column}: beklenmeyen kategori {unknown}")


def validate_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Sütun, tip ve kategori kontrolü. Eksik hücre sayısını döndürür."""
    missing_columns = [column for column in UCI_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"eksik sutunlar: {missing_columns}")
    if "subject" not in frame.columns:
        raise ValueError("subject sutunu yok")

    cleaned = frame.copy()
    for column in NUMERIC_COLUMNS:
        try:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="raise")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{column} sayisal degil") from exc

    checked = list(UCI_COLUMNS) + ["subject"]
    missing_count = int(cleaned[checked].isna().sum().sum())
    key_missing = int(cleaned[list(KEY_COLUMNS)].isna().sum().sum())
    if key_missing:
        raise ValueError(f"student_key sutunlarinda eksik deger: {key_missing}")
    if missing_count:
        raise ValueError(f"eksik deger sayisi: {missing_count}")

    for column in CATEGORICAL_COLUMNS:
        cleaned[column] = cleaned[column].map(lambda value: str(value).strip())
    cleaned["subject"] = cleaned["subject"].map(lambda value: str(value).strip())

    for column, allowed in BINARY_CATEGORIES.items():
        _require_categories(cleaned, column, allowed)
    for column, allowed in NOMINAL_CATEGORIES.items():
        _require_categories(cleaned, column, allowed)
    return cleaned, missing_count


def student_key_payload(frame: pd.DataFrame) -> pd.Series:
    parts: list[pd.Series] = []
    for column in KEY_COLUMNS:
        if column in KEY_INTEGER_COLUMNS:
            parts.append(frame[column].astype("int64").astype(str))
        else:
            parts.append(frame[column].astype(str).str.strip())
    payload = parts[0]
    for part in parts[1:]:
        payload = payload.str.cat(part, sep="|")
    return payload


def add_student_key(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    payloads = student_key_payload(out)

    def _digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    out["student_key"] = payloads.map(_digest)
    return out


def common_student_count(frame: pd.DataFrame) -> int:
    """İki derste de görünen benzersiz student_key sayısı. Literatürden kopyalanmaz."""
    by_subject = {
        str(subject): set(part["student_key"])
        for subject, part in frame.groupby("subject", sort=False)
    }
    return len(by_subject.get("mat", set()) & by_subject.get("por", set()))


def load_students(raw_dir: Path | None = None) -> pd.DataFrame:
    directory = RAW_DIR if raw_dir is None else Path(raw_dir)
    frames = [
        _read_subject(directory / "student-mat.csv", "mat"),
        _read_subject(directory / "student-por.csv", "por"),
    ]
    combined = pd.concat(frames, ignore_index=True)
    cleaned, missing_count = validate_frame(combined)
    keyed = add_student_key(cleaned)
    keyed.attrs["missing_value_count"] = missing_count
    print(f"ortak_ogrenci_sayisi={common_student_count(keyed)}")
    return keyed
