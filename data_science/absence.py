"""UCI devamsızlık analizi: dilim etiketleri, geçme tablosu, G3 ile korelasyon.

Fonksiyonlar 01_uci_eda notebook'undan davranış değişmeden taşınmıştır.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from data_science.features import ABSENCE_BINS


def bucket_labels(bins) -> dict[int, str]:
    """Dilim sınırlarından dilim numarası -> etiket sözlüğü."""
    labels = {}
    edges = list(bins)
    for index, (left, right) in enumerate(zip(edges[:-1], edges[1:])):
        start = 0 if left < 0 else int(left) + 1
        if not np.isfinite(right):
            labels[index] = f"{start}+"
        elif start == int(right):
            labels[index] = str(int(right))
        else:
            labels[index] = f"{start}-{int(right)}"
    return labels


def absence_pass_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Dilim başına satır sayısı ve geçme oranı. `absence_bucket` ve `at_risk` gerekir."""
    labels = bucket_labels(ABSENCE_BINS)
    work = frame.loc[:, ["absence_bucket", "at_risk"]].copy()
    work["passed"] = 1 - work["at_risk"]
    grouped = work.groupby("absence_bucket", sort=True)
    table = pd.DataFrame(
        {
            "n_rows": grouped.size(),
            "pass_rate": grouped["passed"].mean(),
        }
    ).reindex(sorted(labels)).reset_index()
    table["n_rows"] = table["n_rows"].fillna(0).astype(int)
    table["absence_bucket_label"] = table["absence_bucket"].map(labels)
    return table[["absence_bucket", "absence_bucket_label", "n_rows", "pass_rate"]]


def absence_grade_corr(frame: pd.DataFrame) -> tuple[float, float]:
    """absences ile G3 arasında (pearson, spearman)."""
    pearson = float(frame["absences"].corr(frame["G3"], method="pearson"))
    spearman = float(frame["absences"].corr(frame["G3"], method="spearman"))
    return pearson, spearman
