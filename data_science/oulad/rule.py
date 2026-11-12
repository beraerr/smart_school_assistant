"""Sabit sınıf içi kural. Ağırlık, eşik ve sinyal önceden seçilmiştir.

Her (code_module, code_presentation) içinde üç yüzdelik sıranın ortalaması.
at_risk kullanılmaz. n_expected sıfır olan sunumda kural yoktur.
Karşılaştırma, kayıtlı GENERAL hgb ayarıyla aynı uygun öğrenciler üzerindedir.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from data_science.oulad import PROCESSED_OULAD_DIR
from data_science.oulad.dataset import FEATURES_NAME
from data_science.oulad.model import (
    FIT_PRESENTATION,
    REPORT_PATH as METRICS_PATH,
    TEST_PRESENTATION,
    VAL_PRESENTATION,
    _fmt,
    _jsonable,
    _positive_proba,
    _roc_or_none,
    _target,
    design_frame,
    feature_columns,
    make_estimator,
    within_module_flags,
)

RULE_PATH = METRICS_PATH.parent / "rule_metrics.json"
FLAG_RATE = 0.2
METHODS = ("rule", "general_hgb")
PERIODS = (VAL_PRESENTATION, TEST_PRESENTATION)
_PARTS = ("n_unsubmitted", "score_mean", "vle_active_days", "n_expected")


def _require(frame: pd.DataFrame) -> None:
    missing = [column for column in ("code_module", "code_presentation", *_PARTS) if column not in frame.columns]
    if missing:
        raise ValueError(f"eksik ozellik: {missing}")


def _numeric(frame: pd.DataFrame, column: str) -> np.ndarray:
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=np.float64)
    values = np.array(values, dtype=np.float64, copy=True)
    values[~np.isfinite(values)] = np.nan
    return values


def _groups(frame: pd.DataFrame) -> np.ndarray:
    module = frame["code_module"].astype("string").astype(str)
    presentation = frame["code_presentation"].astype("string").astype(str)
    return (module + "\x1f" + presentation).to_numpy()


def eligible_mask(frame: pd.DataFrame) -> np.ndarray:
    """n_expected sıfır olan satır uygun değildir."""
    expected = _numeric(frame, "n_expected")
    return np.isfinite(expected) & (expected != 0.0)


def _rank_pct(values: np.ndarray, groups: np.ndarray, ascending: bool) -> np.ndarray:
    ranked = pd.Series(values).groupby(pd.Series(groups), sort=False).rank(
        method="average",
        pct=True,
        ascending=ascending,
        na_option="keep",
    )
    return ranked.to_numpy(dtype=np.float64)


def _flag_count(n: int) -> int:
    if n < 1:
        return 0
    return math.ceil(FLAG_RATE * n)


def score_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Sunum içi kural skoru ve bayrak. at_risk okunmaz."""
    _require(frame)
    n = len(frame)
    groups = _groups(frame)
    eligible = eligible_mask(frame)
    p_unsub = np.full(n, np.nan, dtype=np.float64)
    p_score = np.full(n, np.nan, dtype=np.float64)
    p_active = np.full(n, np.nan, dtype=np.float64)
    rule_score = np.full(n, np.nan, dtype=np.float64)
    flagged = np.zeros(n, dtype=bool)
    if eligible.any():
        index = np.flatnonzero(eligible)
        sub_groups = groups[index]
        unsub = _numeric(frame, "n_unsubmitted")[index]
        score = _numeric(frame, "score_mean")[index]
        active = _numeric(frame, "vle_active_days")[index]
        score[~np.isfinite(score)] = -np.inf
        p_unsub[index] = _rank_pct(unsub, sub_groups, ascending=True)
        p_score[index] = _rank_pct(score, sub_groups, ascending=False)
        p_active[index] = _rank_pct(active, sub_groups, ascending=False)
        rule_score[index] = (p_unsub[index] + p_score[index] + p_active[index]) / 3.0
        for key in sorted(set(sub_groups.tolist())):
            member = index[sub_groups == key]
            k = _flag_count(int(member.size))
            if k < 1:
                continue
            finite = np.isfinite(rule_score[member])
            pool = member[finite]
            if pool.size < 1:
                continue
            order = np.argsort(-rule_score[pool], kind="mergesort")
            flagged[pool[order[: min(k, pool.size)]]] = True
    return pd.DataFrame(
        {
            "code_module": frame["code_module"].astype("string").astype(str).to_numpy(),
            "code_presentation": frame["code_presentation"].astype("string").astype(str).to_numpy(),
            "p_unsub": p_unsub,
            "p_score": p_score,
            "p_active": p_active,
            "rule_score": rule_score,
            "flagged": flagged,
        }
    )


def excluded_presentations(frame: pd.DataFrame) -> list[dict]:
    """Uygun öğrencisi olmayan sunumlar."""
    _require(frame)
    groups = _groups(frame)
    eligible = eligible_mask(frame)
    module = frame["code_module"].astype("string").astype(str).to_numpy()
    presentation = frame["code_presentation"].astype("string").astype(str).to_numpy()
    rows = []
    for key in sorted(set(groups.tolist())):
        member = groups == key
        if eligible[member].any():
            continue
        rows.append(
            {
                "code_module": str(module[member][0]),
                "code_presentation": str(presentation[member][0]),
                "n": int(member.sum()),
            }
        )
    rows.sort(key=lambda item: (item["code_presentation"], item["code_module"]))
    return rows


def _counts(modules: np.ndarray, y: np.ndarray, flagged: np.ndarray) -> list[dict]:
    rows = []
    labels = np.asarray(modules).astype(str)
    observed = np.asarray(y)
    marks = np.asarray(flagged, dtype=bool)
    for name in sorted(set(labels.tolist())):
        mask = labels == name
        module_y = observed[mask]
        module_flag = marks[mask]
        n = int(mask.sum())
        n_positive = int(np.sum(module_y == 1))
        n_flagged = int(module_flag.sum())
        n_hit = int(np.sum(module_flag & (module_y == 1)))
        rows.append(
            {
                "code_module": name,
                "n": n,
                "n_positive": n_positive,
                "n_flagged": n_flagged,
                "n_hit": n_hit,
                "precision": (n_hit / n_flagged) if n_flagged else float("nan"),
                "recall": (n_hit / n_positive) if n_positive else float("nan"),
            }
        )
    return rows


def _total(rows: list[dict]) -> dict:
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
    }


def _model_rows(modules: np.ndarray, y: np.ndarray, proba: np.ndarray) -> list[dict]:
    block = within_module_flags(modules, y, proba)
    return [
        {
            "code_module": row["code_module"],
            "n": row["n"],
            "n_positive": row["n_positive"],
            "n_flagged": row["n_flagged"],
            "n_hit": row["n_hit"],
            "precision": row["precision"],
            "recall": row["recall"],
        }
        for row in block["rows"]
    ]


def _roc_rows(modules: np.ndarray, y: np.ndarray, rule_score: np.ndarray, proba: np.ndarray) -> list[dict]:
    rows = []
    labels = np.asarray(modules).astype(str)
    for name in sorted(set(labels.tolist())):
        mask = labels == name
        module_y = y[mask]
        rows.append(
            {
                "code_module": name,
                "n": int(mask.sum()),
                "n_positive": int(np.sum(module_y == 1)),
                "rule": _roc_or_none(module_y, rule_score[mask]),
                "general_hgb": _roc_or_none(module_y, proba[mask]),
            }
        )
    return rows


def _predict(frame: pd.DataFrame, params: dict, fit: np.ndarray, predict: np.ndarray) -> np.ndarray:
    columns = feature_columns("GENERAL", list(frame.columns))
    features = design_frame(frame, columns)
    y = _target(frame)
    if not fit.any():
        raise ValueError("train bos")
    if np.unique(y[fit]).size < 2:
        raise ValueError("train tek sinif")
    model = make_estimator("hgb", dict(params), columns)
    model.fit(features.iloc[np.flatnonzero(fit)], y[fit])
    return _positive_proba(model, features.iloc[np.flatnonzero(predict)])


def compare_rule(frame: pd.DataFrame, params: dict) -> dict:
    """2014B doğrulama modeli ve 2014J train modeli. Ayar yenilenmez."""
    _require(frame)
    if "split" not in frame.columns or "at_risk" not in frame.columns:
        raise ValueError("split yok")
    presentation = frame["code_presentation"].astype(str).to_numpy()
    split = frame["split"].astype(str).to_numpy()
    y = _target(frame)
    fit_val = presentation == FIT_PRESENTATION
    fit_test = (split == "train") & (presentation != TEST_PRESENTATION)
    if np.any(presentation[fit_val] == TEST_PRESENTATION) or np.any(presentation[fit_test] == TEST_PRESENTATION):
        raise ValueError("test bolumu egitimde kullanilamaz")
    excluded = []
    rows = []
    totals = []
    roc_rows = []
    for period, fit in ((VAL_PRESENTATION, fit_val), (TEST_PRESENTATION, fit_test)):
        predict = presentation == period
        if not predict.any():
            raise ValueError(f"{period} bos")
        period_frame = frame.loc[predict].reset_index(drop=True)
        for item in excluded_presentations(period_frame):
            excluded.append(item)
        scored = score_frame(period_frame)
        eligible = eligible_mask(period_frame)
        if not eligible.any():
            for method in METHODS:
                totals.append({"presentation": period, "method": method, **_total([])})
            continue
        proba = _predict(frame, params, fit, predict)
        cohort_y = y[predict][eligible]
        modules = period_frame["code_module"].astype(str).to_numpy()[eligible]
        rule_flagged = scored["flagged"].to_numpy()[eligible]
        rule_values = scored["rule_score"].to_numpy(dtype=np.float64)[eligible]
        model_values = np.asarray(proba, dtype=np.float64)[eligible]
        by_method = {
            "rule": _counts(modules, cohort_y, rule_flagged),
            "general_hgb": _model_rows(modules, cohort_y, model_values),
        }
        for method in METHODS:
            for row in by_method[method]:
                rows.append({"presentation": period, "method": method, **row})
            totals.append({"presentation": period, "method": method, **_total(by_method[method])})
        for row in _roc_rows(modules, cohort_y, rule_values, model_values):
            roc_rows.append({"presentation": period, **row})
    return {"excluded": excluded, "rows": rows, "total": totals, "roc_auc": roc_rows}


def _selected_params(metrics: dict) -> dict:
    return dict(metrics["selected_params"]["GENERAL"]["hgb"]["params"])


def print_report(report: dict) -> None:
    print("excluded")
    print("code_module\tcode_presentation\tn")
    for row in report["excluded"]:
        print(f"{row['code_module']}\t{row['code_presentation']}\t{row['n']}")
    print()
    print("flags")
    print("presentation\tmethod\tcode_module\tn\tn_positive\tn_flagged\tn_hit\tprecision\trecall")
    for row in report["rows"]:
        print(
            f"{row['presentation']}\t{row['method']}\t{row['code_module']}\t{row['n']}\t"
            f"{row['n_positive']}\t{row['n_flagged']}\t{row['n_hit']}\t"
            f"{_fmt(row['precision'])}\t{_fmt(row['recall'])}"
        )
    print()
    print("total")
    print("presentation\tmethod\tn\tn_positive\tn_flagged\tn_hit\tprecision\trecall")
    for row in report["total"]:
        print(
            f"{row['presentation']}\t{row['method']}\t{row['n']}\t{row['n_positive']}\t"
            f"{row['n_flagged']}\t{row['n_hit']}\t{_fmt(row['precision'])}\t{_fmt(row['recall'])}"
        )
    print()
    print("roc_auc")
    print("presentation\tcode_module\tn\tn_positive\trule\tgeneral_hgb")
    for row in report["roc_auc"]:
        print(
            f"{row['presentation']}\t{row['code_module']}\t{row['n']}\t{row['n_positive']}\t"
            f"{_fmt(row['rule'])}\t{_fmt(row['general_hgb'])}"
        )


def main() -> None:
    frame = pd.read_parquet(PROCESSED_OULAD_DIR / FEATURES_NAME, engine="pyarrow")
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    report = compare_rule(frame, _selected_params(metrics))
    RULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RULE_PATH.write_text(
        json.dumps(_jsonable(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print_report(report)
    print(f"rule_path={RULE_PATH}")


if __name__ == "__main__":
    main()
