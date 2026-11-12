"""Notebook 03 (OULAD model) hücrelerinde tanımlı tablo hesapları. Model yok.

Bu modüldeki her fonksiyon, daha önce notebooks/03_oulad_model.ipynb ve
notebooks/03_oulad_model_eng.ipynb hücrelerinde satır içi yazılmış kodun davranışı
değiştirilmeden taşınmış hâlidir. Notebook'lar yalnızca bu fonksiyonları çağırır ve basar;
scripts/arastirma_paketi.py aynı fonksiyonları çağırır.

Girdi, notebook'un `frame` değişkenidir: data_science/oulad/features_cutoff60.parquet
içeriği (dataset.FEATURES_NAME).
"""

from __future__ import annotations

import pandas as pd


def presentation_counts(frame: pd.DataFrame) -> pd.DataFrame:
    """Sunum başına bölüm (split), satır ve pozitif sayısı (notebook 'sunum sayımları' tablosu)."""
    rows = []
    for presentation, part in frame.groupby(frame["code_presentation"].astype(str), sort=True):
        splits = part["split"].astype(str).unique()
        if len(splits) != 1:
            raise ValueError(presentation)
        rows.append(
            {
                "code_presentation": str(presentation),
                "split": str(splits[0]),
                "n": int(len(part)),
                "n_positive": int((part["at_risk"] == 1).sum()),
            }
        )
    return pd.DataFrame(rows)


def _train_test(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = frame.loc[frame["split"].astype(str).eq("train")]
    test = frame.loc[frame["split"].astype(str).eq("test")]
    return train, test


def train_hist_rate_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Train bölümünde hist_module_risk_rate sütununun farklı değer sayısı (tek satır)."""
    train, _test = _train_test(frame)
    hist_train = pd.to_numeric(train["hist_module_risk_rate"], errors="coerce")
    return pd.DataFrame(
        [
            {
                "split": "train",
                "n": int(len(train)),
                "n_positive": int((train["at_risk"] == 1).sum()),
                "n_distinct_hist_module_risk_rate": int(hist_train.nunique(dropna=True)),
            }
        ]
    )


def base_rate_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Test modülü başına geçmiş modül oranı, bu dönemin oranı ve train yanı (notebook 'taban oran')."""
    train, test = _train_test(frame)
    hist_train = pd.to_numeric(train["hist_module_risk_rate"], errors="coerce")
    train_module = train["code_module"].astype(str)
    test_module = test["code_module"].astype(str)
    train_distinct = hist_train.groupby(train_module).nunique(dropna=True)
    train_n = train.groupby(train_module).size()
    train_positive = train.groupby(train_module)["at_risk"].sum()
    rows = []
    for name, part in test.groupby(test_module, sort=True):
        hist = pd.to_numeric(part["hist_module_risk_rate"], errors="coerce")
        distinct = int(hist.nunique(dropna=True))
        observed = hist.dropna()
        rows.append(
            {
                "code_module": str(name),
                "n": int(len(part)),
                "n_positive": int((part["at_risk"] == 1).sum()),
                "hist_module_risk_rate": float(observed.iloc[0]) if distinct == 1 else float("nan"),
                "positive_rate": float(part["at_risk"].mean()),
                "test_n_distinct_hist_module_risk_rate": distinct,
                "train_n": int(train_n.get(name, 0)),
                "train_n_positive": int(train_positive.get(name, 0)),
                "train_n_distinct_hist_module_risk_rate": int(train_distinct.get(name, 0)),
            }
        )
    return pd.DataFrame(rows)
