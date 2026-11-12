"""Kapasite eğrisi ve SHAP. Yeni set, model türü veya ayar yok.

Genel hgb, kayıtlı ayarla train bölümünün tamamında yeniden oturtulur.
Test (2014J) yalnızca kapasite eğrisi ve SHAP değerlendirmesinde kullanılır.
"""

from __future__ import annotations

import json
import math
import warnings

import numpy as np
import pandas as pd

from data_science.oulad import PROCESSED_OULAD_DIR
from data_science.oulad.dataset import FEATURES_NAME
from data_science.oulad.model import (
    REPORT_PATH as METRICS_PATH,
    TEST_PRESENTATION,
    _contains_test_rows,
    _flag_count,
    _fmt,
    _jsonable,
    _positive_proba,
    _target,
    design_frame,
    feature_columns,
    make_estimator,
)

EXPLAIN_PATH = METRICS_PATH.parent / "explain.json"
FLAG_RATES = tuple(step / 100 for step in range(5, 55, 5))
PERMUTATION_TEST_ROWS = 1000
PERMUTATION_BACKGROUND_ROWS = 200


def _masks(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    if "split" not in frame.columns or "code_presentation" not in frame.columns:
        raise ValueError("split yok")
    split = frame["split"].astype(str).to_numpy()
    presentation = frame["code_presentation"].astype(str).to_numpy()
    if np.any((split == "train") & (presentation == TEST_PRESENTATION)):
        raise ValueError("test bolumu egitimde kullanilamaz")
    train = (split == "train") & (presentation != TEST_PRESENTATION)
    test = (split == "test") & (presentation == TEST_PRESENTATION)
    if not np.any(train):
        raise ValueError("train bos")
    if not np.any(test):
        raise ValueError("test bos")
    return train, test


def _ranking_counts(y: np.ndarray, proba: np.ndarray, k: int) -> dict:
    labels = np.asarray(y)
    n = int(labels.shape[0])
    n_positive = int(np.sum(labels == 1))
    flagged = int(k)
    if flagged < 1 or n_positive < 1:
        return {
            "n": n,
            "n_positive": n_positive,
            "n_flagged": flagged,
            "n_hit": 0,
            "precision": float("nan"),
            "recall": float("nan"),
        }
    order = np.argsort(-np.asarray(proba, dtype=np.float64), kind="mergesort")
    n_hit = int(np.sum(labels[order[:flagged]] == 1))
    return {
        "n": n,
        "n_positive": n_positive,
        "n_flagged": flagged,
        "n_hit": n_hit,
        "precision": n_hit / flagged,
        "recall": n_hit / n_positive,
    }


def _within_module_at_rate(modules: np.ndarray, y: np.ndarray, proba: np.ndarray, rate: float) -> dict:
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
        k = math.ceil(rate * n)
        if k < 1:
            n_hit = 0
            precision = float("nan")
            recall = float("nan")
        else:
            order = np.argsort(-scores[mask], kind="mergesort")
            n_hit = int(np.sum(module_y[order[:k]] == 1))
            precision = n_hit / k
            recall = (n_hit / n_positive) if n_positive else float("nan")
        rows.append(
            {
                "code_module": name,
                "n": n,
                "n_positive": n_positive,
                "n_flagged": int(k),
                "n_hit": n_hit,
                "precision": precision,
                "recall": recall,
            }
        )
    n_flagged = int(sum(row["n_flagged"] for row in rows))
    n_hit = int(sum(row["n_hit"] for row in rows))
    n_positive = int(sum(row["n_positive"] for row in rows))
    return {
        "n": int(sum(row["n"] for row in rows)),
        "n_positive": n_positive,
        "n_flagged": n_flagged,
        "n_hit": n_hit,
        "precision": (n_hit / n_flagged) if n_flagged else float("nan"),
        "recall": (n_hit / n_positive) if n_positive else float("nan"),
        "rows": rows,
    }


def capacity_curve(
    modules: np.ndarray,
    y: np.ndarray,
    proba: np.ndarray,
    rates: tuple[float, ...] = FLAG_RATES,
) -> list[dict]:
    """Bayrak oranı 5%–50%. Sınıf içi bayrak sayısı her modülde ceil(oran × n)."""
    labels = np.asarray(y)
    scores = np.asarray(proba, dtype=np.float64)
    module_labels = np.asarray(modules)
    if module_labels.shape[0] != labels.shape[0] or labels.shape[0] != scores.shape[0]:
        raise ValueError("modul, hedef ve tahmin uzunlugu farkli")
    rows = []
    n = int(labels.shape[0])
    for rate in rates:
        rate = float(rate)
        global_counts = _ranking_counts(labels, scores, _flag_count(n, rate))
        rows.append(
            {
                "flag_rate": rate,
                "global": global_counts,
                "within_module": _within_module_at_rate(module_labels, labels, scores, rate),
            }
        )
    return rows


def _output_names(model, columns: list[str]) -> list[str]:
    pre = model.named_steps["pre"]
    if getattr(pre, "_fallback", False):
        return ["_bos"]
    if hasattr(pre, "keep_"):
        return [column for column, flag in zip(columns, pre.keep_) if bool(flag)]
    return list(columns)


def _shap_matrix(result, n_rows: int, n_features: int) -> np.ndarray:
    """TreeExplainer.shap_values çıktısı: (satır, öznitelik) biçiminde tek matris.

    shap 0.54.1 ikili sınıflandırıcıda pozitif sınıf için bu biçimi döndürür.
    Başka bir biçim gelirse tahmin yürütülmez, hata yükselir.
    """
    array = np.asarray(result, dtype=np.float64)
    if array.shape != (n_rows, n_features):
        raise ValueError(f"shap boyutu {array.shape}, beklenen {(n_rows, n_features)}")
    return array


def _tree_attribute(model, columns: list[str], test_x: pd.DataFrame):
    import shap

    pre = model.named_steps["pre"]
    clf = model.named_steps["clf"]
    transformed = np.asarray(pre.transform(test_x), dtype=np.float64)
    names = _output_names(model, columns)
    if transformed.ndim != 2 or transformed.shape[1] != len(names):
        raise ValueError("shap sutun")
    explainer = shap.TreeExplainer(clf, feature_perturbation="tree_path_dependent")
    values = explainer.shap_values(transformed, check_additivity=False)
    matrix = _shap_matrix(values, transformed.shape[0], transformed.shape[1])
    return matrix, transformed, names, "TreeExplainer"


def _sample_frame(frame: pd.DataFrame, k: int, seed: int) -> pd.DataFrame:
    n = int(len(frame))
    take = min(n, int(k))
    rng = np.random.default_rng(seed)
    positions = np.sort(rng.choice(n, size=take, replace=False))
    return frame.iloc[positions]


def _attribute(model, columns: list[str], train_x: pd.DataFrame, test_x: pd.DataFrame):
    """Ağaç açıklayıcıyla SHAP değerlerini hesaplar; açıklayıcı hata verirse hata yükselir."""
    return _tree_attribute(model, columns, test_x)


def _column(values: np.ndarray) -> list[float | None]:
    out = []
    for value in np.asarray(values, dtype=np.float64):
        number = float(value)
        out.append(None if not np.isfinite(number) else number)
    return out


def _summarize(names: list[str], values: np.ndarray, matrix: np.ndarray):
    means = np.mean(np.abs(np.asarray(matrix, dtype=np.float64)), axis=0)
    order = sorted(range(len(names)), key=lambda index: (-float(means[index]), names[index]))
    features = [
        {"feature": names[index], "mean_abs_shap": float(means[index])}
        for index in order
    ]
    dependence = []
    for index in order[:3]:
        dependence.append(
            {
                "feature": names[index],
                "value": _column(values[:, index]),
                "shap": _column(matrix[:, index]),
            }
        )
    return features, dependence


def build_report(frame: pd.DataFrame, params: dict) -> dict:
    """Train üzerinde tek oturtma. Test satırı yalnızca değerlendirme kesimindedir."""
    if "code_module" not in frame.columns:
        raise ValueError("code_module yok")
    columns = feature_columns("GENERAL", list(frame.columns))
    features = design_frame(frame, columns)
    y = _target(frame)
    train, test = _masks(frame)
    train_frame = frame.iloc[np.flatnonzero(train)]
    if _contains_test_rows(train_frame):
        raise ValueError("test bolumu egitimde kullanilamaz")
    if np.unique(y[train]).size < 2:
        raise ValueError("train tek sinif")
    model = make_estimator("hgb", dict(params), columns)
    train_x = features.iloc[np.flatnonzero(train)]
    test_x = features.iloc[np.flatnonzero(test)]
    model.fit(train_x, y[train])
    proba = _positive_proba(model, test_x)
    modules = frame["code_module"].astype(str).to_numpy()[test]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        matrix, values, names, method = _attribute(model, columns, train_x, test_x)
    feature_rows, dependence = _summarize(names, values, matrix)
    return {
        "capacity": {
            "set": "GENERAL",
            "model": "hgb",
            "presentation": TEST_PRESENTATION,
            "rows": capacity_curve(modules, y[test], proba),
        },
        "shap": {
            "set": "GENERAL",
            "model": "hgb",
            "method": method,
            "n_explained": int(matrix.shape[0]),
            "features": feature_rows,
            "dependence": dependence,
        },
    }


def _selected_params(metrics: dict) -> dict:
    return dict(metrics["selected_params"]["GENERAL"]["hgb"]["params"])


def print_report(report: dict) -> None:
    capacity = report["capacity"]
    print(f"capacity\tset={capacity['set']}\tmodel={capacity['model']}\tpresentation={capacity['presentation']}")
    print("flag_rate\tranking\tn\tn_positive\tn_flagged\tn_hit\tprecision\trecall")
    for row in capacity["rows"]:
        for ranking in ("global", "within_module"):
            item = row[ranking]
            print(
                f"{_fmt(row['flag_rate'])}\t{ranking}\t{item['n']}\t{item['n_positive']}\t"
                f"{item['n_flagged']}\t{item['n_hit']}\t{_fmt(item['precision'])}\t{_fmt(item['recall'])}"
            )
    print()
    shap_report = report["shap"]
    print(
        f"shap\tset={shap_report['set']}\tmodel={shap_report['model']}\t"
        f"method={shap_report['method']}\tn_explained={shap_report['n_explained']}"
    )
    print("feature\tmean_abs_shap")
    for row in shap_report["features"]:
        print(f"{row['feature']}\t{_fmt(row['mean_abs_shap'])}")
    print()
    print("dependence\tfeature")
    for row in shap_report["dependence"]:
        print(f"dependence\t{row['feature']}")


def _require_shap():
    import shap

    return shap


def main() -> None:
    _require_shap()
    source = PROCESSED_OULAD_DIR / FEATURES_NAME
    frame = pd.read_parquet(source, engine="pyarrow")
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    report = build_report(frame, _selected_params(metrics))
    EXPLAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPLAIN_PATH.write_text(
        json.dumps(_jsonable(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print_report(report)
    print(f"explain_path={EXPLAIN_PATH}")


if __name__ == "__main__":
    main()
