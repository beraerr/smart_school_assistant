"""Sentetik CSV ile yükleme ve özellik sözleşmesi. Ağ yok."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.exceptions import NotFittedError
from sklearn.utils.validation import check_is_fitted

from data_science.features import (
    add_derived_columns,
    build_dataset,
    build_preprocessor,
    feature_columns,
)
from data_science.load import (
    CATEGORICAL_COLUMNS,
    KEY_COLUMNS,
    KEY_INTEGER_COLUMNS,
    NUMERIC_COLUMNS,
    load_students,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load() -> pd.DataFrame:
    return load_students(FIXTURE_DIR)


def _dense(transformed) -> np.ndarray:
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()
    return np.asarray(transformed, dtype=float)


def test_load_columns_and_dtypes():
    frame = _load()
    for column in NUMERIC_COLUMNS:
        assert column in frame.columns
        assert pd.api.types.is_numeric_dtype(frame[column])
    for column in CATEGORICAL_COLUMNS:
        assert column in frame.columns
        assert pd.api.types.is_object_dtype(frame[column]) or pd.api.types.is_string_dtype(
            frame[column]
        )
    assert set(frame["subject"].unique()) == {"mat", "por"}
    assert frame["student_key"].map(lambda value: len(str(value)) == 64).all()
    assert int(frame.isna().sum().sum()) == 0


def test_student_key_is_deterministic():
    first = _load()
    second = _load()
    assert first["student_key"].tolist() == second["student_key"].tolist()
    per_identity = first.groupby(list(KEY_COLUMNS), dropna=False)["student_key"].nunique()
    assert (per_identity == 1).all()
    assert (first.groupby("student_key")["G3"].nunique() > 1).any()

    row = first.iloc[0]
    parts: list[str] = []
    for column in KEY_COLUMNS:
        value = row[column]
        if column in KEY_INTEGER_COLUMNS:
            parts.append(str(int(value)))
        else:
            parts.append(str(value).strip())
    expected = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    assert row["student_key"] == expected
    same_key = first.loc[first["student_key"] == row["student_key"], "G3"]
    assert same_key.nunique() > 1


def test_at_risk_threshold_keeps_g3_zero():
    raw = _load()
    featured = add_derived_columns(raw)
    assert (featured["G3"] == 9).any()
    assert (featured["G3"] == 10).any()
    assert set(featured.loc[featured["G3"] == 9, "at_risk"].tolist()) == {1}
    assert set(featured.loc[featured["G3"] == 10, "at_risk"].tolist()) == {0}
    assert (featured["G3"] == 0).any()
    assert len(featured) == len(raw)
    assert (featured.loc[featured["G3"] == 0, "g3_zero"] == 1).all()
    assert (featured.loc[featured["G3"] != 0, "g3_zero"] == 0).all()


def test_early_and_midterm_grade_columns():
    raw = _load()
    early_columns = feature_columns("early")
    midterm_columns = feature_columns("midterm")
    for banned in ("G1", "G2", "G3"):
        assert banned not in early_columns
    assert "G1" in midterm_columns
    assert "G2" not in midterm_columns
    assert "G3" not in midterm_columns

    early = build_dataset(raw, "early")
    midterm = build_dataset(raw, "midterm")
    for banned in ("G1", "G2", "G3"):
        assert banned not in early.columns
    assert "G2" not in midterm.columns
    assert "G3" not in midterm.columns
    assert "G1" in midterm.columns
    for table in (early, midterm):
        assert {"student_key", "subject", "at_risk"} <= set(table.columns)
        assert len(table) == len(raw)


def test_preprocessor_unfitted_transform_has_no_nan_and_accepts_unknown():
    raw = _load()
    early = build_dataset(raw, "early")
    columns = feature_columns("early")
    features = early[columns]
    preprocessor = build_preprocessor("early")
    with pytest.raises(NotFittedError):
        check_is_fitted(preprocessor)

    fitted = preprocessor.fit_transform(features)
    assert not np.isnan(_dense(fitted)).any()

    unknown = features.copy()
    unknown.loc[unknown.index[0], "Mjob"] = "astronaut"
    unknown.loc[unknown.index[0], "reason"] = "not_a_reason"
    unknown.loc[unknown.index[0], "school"] = "ZZ"
    transformed = preprocessor.transform(unknown)
    assert not np.isnan(_dense(transformed)).any()

    midterm = build_dataset(raw, "midterm")
    midterm_preprocessor = build_preprocessor("midterm")
    midterm_out = midterm_preprocessor.fit_transform(midterm[feature_columns("midterm")])
    assert not np.isnan(_dense(midterm_out)).any()
