"""Kesim günü 60: genel, göreli ve ders geçmişli modeller.

Ayar 2013J üzerinde eğitilir ve 2014B log loss ile seçilir. Seçilen ayar
train (2013J + 2014B) üzerinde yeniden oturtulur. Test (2014J) yalnızca
son değerlendirmede kullanılır. Doğrulama, seçilen ayarla yalnızca 2013J
üzerinde eğitilmiş modelin 2014B tahminleridir. LOMO, seçilen hgb ayarıyla
her modülü eğitimden çıkarır; ayar yenilenmez.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from data_science.oulad import PROCESSED_OULAD_DIR
from data_science.oulad.dataset import FEATURES_NAME, HISTORY_VALUE_COLUMNS
from data_science.oulad.load import SOCIO_COLUMNS
from data_science.oulad.relative import REL_COLUMNS, add_relative_features

RANDOM_STATE = 42
N_BOOTSTRAP = 1000
TOP_FRACTION = 0.2
FIT_PRESENTATION = "2013J"
VAL_PRESENTATION = "2014B"
TEST_PRESENTATION = "2014J"

PREDICTIONS_NAME = "predictions_cutoff60.parquet"
REPORT_PATH = Path(__file__).resolve().parent / "reports" / "model_metrics.json"

BASE_SET_NAMES = ("GENERAL", "GENERAL_MODULE", "HISTORY")
SET_NAMES = (*BASE_SET_NAMES, "GENERAL_REL", "HISTORY_SLOT")
LOMO_SET_NAMES = ("GENERAL", "GENERAL_MODULE", "GENERAL_REL", "HISTORY")
MODEL_NAMES = ("logreg", "hgb")
ASSIGNMENT_COLUMNS = (
    "n_expected",
    "n_submitted",
    "n_unsubmitted",
    "score_mean",
    "score_weighted_mean",
    "delay_mean",
    "n_banked",
)
VLE_COLUMNS = (
    "vle_clicks",
    "vle_active_days",
    "vle_days_to_cutoff",
)
HISTORY_COLUMNS = (*HISTORY_VALUE_COLUMNS, "has_history")
HISTORY_SLOT_COLUMNS = (
    "hist_slot_mean",
    "hist_slot_submit_rate",
    "score_vs_hist",
    "has_history",
)
ID_COLUMNS = ("code_module", "code_presentation", "id_student")
BLOCKED_COLUMNS = frozenset(SOCIO_COLUMNS) | {
    "code_presentation",
    "id_student",
    "at_risk",
    "split",
}
METRIC_NAMES = (
    "roc_auc",
    "pr_auc",
    "brier",
    "log_loss",
    "precision_at_20",
    "recall_at_20",
)
PAIRED_METRICS = ("roc_auc", "pr_auc", "brier")
PAIRED_CONTRASTS = (
    ("HISTORY-GENERAL", "HISTORY", "GENERAL"),
    ("HISTORY-GENERAL_MODULE", "HISTORY", "GENERAL_MODULE"),
    ("GENERAL_REL-GENERAL", "GENERAL_REL", "GENERAL"),
    ("GENERAL_REL-GENERAL_MODULE", "GENERAL_REL", "GENERAL_MODULE"),
    ("HISTORY_SLOT-GENERAL", "HISTORY_SLOT", "GENERAL"),
)
LOGREG_GRID = ({"C": 0.01}, {"C": 0.1}, {"C": 1.0})
HGB_GRID = tuple(
    {
        "learning_rate": learning_rate,
        "max_leaf_nodes": max_leaf_nodes,
        "max_iter": max_iter,
    }
    for learning_rate in (0.05, 0.1)
    for max_leaf_nodes in (15, 31)
    for max_iter in (200, 400)
)


def feature_columns(set_name: str, available: list[str] | tuple[str, ...]) -> list[str]:
    """Sete giren sutunlar. Kimlik, hedef, split ve sosyokulturel sutun yok."""
    if set_name not in SET_NAMES:
        raise ValueError(f"bilinmeyen set: {set_name}")
    present = set(available)
    if set_name == "GENERAL_REL":
        required = [*REL_COLUMNS, "date_registration"]
        missing = [column for column in required if column not in present]
        if missing:
            raise ValueError(f"eksik ozellik: {missing}")
        columns = [*REL_COLUMNS, "date_registration"]
        _assert_allowed(columns, set_name)
        return columns

    required = ["date_registration", *ASSIGNMENT_COLUMNS, *VLE_COLUMNS]
    if set_name == "GENERAL_MODULE":
        required.append("code_module")
    if set_name == "HISTORY":
        required.extend(HISTORY_COLUMNS)
    if set_name == "HISTORY_SLOT":
        required.extend(HISTORY_SLOT_COLUMNS)
    missing = [column for column in required if column not in present]
    if missing:
        raise ValueError(f"eksik ozellik: {missing}")

    columns: list[str] = []
    for column in (*ASSIGNMENT_COLUMNS, *VLE_COLUMNS):
        columns.append(column)
    for column in available:
        if column.startswith("vle_click_") and column not in columns and column not in BLOCKED_COLUMNS:
            columns.append(column)
    columns.append("date_registration")
    if set_name == "GENERAL_MODULE":
        columns.append("code_module")
    if set_name == "HISTORY":
        columns.extend(HISTORY_COLUMNS)
    if set_name == "HISTORY_SLOT":
        columns.extend(HISTORY_SLOT_COLUMNS)
    _assert_allowed(columns, set_name)
    return columns


def _assert_allowed(columns: list[str], set_name: str) -> None:
    banned = [column for column in columns if column in BLOCKED_COLUMNS]
    if banned:
        raise ValueError(f"yasak sutun: {banned}")
    if set_name != "GENERAL_MODULE" and "code_module" in columns:
        raise ValueError("code_module bu sette yok")
    if set_name == "HISTORY_SLOT" and "hist_module_risk_rate" in columns:
        raise ValueError("hist_module_risk_rate bu sette yok")
    if set_name == "GENERAL_REL":
        allowed = set(REL_COLUMNS) | {"date_registration"}
        extra = [column for column in columns if column not in allowed]
        if extra:
            raise ValueError(f"goreli sette fazla sutun: {extra}")
        return
    if any(column.startswith("rel_") for column in columns):
        raise ValueError("goreli sutun bu sette yok")
    if set_name not in ("HISTORY", "HISTORY_SLOT"):
        leaked = [
            column
            for column in columns
            if column == "has_history" or column.startswith("hist_")
        ]
        if leaked:
            raise ValueError(f"gecmis sutunu bu sette yok: {leaked}")


def _contains_test_rows(frame: pd.DataFrame) -> bool:
    if "split" in frame.columns and frame["split"].astype(str).eq("test").any():
        return True
    if "code_presentation" in frame.columns and frame["code_presentation"].astype(str).eq(TEST_PRESENTATION).any():
        return True
    return False


def _target(frame: pd.DataFrame, column: str = "at_risk") -> np.ndarray:
    if column not in frame.columns:
        raise ValueError(f"{column} yok")
    values = pd.to_numeric(frame[column], errors="coerce")
    if values.isna().any():
        raise ValueError(f"{column} bos")
    return values.to_numpy(dtype=np.int64)


def design_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    data = pd.DataFrame(index=frame.index)
    for column in columns:
        if column == "code_module":
            data[column] = frame[column].astype("string").astype(str)
        else:
            data[column] = pd.to_numeric(frame[column], errors="coerce").astype("float64")
    return data


class _KeepObserved(BaseEstimator, TransformerMixin):
    """Gozlenen degeri olan sutunlari oldugu gibi birakir. Tamami bos sutun cikar."""

    def fit(self, X, y=None):
        array = np.asarray(X, dtype=np.float64)
        self.n_features_in_ = array.shape[1]
        self.keep_ = np.any(~np.isnan(array), axis=0)
        self._fallback = not bool(self.keep_.any())
        return self

    def transform(self, X):
        array = np.asarray(X, dtype=np.float64)
        if self._fallback:
            return np.zeros((array.shape[0], 1), dtype=np.float64)
        return array[:, self.keep_]


def make_estimator(model_name: str, params: dict, columns: list[str]):
    numeric = [column for column in columns if column != "code_module"]
    has_module = "code_module" in columns
    if model_name == "logreg":
        numeric_step = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                ("scaler", StandardScaler()),
            ]
        )
        classifier = LogisticRegression(
            C=float(params["C"]),
            solver="lbfgs",
            max_iter=1000,
            random_state=RANDOM_STATE,
        )
    elif model_name == "hgb":
        numeric_step = _KeepObserved()
        classifier = HistGradientBoostingClassifier(
            learning_rate=float(params["learning_rate"]),
            max_leaf_nodes=int(params["max_leaf_nodes"]),
            max_iter=int(params["max_iter"]),
            early_stopping=False,
            categorical_features=None,
            random_state=RANDOM_STATE,
        )
    else:
        raise ValueError(f"bilinmeyen model: {model_name}")

    if has_module:
        preprocessor = ColumnTransformer(
            transformers=[
                ("numeric", numeric_step, numeric),
                (
                    "module",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=np.float64),
                    ["code_module"],
                ),
            ],
            remainder="drop",
        )
        return Pipeline([("pre", preprocessor), ("clf", classifier)])
    return Pipeline([("pre", numeric_step), ("clf", classifier)])


def _positive_proba(model, features: pd.DataFrame) -> np.ndarray:
    proba = np.asarray(model.predict_proba(features), dtype=np.float64)
    classifier = model.named_steps["clf"] if hasattr(model, "named_steps") and "clf" in model.named_steps else model
    classes = np.asarray(classifier.classes_)
    match = np.flatnonzero(classes == 1)
    if match.size != 1:
        raise ValueError("pozitif sinif yok")
    return np.asarray(proba[:, int(match[0])], dtype=np.float64)


def _grid(model_name: str) -> tuple[dict, ...]:
    if model_name == "logreg":
        return LOGREG_GRID
    if model_name == "hgb":
        return HGB_GRID
    raise ValueError(f"bilinmeyen model: {model_name}")


def select_hyperparameters(
    frame: pd.DataFrame,
    columns: list[str],
    model_name: str,
    target_column: str = "at_risk",
) -> dict:
    """2013J ile egit, 2014B log loss ile sec. Test satiri varsa hata verir."""
    if _contains_test_rows(frame):
        raise ValueError("test bolumu ayarda kullanilamaz")
    if "code_presentation" not in frame.columns:
        raise ValueError("code_presentation yok")
    presentation = frame["code_presentation"].astype(str).to_numpy()
    y = _target(frame, target_column)
    fit = presentation == FIT_PRESENTATION
    val = presentation == VAL_PRESENTATION
    if not fit.any() or not val.any():
        raise ValueError("ayar icin 2013J ve 2014B gerekli")
    if np.unique(y[fit]).size < 2:
        raise ValueError("2013J tek sinif")

    features = design_frame(frame, list(columns))
    fit_rows = features.iloc[np.flatnonzero(fit)]
    val_rows = features.iloc[np.flatnonzero(val)]
    y_fit = y[fit]
    y_val = y[val]
    best_params = None
    best_loss = None
    for params in _grid(model_name):
        model = make_estimator(model_name, params, list(columns))
        model.fit(fit_rows, y_fit)
        loss = float(log_loss(y_val, _positive_proba(model, val_rows), labels=[0, 1]))
        if best_loss is None or loss < best_loss:
            best_loss = loss
            best_params = dict(params)
    return {"params": best_params, "val_log_loss": float(best_loss)}


def validation_report(frame: pd.DataFrame, selected: dict) -> dict:
    """Secilen ayarla 2013J egitimi ve 2014B tahminleri. 2014J satiri hata verir."""
    if _contains_test_rows(frame):
        raise ValueError("test bolumu dogrulamada kullanilamaz")
    if "code_presentation" not in frame.columns or "code_module" not in frame.columns:
        raise ValueError("code_presentation yok")
    presentation = frame["code_presentation"].astype(str).to_numpy()
    y = _target(frame)
    fit = presentation == FIT_PRESENTATION
    val = presentation == VAL_PRESENTATION
    if not fit.any() or not val.any():
        raise ValueError("dogrulama icin 2013J ve 2014B gerekli")
    if np.unique(y[fit]).size < 2:
        raise ValueError("2013J tek sinif")

    module_labels = frame["code_module"].astype(str).to_numpy()
    rows = []
    module_rows = []
    for set_name in SET_NAMES:
        columns = feature_columns(set_name, list(frame.columns))
        features = design_frame(frame, columns)
        fit_rows = features.iloc[np.flatnonzero(fit)]
        val_rows = features.iloc[np.flatnonzero(val)]
        y_fit = y[fit]
        y_val = y[val]
        val_modules = module_labels[val]
        for model_name in MODEL_NAMES:
            params = selected[set_name][model_name]["params"]
            model = make_estimator(model_name, params, columns)
            model.fit(fit_rows, y_fit)
            proba = _positive_proba(model, val_rows)
            stats = metric_values(y_val, proba)
            rows.append(
                {
                    "set": set_name,
                    "model": model_name,
                    "roc_auc": stats["roc_auc"],
                    "pr_auc": stats["pr_auc"],
                    "brier": stats["brier"],
                    "log_loss": stats["log_loss"],
                    "mean_prediction": float(np.mean(proba)),
                    "positive_rate": float(np.mean(y_val)),
                }
            )
            if model_name != "hgb":
                continue
            for module in sorted(set(val_modules.tolist())):
                mask = val_modules == module
                module_y = y_val[mask]
                module_rows.append(
                    {
                        "set": set_name,
                        "code_module": module,
                        "n": int(mask.sum()),
                        "n_positive": int(np.sum(module_y == 1)),
                        "roc_auc": _roc_or_none(module_y, proba[mask]),
                    }
                )
    return {"rows": rows, "modules": {"model": "hgb", "rows": module_rows}}


def _flag_count(n: int, fraction: float) -> int:
    if fraction == 0.2:
        return (int(n) * 2) // 10
    return int(np.floor(int(n) * float(fraction)))


def _ceil_flag_count(n: int) -> int:
    """ceil(0.2 * n)."""
    return (int(n) * 2 + 9) // 10


def precision_recall_at_fraction(
    y: np.ndarray,
    proba: np.ndarray,
    fraction: float = TOP_FRACTION,
) -> tuple[float, float]:
    """En yuksek riskli kesimin precision ve recall degerleri."""
    labels = np.asarray(y)
    scores = np.asarray(proba, dtype=np.float64)
    n = int(labels.shape[0])
    k = _flag_count(n, fraction)
    positives = int(np.sum(labels == 1))
    if k < 1 or positives < 1:
        return float("nan"), float("nan")
    order = np.argsort(-scores, kind="mergesort")
    hits = int(np.sum(labels[order[:k]] == 1))
    return hits / k, hits / positives


def within_module_flags(
    modules: np.ndarray,
    y: np.ndarray,
    proba: np.ndarray,
) -> dict:
    """Her modulde en yuksek riskli ceil(0.2 * n) ogrenci."""
    labels = np.asarray(modules).astype(str)
    observed = np.asarray(y)
    scores = np.asarray(proba, dtype=np.float64)
    if labels.shape[0] != observed.shape[0] or labels.shape[0] != scores.shape[0]:
        raise ValueError("modul, hedef ve tahmin uzunlugu farkli")
    rows = []
    for name in sorted(set(labels.tolist())):
        mask = labels == name
        module_y = observed[mask]
        n = int(mask.sum())
        n_positive = int(np.sum(module_y == 1))
        k = _ceil_flag_count(n)
        if k < 1:
            continue
        order = np.argsort(-scores[mask], kind="mergesort")
        n_hit = int(np.sum(module_y[order[:k]] == 1))
        rows.append(
            {
                "code_module": name,
                "n": n,
                "n_positive": n_positive,
                "n_flagged": k,
                "n_hit": n_hit,
                "precision": n_hit / k,
                "recall": (n_hit / n_positive) if n_positive else float("nan"),
            }
        )
    n_flagged = int(sum(row["n_flagged"] for row in rows))
    n_hit = int(sum(row["n_hit"] for row in rows))
    n_positive = int(sum(row["n_positive"] for row in rows))
    total = {
        "n": int(sum(row["n"] for row in rows)),
        "n_positive": n_positive,
        "n_flagged": n_flagged,
        "n_hit": n_hit,
        "precision": (n_hit / n_flagged) if n_flagged else float("nan"),
        "recall": (n_hit / n_positive) if n_positive else float("nan"),
    }
    return {"rows": rows, "total": total}


def metric_values(y: np.ndarray, proba: np.ndarray) -> dict[str, float]:
    labels = np.asarray(y)
    scores = np.asarray(proba, dtype=np.float64)
    both = np.unique(labels).size > 1
    precision, recall = precision_recall_at_fraction(labels, scores, TOP_FRACTION)
    return {
        "roc_auc": float(roc_auc_score(labels, scores)) if both else float("nan"),
        "pr_auc": float(average_precision_score(labels, scores)) if both else float("nan"),
        "brier": float(brier_score_loss(labels, scores)),
        "log_loss": float(log_loss(labels, scores, labels=[0, 1])),
        "precision_at_20": precision,
        "recall_at_20": recall,
    }


def bootstrap_indices(
    modules: np.ndarray,
    y: np.ndarray,
    n_boot: int,
    seed: int,
) -> np.ndarray:
    """Modul icinde sinifa gore tabakali bootstrap. Her orneklem modul sayilarini korur."""
    module_labels = np.asarray(modules).astype(str)
    labels = np.asarray(y).astype(np.int64)
    if module_labels.shape[0] != labels.shape[0]:
        raise ValueError("modul ve hedef uzunlugu farkli")
    if n_boot < 1:
        raise ValueError("n_boot gecersiz")
    n = int(module_labels.shape[0])
    strata: list[np.ndarray] = []
    for module in sorted(set(module_labels.tolist())):
        member = np.flatnonzero(module_labels == module)
        for cls in sorted(set(labels[member].tolist())):
            strata.append(np.sort(member[labels[member] == cls]))
    rng = np.random.default_rng(seed)
    indices = np.empty((n_boot, n), dtype=np.int64)
    for draw in range(n_boot):
        parts = [rng.choice(stratum, size=stratum.size, replace=True) for stratum in strata]
        drawn = np.concatenate(parts)
        if drawn.shape[0] != n:
            raise ValueError("bootstrap uzunlugu")
        indices[draw] = drawn
    return indices


def _interval(estimate: float, samples: np.ndarray) -> dict[str, float]:
    low, high = np.quantile(np.asarray(samples, dtype=np.float64), [0.025, 0.975])
    return {"estimate": float(estimate), "low": float(low), "high": float(high)}


def _bootstrap_samples(
    y: np.ndarray,
    proba: np.ndarray,
    indices: np.ndarray,
) -> dict[str, np.ndarray]:
    collected = {name: np.empty(indices.shape[0], dtype=np.float64) for name in METRIC_NAMES}
    for draw, sample in enumerate(indices):
        # Esit olasilikta sira, orijinal satir sirasidir.
        ordered = np.sort(sample)
        stats = metric_values(y[ordered], proba[ordered])
        for name in METRIC_NAMES:
            collected[name][draw] = stats[name]
    return collected


def metric_intervals(
    y: np.ndarray,
    proba: np.ndarray,
    modules: np.ndarray,
    n_boot: int = N_BOOTSTRAP,
    seed: int = RANDOM_STATE,
    indices: np.ndarray | None = None,
    samples: dict[str, np.ndarray] | None = None,
) -> dict[str, dict[str, float]]:
    """samples verilirse (ayni indices ile hesaplanmis) yeniden hesaplanmaz."""
    point = metric_values(y, proba)
    if samples is None:
        if indices is None:
            indices = bootstrap_indices(modules, y, n_boot, seed)
        samples = _bootstrap_samples(y, proba, indices)
    return {name: _interval(point[name], samples[name]) for name in METRIC_NAMES}


def paired_difference(
    y: np.ndarray,
    proba_left: np.ndarray,
    proba_right: np.ndarray,
    modules: np.ndarray,
    n_boot: int = N_BOOTSTRAP,
    seed: int = RANDOM_STATE,
    indices: np.ndarray | None = None,
    samples_left: dict[str, np.ndarray] | None = None,
    samples_right: dict[str, np.ndarray] | None = None,
) -> dict[str, dict[str, float]]:
    """Ayni orneklemlerde metric(left) - metric(right).

    samples_left ve samples_right verilirse (ayni indices ile hesaplanmis)
    yeniden hesaplanmaz.
    """
    left = metric_values(y, proba_left)
    right = metric_values(y, proba_right)
    if samples_left is None or samples_right is None:
        if indices is None:
            indices = bootstrap_indices(modules, y, n_boot, seed)
    left_samples = samples_left if samples_left is not None else _bootstrap_samples(y, proba_left, indices)
    right_samples = samples_right if samples_right is not None else _bootstrap_samples(y, proba_right, indices)
    return {
        name: _interval(left[name] - right[name], left_samples[name] - right_samples[name])
        for name in PAIRED_METRICS
    }


def _roc_or_none(y: np.ndarray, proba: np.ndarray) -> float | None:
    if np.unique(y).size < 2:
        return None
    return float(roc_auc_score(y, proba))


def _best_model(test_metrics: dict) -> str:
    ranking = []
    for model_name in MODEL_NAMES:
        roc_mean = float(
            np.mean([test_metrics[set_name][model_name]["roc_auc"]["estimate"] for set_name in BASE_SET_NAMES])
        )
        brier_mean = float(
            np.mean([test_metrics[set_name][model_name]["brier"]["estimate"] for set_name in BASE_SET_NAMES])
        )
        ranking.append((-roc_mean, brier_mean, MODEL_NAMES.index(model_name), model_name))
    ranking.sort()
    return ranking[0][3]


def _module_table(
    modules: np.ndarray,
    y: np.ndarray,
    proba_by_set: dict[str, np.ndarray],
    model_name: str,
    set_names: tuple[str, ...] = SET_NAMES,
) -> dict:
    rows = []
    for module in sorted(set(np.asarray(modules).astype(str).tolist())):
        mask = np.asarray(modules).astype(str) == module
        module_y = y[mask]
        row = {
            "code_module": module,
            "n": int(mask.sum()),
            "n_positive": int(np.sum(module_y == 1)),
            "roc_auc": {set_name: _roc_or_none(module_y, proba_by_set[set_name][mask]) for set_name in set_names},
        }
        rows.append(row)
    mean = {}
    for set_name in set_names:
        usable = [row for row in rows if row["roc_auc"][set_name] is not None]
        if not usable:
            mean[set_name] = {"n": 0, "n_positive": 0, "roc_auc": None}
            continue
        mean[set_name] = {
            "n": int(sum(row["n"] for row in usable)),
            "n_positive": int(sum(row["n_positive"] for row in usable)),
            "roc_auc": float(np.mean([row["roc_auc"][set_name] for row in usable])),
        }
    return {"model": model_name, "rows": rows, "mean": mean}


def _within_module_table(
    modules: np.ndarray,
    y: np.ndarray,
    proba_by_set: dict[str, np.ndarray],
) -> dict:
    rows = []
    totals = []
    for set_name in SET_NAMES:
        block = within_module_flags(modules, y, proba_by_set[set_name])
        for row in block["rows"]:
            rows.append(
                {
                    "set": set_name,
                    "code_module": row["code_module"],
                    "n": row["n"],
                    "n_positive": row["n_positive"],
                    "n_flagged": row["n_flagged"],
                    "n_hit": row["n_hit"],
                    "precision": row["precision"],
                    "recall": row["recall"],
                }
            )
        total = block["total"]
        totals.append(
            {
                "set": set_name,
                "n": total["n"],
                "n_positive": total["n_positive"],
                "n_flagged": total["n_flagged"],
                "n_hit": total["n_hit"],
                "precision": total["precision"],
                "recall": total["recall"],
            }
        )
    return {"model": "hgb", "rows": rows, "total": totals}


def lomo_folds(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Her modul: train bolumunden modul cikar, test 2014J'de o modul.

    Test modulu egitim maskesinde yoktur.
    """
    for column in ("code_module", "code_presentation", "split"):
        if column not in frame.columns:
            raise ValueError(f"{column} yok")
    module = frame["code_module"].astype(str).to_numpy()
    presentation = frame["code_presentation"].astype(str).to_numpy()
    split = frame["split"].astype(str).to_numpy()
    train_base = split == "train"
    test_base = presentation == TEST_PRESENTATION
    names = sorted(set(module[test_base].tolist()))
    folds = []
    for name in names:
        held = module == name
        train_mask = train_base & ~held
        test_mask = test_base & held
        if np.any(module[train_mask] == name):
            raise ValueError("test modulu egitimde")
        folds.append({"code_module": name, "train": train_mask, "test": test_mask})
    return folds


def _calibration_table(
    modules: np.ndarray,
    y: np.ndarray,
    proba_by_set: dict[str, np.ndarray],
) -> dict:
    labels = np.asarray(modules).astype(str)
    observed = np.asarray(y)
    rows = []
    for set_name in SET_NAMES:
        scores = np.asarray(proba_by_set[set_name], dtype=np.float64)
        for name in sorted(set(labels.tolist())):
            mask = labels == name
            n = int(mask.sum())
            if n < 1:
                continue
            rows.append(
                {
                    "set": set_name,
                    "code_module": name,
                    "n": n,
                    "positive_rate": float(np.mean(observed[mask])),
                    "mean_prediction": float(np.mean(scores[mask])),
                }
            )
    return {"model": "hgb", "rows": rows}


def _fmt_module_n(mapping: dict) -> str:
    return ",".join(f"{name}={int(mapping[name])}" for name in mapping)


def leave_one_module_out(frame: pd.DataFrame, selected: dict) -> dict:
    """Secilen hgb ayariyla modul disarida birakma. Ayar yenilenmez."""
    folds = lomo_folds(frame)
    y = _target(frame)
    prepared: dict[str, tuple[list[str], pd.DataFrame]] = {}
    for set_name in LOMO_SET_NAMES:
        columns = feature_columns(set_name, list(frame.columns))
        prepared[set_name] = (columns, design_frame(frame, columns))
    module_labels = frame["code_module"].astype(str).to_numpy()
    rows = []
    for fold in folds:
        name = str(fold["code_module"])
        train_mask = np.asarray(fold["train"], dtype=bool)
        test_mask = np.asarray(fold["test"], dtype=bool)
        if np.any(module_labels[train_mask] == name):
            raise ValueError("test modulu egitimde")
        if not test_mask.any():
            continue
        if not train_mask.any() or np.unique(y[train_mask]).size < 2:
            raise ValueError("lomo egitim tek sinif")
        y_test = y[test_mask]
        n = int(test_mask.sum())
        n_positive = int(np.sum(y_test == 1))
        train_pos = np.flatnonzero(train_mask)
        test_pos = np.flatnonzero(test_mask)
        for set_name in LOMO_SET_NAMES:
            columns, features = prepared[set_name]
            params = selected[set_name]["hgb"]["params"]
            model = make_estimator("hgb", params, columns)
            model.fit(features.iloc[train_pos], y[train_mask])
            proba = _positive_proba(model, features.iloc[test_pos])
            rows.append(
                {
                    "code_module": name,
                    "set": set_name,
                    "n": n,
                    "n_positive": n_positive,
                    "roc_auc": _roc_or_none(y_test, proba),
                    "brier": float(brier_score_loss(y_test, proba)),
                    "mean_prediction": float(np.mean(proba)),
                    "positive_rate": float(n_positive / n),
                }
            )
    mean: dict = {}
    for set_name in LOMO_SET_NAMES:
        subset = [row for row in rows if row["set"] == set_name and row["roc_auc"] is not None]
        n_by_module = {row["code_module"]: row["n"] for row in subset}
        if not subset:
            mean[set_name] = {
                "n": 0,
                "n_positive": 0,
                "roc_auc": None,
                "brier": None,
                "n_by_module": {},
            }
            continue
        mean[set_name] = {
            "n": int(sum(row["n"] for row in subset)),
            "n_positive": int(sum(row["n_positive"] for row in subset)),
            "roc_auc": float(np.mean([row["roc_auc"] for row in subset])),
            "brier": float(np.mean([row["brier"] for row in subset])),
            "n_by_module": n_by_module,
        }
    return {"model": "hgb", "rows": rows, "mean": mean}


def compare_models(frame: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    frame = add_relative_features(frame).reset_index(drop=True)
    for column in (*ID_COLUMNS, "split", "at_risk"):
        if column not in frame.columns:
            raise ValueError(f"{column} yok")
    y = _target(frame)
    split = frame["split"].astype(str)
    train = split.eq("train").to_numpy()
    test = split.eq("test").to_numpy()
    if not train.any():
        raise ValueError("train bos")
    if not test.any():
        raise ValueError("test bos")
    train_frame = frame.loc[split.eq("train")].reset_index(drop=True)

    selected: dict = {}
    proba_all: dict[tuple[str, str], np.ndarray] = {}
    for set_name in SET_NAMES:
        columns = feature_columns(set_name, list(frame.columns))
        features = design_frame(frame, columns)
        selected[set_name] = {}
        for model_name in MODEL_NAMES:
            chosen = select_hyperparameters(train_frame, columns, model_name)
            selected[set_name][model_name] = chosen
            model = make_estimator(model_name, chosen["params"], columns)
            model.fit(features.iloc[np.flatnonzero(train)], y[train])
            proba_all[(set_name, model_name)] = _positive_proba(model, features)

    test_pos = np.flatnonzero(test)
    y_test = y[test_pos]
    modules = frame["code_module"].astype(str).to_numpy()[test_pos]
    indices = bootstrap_indices(modules, y_test, N_BOOTSTRAP, RANDOM_STATE)
    test_metrics: dict = {}
    point: dict[tuple[str, str], dict[str, float]] = {}
    samples: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    proba_test: dict[tuple[str, str], np.ndarray] = {}
    for set_name in SET_NAMES:
        test_metrics[set_name] = {}
        for model_name in MODEL_NAMES:
            scores = proba_all[(set_name, model_name)][test_pos]
            proba_test[(set_name, model_name)] = scores
            point[(set_name, model_name)] = metric_values(y_test, scores)
            samples[(set_name, model_name)] = _bootstrap_samples(y_test, scores, indices)
            test_metrics[set_name][model_name] = {
                name: _interval(point[(set_name, model_name)][name], samples[(set_name, model_name)][name])
                for name in METRIC_NAMES
            }

    paired: dict = {}
    for model_name in MODEL_NAMES:
        paired[model_name] = {}
        for contrast, left_name, right_name in PAIRED_CONTRASTS:
            left_key = (left_name, model_name)
            right_key = (right_name, model_name)
            paired[model_name][contrast] = {
                name: _interval(
                    point[left_key][name] - point[right_key][name],
                    samples[left_key][name] - samples[right_key][name],
                )
                for name in PAIRED_METRICS
            }

    model_name = _best_model(test_metrics)
    hgb_test = {set_name: proba_test[(set_name, "hgb")] for set_name in SET_NAMES}
    modules_report = _module_table(
        modules,
        y_test,
        {set_name: proba_test[(set_name, model_name)] for set_name in SET_NAMES},
        model_name,
    )
    calibration = _calibration_table(modules, y_test, hgb_test)
    lomo = leave_one_module_out(frame, selected)
    report = {
        "selected_params": selected,
        "validation": validation_report(train_frame, selected),
        "test_metrics": test_metrics,
        "paired_differences": paired,
        "modules": modules_report,
        "within_module": _within_module_table(modules, y_test, hgb_test),
        "calibration": calibration,
        "lomo": lomo,
    }
    predictions = _prediction_frame(frame, proba_all)
    return report, predictions


def _prediction_frame(frame: pd.DataFrame, proba_all: dict[tuple[str, str], np.ndarray]) -> pd.DataFrame:
    base = frame.loc[:, list(ID_COLUMNS) + ["split"]]
    parts = []
    for set_name in SET_NAMES:
        for model_name in MODEL_NAMES:
            part = base.copy()
            part["set"] = set_name
            part["model"] = model_name
            part["proba"] = np.asarray(proba_all[(set_name, model_name)], dtype=np.float64)
            parts.append(part)
    predictions = pd.concat(parts, ignore_index=True)
    return predictions.sort_values(
        ["set", "model", "code_module", "code_presentation", "id_student"],
        kind="mergesort",
    ).reset_index(drop=True)


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if np.isnan(number):
            return None
        return number
    if isinstance(value, (np.integer,)):
        return int(value)
    return value


def _fmt(value) -> str:
    if value is None:
        return ""
    number = float(value)
    if np.isnan(number):
        return ""
    return f"{number:.6f}"


def _fmt_params(params: dict) -> str:
    return ",".join(f"{key}={params[key]}" for key in params)


def print_report(report: dict) -> None:
    print("selected_params")
    print("set\tmodel\tval_log_loss\tparams")
    for set_name in SET_NAMES:
        for model_name in MODEL_NAMES:
            chosen = report["selected_params"][set_name][model_name]
            print(
                f"{set_name}\t{model_name}\t{_fmt(chosen['val_log_loss'])}\t{_fmt_params(chosen['params'])}"
            )
    print()
    print("validation")
    print("set\tmodel\troc_auc\tpr_auc\tbrier\tlog_loss\tmean_prediction\tpositive_rate")
    for row in report["validation"]["rows"]:
        print(
            f"{row['set']}\t{row['model']}\t{_fmt(row['roc_auc'])}\t{_fmt(row['pr_auc'])}\t"
            f"{_fmt(row['brier'])}\t{_fmt(row['log_loss'])}\t"
            f"{_fmt(row['mean_prediction'])}\t{_fmt(row['positive_rate'])}"
        )
    print()
    print(f"validation_modules\tmodel={report['validation']['modules']['model']}")
    print("set\tcode_module\tn\tn_positive\troc_auc")
    for row in report["validation"]["modules"]["rows"]:
        print(
            f"{row['set']}\t{row['code_module']}\t{row['n']}\t{row['n_positive']}\t{_fmt(row['roc_auc'])}"
        )
    print()
    print("test_metrics")
    header = ["set", "model"]
    for name in METRIC_NAMES:
        header.extend([name, f"{name}_low", f"{name}_high"])
    print("\t".join(header))
    for set_name in SET_NAMES:
        for model_name in MODEL_NAMES:
            cells = [set_name, model_name]
            metrics = report["test_metrics"][set_name][model_name]
            for name in METRIC_NAMES:
                cells.extend(
                    [
                        _fmt(metrics[name]["estimate"]),
                        _fmt(metrics[name]["low"]),
                        _fmt(metrics[name]["high"]),
                    ]
                )
            print("\t".join(cells))
    print()
    print("paired_differences")
    print("model\tcontrast\tmetric\testimate\tlow\thigh")
    for model_name in MODEL_NAMES:
        for contrast, _left, _right in PAIRED_CONTRASTS:
            block = report["paired_differences"][model_name][contrast]
            for name in PAIRED_METRICS:
                item = block[name]
                print(
                    f"{model_name}\t{contrast}\t{name}\t{_fmt(item['estimate'])}\t{_fmt(item['low'])}\t{_fmt(item['high'])}"
                )
    print()
    print(f"module_roc_auc\tmodel={report['modules']['model']}")
    print("code_module\tn\tn_positive\t" + "\t".join(SET_NAMES))
    for row in report["modules"]["rows"]:
        auc = row["roc_auc"]
        cells = [str(row["code_module"]), str(row["n"]), str(row["n_positive"])]
        cells.extend(_fmt(auc[set_name]) for set_name in SET_NAMES)
        print("\t".join(cells))
    print("mean\tset\tn\tn_positive\troc_auc")
    for set_name in SET_NAMES:
        item = report["modules"]["mean"][set_name]
        print(f"mean\t{set_name}\t{item['n']}\t{item['n_positive']}\t{_fmt(item['roc_auc'])}")
    print()
    print(f"within_module\tmodel={report['within_module']['model']}")
    print("set\tcode_module\tn\tn_positive\tn_flagged\tn_hit\tprecision\trecall")
    for row in report["within_module"]["rows"]:
        print(
            f"{row['set']}\t{row['code_module']}\t{row['n']}\t{row['n_positive']}\t"
            f"{row['n_flagged']}\t{row['n_hit']}\t{_fmt(row['precision'])}\t{_fmt(row['recall'])}"
        )
    print("total\tset\tn\tn_positive\tn_flagged\tn_hit\tprecision\trecall")
    for row in report["within_module"]["total"]:
        print(
            f"total\t{row['set']}\t{row['n']}\t{row['n_positive']}\t"
            f"{row['n_flagged']}\t{row['n_hit']}\t{_fmt(row['precision'])}\t{_fmt(row['recall'])}"
        )
    print()
    print(f"calibration\tmodel={report['calibration']['model']}")
    print("set\tcode_module\tn\tpositive_rate\tmean_prediction")
    for row in report["calibration"]["rows"]:
        print(
            f"{row['set']}\t{row['code_module']}\t{row['n']}\t"
            f"{_fmt(row['positive_rate'])}\t{_fmt(row['mean_prediction'])}"
        )
    print()
    print(f"lomo\tmodel={report['lomo']['model']}")
    print("code_module\tset\tn\tn_positive\troc_auc\tbrier\tmean_prediction\tpositive_rate")
    for row in report["lomo"]["rows"]:
        print(
            f"{row['code_module']}\t{row['set']}\t{row['n']}\t{row['n_positive']}\t"
            f"{_fmt(row['roc_auc'])}\t{_fmt(row['brier'])}\t"
            f"{_fmt(row['mean_prediction'])}\t{_fmt(row['positive_rate'])}"
        )
    print("mean\tset\tn\tn_positive\troc_auc\tbrier\tn_by_module")
    for set_name in LOMO_SET_NAMES:
        item = report["lomo"]["mean"][set_name]
        print(
            f"mean\t{set_name}\t{item['n']}\t{item['n_positive']}\t"
            f"{_fmt(item['roc_auc'])}\t{_fmt(item['brier'])}\t{_fmt_module_n(item['n_by_module'])}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lomo", action="store_true")
    parser.parse_args()
    source = PROCESSED_OULAD_DIR / FEATURES_NAME
    frame = pd.read_parquet(source, engine="pyarrow")
    report, predictions = compare_models(frame)
    dest = PROCESSED_OULAD_DIR / PREDICTIONS_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(dest, engine="pyarrow", index=False)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(_jsonable(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print_report(report)
    print(f"predictions_path={dest}")
    print(f"metrics_path={REPORT_PATH}")


if __name__ == "__main__":
    main()
