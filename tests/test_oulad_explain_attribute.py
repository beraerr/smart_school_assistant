"""_attribute ve _tree_attribute: tek açıklama yolu, başka yönteme ya da biçime geçilmez. Ağ yok."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data_science.oulad import explain


def test_attribute_raises_when_tree_explainer_fails_and_does_not_fall_back(monkeypatch):
    def failing_tree(model, columns, test_x):
        raise RuntimeError("TreeExplainer desteklenmiyor")

    monkeypatch.setattr(explain, "_tree_attribute", failing_tree)
    frame = pd.DataFrame({"a": [1.0, 2.0]})

    with pytest.raises(RuntimeError, match="TreeExplainer desteklenmiyor"):
        explain._attribute(object(), ["a"], frame, frame)

    assert hasattr(explain, "_permutation_attribute") is False


def test_attribute_returns_tree_result_unchanged(monkeypatch):
    sonuc = ("matris", "degerler", ["a"], "TreeExplainer")
    monkeypatch.setattr(explain, "_tree_attribute", lambda model, columns, test_x: sonuc)
    frame = pd.DataFrame({"a": [1.0]})

    assert explain._attribute(object(), ["a"], frame, frame) is sonuc


def _hgb_hattı(n_rows: int = 120, n_features: int = 4):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import FunctionTransformer

    rng = np.random.default_rng(0)
    columns = [f"x{i}" for i in range(n_features)]
    frame = pd.DataFrame(rng.normal(size=(n_rows, n_features)), columns=columns)
    labels = (frame["x0"] > 0).astype(int)
    model = Pipeline(
        [("pre", FunctionTransformer()), ("clf", HistGradientBoostingClassifier(max_iter=20))]
    ).fit(frame, labels)
    return model, columns, frame


def test_tree_attribute_returns_row_by_feature_matrix_with_pinned_shap():
    model, columns, frame = _hgb_hattı()

    matrix, transformed, names, method = explain._tree_attribute(model, columns, frame)

    assert matrix.shape == (len(frame), len(columns))
    assert transformed.shape == (len(frame), len(columns))
    assert names == columns
    assert method == "TreeExplainer"


def test_shap_matrix_accepts_only_row_by_feature_shape():
    dogru = np.zeros((3, 2))
    assert explain._shap_matrix(dogru, 3, 2).shape == (3, 2)

    for yanlis in (np.zeros((2, 3)), np.zeros((3, 2, 2)), [np.zeros((3, 2)), np.zeros((3, 2))]):
        with pytest.raises(ValueError, match="shap boyutu"):
            explain._shap_matrix(yanlis, 3, 2)
