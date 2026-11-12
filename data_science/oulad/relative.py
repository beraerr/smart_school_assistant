"""Sunum içi göreli özellikler.

Kaynaklar o sunumun kesim günü 60 sütunlarıdır. Yüzdelik sıra yalnızca
(code_module, code_presentation) içinde hesaplanır. at_risk kullanılmaz.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REL_COLUMNS = (
    "rel_score_mean",
    "rel_submit_ratio",
    "rel_vle_clicks",
    "rel_vle_active_days",
    "rel_vle_recency",
    "rel_delay",
)

_REQUIRED = (
    "code_module",
    "code_presentation",
    "score_mean",
    "n_submitted",
    "n_expected",
    "vle_clicks",
    "vle_active_days",
    "vle_days_to_cutoff",
    "delay_mean",
)


def _finite_array(series: pd.Series) -> np.ndarray:
    values = pd.to_numeric(series, errors="coerce").astype("float64").to_numpy(dtype=np.float64)
    values = np.array(values, dtype=np.float64, copy=True)
    values[~np.isfinite(values)] = np.nan
    return values


def _rank_pct(values: np.ndarray, groups: np.ndarray, higher_is_better: bool) -> np.ndarray:
    """Ortalama sıra / grupta sonlu gözlem sayısı. NaN NaN kalır."""
    ranked = pd.Series(values).groupby(pd.Series(groups), sort=False).rank(
        method="average",
        pct=True,
        ascending=higher_is_better,
        na_option="keep",
    )
    return ranked.to_numpy(dtype=np.float64)


def add_relative_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Her sunum içinde rel_* yüzdelik sıralarını ekler. Girdi değişmez."""
    missing = [column for column in _REQUIRED if column not in frame.columns]
    if missing:
        raise ValueError(f"eksik ozellik: {missing}")
    out = frame.drop(columns=[column for column in REL_COLUMNS if column in frame.columns]).copy()
    groups = np.asarray(
        out["code_module"].astype("string").astype(str)
        + "\x1f"
        + out["code_presentation"].astype("string").astype(str)
    )
    submitted = _finite_array(out["n_submitted"])
    expected = _finite_array(out["n_expected"])
    ratio = np.full(submitted.shape[0], np.nan, dtype=np.float64)
    valid = np.isfinite(submitted) & np.isfinite(expected) & (expected != 0.0)
    ratio[valid] = submitted[valid] / expected[valid]
    sources = (
        ("rel_score_mean", _finite_array(out["score_mean"]), True),
        ("rel_submit_ratio", ratio, True),
        ("rel_vle_clicks", _finite_array(out["vle_clicks"]), True),
        ("rel_vle_active_days", _finite_array(out["vle_active_days"]), True),
        ("rel_vle_recency", _finite_array(out["vle_days_to_cutoff"]), False),
        ("rel_delay", _finite_array(out["delay_mean"]), False),
    )
    for name, values, higher_is_better in sources:
        out[name] = _rank_pct(values, groups, higher_is_better)
    return out
