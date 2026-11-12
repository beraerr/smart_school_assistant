"""Ek analizler E1 (sinyal ayrıştırma) ve E2 (hedef ayrıştırma). Keşifsel.

Ön kayıt: docs/ek_analizler_on_kayit.md ve docs/ek_analizler_on_kayit_eki.md.
Protokol, bootstrap, metrikler ve GGG dışlaması model.py ve rule.py içindeki
mevcut fonksiyonlarla yapılır. Burada yalnız özellik listesi ve hedef değişir.
Okul sistemindeki kuralı değiştirmez; mevcut rapor JSON'larına yazmaz.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from data_science.oulad import PROCESSED_OULAD_DIR
from data_science.oulad.dataset import (
    AT_RISK_NEGATIVE,
    AT_RISK_POSITIVE,
    FEATURES_NAME,
    STUDENT_KEY,
    build_features,
)
from data_science.oulad.load import load_table, load_tables
from data_science.oulad.vle import DAILY_NAME
from data_science.oulad.model import (
    FIT_PRESENTATION,
    MODEL_NAMES,
    N_BOOTSTRAP,
    RANDOM_STATE,
    REPORT_PATH as MODEL_REPORT_PATH,
    TEST_PRESENTATION,
    VAL_PRESENTATION,
    _assert_allowed,
    _bootstrap_samples,
    _fmt,
    _jsonable,
    _module_table,
    _target,
    bootstrap_indices,
    feature_columns,
    metric_intervals,
    paired_difference,
    select_hyperparameters,
    within_module_flags,
)
from data_science.oulad.rule import (
    RULE2_PATH,
    RULE2_SIGNALS,
    _predict,
    eligible_mask,
    excluded_presentations,
    score_frame,
)

EK_REPORT_PATH = MODEL_REPORT_PATH.parent / "ek_metrics.json"
DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
PRE_REGISTRATION_PATH = DOCS_DIR / "ek_analizler_on_kayit.md"
PRE_REGISTRATION_ADDENDUM_PATH = DOCS_DIR / "ek_analizler_on_kayit_eki.md"
PRE_REGISTRATION_ADDENDUM2_PATH = DOCS_DIR / "ek_analizler_on_kayit_eki2.md"
PRE_REGISTRATION_PATHS = (
    PRE_REGISTRATION_PATH,
    PRE_REGISTRATION_ADDENDUM_PATH,
    PRE_REGISTRATION_ADDENDUM2_PATH,
)
PRE_REGISTRATION_MD5_PATH = DOCS_DIR / "on_kayit_md5.txt"

TARGET_COLUMN = "ek_target"
EXCLUDED_MODULE = "GGG"
EVALUATION_PRESENTATIONS = (VAL_PRESENTATION, TEST_PRESENTATION)
PERIODS = ("validation", "test")
FINAL_RESULTS = frozenset({"Pass", "Distinction", "Fail", "Withdrawn"})

# --- Grup ataması (ön kayıt eki ile birebir aynı; test sınar) ---------------
GROUP_NAMES = ("NOT", "TESLİM", "ETKİNLİK", "KAYIT")
GROUP_OF: dict[str, str] = {
    "score_mean": "NOT",
    "score_weighted_mean": "NOT",
    "n_expected": "TESLİM",
    "n_submitted": "TESLİM",
    "n_unsubmitted": "TESLİM",
    "delay_mean": "TESLİM",
    "n_banked": "TESLİM",
    "vle_clicks": "ETKİNLİK",
    "vle_active_days": "ETKİNLİK",
    "vle_days_to_cutoff": "ETKİNLİK",
    "vle_click_forumng": "ETKİNLİK",
    "vle_click_subpage": "ETKİNLİK",
    "vle_click_oucontent": "ETKİNLİK",
    "vle_click_homepage": "ETKİNLİK",
    "vle_click_resource": "ETKİNLİK",
    "date_registration": "KAYIT",
}
SET_GROUPS: dict[str, tuple[str, ...]] = {
    "NOT": ("NOT",),
    "TESLİM": ("TESLİM",),
    "ETKİNLİK": ("ETKİNLİK",),
    "NOT_TESLİM": ("NOT", "TESLİM"),
    "GENERAL": ("NOT", "TESLİM", "ETKİNLİK", "KAYIT"),
}
E1_SETS = tuple(SET_GROUPS)
E2_SETS = ("GENERAL", "NOT", "TESLİM", "ETKİNLİK")

# hedef: (pozitif final_result, negatif final_result). Geri kalan satır dışarıda.
TARGET_SPEC: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "KALDI": (frozenset({"Fail"}), frozenset({"Pass", "Distinction"})),
    "BIRAKTI": (frozenset({"Withdrawn"}), frozenset({"Pass", "Distinction"})),
    "referans": (frozenset(AT_RISK_POSITIVE), frozenset(AT_RISK_NEGATIVE)),
}
TARGET_NAMES = tuple(TARGET_SPEC)

# --- Ön kayıt ölçütleri ----------------------------------------------------
B1_MIN_GAP = 0.02
B3_MAX_GAP = 0.03
B4_MIN_GAP = 0.03
B7_MIN_SHARE = 0.5
EXPECTATION_TEXT: dict[str, tuple[str, str]] = {
    "B1": (
        "Hiçbir tek grup GENERAL'e ulaşmaz.",
        "her tek grubun test ROC AUC'si GENERAL'den en az 0,02 düşük.",
    ),
    "B2": (
        "Yalnız NOT en zayıf tek gruptur.",
        "yalnız NOT'un test ROC AUC'si, yalnız TESLİM ve yalnız ETKİNLİK'ten düşük.",
    ),
    "B3": (
        "Etkinliksiz model (NOT + TESLİM), GENERAL'in çok gerisinde kalmaz.",
        "fark 0,03'ten küçük.",
    ),
    "B4": (
        "BIRAKTI, KALDI'dan daha kolay bulunur.",
        "GENERAL'in test ROC AUC'si BIRAKTI'da KALDI'dan en az 0,03 yüksek.",
    ),
    "B5": (
        "BIRAKTI'da ETKİNLİK tek başına güçlüdür.",
        "yalnız ETKİNLİK ile GENERAL arasındaki fark BIRAKTI'da, KALDI'dakinden küçük.",
    ),
    "B6": (
        "KALDI'da NOT'un payı artar.",
        "KALDI'da yalnız NOT ile yalnız ETKİNLİK arasındaki ROC AUC farkı, "
        "referans hedeftekinden NOT lehine daha büyük.",
    ),
    "B7": (
        "İki sinyalli kural, isabetlerinin çoğunu bırakanlardan alır.",
        "kuralın %20 bayraklarındaki isabetlerin yarısından fazlası Withdrawn "
        "(test dönemi; doğrulama da raporlanır).",
    ),
}
B8_MAX_DROP = 0.01
B10_MAX_GAP = 0.02
E3_EXPECTATION_TEXT: dict[str, tuple[str, str]] = {
    "B8": (
        "Başarı kesim günüyle artar.",
        "(b) görünümünde test ROC AUC'si 14 → 120 boyunca hiçbir adımda 0,01'den fazla düşmez.",
    ),
    "B9": (
        "Kazancın büyük kısmı erken gelir.",
        "(b) görünümünde 14 → 60 artışı, 60 → 120 artışından büyük.",
    ),
    "B10": (
        "14. günde notlu ödev neredeyse yoktur; erken başarının çoğunu ETKİNLİK taşır.",
        "14. günde yalnız ETKİNLİK seti GENERAL'e 0,02'den yakın.",
    ),
}
E3_CUTOFFS = (14, 30, 60, 90, 120)
COHORT_CUTOFF = 120
E3_SETS = ("GENERAL", "ETKİNLİK")
VIEW_OWN = "a_kendi_orneklem"
VIEW_COHORT = "b_sabit_kohort"
PERIOD_ROLE = {FIT_PRESENTATION: "train", VAL_PRESENTATION: "validation", TEST_PRESENTATION: "test"}
NOTES = (
    "Karar: doğrulama (2014B) ve test (2014J) ikisinde de sağlanırsa tuttu, ikisinde de sağlanmazsa "
    "tutmadı, dönemler ayrışırsa belirsiz. Tek dönem karar vermez.",
    "NOT_TESLİM setinde KAYIT yok; B3'teki fark ETKİNLİK ile birlikte KAYIT'ı da kapsar.",
    "B1-B6 ölçütleri hgb modeliyle hesaplanır (ön kayıt: lojistik regresyon yalnız E1'de raporlanır).",
    "B5'te 'fark' işaretli GENERAL - ETKİNLİK farkıdır.",
    "GGG, doğrulama (2014B) ve test (2014J) dönemlerinde dışlanır (rule.eligible_mask); "
    "2013J eğitim satırlarına dokunulmaz (Hafta 11 ile aynı).",
    "Referans hedef GGG dışlamasıyla yeniden hesaplanır; model_metrics.json ile birebir aynı olmayabilir.",
)


# --- Grup ve set yardımcıları ---------------------------------------------
def group_columns(available: list[str] | tuple[str, ...]) -> dict[str, list[str]]:
    """GENERAL sütunlarını gruplara böler. Gruba atanmamış sütun varsa hata verir."""
    general = feature_columns("GENERAL", list(available))
    unknown = [column for column in general if column not in GROUP_OF]
    if unknown:
        raise ValueError(f"grupsuz sutun: {unknown}")
    groups: dict[str, list[str]] = {name: [] for name in GROUP_NAMES}
    for column in general:
        groups[GROUP_OF[column]].append(column)
    return groups


def set_columns(available: list[str] | tuple[str, ...]) -> dict[str, list[str]]:
    """E1 setlerinin sütunları. GENERAL sırası korunur."""
    general = feature_columns("GENERAL", list(available))
    group_columns(available)
    sets: dict[str, list[str]] = {}
    for name, parts in SET_GROUPS.items():
        columns = [column for column in general if GROUP_OF[column] in parts]
        if not columns:
            raise ValueError(f"bos set: {name}")
        _assert_allowed(columns, "GENERAL")
        sets[name] = columns
    if sets["GENERAL"] != general:
        raise ValueError("GENERAL seti eksik")
    return sets


# --- Veri hazırlığı --------------------------------------------------------
def _normalized_keys(frame: pd.DataFrame) -> pd.DataFrame:
    keys = frame.loc[:, list(STUDENT_KEY)].copy()
    for column in ("code_module", "code_presentation"):
        keys[column] = keys[column].astype("string").astype(str)
    keys["id_student"] = pd.to_numeric(keys["id_student"], errors="raise").astype("int64")
    return keys.reset_index(drop=True)


def attach_final_result(frame: pd.DataFrame, student_info: pd.DataFrame) -> pd.DataFrame:
    """studentInfo.final_result sütununu anahtarla ekler. Eksik ya da bilinmeyen değer hata verir."""
    required = (*STUDENT_KEY, "final_result")
    missing = [column for column in required if column not in student_info.columns]
    if missing:
        raise ValueError(f"studentInfo eksik sutunlar: {missing}")
    info = _normalized_keys(student_info)
    info["final_result"] = student_info["final_result"].astype("string").astype(str).to_numpy()
    if info.duplicated(list(STUDENT_KEY)).any():
        raise ValueError("studentInfo anahtari tekil degil")
    keys = _normalized_keys(frame)
    merged = keys.merge(info, on=list(STUDENT_KEY), how="left", validate="many_to_one")
    if len(merged) != len(frame):
        raise ValueError("birlestirme satir sayisini degistirdi")
    result = merged["final_result"]
    if result.isna().any():
        raise ValueError("final_result bulunamayan satir var")
    unknown = sorted(set(result.astype(str)) - FINAL_RESULTS)
    if unknown:
        raise ValueError(f"bilinmeyen final_result: {unknown}")
    out = frame.copy()
    out["final_result"] = result.astype(str).to_numpy()
    if "at_risk" in out.columns:
        expected = out["final_result"].isin(AT_RISK_POSITIVE).astype("int64").to_numpy()
        if not np.array_equal(expected, pd.to_numeric(out["at_risk"]).to_numpy(dtype=np.int64)):
            raise ValueError("at_risk final_result ile tutarsiz")
    return out


def exclude_ggg(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Doğrulama ve test dönemlerinde uygun öğrencisi olmayan sunumları dışlar.

    rule.eligible_mask ve rule.excluded_presentations kullanılır. Dışlanan
    sunumların hepsi GGG olmalı ve bu dönemlerde GGG'nin hiç uygun satırı
    kalmamalıdır; aksi halde hata verilir.
    """
    presentation = frame["code_presentation"].astype(str).to_numpy()
    module = frame["code_module"].astype(str).to_numpy()
    evaluation = np.isin(presentation, EVALUATION_PRESENTATIONS)
    eligible = eligible_mask(frame)
    excluded = excluded_presentations(frame.loc[evaluation].reset_index(drop=True))
    foreign = [item for item in excluded if item["code_module"] != EXCLUDED_MODULE]
    if foreign:
        raise ValueError(f"GGG disinda uygun ogrencisi olmayan sunum: {foreign}")
    drop = evaluation & ~eligible
    if np.any(drop & (module != EXCLUDED_MODULE)):
        raise ValueError("GGG disinda uygun olmayan satir var")
    if np.any(evaluation & eligible & (module == EXCLUDED_MODULE)):
        raise ValueError("GGG satirlari uygun; dislama varsayimi tutmuyor")
    return frame.loc[~drop].reset_index(drop=True), excluded


def prepare_frame(features: pd.DataFrame, student_info: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """final_result ekle, history satırlarını at, GGG'yi dışla."""
    frame = attach_final_result(features, student_info)
    frame = frame.loc[frame["split"].astype(str).isin(("train", "test"))].reset_index(drop=True)
    return exclude_ggg(frame)


def target_frame(frame: pd.DataFrame, target: str) -> pd.DataFrame:
    """Hedef satırları ve TARGET_COLUMN. Dışarıda kalan final_result satırı atılır."""
    if target not in TARGET_SPEC:
        raise ValueError(f"bilinmeyen hedef: {target}")
    positive, negative = TARGET_SPEC[target]
    final = frame["final_result"].astype(str)
    keep = final.isin(positive | negative)
    out = frame.loc[keep].reset_index(drop=True)
    out[TARGET_COLUMN] = out["final_result"].astype(str).isin(positive).astype("int64")
    return out


def target_counts(frame: pd.DataFrame) -> dict:
    """Hedef çerçevesinin dilimlere göre satır ve pozitif sayıları."""
    y = _target(frame, TARGET_COLUMN)
    presentation = frame["code_presentation"].astype(str).to_numpy()
    split = frame["split"].astype(str).to_numpy()
    slices = {
        "fit_2013J": presentation == FIT_PRESENTATION,
        "validation_2014B": presentation == VAL_PRESENTATION,
        "train": split == "train",
        "test_2014J": presentation == TEST_PRESENTATION,
    }
    counts = {name: {"n": int(mask.sum()), "n_positive": int(y[mask].sum())} for name, mask in slices.items()}
    counts["final_result"] = {
        str(name): int(count) for name, count in frame["final_result"].astype(str).value_counts().sort_index().items()
    }
    return counts


# --- Çalıştırma ------------------------------------------------------------
def _period_masks(frame: pd.DataFrame, allow_empty: bool = False) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    presentation = frame["code_presentation"].astype(str).to_numpy()
    split = frame["split"].astype(str).to_numpy()
    masks = {
        "validation": (presentation == FIT_PRESENTATION, presentation == VAL_PRESENTATION),
        "test": (split == "train", presentation == TEST_PRESENTATION),
    }
    for period, (fit, predict) in masks.items():
        if not predict.any() and not allow_empty:
            raise ValueError(f"{period} bos")
        if np.any(fit & predict):
            raise ValueError(f"{period} egitim ve tahmin cakisiyor")
    return masks


def run_target(
    frame: pd.DataFrame,
    sets: dict[str, list[str]],
    model_names: tuple[str, ...],
    n_boot: int = N_BOOTSTRAP,
    seed: int = RANDOM_STATE,
    log=None,
    eval_masks: dict[str, np.ndarray] | None = None,
    allow_empty: bool = False,
    empty_reason: str = "degerlendirme satiri yok",
) -> dict:
    """Bir hedef için her set ve model: ayar, doğrulama, test, GENERAL'e göre eşli fark.

    frame target_frame çıktısıdır. Protokol Hafta 10 ile aynıdır: 2013J'de eğit,
    2014B log loss ile seç; doğrulama 2013J modeli, test 2013J + 2014B modeli.

    eval_masks verilirse (görünüm adı -> frame satırları üzerinde bool maske,
    None tüm satırlar) model bir kez eğitilir ve her görünümde yalnız o
    satırlar değerlendirilir; sonuçlar entry[görünüm][dönem] altındadır ve
    eşli fark hesaplanmaz. Verilmezse entry[dönem] (E1/E2 biçimi).
    allow_empty açıkken değerlendirme satırı kalmayan dönem
    {"undefined": True, "reason": empty_reason} yazılır; kapalıyken hata verilir.
    """
    y = _target(frame, TARGET_COLUMN)
    modules_all = frame["code_module"].astype(str).to_numpy()
    train_frame = frame.loc[frame["split"].astype(str).eq("train")].reset_index(drop=True)
    views: dict = {None: None} if eval_masks is None else dict(eval_masks)
    period_masks = _period_masks(frame, allow_empty)
    context: dict = {}
    for period, (fit, predict) in period_masks.items():
        for view, mask in views.items():
            if not predict.any():
                context[(view, period)] = {"undefined": True, "reason": empty_reason}
                continue
            keep = np.ones(int(predict.sum()), dtype=bool) if mask is None else np.asarray(mask, dtype=bool)[predict]
            if not keep.any():
                if not allow_empty:
                    raise ValueError(f"{period} {view} bos")
                context[(view, period)] = {"undefined": True, "reason": empty_reason}
                continue
            y_period = y[predict][keep]
            modules = modules_all[predict][keep]
            context[(view, period)] = {
                "keep": keep,
                "y": y_period,
                "modules": modules,
                "indices": bootstrap_indices(modules, y_period, n_boot, seed),
            }
    results: dict = {}
    probas: dict = {}
    samples: dict = {}
    for set_name, columns in sets.items():
        results[set_name] = {}
        for model_name in model_names:
            if log is not None:
                log(f"  {set_name} {model_name}")
            selected = select_hyperparameters(train_frame, list(columns), model_name, TARGET_COLUMN)
            entry: dict = {"columns": list(columns), "selected": selected}
            for period, (fit, predict) in period_masks.items():
                needed = [view for view in views if "undefined" not in context[(view, period)]]
                proba = None
                if needed:
                    proba = _predict(
                        frame,
                        selected["params"],
                        fit,
                        predict,
                        list(columns),
                        model_name,
                        TARGET_COLUMN,
                    )
                for view in views:
                    ctx = context[(view, period)]
                    if "undefined" in ctx:
                        block: dict = dict(ctx)
                    else:
                        scores = proba[ctx["keep"]]
                        boot = _bootstrap_samples(ctx["y"], scores, ctx["indices"])
                        if eval_masks is None:
                            probas[(period, set_name, model_name)] = scores
                            samples[(period, set_name, model_name)] = boot
                        intervals = metric_intervals(
                            ctx["y"], scores, ctx["modules"], indices=ctx["indices"], samples=boot
                        )
                        module_block = _module_table(
                            ctx["modules"], ctx["y"], {set_name: scores}, model_name, set_names=(set_name,)
                        )
                        block = {
                            "n": int(ctx["y"].shape[0]),
                            "n_positive": int(ctx["y"].sum()),
                            "roc_auc": intervals["roc_auc"],
                            "module_mean_roc_auc": module_block["mean"][set_name],
                            "within_module_20": within_module_flags(ctx["modules"], ctx["y"], scores)["total"],
                        }
                    if eval_masks is None:
                        entry[period] = block
                    else:
                        entry.setdefault(view, {})[period] = block
            results[set_name][model_name] = entry
    paired: dict = {}
    if "GENERAL" in sets and eval_masks is None:
        for model_name in model_names:
            paired[model_name] = {}
            for set_name in sets:
                if set_name == "GENERAL":
                    continue
                label = f"{set_name}-GENERAL"
                paired[model_name][label] = {}
                for period in period_masks:
                    ctx = context[(None, period)]
                    if "undefined" in ctx:
                        paired[model_name][label][period] = dict(ctx)
                        continue
                    paired[model_name][label][period] = paired_difference(
                        ctx["y"],
                        probas[(period, set_name, model_name)],
                        probas[(period, "GENERAL", model_name)],
                        ctx["modules"],
                        indices=ctx["indices"],
                        samples_left=samples[(period, set_name, model_name)],
                        samples_right=samples[(period, "GENERAL", model_name)],
                    )
    return {"results": results, "paired_vs_general": paired}


def rule2_hits_by_final_result(period_frame: pd.DataFrame) -> dict:
    """İki sinyalli kuralın %20 bayraklarındaki isabetlerin final_result kırılımı.

    period_frame tek bir sunumun (GGG dışlanmış) satırlarıdır. Bayrak
    rule.score_frame(signals=RULE2_SIGNALS) ile; isabet Fail veya Withdrawn.
    """
    scored = score_frame(period_frame, signals=RULE2_SIGNALS)
    flagged = scored["flagged"].to_numpy(dtype=bool)
    final = period_frame["final_result"].astype(str).to_numpy()
    n_fail = int(np.sum(flagged & (final == "Fail")))
    n_withdrawn = int(np.sum(flagged & (final == "Withdrawn")))
    n_passed = int(np.sum(flagged & np.isin(final, ("Pass", "Distinction"))))
    return {
        "n": int(len(period_frame)),
        "n_flagged": int(flagged.sum()),
        "n_hit": n_fail + n_withdrawn,
        "n_fail": n_fail,
        "n_withdrawn": n_withdrawn,
        "n_pass_distinction": n_passed,
    }


def evaluate_expectations(
    hgb_auc: dict | None = None,
    b7: dict | None = None,
    e3_auc: dict | None = None,
) -> dict:
    """B1-B10 ölçütleri, ön kayıt metniyle birebir.

    Karar: doğrulama ve test ikisinde de sağlanırsa "tuttu", ikisinde de
    sağlanmazsa "tutmadı", dönemler ayrışırsa "belirsiz".

    hgb_auc[period][hedef][set] hgb doğrulama/test ROC AUC tahminidir (B1-B6).
    b7[period] rule2_hits_by_final_result çıktısıdır (B7); hgb_auc ile birlikte verilir.
    e3_auc[period][kesim günü][set] sabit kohort (b) görünümünün ana (dışlamasız)
    hgb ROC AUC tahminidir; GENERAL ve ETKİNLİK gerekir (B8-B10).
    Verilmeyen grubun beklentileri rapora girmez. Eksik ya da sonlu olmayan
    değer hata verir.
    """
    if hgb_auc is None and e3_auc is None:
        raise ValueError("ne hgb_auc ne e3_auc verildi")
    if hgb_auc is not None and b7 is None:
        raise ValueError("b7 yok")
    report: dict = {}
    if hgb_auc is not None:
        for key, (expectation, criterion) in EXPECTATION_TEXT.items():
            report[key] = {"expectation": expectation, "criterion": criterion}
    if e3_auc is not None:
        for key, (expectation, criterion) in E3_EXPECTATION_TEXT.items():
            report[key] = {"expectation": expectation, "criterion": criterion}
        for period in PERIODS:

            def early(cutoff: int, set_name: str) -> float:
                number = e3_auc[period][cutoff][set_name]
                if number is None or not np.isfinite(float(number)):
                    raise ValueError(f"ROC AUC yok: {period} kesim {cutoff} {set_name}")
                return float(number)

            general_by_cutoff = {cutoff: early(cutoff, "GENERAL") for cutoff in E3_CUTOFFS}
            steps = [
                {
                    "from": earlier,
                    "to": later,
                    "drop": general_by_cutoff[earlier] - general_by_cutoff[later],
                }
                for earlier, later in zip(E3_CUTOFFS[:-1], E3_CUTOFFS[1:])
            ]
            report["B8"][period] = {
                "general_auc": {str(cutoff): value for cutoff, value in general_by_cutoff.items()},
                "steps": steps,
                "max_drop": max(step["drop"] for step in steps),
                "max_allowed_drop": B8_MAX_DROP,
                "holds": bool(all(step["drop"] <= B8_MAX_DROP for step in steps)),
            }
            early_gain = general_by_cutoff[60] - general_by_cutoff[14]
            late_gain = general_by_cutoff[120] - general_by_cutoff[60]
            report["B9"][period] = {
                "gain_14_60": early_gain,
                "gain_60_120": late_gain,
                "holds": bool(early_gain > late_gain),
            }
            activity_gap = general_by_cutoff[14] - early(14, "ETKİNLİK")
            report["B10"][period] = {
                "general_auc_14": general_by_cutoff[14],
                "activity_auc_14": early(14, "ETKİNLİK"),
                "gap": activity_gap,
                "max_gap": B10_MAX_GAP,
                "holds": bool(abs(activity_gap) < B10_MAX_GAP),
            }
    for period in (PERIODS if hgb_auc is not None else ()):
        auc = hgb_auc[period]

        def value(target: str, set_name: str) -> float:
            number = auc[target][set_name]
            if number is None or not np.isfinite(float(number)):
                raise ValueError(f"ROC AUC yok: {period} {target} {set_name}")
            return float(number)

        general = value("referans", "GENERAL")
        gaps = {name: general - value("referans", name) for name in ("NOT", "TESLİM", "ETKİNLİK")}
        report["B1"][period] = {
            "general_auc": general,
            "gap_to_general": gaps,
            "min_gap": B1_MIN_GAP,
            "holds": bool(all(gap >= B1_MIN_GAP for gap in gaps.values())),
        }
        only_not = value("referans", "NOT")
        only_submit = value("referans", "TESLİM")
        only_activity = value("referans", "ETKİNLİK")
        report["B2"][period] = {
            "auc": {"NOT": only_not, "TESLİM": only_submit, "ETKİNLİK": only_activity},
            "holds": bool(only_not < only_submit and only_not < only_activity),
        }
        gap_without_activity = general - value("referans", "NOT_TESLİM")
        report["B3"][period] = {
            "general_auc": general,
            "not_submit_auc": value("referans", "NOT_TESLİM"),
            "gap": gap_without_activity,
            "max_gap": B3_MAX_GAP,
            "holds": bool(gap_without_activity < B3_MAX_GAP),
        }
        general_failed = value("KALDI", "GENERAL")
        general_left = value("BIRAKTI", "GENERAL")
        difference = general_left - general_failed
        report["B4"][period] = {
            "general_auc_BIRAKTI": general_left,
            "general_auc_KALDI": general_failed,
            "difference": difference,
            "min_gap": B4_MIN_GAP,
            "holds": bool(difference >= B4_MIN_GAP),
        }
        gap_left = value("BIRAKTI", "GENERAL") - value("BIRAKTI", "ETKİNLİK")
        gap_failed = value("KALDI", "GENERAL") - value("KALDI", "ETKİNLİK")
        report["B5"][period] = {
            "gap_BIRAKTI": gap_left,
            "gap_KALDI": gap_failed,
            "holds": bool(gap_left < gap_failed),
        }
        not_minus_activity_failed = value("KALDI", "NOT") - value("KALDI", "ETKİNLİK")
        not_minus_activity_reference = value("referans", "NOT") - value("referans", "ETKİNLİK")
        report["B6"][period] = {
            "not_minus_activity_KALDI": not_minus_activity_failed,
            "not_minus_activity_referans": not_minus_activity_reference,
            "holds": bool(not_minus_activity_failed > not_minus_activity_reference),
        }
        hits = b7[period]
        if int(hits["n_hit"]) < 1:
            raise ValueError(f"kuralin isabeti yok: {period}")
        share = int(hits["n_withdrawn"]) / int(hits["n_hit"])
        report["B7"][period] = {
            "n_hit": int(hits["n_hit"]),
            "n_withdrawn": int(hits["n_withdrawn"]),
            "n_fail": int(hits["n_fail"]),
            "withdrawn_share": share,
            "min_share": B7_MIN_SHARE,
            "holds": bool(share > B7_MIN_SHARE),
        }
    for key in report:
        validation_holds = report[key]["validation"]["holds"]
        test_holds = report[key]["test"]["holds"]
        if validation_holds and test_holds:
            report[key]["result"] = "tuttu"
        elif not validation_holds and not test_holds:
            report[key]["result"] = "tutmadı"
        else:
            report[key]["result"] = "belirsiz"
    return report


def _hgb_auc(targets: dict) -> dict:
    out: dict = {}
    for period in PERIODS:
        out[period] = {}
        for target, block in targets.items():
            out[period][target] = {
                set_name: models["hgb"][period]["roc_auc"]["estimate"]
                for set_name, models in block["results"].items()
                if "hgb" in models
            }
    return out


def build_report(
    features: pd.DataFrame,
    student_info: pd.DataFrame,
    n_boot: int = N_BOOTSTRAP,
    seed: int = RANDOM_STATE,
    log=None,
    registration: dict | None = None,
) -> dict:
    """registration: {dosya adı: {"md5", "history"}}; None ise diskten okunur."""
    available = list(features.columns)
    sets = set_columns(available)
    frame, excluded = prepare_frame(features, student_info)

    targets: dict = {}
    counts: dict = {}
    plans = (
        ("referans", E1_SETS, MODEL_NAMES),
        ("KALDI", E2_SETS, ("hgb",)),
        ("BIRAKTI", E2_SETS, ("hgb",)),
    )
    for target, set_names, model_names in plans:
        if log is not None:
            log(f"hedef {target}")
        framed = target_frame(frame, target)
        counts[target] = target_counts(framed)
        targets[target] = run_target(
            framed,
            {name: sets[name] for name in set_names},
            model_names,
            n_boot=n_boot,
            seed=seed,
            log=log,
        )

    presentation = frame["code_presentation"].astype(str).to_numpy()
    b7 = {
        period: rule2_hits_by_final_result(frame.loc[presentation == presentation_name].reset_index(drop=True))
        for period, presentation_name in (("validation", VAL_PRESENTATION), ("test", TEST_PRESENTATION))
    }
    expectations = evaluate_expectations(_hgb_auc(targets), b7)

    reference = targets["referans"]
    e2_reference = {
        "results": {name: {"hgb": reference["results"][name]["hgb"]} for name in E2_SETS},
        "note": "E1 referans hedefiyle aynı çalıştırma (aynı sayılar).",
    }
    return {
        "label": "ek analiz (keşifsel)",
        "protocol": {
            "fit_presentation": FIT_PRESENTATION,
            "validation_presentation": VAL_PRESENTATION,
            "test_presentation": TEST_PRESENTATION,
            "n_bootstrap": n_boot,
            "seed": seed,
            "flag_fraction": 0.2,
            "excluded_module": EXCLUDED_MODULE,
        },
        "notes": list(NOTES),
        "pre_registration_md5": registration if registration is not None else _current_registration(),
        "excluded_presentations": excluded,
        "groups": {name: [c for c in GROUP_OF if GROUP_OF[c] == name] for name in GROUP_NAMES},
        "group_of": dict(GROUP_OF),
        "sets": {name: columns for name, columns in sets.items()},
        "e1": {
            "target": "referans",
            "counts": counts["referans"],
            "results": reference["results"],
            "paired_vs_general": reference["paired_vs_general"],
        },
        "e2": {
            "counts": counts,
            "targets": {
                "referans": e2_reference,
                "KALDI": targets["KALDI"],
                "BIRAKTI": targets["BIRAKTI"],
            },
        },
        "b7_rule2_hits": b7,
        "expectations": expectations,
    }


# --- E3: ne kadar erken? ---------------------------------------------------
SECONDARY_EMPTY_REASON = (
    "kesim gününe kadar notlu ödevi olan modül-dönem kalmadı; "
    "ikincil (dışlamalı) ROC AUC tanımsız"
)


def exclude_ineligible(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Doğrulama ve test dönemlerinde n_expected == 0 olan modül-dönemleri dışlar.

    exclude_ggg ile aynı mantık (rule.eligible_mask, rule.excluded_presentations);
    farkı, dışlananların GGG olmasını şart koşmaz (kesim gününe göre değişir).
    Bir modül-dönemin yalnız bir kısmı uygunsa hata verir. Eğitim satırlarına dokunmaz.
    """
    presentation = frame["code_presentation"].astype(str).to_numpy()
    module = frame["code_module"].astype(str).to_numpy()
    evaluation = np.isin(presentation, EVALUATION_PRESENTATIONS)
    eligible = eligible_mask(frame)
    groups = pd.DataFrame(
        {
            "group": pd.Series(module[evaluation]) + "\x1f" + pd.Series(presentation[evaluation]),
            "eligible": eligible[evaluation],
        }
    )
    summary = groups.groupby("group")["eligible"].agg(["any", "all"])
    mixed = summary.index[summary["any"] & ~summary["all"]].tolist()
    if mixed:
        raise ValueError(f"modul-donemin yalniz bir kismi uygun: {mixed}")
    excluded = excluded_presentations(frame.loc[evaluation].reset_index(drop=True))
    return frame.loc[~(evaluation & ~eligible)].reset_index(drop=True), excluded


def ineligible_listing(frame: pd.DataFrame) -> list[dict]:
    """Kesim gününe kadar notlu ödevi olmayan tüm modül-dönemler (bilgi; dışlama değil)."""
    return [
        {**row, "role": PERIOD_ROLE.get(row["code_presentation"], "other")}
        for row in excluded_presentations(frame)
    ]


def e3_frame(features: pd.DataFrame, student_info: pd.DataFrame) -> pd.DataFrame:
    """final_result ekle, history satırlarını at. Dışlama YOK (E3 ana görünümü)."""
    frame = attach_final_result(features, student_info)
    return frame.loc[frame["split"].astype(str).isin(("train", "test"))].reset_index(drop=True)


def _key_tuples(frame: pd.DataFrame) -> list[tuple]:
    keys = _normalized_keys(frame)
    return list(zip(keys["code_module"].tolist(), keys["code_presentation"].tolist(), keys["id_student"].tolist()))


def cohort_keys(frame: pd.DataFrame) -> set[tuple]:
    """Sabit kohort: kohort kesimindeki örneklemin doğrulama ve test dönemi öğrencileri."""
    presentation = frame["code_presentation"].astype(str).to_numpy()
    rows = frame.loc[np.isin(presentation, EVALUATION_PRESENTATIONS)]
    return set(_key_tuples(rows))


def cohort_mask(frame: pd.DataFrame, cohort: set[tuple]) -> np.ndarray:
    """frame satırları için kohort üyeliği. Yalnız değerlendirme satırlarında anlamlıdır."""
    return np.fromiter((key in cohort for key in _key_tuples(frame)), dtype=bool, count=len(frame))


def _secondary_block(
    kept: pd.DataFrame,
    excluded: list[dict],
    sets: dict[str, list[str]],
    n_boot: int,
    seed: int,
    log,
) -> dict:
    """İkincil: kesimin notlu ödevi olmayan modül-dönemleri değerlendirmeden çıkarılmış ROC AUC (yalnız (a))."""
    framed = target_frame(kept, "referans")
    block: dict = {
        "definition": "doğrulama ve test dönemlerinde n_expected == 0 modül-dönemler dışarıda; eğitim satırları kalır (E1/E2 ile aynı mantık)",
        "excluded_presentations": excluded,
        "counts": target_counts(framed),
    }
    if not framed["code_presentation"].astype(str).eq(VAL_PRESENTATION).any():
        block["status"] = "tanımsız"
        block["reason"] = SECONDARY_EMPTY_REASON + " (doğrulama dönemi boş; ayar yapılamaz)"
        block["results"] = {}
        return block
    out = run_target(
        framed,
        sets,
        ("hgb",),
        n_boot=n_boot,
        seed=seed,
        log=log,
        allow_empty=True,
        empty_reason=SECONDARY_EMPTY_REASON,
    )
    block["results"] = out["results"]
    has_test = framed["code_presentation"].astype(str).eq(TEST_PRESENTATION).any()
    block["status"] = "tanımlı" if has_test else "kısmen tanımsız"
    if not has_test:
        block["reason"] = SECONDARY_EMPTY_REASON + " (test dönemi)"
    return block


def build_e3(
    feature_builder,
    student_info: pd.DataFrame,
    cutoffs: tuple[int, ...] = E3_CUTOFFS,
    cohort_cutoff: int = COHORT_CUTOFF,
    n_boot: int = N_BOOTSTRAP,
    seed: int = RANDOM_STATE,
    log=None,
    registration: dict | None = None,
) -> dict:
    """E3: kesim günü başına GENERAL ve ETKİNLİK (hgb), iki görünüm, ikincil değer.

    feature_builder(kesim_günü) özellik tablosu döndürür (dataset.build_features).
    Model her kesimde o kesimin kendi eğitim örneklemiyle eğitilir; sabit kohort
    yalnızca değerlendirme satırlarını sabitler.
    """
    if cohort_cutoff not in cutoffs:
        raise ValueError("kohort kesimi kesim gunleri arasinda degil")
    features: dict = {}
    problems = []
    for cutoff in cutoffs:
        built = feature_builder(cutoff)
        try:
            set_columns(list(built.columns))
        except ValueError as error:
            problems.append(f"kesim {cutoff}: {error}")
        features[cutoff] = built
    if problems:
        raise ValueError("E3 grup atamasi durdu: " + "; ".join(problems))
    frames = {cutoff: e3_frame(features[cutoff], student_info) for cutoff in cutoffs}
    exclusions = {cutoff: exclude_ineligible(frames[cutoff]) for cutoff in cutoffs}
    cohort = cohort_keys(frames[cohort_cutoff])
    for cutoff in cutoffs:
        if int(cohort_mask(frames[cutoff], cohort).sum()) != len(cohort):
            raise ValueError(f"sabit kohort kesim {cutoff} ornekleminde eksik")

    blocks: dict = {}
    for cutoff in cutoffs:
        if log is not None:
            log(f"E3 kesim {cutoff}")
        frame = frames[cutoff]
        sets = set_columns(list(frame.columns))
        chosen = {name: sets[name] for name in E3_SETS}
        block: dict = {
            "n_rows": int(len(frame)),
            "vle_click_columns": [column for column in sets["GENERAL"] if column.startswith("vle_click_")],
            "no_graded_assignment_presentations": ineligible_listing(frame),
            "targets": {},
        }
        for target, set_names in (("referans", E3_SETS), ("KALDI", ("GENERAL",)), ("BIRAKTI", ("GENERAL",))):
            framed = target_frame(frame, target)
            out = run_target(
                framed,
                {name: chosen[name] for name in set_names},
                ("hgb",),
                n_boot=n_boot,
                seed=seed,
                log=log,
                eval_masks={VIEW_OWN: None, VIEW_COHORT: cohort_mask(framed, cohort)},
            )
            block["targets"][target] = {"counts": target_counts(framed), "results": out["results"]}
        kept, excluded = exclusions[cutoff]
        block["secondary"] = _secondary_block(kept, excluded, chosen, n_boot, seed, log)
        blocks[str(cutoff)] = block

    report: dict = {
        "label": "ek analiz E3 (keşifsel)",
        "cutoffs": list(cutoffs),
        "views": {
            VIEW_OWN: "her kesimin kendi örneklemi; notlu ödev dışlaması yok",
            VIEW_COHORT: (
                f"{cohort_cutoff}. günde hâlâ kayıtlı doğrulama ve test öğrencileri (bütün modül-dönemler); "
                "değerlendirme satırları her kesimde aynı"
            ),
        },
        "cohort": {
            "cutoff": cohort_cutoff,
            "n_students": len(cohort),
            "n_by_period": {
                period: sum(1 for key in cohort if key[1] == presentation)
                for period, presentation in (("validation", VAL_PRESENTATION), ("test", TEST_PRESENTATION))
            },
        },
        "notes": [
            "Model her kesimde o kesimin kendi eğitim örneklemiyle eğitilir; sabit kohort yalnızca değerlendirme satırlarını sabitler.",
            "Ana görünümlerde notlu ödev dışlaması uygulanmaz; ikincil değer yalnız (a) görünümünde ve referans hedefte raporlanır.",
            "Ana görünümün 60. gün değeri E1'den farklı olabilir çünkü ana görünümde GGG dahildir; ikincil 60. gün değeri E1 GENERAL ile birebir aynıdır.",
            "KALDI ve BIRAKTI GENERAL değerleri beklenti değildir, yalnızca raporlanır.",
            "Kural tabanlı ölçü (rule2) E3'te raporlanmaz.",
            "Kohort örneklemi dataset.build_features ile aynı kuralla kurulur: date_unregistration < kesim olanlar dışarıda.",
        ],
        "pre_registration_md5": registration if registration is not None else _current_registration(),
        "cutoff_results": blocks,
    }
    if tuple(cutoffs) == E3_CUTOFFS:
        e3_auc: dict = {}
        for period in PERIODS:
            e3_auc[period] = {}
            for cutoff in cutoffs:
                results = blocks[str(cutoff)]["targets"]["referans"]["results"]
                e3_auc[period][cutoff] = {}
                for set_name in E3_SETS:
                    cell = results[set_name]["hgb"][VIEW_COHORT][period]
                    e3_auc[period][cutoff][set_name] = (
                        None if "undefined" in cell else cell["roc_auc"]["estimate"]
                    )
        report["expectations"] = evaluate_expectations(e3_auc=e3_auc)
    else:
        report["expectations"] = {}
        report["expectations_note"] = "kesim günleri ön kayıttaki (14, 30, 60, 90, 120) değil; B8-B10 hesaplanmadı"
    return report


def check_e3_matches_e1(e3: dict, e1: dict, cutoff: int = 60) -> None:
    """60. günün ikincil (dışlamalı) GENERAL ve ETKİNLİK sonuçları E1 ile aynı olmalı."""
    block = e3["cutoff_results"].get(str(cutoff))
    if block is None:
        raise ValueError(f"E3'te kesim {cutoff} yok")
    secondary = block["secondary"]
    if secondary["status"] != "tanımlı":
        raise ValueError(f"kesim {cutoff} ikincil sonuc tanimli degil")
    for set_name in E3_SETS:
        mine = secondary["results"][set_name]["hgb"]
        reference = e1["results"][set_name]["hgb"]
        if mine["selected"]["params"] != reference["selected"]["params"]:
            raise ValueError(f"E3 kesim {cutoff} {set_name} ayari E1 ile farkli")
        for period in PERIODS:
            for key in ("n", "n_positive"):
                if int(mine[period][key]) != int(reference[period][key]):
                    raise ValueError(f"E3 kesim {cutoff} {set_name} {period} {key} E1 ile farkli")
            if not math.isclose(
                float(mine[period]["roc_auc"]["estimate"]),
                float(reference[period]["roc_auc"]["estimate"]),
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                raise ValueError(f"E3 kesim {cutoff} {set_name} {period} ROC AUC E1 ile farkli")


def print_e3(e3: dict) -> None:
    print("e3_hgb_roc_auc (referans hedef)")
    print("cutoff\tview\tset\tvalidation\ttest")
    for cutoff, block in e3["cutoff_results"].items():
        for set_name, models in block["targets"]["referans"]["results"].items():
            for view in (VIEW_OWN, VIEW_COHORT):
                cells = models["hgb"][view]
                print(
                    f"{cutoff}\t{view}\t{set_name}\t{_fmt(cells['validation']['roc_auc']['estimate'])}\t"
                    f"{_fmt(cells['test']['roc_auc']['estimate'])}"
                )
    print()
    print("e3_secondary (notlu ödevi olmayan modül-dönemler dışarıda)")
    print("cutoff\tstatus\tset\tvalidation\ttest")
    for cutoff, block in e3["cutoff_results"].items():
        secondary = block["secondary"]
        for set_name, models in secondary["results"].items():
            cells = models["hgb"]
            values = [
                "tanımsız" if "undefined" in cells[period] else _fmt(cells[period]["roc_auc"]["estimate"])
                for period in PERIODS
            ]
            print(f"{cutoff}\t{secondary['status']}\t{set_name}\t{values[0]}\t{values[1]}")
        if not secondary["results"]:
            print(f"{cutoff}\t{secondary['status']}\t-\ttanımsız\ttanımsız")
    print()
    print("e3_expectations")
    print("id\tvalidation_holds\ttest_holds\tresult")
    for key, block in e3["expectations"].items():
        print(f"{key}\t{block['validation']['holds']}\t{block['test']['holds']}\t{block['result']}")


# --- Bütünlük denetimleri --------------------------------------------------
def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _is_record(line: str) -> bool:
    parts = line.split()
    return len(parts) == 2 and len(parts[0]) == 32 and all(char in "0123456789abcdef" for char in parts[0].lower())


def registration_history(text: str, name: str) -> list[dict]:
    """on_kayit_md5.txt içinde name için kayıtlar, dosya sırasıyla.

    Biçim: 'md5  yol' satırı ve ardından zaman satırı. Kayıt yoksa ya da
    kaydın zaman satırı yoksa hata verir.
    """
    lines = text.splitlines()
    history = []
    for index, line in enumerate(lines):
        if not _is_record(line):
            continue
        digest, path = line.split()
        if Path(path).name != name:
            continue
        stamp = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if not stamp or _is_record(stamp):
            raise ValueError(f"{name} kaydinin zaman satiri yok ({digest})")
        history.append({"md5": digest, "time": stamp})
    if not history:
        raise ValueError(f"{name} icin kayitli md5 yok ({PRE_REGISTRATION_MD5_PATH.name})")
    return history


def check_pre_registration(
    md5_path: Path | None = None,
    paths: tuple[Path, ...] | None = None,
) -> dict[str, list[dict]]:
    """Her dosyanın md5 değeri on_kayit_md5.txt'deki SON kayıtla aynı olmalı.

    Kayıt geçmişini ({dosya adı: [{md5, time}, ...]}) döndürür.
    """
    source = PRE_REGISTRATION_MD5_PATH if md5_path is None else Path(md5_path)
    files = PRE_REGISTRATION_PATHS if paths is None else tuple(paths)
    text = source.read_text(encoding="utf-8")
    histories: dict[str, list[dict]] = {}
    for path in files:
        history = registration_history(text, path.name)
        if _md5(path) != history[-1]["md5"]:
            raise ValueError(f"{path.name} son kayittan sonra degismis")
        histories[path.name] = history
    return histories


def check_rule2_consistency(b7: dict, rule2_report: dict) -> None:
    """B7 isabet sayıları rule2_metrics.json ile aynı olmalı."""
    for period_block in rule2_report["periods"]:
        period = period_block["role"]
        total = next(row for row in period_block["total"] if row["method"] == "rule2")
        mine = b7[period]
        for key in ("n", "n_flagged", "n_hit"):
            if int(mine[key]) != int(total[key]):
                raise ValueError(f"rule2 tutarsiz: {period} {key} {mine[key]} != {total[key]}")


def registration_block(histories: dict[str, list[dict]]) -> dict:
    """Rapor için: dosya başına geçerli (son) md5 ve sıralı kayıt geçmişi."""
    return {
        name: {"md5": history[-1]["md5"], "history": [dict(item) for item in history]}
        for name, history in histories.items()
    }


def _current_registration() -> dict:
    text = PRE_REGISTRATION_MD5_PATH.read_text(encoding="utf-8")
    return registration_block(
        {
            path.name: registration_history(text, path.name)
            for path in PRE_REGISTRATION_PATHS
        }
    )


def print_report(report: dict) -> None:
    print("e1_test_roc_auc (referans hedef)")
    print("set\tmodel\tvalidation\ttest\ttest_module_mean")
    for set_name, models in report["e1"]["results"].items():
        for model_name, entry in models.items():
            print(
                f"{set_name}\t{model_name}\t{_fmt(entry['validation']['roc_auc']['estimate'])}\t"
                f"{_fmt(entry['test']['roc_auc']['estimate'])}\t"
                f"{_fmt(entry['test']['module_mean_roc_auc']['roc_auc'])}"
            )
    print()
    print("e2_hgb_roc_auc")
    print("target\tset\tn_test\tn_positive_test\tvalidation\ttest")
    for target, block in report["e2"]["targets"].items():
        for set_name, models in block["results"].items():
            entry = models["hgb"]
            print(
                f"{target}\t{set_name}\t{entry['test']['n']}\t{entry['test']['n_positive']}\t"
                f"{_fmt(entry['validation']['roc_auc']['estimate'])}\t{_fmt(entry['test']['roc_auc']['estimate'])}"
            )
    print()
    print("b7_rule2_hits")
    print("period\tn_flagged\tn_hit\tn_fail\tn_withdrawn")
    for period, hits in report["b7_rule2_hits"].items():
        print(f"{period}\t{hits['n_flagged']}\t{hits['n_hit']}\t{hits['n_fail']}\t{hits['n_withdrawn']}")
    print()
    print("expectations")
    print("id\tvalidation_holds\ttest_holds\tresult")
    for key, block in report["expectations"].items():
        print(f"{key}\t{block['validation']['holds']}\t{block['test']['holds']}\t{block['result']}")


def _write_report(report: dict) -> None:
    EK_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EK_REPORT_PATH.write_text(
        json.dumps(_jsonable(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_e1_e2(histories: dict) -> None:
    features = pd.read_parquet(PROCESSED_OULAD_DIR / FEATURES_NAME, engine="pyarrow")
    student_info = load_table("studentInfo")
    report = build_report(
        features,
        student_info,
        log=print,
        registration=registration_block(histories),
    )
    rule2_report = json.loads(RULE2_PATH.read_text(encoding="utf-8"))
    check_rule2_consistency(report["b7_rule2_hits"], rule2_report)
    if EK_REPORT_PATH.is_file():
        previous = json.loads(EK_REPORT_PATH.read_text(encoding="utf-8"))
        if "e3" in previous:
            report["e3"] = previous["e3"]
    _write_report(report)
    print_report(report)
    print(f"ek_metrics_path={EK_REPORT_PATH}")


def run_e3(histories: dict) -> None:
    """E3'ü koşar ve ek_metrics.json'a yalnız "e3" anahtarını yazar; diğer alanlar aynen kalır."""
    if not EK_REPORT_PATH.is_file():
        raise FileNotFoundError(f"once E1/E2 kosusu gerekli: {EK_REPORT_PATH}")
    existing = json.loads(EK_REPORT_PATH.read_text(encoding="utf-8"))
    if "e1" not in existing:
        raise ValueError("ek_metrics.json'da e1 yok")
    tables = load_tables()
    daily = pd.read_parquet(PROCESSED_OULAD_DIR / DAILY_NAME, engine="pyarrow")
    e3 = build_e3(
        lambda cutoff: build_features(tables, daily, cutoff=cutoff),
        tables["studentInfo"],
        log=print,
        registration=registration_block(histories),
    )
    check_e3_matches_e1(e3, existing["e1"])
    existing["e3"] = e3
    _write_report(existing)
    print_e3(e3)
    print(f"ek_metrics_path={EK_REPORT_PATH}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--e3", action="store_true", help="yalniz E3: ek_metrics.json'a e3 anahtarini yazar")
    args = parser.parse_args(argv)
    histories = check_pre_registration()
    if args.e3:
        run_e3(histories)
    else:
        run_e1_e2(histories)


if __name__ == "__main__":
    main()
