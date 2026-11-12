"""data_science.absence birim testleri ve Hafta 8 değerleriyle karşılaştırma. Ağ yok."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from data_science.absence import absence_grade_corr, absence_pass_table, bucket_labels
from data_science.config import RAW_DIR, REPORTS_DIR
from data_science.eda import build_absence_summary
from data_science.features import ABSENCE_BINS, absence_bucket
from data_science.load import load_students


def _synthetic() -> pd.DataFrame:
    absences = pd.Series([0, 0, 0, 3, 5, 6, 10, 11, 20, 21, 30, 4])
    at_risk = pd.Series([1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0])
    frame = pd.DataFrame(
        {
            "absences": absences,
            "G3": [0, 12, 15, 11, 8, 14, 9, 7, 5, 6, 13, 16],
            "at_risk": at_risk,
        }
    )
    frame["absence_bucket"] = absence_bucket(frame["absences"])
    return frame


def test_bucket_labels_follow_features_bins():
    assert bucket_labels(ABSENCE_BINS) == {0: "0", 1: "1-5", 2: "6-10", 3: "11-20", 4: "21+"}


def test_pass_table_counts_and_rates():
    table = absence_pass_table(_synthetic())
    assert list(table["absence_bucket_label"]) == ["0", "1-5", "6-10", "11-20", "21+"]
    assert list(table["n_rows"]) == [3, 3, 2, 2, 2]
    expected = [2 / 3, 2 / 3, 0.5, 0.0, 0.5]
    assert np.allclose(table["pass_rate"].to_numpy(), expected)


def test_pass_table_keeps_empty_bucket_as_zero_rows():
    frame = _synthetic()
    table = absence_pass_table(frame.loc[frame["absences"] <= 10])
    assert list(table["n_rows"]) == [3, 3, 2, 0, 0]
    assert table["pass_rate"].iloc[3:].isna().all()


def test_grade_corr_matches_pandas():
    frame = _synthetic()
    pearson, spearman = absence_grade_corr(frame)
    assert pearson == pytest.approx(float(frame["absences"].corr(frame["G3"])))
    assert spearman == pytest.approx(float(frame["absences"].corr(frame["G3"], method="spearman")))
    assert -1.0 <= pearson <= 1.0 and -1.0 <= spearman <= 1.0


needs_uci = pytest.mark.skipif(
    not ((RAW_DIR / "student-mat.csv").is_file() and (RAW_DIR / "student-por.csv").is_file()),
    reason="UCI ham verisi diskte yok",
)

WEEK8_CORR = {
    "pearson_all": -0.05,
    "pearson_excl": -0.22,
    "spearman_all": -0.11,
    "spearman_excl": -0.24,
}
WEEK8_BUCKETS = [
    # bucket, n_excl, pass_all, pass_excl
    ("0", 306, 0.766, 0.899),
    ("1-5", 368, 0.834, 0.834),
    ("6-10", 202, 0.787, 0.787),
    ("11-20", 92, 0.663, 0.663),
    ("21+", 23, 0.522, 0.522),
]


@pytest.fixture(scope="module")
def real_absence() -> dict:
    return build_absence_summary(load_students())


@needs_uci
def test_week8_correlations(real_absence):
    for name, expected in WEEK8_CORR.items():
        assert round(real_absence[name], 2) == expected, name


@needs_uci
def test_week8_buckets(real_absence):
    buckets = real_absence["buckets"]
    assert [row["bucket"] for row in buckets] == [row[0] for row in WEEK8_BUCKETS]
    for row, (label, n_excl, pass_all, pass_excl) in zip(buckets, WEEK8_BUCKETS):
        assert set(row) == {"bucket", "n_excl", "pass_all", "pass_excl"}
        assert row["n_excl"] == n_excl, label
        assert round(row["pass_all"], 3) == pass_all, label
        assert round(row["pass_excl"], 3) == pass_excl, label


@needs_uci
def test_eda_summary_json_matches_fresh_computation(real_absence):
    path = REPORTS_DIR / "eda_summary.json"
    assert path.is_file(), "eda_summary.json yok; önce data_science.eda çalıştırılmalı"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert "absence" in written, "eda_summary.json eski; data_science.eda yeniden çalıştırılmalı"
    stored = written["absence"]
    assert [row["bucket"] for row in stored["buckets"]] == [row["bucket"] for row in real_absence["buckets"]]
    for name in WEEK8_CORR:
        assert math.isclose(stored[name], real_absence[name], rel_tol=0, abs_tol=1e-12)
    for left, right in zip(stored["buckets"], real_absence["buckets"]):
        assert left["n_excl"] == right["n_excl"]
        assert math.isclose(left["pass_all"], right["pass_all"], abs_tol=1e-12)
        assert math.isclose(left["pass_excl"], right["pass_excl"], abs_tol=1e-12)
