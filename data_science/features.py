"""Türetilmiş özellikler ve fit edilmemiş ön işlemci. Model eğitmez."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder

from data_science.config import PASS_THRESHOLD_20, PROCESSED_DIR
from data_science.load import BINARY_CATEGORIES, load_students

NOMINAL_COLUMNS = ("Mjob", "Fjob", "reason", "guardian", "subject")

# Sıralı ölçekler ve düz sayılar olduğu gibi kalır. Ölçekleme Hafta 9 CV içindedir.
ORDINAL_COLUMNS = (
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
    "parent_edu_max",
    "alcohol_total",
    "support_any",
    "has_failures",
    "absences_log1p",
    "absence_bucket",
    "G1",
)

# absence_bucket: 0 → 0, 1–5 → 1, 6–10 → 2, 11–20 → 3, 21+ → 4.
ABSENCE_BINS = (-1, 0, 5, 10, 20, np.inf)

EARLY_FEATURES = (
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
    "subject",
    "parent_edu_max",
    "alcohol_total",
    "support_any",
    "has_failures",
    "absences_log1p",
    "absence_bucket",
)

MIDTERM_FEATURES = EARLY_FEATURES + ("G1",)

_FEATURE_SETS = {"early": EARLY_FEATURES, "midterm": MIDTERM_FEATURES}


def feature_columns(feature_set: str) -> list[str]:
    name = feature_set.strip().lower()
    if name not in _FEATURE_SETS:
        raise ValueError(f"bilinmeyen feature_set: {feature_set}")
    return list(_FEATURE_SETS[name])


def absence_bucket(absences: pd.Series) -> pd.Series:
    buckets = pd.cut(absences, bins=list(ABSENCE_BINS), labels=False, right=True)
    return buckets.astype("int64")


def add_derived_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """G3=0 satırları durur. at_risk ve g3_zero G3'ten hesaplanır."""
    out = frame.copy()
    out["g3_zero"] = (out["G3"] == 0).astype("int64")
    out["at_risk"] = (out["G3"] < PASS_THRESHOLD_20).astype("int64")
    out["parent_edu_max"] = out[["Medu", "Fedu"]].max(axis=1).astype("int64")
    out["alcohol_total"] = (out["Dalc"] + out["Walc"]).astype("int64")
    out["support_any"] = ((out["schoolsup"] == "yes") | (out["famsup"] == "yes")).astype("int64")
    out["has_failures"] = (out["failures"] > 0).astype("int64")
    out["absences_log1p"] = np.log1p(out["absences"].astype("float64"))
    out["absence_bucket"] = absence_bucket(out["absences"])
    return out


def build_dataset(frame: pd.DataFrame, feature_set: str) -> pd.DataFrame:
    featured = add_derived_columns(frame)
    columns = feature_columns(feature_set)
    ordered = ["student_key", "subject", "at_risk", "g3_zero"]
    for column in columns:
        if column not in ordered:
            ordered.append(column)
    missing = [column for column in ordered if column not in featured.columns]
    if missing:
        raise ValueError(f"eksik ozellik: {missing}")
    return featured.loc[:, ordered].reset_index(drop=True)


def _column_groups(feature_set: str) -> tuple[list[str], list[str], list[str]]:
    columns = feature_columns(feature_set)
    leaked = {"G2", "G3"} & set(columns)
    if leaked:
        raise ValueError(f"hedef sizintisi: {sorted(leaked)}")
    if feature_set.strip().lower() == "early" and "G1" in columns:
        raise ValueError("EARLY setinde G1 olamaz")
    binary = [column for column in columns if column in BINARY_CATEGORIES]
    nominal = [column for column in columns if column in NOMINAL_COLUMNS]
    ordinal = [column for column in columns if column in ORDINAL_COLUMNS]
    covered = set(binary) | set(nominal) | set(ordinal)
    missing = [column for column in columns if column not in covered]
    if missing:
        raise ValueError(f"siniflanmamis sutun: {missing}")
    return binary, nominal, ordinal


def build_preprocessor(feature_set: str) -> ColumnTransformer:
    """Fit edilmemiş ColumnTransformer. Hafta 9 CV içinde fit edilir.

    İkili kategoriler 0/1, nominal kategoriler one-hot, sıralı ve sayısal
    sütunlar olduğu gibi kalır. Bilinmeyen nominal kategori hata vermez.
    """
    binary_cols, nominal_cols, ordinal_cols = _column_groups(feature_set)
    binary = OrdinalEncoder(
        categories=[list(BINARY_CATEGORIES[column]) for column in binary_cols],
        handle_unknown="use_encoded_value",
        unknown_value=-1,
        encoded_missing_value=-1,
        dtype=np.float64,
    )
    nominal = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False,
        dtype=np.float64,
    )
    return ColumnTransformer(
        transformers=[
            ("binary", binary, binary_cols),
            ("nominal", nominal, nominal_cols),
            ("ordinal", "passthrough", ordinal_cols),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def main() -> None:
    frame = load_students()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for feature_set in ("early", "midterm"):
        table = build_dataset(frame, feature_set)
        build_preprocessor(feature_set)
        table.to_parquet(PROCESSED_DIR / f"features_{feature_set}.parquet", index=False)


if __name__ == "__main__":
    main()
