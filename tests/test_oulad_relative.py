"""Goreli ozellik kontrolleri. Ag yok."""

from __future__ import annotations

import numpy as np
import pandas as pd

from data_science.oulad.relative import REL_COLUMNS, add_relative_features


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code_module": ["AAA", "AAA", "AAA", "BBB", "BBB", "AAA", "AAA"],
            "code_presentation": ["2013J", "2013J", "2013J", "2013J", "2013J", "2014B", "2014B"],
            "id_student": [1, 2, 3, 4, 5, 6, 7],
            "at_risk": [0, 1, 0, 1, 0, 1, 0],
            "score_mean": [10.0, 20.0, 20.0, 1.0, 2.0, 3.0, 4.0],
            "n_submitted": [1, 2, 4, 1, 1, 1, 0],
            "n_expected": [2, 2, 0, 1, 2, 1, 1],
            "vle_clicks": [5.0, 15.0, 10.0, 1.0, 2.0, 3.0, 4.0],
            "vle_active_days": [1, 3, 2, 1, 2, 1, 2],
            "vle_days_to_cutoff": [10.0, 0.0, 5.0, 4.0, 1.0, 2.0, 3.0],
            "delay_mean": [3.0, 1.0, np.nan, 2.0, 0.0, 1.0, 5.0],
        }
    )


def _aaa(frame: pd.DataFrame) -> pd.Series:
    return frame["code_module"].eq("AAA") & frame["code_presentation"].eq("2013J")


def test_relative_ranks_stay_inside_presentation():
    frame = _frame()
    original = frame.copy()
    out = add_relative_features(frame)
    pd.testing.assert_frame_equal(frame, original)
    expected = {
        "rel_score_mean": [1 / 3, 2.5 / 3, 2.5 / 3],
        "rel_submit_ratio": [0.5, 1.0, np.nan],
        "rel_vle_clicks": [1 / 3, 1.0, 2 / 3],
        "rel_vle_active_days": [1 / 3, 1.0, 2 / 3],
        "rel_vle_recency": [1 / 3, 1.0, 2 / 3],
        "rel_delay": [0.5, 1.0, np.nan],
    }
    group = _aaa(frame)
    for column, values in expected.items():
        got = out.loc[group, column].to_numpy(dtype=float)
        assert np.allclose(got, np.asarray(values, dtype=float), equal_nan=True)
    for column in REL_COLUMNS:
        present = out[column].dropna()
        assert ((present >= 0) & (present <= 1)).all()

    changed = frame.copy()
    other = ~group
    changed.loc[other, "score_mean"] = 5.0
    changed.loc[other, "n_submitted"] = 9
    changed.loc[other, "n_expected"] = 9
    changed.loc[other, "vle_clicks"] = 0.0
    changed.loc[other, "vle_active_days"] = 0
    changed.loc[other, "vle_days_to_cutoff"] = 50.0
    changed.loc[other, "delay_mean"] = 100.0
    out_changed = add_relative_features(changed)
    for column in REL_COLUMNS:
        assert np.allclose(
            out.loc[group, column].to_numpy(dtype=float),
            out_changed.loc[group, column].to_numpy(dtype=float),
            equal_nan=True,
        )
    bbb = frame["code_module"].eq("BBB")
    assert not np.allclose(
        out.loc[bbb, "rel_score_mean"].to_numpy(dtype=float),
        out_changed.loc[bbb, "rel_score_mean"].to_numpy(dtype=float),
    )


def test_relative_features_ignore_at_risk():
    frame = _frame()
    out = add_relative_features(frame)
    changed = frame.copy()
    changed["at_risk"] = 1 - changed["at_risk"]
    out_changed = add_relative_features(changed)
    for column in REL_COLUMNS:
        assert np.allclose(
            out[column].to_numpy(dtype=float),
            out_changed[column].to_numpy(dtype=float),
            equal_nan=True,
        )


def test_submit_ratio_is_nan_when_expected_is_zero():
    frame = _frame()
    out = add_relative_features(frame)
    zero = frame["n_expected"].eq(0)
    assert zero.any()
    assert out.loc[zero, "rel_submit_ratio"].isna().all()
    assert out.loc[~zero, "rel_submit_ratio"].notna().all()
