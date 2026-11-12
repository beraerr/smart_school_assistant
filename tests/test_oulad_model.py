"""Sentetik model kontrolleri. Ag yok."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from data_science.oulad.dataset import HISTORY_VALUE_COLUMNS
from data_science.oulad.load import SOCIO_COLUMNS
from data_science.oulad.model import (
    bootstrap_indices,
    feature_columns,
    lomo_folds,
    metric_intervals,
    paired_difference,
    precision_recall_at_fraction,
    select_hyperparameters,
    validation_report,
    within_module_flags,
)
from data_science.oulad.relative import REL_COLUMNS

ASSIGNMENT = (
    "n_expected",
    "n_submitted",
    "n_unsubmitted",
    "score_mean",
    "score_weighted_mean",
    "delay_mean",
    "n_banked",
)
VLE = (
    "vle_clicks",
    "vle_active_days",
    "vle_days_to_cutoff",
    "vle_click_forumng",
    "vle_click_resource",
)


def _available() -> list[str]:
    return [
        "code_module",
        "code_presentation",
        "id_student",
        "at_risk",
        "split",
        "date_registration",
        *ASSIGNMENT,
        *VLE,
        "has_history",
        *HISTORY_VALUE_COLUMNS,
        *SOCIO_COLUMNS,
        "num_of_prev_attempts",
        "studied_credits",
        "pres_rank",
    ]


def _counts(modules: np.ndarray, y: np.ndarray | None = None) -> dict:
    if y is None:
        out: dict = {}
        for label in modules:
            out[str(label)] = out.get(str(label), 0) + 1
        return out
    out = {}
    for label, value in zip(modules, y):
        key = (str(label), int(value))
        out[key] = out.get(key, 0) + 1
    return out


def test_feature_sets_omit_identity_target_split_and_socio():
    available = _available()
    general = feature_columns("GENERAL", available)
    module = feature_columns("GENERAL_MODULE", available)
    history = feature_columns("HISTORY", available)
    forbidden = set(SOCIO_COLUMNS) | {
        "code_presentation",
        "id_student",
        "at_risk",
        "split",
        "num_of_prev_attempts",
        "studied_credits",
    }
    for columns in (general, module, history):
        assert forbidden.isdisjoint(columns)
    assert set(general) == {"date_registration", *ASSIGNMENT, *VLE}
    assert "code_module" not in general
    assert "has_history" not in general
    assert not any(column.startswith("hist_") for column in general)
    assert set(module) == set(general) | {"code_module"}
    assert "has_history" not in module
    assert not any(column.startswith("hist_") for column in module)
    assert set(history) == set(general) | {
        "hist_slot_mean",
        "hist_slot_submit_rate",
        "score_vs_hist",
        "hist_module_risk_rate",
        "has_history",
    }
    assert "code_module" not in history


def test_select_hyperparameters_rejects_test_rows():
    by_split = pd.DataFrame(
        {
            "split": ["test"],
            "code_presentation": ["2013J"],
            "at_risk": [1],
            "date_registration": [0],
        }
    )
    by_presentation = pd.DataFrame(
        {
            "split": ["train"],
            "code_presentation": ["2014J"],
            "at_risk": [0],
            "date_registration": [0],
        }
    )
    with pytest.raises(ValueError, match="test"):
        select_hyperparameters(by_split, ["date_registration"], "logreg")
    with pytest.raises(ValueError, match="test"):
        select_hyperparameters(by_presentation, ["date_registration"], "logreg")


def test_paired_difference_is_zero_for_identical_predictions():
    y = np.array([1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0])
    proba = np.array([0.2, 0.8, 0.4, 0.1, 0.7, 0.6, 0.3, 0.9, 0.05, 0.55, 0.35, 0.15])
    modules = np.array(["AAA", "AAA", "AAA", "AAA", "BBB", "BBB", "BBB", "BBB", "CCC", "CCC", "CCC", "CCC"])
    diff = paired_difference(y, proba, proba, modules, n_boot=40, seed=42)
    for metric in ("roc_auc", "pr_auc", "brier"):
        assert diff[metric]["estimate"] == 0.0
        assert diff[metric]["low"] == 0.0
        assert diff[metric]["high"] == 0.0


def test_bootstrap_intervals_match_for_the_same_seed():
    y = np.array([1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0])
    proba = np.array([0.2, 0.8, 0.4, 0.1, 0.7, 0.6, 0.3, 0.9, 0.05, 0.55, 0.35, 0.15])
    modules = np.array(["AAA", "AAA", "AAA", "AAA", "BBB", "BBB", "BBB", "BBB", "CCC", "CCC", "CCC", "CCC"])
    assert np.array_equal(
        bootstrap_indices(modules, y, 30, 42),
        bootstrap_indices(modules, y, 30, 42),
    )
    first = metric_intervals(y, proba, modules, n_boot=30, seed=42)
    second = metric_intervals(y, proba, modules, n_boot=30, seed=42)
    assert first == second


def test_precision_recall_at_20_matches_hand_count():
    y = np.array([1, 0, 1, 0, 0, 1, 0, 0, 1, 0])
    proba = np.array([0.91, 0.90, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10, 0.05])
    # n=10, bayrak=2. Siralama 0.91 ve 0.90, etiket 1 ve 0. precision=1/2, recall=1/4.
    precision, recall = precision_recall_at_fraction(y, proba, 0.2)
    assert precision == 0.5
    assert recall == 0.25


def test_existing_feature_lists_unchanged():
    base = _available()
    with_relative = [*base, *REL_COLUMNS]
    for name in ("GENERAL", "GENERAL_MODULE", "HISTORY"):
        assert feature_columns(name, base) == feature_columns(name, with_relative)
    general = feature_columns("GENERAL", with_relative)
    module = feature_columns("GENERAL_MODULE", with_relative)
    history = feature_columns("HISTORY", with_relative)
    assert set(general) == {"date_registration", *ASSIGNMENT, *VLE}
    assert set(module) == set(general) | {"code_module"}
    assert set(history) == set(general) | {
        "hist_slot_mean",
        "hist_slot_submit_rate",
        "score_vs_hist",
        "hist_module_risk_rate",
        "has_history",
    }
    assert not any(column.startswith("rel_") for column in (*general, *module, *history))
    assert feature_columns("GENERAL_REL", with_relative) == [*REL_COLUMNS, "date_registration"]
    slot = feature_columns("HISTORY_SLOT", with_relative)
    assert slot == [
        *general,
        "hist_slot_mean",
        "hist_slot_submit_rate",
        "score_vs_hist",
        "has_history",
    ]
    assert "hist_module_risk_rate" not in slot
    assert "code_module" not in slot


def test_lomo_training_excludes_the_test_module():
    frame = pd.DataFrame(
        {
            "code_module": ["AAA", "AAA", "AAA", "BBB", "BBB", "BBB", "CCC"],
            "code_presentation": ["2013J", "2014B", "2014J", "2013J", "2014J", "2013B", "2014J"],
            "split": ["train", "train", "test", "train", "test", "history", "test"],
        }
    )
    folds = {fold["code_module"]: fold for fold in lomo_folds(frame)}
    assert list(folds) == ["AAA", "BBB", "CCC"]
    for name, fold in folds.items():
        train = frame.iloc[np.flatnonzero(fold["train"])]
        test = frame.iloc[np.flatnonzero(fold["test"])]
        assert name not in set(train["code_module"].astype(str))
        assert set(test["code_module"].astype(str)) == {name}
        assert set(test["code_presentation"].astype(str)) == {"2014J"}
        assert set(train["split"].astype(str)) <= {"train"}
    aaa_train = frame.iloc[np.flatnonzero(folds["AAA"]["train"])]
    assert list(aaa_train["code_module"]) == ["BBB"]


def test_validation_report_rejects_2014j_rows():
    frame = pd.DataFrame(
        {
            "split": ["train"],
            "code_presentation": ["2014J"],
            "code_module": ["AAA"],
            "at_risk": [0],
            "date_registration": [0.0],
        }
    )
    with pytest.raises(ValueError, match="test"):
        validation_report(frame, {})


def test_within_module_flag_selects_ceil_fraction():
    # AAA n=6 -> 2, BBB n=4 -> 1, CCC n=1 -> 1.
    modules = np.array(
        ["AAA", "AAA", "AAA", "AAA", "AAA", "AAA", "BBB", "BBB", "BBB", "BBB", "CCC"]
    )
    y = np.array([1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0])
    proba = np.array([0.9, 0.8, 0.1, 0.7, 0.2, 0.3, 0.4, 0.95, 0.05, 0.2, 0.5])
    result = within_module_flags(modules, y, proba)
    by_module = {row["code_module"]: row for row in result["rows"]}
    assert list(by_module) == ["AAA", "BBB", "CCC"]
    for row in result["rows"]:
        assert row["n_flagged"] == math.ceil(0.2 * row["n"])
    assert by_module["AAA"]["n_flagged"] == 2
    assert by_module["BBB"]["n_flagged"] == 1
    assert by_module["CCC"]["n_flagged"] == 1
    assert by_module["AAA"]["n_hit"] == 1
    assert by_module["AAA"]["n_positive"] == 3
    assert by_module["AAA"]["precision"] == 1 / 2
    assert by_module["AAA"]["recall"] == 1 / 3
    assert by_module["BBB"]["n_hit"] == 0
    assert by_module["BBB"]["precision"] == 0.0
    assert by_module["BBB"]["recall"] == 0.0
    assert by_module["CCC"]["n_hit"] == 0
    assert by_module["CCC"]["n_positive"] == 0
    assert math.isnan(by_module["CCC"]["recall"])
    total = result["total"]
    assert total["n"] == 11
    assert total["n_positive"] == 4
    assert total["n_flagged"] == 4
    assert total["n_hit"] == 1
    assert total["precision"] == 1 / 4
    assert total["recall"] == 1 / 4
    # Genel kesim tabani durur: n=6 icin floor(0.2*n)=1.
    precision, recall = precision_recall_at_fraction(y[:6], proba[:6], 0.2)
    assert precision == 1.0
    assert recall == 1 / 3


def test_stratified_bootstrap_preserves_module_counts():
    y = np.array([1, 0, 1, 0, 0, 1, 0])
    modules = np.array(["AAA", "AAA", "AAA", "BBB", "BBB", "CCC", "CCC"])
    indices = bootstrap_indices(modules, y, n_boot=25, seed=42)
    expected_modules = _counts(modules)
    expected_classes = _counts(modules, y)
    for sample in indices:
        assert _counts(modules[sample]) == expected_modules
        assert _counts(modules[sample], y[sample]) == expected_classes
