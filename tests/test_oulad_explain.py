"""Kapasite eğrisi ve grafik katalogu. Ağ yok."""

from __future__ import annotations

import json
import math
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from data_science.oulad.explain import FLAG_RATES, build_report, capacity_curve
from data_science.oulad.figures import _draw_shap, _draw_slope, write_figures
from data_science.oulad.model import precision_recall_at_fraction

PARAMS = {"learning_rate": 0.1, "max_leaf_nodes": 8, "max_iter": 15}


def test_within_module_flag_count_is_ceil_of_rate():
    modules = np.array(["AAA"] * 6 + ["BBB"] * 4 + ["CCC"])
    y = np.array([1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0])
    proba = np.array([0.9, 0.8, 0.1, 0.7, 0.2, 0.3, 0.4, 0.95, 0.05, 0.2, 0.5])
    rows = capacity_curve(modules, y, proba)
    assert [row["flag_rate"] for row in rows] == list(FLAG_RATES)
    for row in rows:
        rate = row["flag_rate"]
        by_module = {item["code_module"]: item for item in row["within_module"]["rows"]}
        assert list(by_module) == ["AAA", "BBB", "CCC"]
        for item in row["within_module"]["rows"]:
            assert item["n_flagged"] == math.ceil(rate * item["n"])
        assert by_module["AAA"]["n_flagged"] == math.ceil(rate * 6)
        assert by_module["BBB"]["n_flagged"] == math.ceil(rate * 4)
        assert by_module["CCC"]["n_flagged"] == math.ceil(rate * 1)
        precision, recall = precision_recall_at_fraction(y, proba, rate)
        assert row["global"]["precision"] == pytest.approx(precision, nan_ok=True)
        assert row["global"]["recall"] == pytest.approx(recall, nan_ok=True)
    at_20 = next(row for row in rows if row["flag_rate"] == 0.2)
    assert at_20["global"]["n_flagged"] == 2
    assert at_20["within_module"]["rows"][0]["n_flagged"] == 2
    assert at_20["within_module"]["rows"][0]["n_hit"] == 1
    assert at_20["within_module"]["rows"][0]["precision"] == 0.5
    assert at_20["within_module"]["rows"][0]["recall"] == pytest.approx(1 / 3)


def _synthetic() -> pd.DataFrame:
    rows = []
    student = 0
    blocks = (("2013J", "train", 24), ("2014J", "test", 12), ("2013B", "history", 4))
    for presentation, split, count in blocks:
        for index in range(count):
            student += 1
            label = int(index % 2 == 0)
            score = 80.0 - 40.0 * label
            rows.append(
                {
                    "code_module": "AAA" if index % 2 == 0 else "BBB",
                    "code_presentation": presentation,
                    "id_student": student,
                    "at_risk": label,
                    "split": split,
                    "date_registration": -20.0 + index,
                    "n_expected": 4,
                    "n_submitted": 3 - label,
                    "n_unsubmitted": label,
                    "score_mean": score,
                    "score_weighted_mean": score,
                    "delay_mean": float(label),
                    "n_banked": 0,
                    "vle_clicks": 30 - 10 * label,
                    "vle_active_days": 8 - 2 * label,
                    "vle_days_to_cutoff": 2 + label,
                }
            )
    return pd.DataFrame(rows)


def test_explain_uses_test_rows_only_for_evaluation(monkeypatch):
    frame = _synthetic()
    seen = {"calls": 0, "n": None, "y": None, "train_n": None, "test_n": None}

    original = Pipeline.fit

    def spy(self, X, y=None, **kwargs):
        seen["calls"] += 1
        seen["n"] = len(X)
        seen["y"] = [int(value) for value in y]
        return original(self, X, y, **kwargs)

    def fake_attribute(model, columns, train_x, test_x):
        seen["train_n"] = len(train_x)
        seen["test_n"] = len(test_x)
        width = len(columns)
        matrix = np.zeros((len(test_x), width), dtype=np.float64)
        values = test_x.to_numpy(dtype=np.float64)
        return matrix, values, list(columns), "TreeExplainer"

    monkeypatch.setattr(Pipeline, "fit", spy)
    monkeypatch.setattr("data_science.oulad.explain._attribute", fake_attribute)
    report = build_report(frame, PARAMS)
    train = frame.loc[frame["split"].eq("train")]
    test = frame.loc[frame["split"].eq("test")]
    assert seen["calls"] == 1
    assert seen["n"] == len(train)
    assert seen["train_n"] == len(train)
    assert seen["test_n"] == len(test)
    assert seen["y"] == [int(value) for value in train["at_risk"]]
    assert "2014J" not in set(train["code_presentation"].astype(str))
    assert set(test["code_presentation"].astype(str)) == {"2014J"}
    assert report["capacity"]["rows"][0]["global"]["n"] == len(test)
    assert report["shap"]["n_explained"] == len(test)
    leaked = frame.copy()
    leaked.loc[leaked.index[0], "code_presentation"] = "2014J"
    leaked.loc[leaked.index[0], "split"] = "train"
    with pytest.raises(ValueError, match="test"):
        build_report(leaked, PARAMS)


def _metrics() -> dict:
    sets = ("GENERAL", "GENERAL_MODULE", "HISTORY", "GENERAL_REL", "HISTORY_SLOT")
    validation = [
        {"set": name, "model": "hgb", "roc_auc": 0.70 + 0.01 * index}
        for index, name in enumerate(sets)
    ]
    test_metrics = {
        name: {
            "hgb": {
                "roc_auc": {
                    "estimate": 0.66 + 0.01 * index,
                    "low": 0.60 + 0.01 * index,
                    "high": 0.72 + 0.01 * index,
                }
            }
        }
        for index, name in enumerate(sets)
    }
    calibration = []
    for module, rate in (("AAA", 0.25), ("GGG", 0.36)):
        for name, prediction in (("GENERAL", 0.40), ("GENERAL_MODULE", 0.30), ("HISTORY", 0.55)):
            calibration.append(
                {
                    "set": name,
                    "code_module": module,
                    "positive_rate": rate,
                    "mean_prediction": prediction,
                }
            )
    lomo = []
    for module, rate, general, relative in (
        ("AAA", 0.25, 0.50, 0.48),
        ("GGG", 0.36, 0.90, 0.80),
    ):
        lomo.append(
            {
                "code_module": module,
                "set": "GENERAL",
                "positive_rate": rate,
                "mean_prediction": general,
            }
        )
        lomo.append(
            {
                "code_module": module,
                "set": "GENERAL_REL",
                "positive_rate": rate,
                "mean_prediction": relative,
            }
        )
    return {
        "validation": {"rows": validation},
        "test_metrics": test_metrics,
        "calibration": {"rows": calibration},
        "lomo": {"rows": lomo},
    }


def _explain() -> dict:
    return {
        "capacity": {
            "rows": [
                {
                    "flag_rate": 0.05,
                    "global": {"precision": 0.80},
                    "within_module": {"precision": 0.76},
                },
                {
                    "flag_rate": 0.10,
                    "global": {"precision": 0.74},
                    "within_module": {"precision": 0.71},
                },
            ]
        },
        "shap": {
            "features": [
                {"feature": "score_mean", "mean_abs_shap": 0.20},
                {"feature": "vle_clicks", "mean_abs_shap": 0.10},
                {"feature": "delay_mean", "mean_abs_shap": 0.05},
            ],
            "dependence": [
                {
                    "feature": "score_mean",
                    "value": [10.0, 20.0, None],
                    "shap": [0.1, -0.2, 0.0],
                }
            ],
        },
    }


def test_figures_catalog_has_both_languages_and_files(tmp_path):
    metrics_path = tmp_path / "model_metrics.json"
    explain_path = tmp_path / "explain.json"
    metrics_path.write_text(json.dumps(_metrics()), encoding="utf-8")
    explain_path.write_text(json.dumps(_explain()), encoding="utf-8")
    dest = tmp_path / "figures"
    write_figures(metrics_path, explain_path, dest)
    catalog = json.loads((dest / "figures.json").read_text(encoding="utf-8"))
    assert len(catalog) == 5
    for item in catalog:
        for key in ("başlık_tr", "başlık_en", "alt_tr", "alt_en"):
            assert isinstance(item[key], str) and item[key]
        assert item["başlık_tr"] != item["başlık_en"]
        assert item["alt_tr"] != item["alt_en"]
        assert re.search(r"\d", item["alt_tr"]) is None
        assert re.search(r"\d", item["alt_en"]) is None
        for lang in ("tr", "en"):
            path = dest / f"{item['dosya']}_{lang}.png"
            assert path.is_file()
            assert path.stat().st_size > 0


def test_slope_figure_has_no_legend():
    fig = _draw_slope(_metrics(), "tr")
    try:
        assert fig.axes[0].get_legend() is None
        assert fig.legends == []
    finally:
        plt.close(fig)


def test_shap_right_panel_x_ticks_are_integers():
    fig = _draw_shap(_explain(), "en")
    try:
        ticks = [float(tick) for tick in fig.axes[1].get_xticks()]
        assert ticks
        for tick in ticks:
            assert math.isclose(tick, round(tick), abs_tol=1e-8)
    finally:
        plt.close(fig)
