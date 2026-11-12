"""OULAD tablolarını açık dtype ile okur. studentVle bu modülde yüklenmez."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_science.oulad import RAW_OULAD_DIR

KEY_COLUMNS = (
    "code_module",
    "code_presentation",
    "id_student",
    "id_assessment",
    "id_site",
)

STUDENT_KEY_COLUMNS = (
    "code_module",
    "code_presentation",
    "id_student",
)

# Belgelenen sosyo-demografik sütunlar. Tabloda kalır; silinmez ve kullanılmaz.
SOCIO_COLUMNS = (
    "gender",
    "region",
    "highest_education",
    "imd_band",
    "age_band",
    "disability",
)

TABLE_FILES = {
    "courses": "courses.csv",
    "assessments": "assessments.csv",
    "vle": "vle.csv",
    "studentInfo": "studentInfo.csv",
    "studentRegistration": "studentRegistration.csv",
    "studentAssessment": "studentAssessment.csv",
}

TABLE_DTYPES: dict[str, dict[str, str]] = {
    "courses": {
        "code_module": "string",
        "code_presentation": "string",
        "module_presentation_length": "int64",
    },
    "assessments": {
        "code_module": "string",
        "code_presentation": "string",
        "id_assessment": "int64",
        "assessment_type": "string",
        "date": "Int64",
        "weight": "float64",
    },
    "vle": {
        "id_site": "int64",
        "code_module": "string",
        "code_presentation": "string",
        "activity_type": "string",
        "week_from": "Int64",
        "week_to": "Int64",
    },
    "studentInfo": {
        "code_module": "string",
        "code_presentation": "string",
        "id_student": "int64",
        "gender": "string",
        "region": "string",
        "highest_education": "string",
        "imd_band": "string",
        "age_band": "string",
        "num_of_prev_attempts": "int64",
        "studied_credits": "int64",
        "disability": "string",
        "final_result": "string",
    },
    "studentRegistration": {
        "code_module": "string",
        "code_presentation": "string",
        "id_student": "int64",
        "date_registration": "Int64",
        "date_unregistration": "Int64",
    },
    "studentAssessment": {
        "id_assessment": "int64",
        "id_student": "int64",
        "date_submitted": "Int64",
        "is_banked": "int64",
        "score": "Int64",
    },
}


def _pandas_dtype(kind: str) -> str:
    if kind in {"string", "int64", "Int64", "float64"}:
        return kind
    raise ValueError(f"bilinmeyen dtype: {kind}")


def _clean_columns(columns: pd.Index) -> list[str]:
    return [str(column).replace("\ufeff", "").strip() for column in columns]


def _cast_frame(frame: pd.DataFrame, dtypes: dict[str, str]) -> pd.DataFrame:
    missing = [column for column in dtypes if column not in frame.columns]
    if missing:
        raise ValueError(f"eksik sutunlar: {missing}")
    for column, kind in dtypes.items():
        if kind == "string":
            frame[column] = frame[column].astype("string")
            continue
        try:
            numeric = pd.to_numeric(frame[column], errors="raise")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{column} sayisal degil") from exc
        if kind == "float64":
            frame[column] = numeric.astype("float64")
            continue
        integral = numeric.dropna()
        if ((integral % 1) != 0).any():
            raise ValueError(f"{column} sayisal degil")
        if kind == "int64":
            if numeric.isna().any():
                raise ValueError(f"{column} sayisal degil")
            frame[column] = numeric.astype("int64")
        elif kind == "Int64":
            frame[column] = numeric.astype("Int64")
        else:
            raise ValueError(f"bilinmeyen dtype: {kind}")
    return frame


def _read_csv(path: Path, dtypes: dict[str, str], chunksize: int | None = None):
    if not path.is_file():
        raise FileNotFoundError(path)
    kwargs: dict[str, object] = {
        "na_values": ["?"],
        "keep_default_na": True,
        "encoding": "utf-8",
        "dtype": {column: _pandas_dtype(kind) for column, kind in dtypes.items()},
    }
    if chunksize is not None:
        kwargs["chunksize"] = chunksize
    return pd.read_csv(path, **kwargs)


def read_typed_csv(path: Path, dtypes: dict[str, str]) -> pd.DataFrame:
    frame = _read_csv(path, dtypes)
    frame.columns = _clean_columns(frame.columns)
    return _cast_frame(frame, dtypes)


def iter_typed_csv(path: Path, dtypes: dict[str, str], chunksize: int):
    if chunksize < 1:
        raise ValueError("chunksize en az 1 olmali")
    reader = _read_csv(path, dtypes, chunksize=chunksize)
    for chunk in reader:
        chunk.columns = _clean_columns(chunk.columns)
        yield _cast_frame(chunk, dtypes)


def load_table(name: str, raw_dir: Path | None = None) -> pd.DataFrame:
    if name not in TABLE_FILES:
        raise ValueError(f"bilinmeyen tablo: {name}")
    directory = RAW_OULAD_DIR if raw_dir is None else Path(raw_dir)
    return read_typed_csv(directory / TABLE_FILES[name], TABLE_DTYPES[name])


def load_tables(raw_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    return {name: load_table(name, raw_dir) for name in TABLE_FILES}
