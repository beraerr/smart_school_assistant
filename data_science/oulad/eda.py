"""Notebook 02 (OULAD keşif) hesaplarını içerir.

Bu modüldeki her fonksiyon, daha önce notebooks/02_oulad_eda.ipynb ve
notebooks/02_oulad_eda_eng.ipynb hücrelerinde tanımlı olan kodun davranışı
değiştirilmeden taşınmış hâlidir. Notebook'lar yalnızca bu fonksiyonları çağırır,
basar ve çizer; scripts/arastirma_paketi.py aynı fonksiyonları çağırır.
Grafik çizen kod (matplotlib) notebook'ta kalır.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_science.oulad import PROCESSED_OULAD_DIR, RAW_OULAD_DIR
from data_science.oulad.dataset import (
    CUTOFF_DAY,
    FEATURE_LIST_PATH,
    PRESENTATION_ORDER,
    SCHOOL_ABSENCE,
    SCHOOL_GRADE,
    SCHOOL_HISTORY_GRADES,
    SCHOOL_HISTORY_OUTCOMES,
    SCHOOL_IDENTIFIER,
    SCHOOL_NONE,
    SCHOOL_SUBMISSION,
    SCHOOL_TARGET,
    build_features,
)
from data_science.oulad.load import TABLE_FILES, iter_typed_csv
from data_science.oulad.vle import (
    DAILY_NAME,
    DEFAULT_CHUNKSIZE,
    STUDENT_VLE_DTYPES,
    STUDENT_VLE_NAME,
)

KEYS = ["code_module", "code_presentation", "id_student"]
N_QUANTILES = 5
SPLIT_ORDER = ["history", "train", "test"]
LEFT_OUT_INFO = ("num_of_prev_attempts", "studied_credits")

# Erken sinyaller: sinyal -> dilim sayısı (None: değer değer).
SIGNAL_QUANTILES = {
    "n_unsubmitted": None,
    "vle_clicks": N_QUANTILES,
    "score_mean": N_QUANTILES,
    "score_vs_hist": N_QUANTILES,
}

CATALOG_COLUMNS = ["column", "definition", "scope", "school_tr", "school_en", "group"]

# Katalog sırası: okul karşılığı (TR) bu sırayla, sonra sütun adı.
SCHOOL_ORDER = {
    school_tr: order
    for order, (school_tr, _) in enumerate(
        (
            SCHOOL_GRADE,
            SCHOOL_SUBMISSION,
            SCHOOL_ABSENCE,
            SCHOOL_NONE,
            SCHOOL_HISTORY_GRADES,
            SCHOOL_HISTORY_OUTCOMES,
            SCHOOL_IDENTIFIER,
            SCHOOL_TARGET,
        )
    )
}
NON_MODEL_SCHOOL_TR = frozenset({SCHOOL_IDENTIFIER[0], SCHOOL_TARGET[0]})

GGG_PRESENTATIONS = ["2014B", "2014J"]

LABELS_TR = {
    "module": "modül",
    "presentation": "sunum",
    "at_risk_rate": "risk oranı",
    "rows": "satır",
    "has_history_rate": "geçmiş oranı",
    "missing": "eksik",
    "heatmap_title": "Modül ve sunuma göre risk oranı",
    "scatter_title": "Geçmiş modül risk oranı ve bu sunumun risk oranı",
    "scatter_xlabel": "Önceki sunumların risk oranı",
    "scatter_ylabel": "Bu sunumun risk oranı",
    "slot_title": "{module}",
    "slot_suptitle": "Aynı yuvanın sunumlar arası ortalama notu",
    "slot_xlabel": "sunum",
    "slot_ylabel": "ortalama not",
    "unsubmitted_title": "Teslim edilmeyen ödev sayısı ve risk oranı",
    "unsubmitted_xlabel": "teslim edilmeyen ödev sayısı",
    "clicks_title": "Tıklama dilimleri ve risk oranı",
    "clicks_xlabel": "tıklama dilimi",
    "score_title": "Ortalama not dilimleri ve risk oranı",
    "score_xlabel": "ortalama not dilimi",
    "history_gap_title": "Geçmiş nota göre fark dilimleri ve risk oranı",
    "history_gap_xlabel": "not eksi geçmiş yuva ortalaması",
    "feature": "özellik",
    "school": "okul karşılığı",
    "school_not": "not",
    "school_absence": "devamsızlık",
    "school_context": "ders bağlamı",
}

LABELS_EN = {
    "module": "module",
    "presentation": "presentation",
    "at_risk_rate": "at-risk rate",
    "rows": "rows",
    "has_history_rate": "history rate",
    "missing": "missing",
    "heatmap_title": "At-risk rate by module and presentation",
    "scatter_title": "Earlier module risk rate and this presentation's at-risk rate",
    "scatter_xlabel": "At-risk rate of earlier presentations",
    "scatter_ylabel": "At-risk rate of this presentation",
    "slot_title": "{module}",
    "slot_suptitle": "Mean score of the same slot across presentations",
    "slot_xlabel": "presentation",
    "slot_ylabel": "mean score",
    "unsubmitted_title": "Unsubmitted assessments and at-risk rate",
    "unsubmitted_xlabel": "unsubmitted assessments",
    "clicks_title": "Click bins and at-risk rate",
    "clicks_xlabel": "click bin",
    "score_title": "Mean-score bins and at-risk rate",
    "score_xlabel": "mean-score bin",
    "history_gap_title": "Score-versus-history bins and at-risk rate",
    "history_gap_xlabel": "score minus historical slot mean",
    "feature": "feature",
    "school": "school counterpart",
    "school_not": "grade",
    "school_absence": "attendance",
    "school_context": "course context",
}

LABELS_BY_LANG = {"tr": LABELS_TR, "en": LABELS_EN}


def _bin_label(interval):
    return f"({float(interval.left):.2f}, {float(interval.right):.2f}]"


def rate_by_bin(frame, column, quantiles, missing_label):
    if quantiles is None:
        labels = frame[column].astype("int64").astype(str)
        categories = [str(value) for value in sorted(frame[column].astype("int64").unique())]
    else:
        observed = frame[column].notna()
        labels = pd.Series(pd.NA, index=frame.index, dtype="object")
        categories = []
        if observed.any():
            cut = pd.qcut(
                frame.loc[observed, column].astype("float64"),
                quantiles,
                duplicates="drop",
            )
            categories = [_bin_label(item) for item in cut.cat.categories]
            labels.loc[observed] = cut.map(_bin_label).to_numpy()
        if (~observed).any():
            categories.append(missing_label)
            labels.loc[~observed] = missing_label
        labels = labels.astype(str)
    work = pd.DataFrame({"bin": labels.to_numpy(), "at_risk": frame["at_risk"].to_numpy()})
    counts = work.groupby("bin", sort=False).size()
    rates = work.groupby("bin", sort=False)["at_risk"].mean()
    table = pd.DataFrame({"bin": categories})
    table["n"] = table["bin"].map(counts).fillna(0).astype(int)
    table["at_risk_rate"] = table["bin"].map(rates).astype(float)
    return table


def print_rate_table(table):
    print(table.to_string(index=False, float_format="{:.6f}".format))


def read_feature_catalog(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(cells) != len(CATALOG_COLUMNS):
            raise ValueError(f"katalog satırı {len(CATALOG_COLUMNS)} hücre olmalı: {line}")
        if cells[0].startswith("-") or cells[0] == "sütun":
            continue
        rows.append(cells)
    return pd.DataFrame(rows, columns=CATALOG_COLUMNS)


# --- Veri (notebook hücre 1) --------------------------------------------------------------


def student_vle_shape():
    """studentVle satır ve sütun sayısı; load_tables dışında, aynı tür dönüşümüyle parça parça."""
    student_vle_rows = 0
    student_vle_cols = len(STUDENT_VLE_DTYPES)
    for chunk in iter_typed_csv(
        RAW_OULAD_DIR / STUDENT_VLE_NAME,
        STUDENT_VLE_DTYPES,
        DEFAULT_CHUNKSIZE,
    ):
        student_vle_rows += len(chunk)
        student_vle_cols = chunk.shape[1]
    return student_vle_rows, student_vle_cols


def table_shapes(tables, student_vle_rows, student_vle_cols):
    """[{table, rows, cols}]: TABLE_FILES sırasıyla, sonra studentVle."""
    shapes = []
    for name in TABLE_FILES:
        frame = tables[name]
        shapes.append({"table": name, "rows": len(frame), "cols": frame.shape[1]})
    shapes.append({"table": "studentVle", "rows": student_vle_rows, "cols": student_vle_cols})
    return shapes


def load_features(tables, cutoff=CUTOFF_DAY):
    daily = pd.read_parquet(PROCESSED_OULAD_DIR / DAILY_NAME)
    features = build_features(tables, daily, cutoff=cutoff)
    del daily
    return features


# --- Örneklem (notebook hücre 3) ----------------------------------------------------------


def sample_counts(tables, cutoff=CUTOFF_DAY):
    info = tables["studentInfo"]
    registration = tables["studentRegistration"]
    base = info.merge(
        registration.loc[:, KEYS + ["date_unregistration"]],
        on=KEYS,
        how="left",
    )
    removed = base["date_unregistration"].notna() & (base["date_unregistration"] < cutoff)
    removed = removed.fillna(False)
    return {
        "cutoff_day": cutoff,
        "rows_before": len(base),
        "rows_removed": int(removed.sum()),
        "rows_kept": int((~removed).sum()),
    }


def final_result_mapping(features, info):
    mapped = features.merge(info.loc[:, KEYS + ["final_result"]], on=KEYS, how="left")
    mapping = mapped.groupby("final_result", as_index=False).agg(
        n=("at_risk", "size"),
        at_risk_min=("at_risk", "min"),
        at_risk_max=("at_risk", "max"),
    )
    mapping = mapping.sort_values("final_result", kind="mergesort")
    return mapping


# --- Bölme (notebook hücre 4) -------------------------------------------------------------


def split_summary(features):
    split_table = features.groupby("split", as_index=False).agg(
        n_rows=("id_student", "size"),
        at_risk_rate=("at_risk", "mean"),
        has_history_rate=("has_history", "mean"),
    )
    split_table["split"] = pd.Categorical(split_table["split"], SPLIT_ORDER, ordered=True)
    split_table = split_table.sort_values("split").reset_index(drop=True)
    return split_table


# --- Ders bağlamı (notebook hücre 5, 6, 7) ------------------------------------------------


def risk_rate_pivot(features):
    risk_rate = (
        features.groupby(["code_module", "code_presentation"], as_index=False)["at_risk"]
        .mean()
        .pivot(index="code_module", columns="code_presentation", values="at_risk")
        .reindex(columns=list(PRESENTATION_ORDER))
        .sort_index()
    )
    return risk_rate


def hist_vs_current_points(features):
    points = features.groupby(["code_module", "code_presentation"], as_index=False).agg(
        n=("id_student", "size"),
        at_risk_rate=("at_risk", "mean"),
        hist_module_risk_rate=("hist_module_risk_rate", "first"),
    )
    points["code_module"] = points["code_module"].astype(str)
    points["code_presentation"] = points["code_presentation"].astype(str)
    points["pres_rank"] = points["code_presentation"].map(
        {name: index for index, name in enumerate(PRESENTATION_ORDER)}
    )
    points = points.sort_values(["code_module", "pres_rank"], kind="mergesort")
    return points


def slot_means_table(tables, features, cutoff=CUTOFF_DAY):
    window = tables["assessments"].loc[
        tables["assessments"]["assessment_type"].ne("Exam")
        & tables["assessments"]["date"].notna()
        & (tables["assessments"]["date"] <= cutoff),
        [
            "code_module",
            "code_presentation",
            "id_assessment",
            "assessment_type",
            "date",
            "weight",
        ],
    ].copy()
    window = window.sort_values(
        ["code_module", "code_presentation", "assessment_type", "date", "id_assessment"],
        kind="mergesort",
    )
    window["slot"] = (
        window.groupby(
            ["code_module", "code_presentation", "assessment_type"],
            sort=False,
        ).cumcount()
        + 1
    ).astype("int64")

    submissions = tables["studentAssessment"].loc[
        :,
        ["id_assessment", "id_student", "date_submitted", "score"],
    ].copy()
    submissions = submissions.loc[
        submissions["date_submitted"].notna() & (submissions["date_submitted"] <= cutoff)
    ]
    submissions = submissions.sort_values(
        ["id_assessment", "id_student", "date_submitted"],
        kind="mergesort",
    )
    submissions = submissions.drop_duplicates(["id_assessment", "id_student"], keep="last")
    scored = submissions.merge(
        window.loc[:, ["id_assessment", "code_module", "code_presentation", "assessment_type", "slot"]],
        on="id_assessment",
        how="inner",
    )
    scored = scored.merge(features.loc[:, KEYS], on=KEYS, how="inner")
    scored = scored.loc[scored["score"].notna()]
    slot_means = scored.groupby(
        ["code_module", "code_presentation", "assessment_type", "slot"],
        as_index=False,
        sort=False,
    ).agg(n=("score", "size"), mean_score=("score", "mean"))
    slot_means["code_module"] = slot_means["code_module"].astype(str)
    slot_means["code_presentation"] = slot_means["code_presentation"].astype(str)
    slot_means["assessment_type"] = slot_means["assessment_type"].astype(str)
    rank = {name: index for index, name in enumerate(PRESENTATION_ORDER)}
    slot_means["pres_rank"] = slot_means["code_presentation"].map(rank).astype(int)
    slot_means = slot_means.sort_values(
        ["code_module", "pres_rank", "assessment_type", "slot"],
        kind="mergesort",
    )
    slot_means["slot_label"] = (
        slot_means["assessment_type"] + " " + slot_means["slot"].astype(str)
    )
    return slot_means


def feature_modules(features):
    return sorted(features["code_module"].astype(str).unique())


def modules_without_scored_slot(modules, slot_means):
    return [module for module in modules if module not in set(slot_means["code_module"])]


# --- Erken sinyaller (notebook hücre 8-11) ------------------------------------------------


def train_rows(features):
    return features.loc[features["split"].eq("train")]


def signal_table(train, signal, missing_label):
    """Sinyalin dilim tablosu; dilim sayısı SIGNAL_QUANTILES'tan."""
    return rate_by_bin(train, signal, SIGNAL_QUANTILES[signal], missing_label)


# --- Veri notları (notebook hücre 12) -----------------------------------------------------


def ggg_cutoff_summary(features):
    ggg = features.loc[
        features["code_module"].eq("GGG") & features["code_presentation"].isin(GGG_PRESENTATIONS)
    ]
    ggg_summary = ggg.groupby("code_presentation", as_index=False).agg(
        n_rows=("id_student", "size"),
        n_expected_min=("n_expected", "min"),
        n_expected_max=("n_expected", "max"),
        score_mean_missing=("score_mean", lambda s: int(s.isna().sum())),
        vle_clicks_positive=("vle_clicks", lambda s: int((s > 0).sum())),
    )
    for column in ggg_summary.columns:
        if column != "code_presentation":
            ggg_summary[column] = ggg_summary[column].astype(int)
    return ggg_summary


def ggg_assessments(tables):
    return tables["assessments"].loc[
        tables["assessments"]["code_module"].eq("GGG")
        & tables["assessments"]["code_presentation"].isin(GGG_PRESENTATIONS)
    ]


def ggg_non_exam_in_window(ggg_assessment_rows, cutoff=CUTOFF_DAY):
    in_window = (
        ggg_assessment_rows["assessment_type"].ne("Exam")
        & ggg_assessment_rows["date"].notna()
        & (ggg_assessment_rows["date"] <= cutoff)
    )
    return int(in_window.sum())


def bbb_zero_weight_summary(tables, features, cutoff=CUTOFF_DAY):
    """BBB 2014J: kesim penceresindeki ödevler ve ağırlığı 0 olan TMA'nın etkisi.

    only_zero_weight_score: notlu tek teslimi ağırlığı 0 olan ödev(ler) olan öğrenci sayısı
    (WEEK_09 veri notu 2).
    """
    bbb_window = tables["assessments"].loc[
        tables["assessments"]["code_module"].eq("BBB")
        & tables["assessments"]["code_presentation"].eq("2014J")
        & tables["assessments"]["assessment_type"].ne("Exam")
        & tables["assessments"]["date"].notna()
        & (tables["assessments"]["date"] <= cutoff)
    ].copy()
    zero_weight = bbb_window.loc[bbb_window["weight"].eq(0)]

    bbb_rows = features.loc[
        features["code_module"].eq("BBB") & features["code_presentation"].eq("2014J")
    ].copy()
    zero_ids = set(zero_weight["id_assessment"].astype("int64"))
    window_ids = set(bbb_window["id_assessment"].astype("int64"))
    submitted = tables["studentAssessment"].loc[
        tables["studentAssessment"]["id_assessment"].isin(window_ids)
        & tables["studentAssessment"]["date_submitted"].notna()
        & (tables["studentAssessment"]["date_submitted"] <= cutoff)
        & tables["studentAssessment"]["score"].notna(),
        ["id_assessment", "id_student"],
    ].copy()
    submitted = submitted.loc[submitted["id_student"].isin(set(bbb_rows["id_student"].astype("int64")))]
    submitted["zero_weight"] = submitted["id_assessment"].astype("int64").isin(zero_ids)
    per_student = submitted.groupby("id_student", as_index=False).agg(
        n_scored=("id_assessment", "size"),
        n_zero=("zero_weight", "sum"),
    )
    per_student["only_zero"] = per_student["n_zero"].gt(0) & per_student["n_scored"].eq(per_student["n_zero"])
    only_zero_ids = set(per_student.loc[per_student["only_zero"], "id_student"].astype("int64"))
    only_zero_flag = bbb_rows["id_student"].astype("int64").isin(only_zero_ids)
    weighted_missing = bbb_rows["score_weighted_mean"].isna()
    return {
        "window": bbb_window,
        "zero_weight": zero_weight,
        "rows": len(bbb_rows),
        "weighted_missing": int(weighted_missing.sum()),
        "only_zero_weight_score": int(only_zero_flag.sum()),
        "only_zero_weight_and_weighted_missing": int((only_zero_flag & weighted_missing).sum()),
    }


def missing_by_column(features):
    missing = pd.DataFrame({"column": list(features.columns)})
    missing["n_missing"] = [int(features[column].isna().sum()) for column in missing["column"]]
    missing["missing_rate"] = missing["n_missing"] / len(features)
    return missing


# --- Okul sistemine köprü (notebook hücre 13) ---------------------------------------------


def sorted_feature_catalog(path=FEATURE_LIST_PATH):
    """feature_list.md kataloğu: okul karşılığı sırası (SCHOOL_ORDER), sonra sütun adı."""
    catalog = read_feature_catalog(path)
    unknown = sorted(set(catalog["school_tr"]) - set(SCHOOL_ORDER))
    if unknown:
        raise ValueError(unknown)
    catalog["school_order"] = catalog["school_tr"].map(SCHOOL_ORDER)
    catalog = catalog.sort_values(["school_order", "column"], kind="mergesort")
    return catalog


# --- Özet (notebook son hücre) ------------------------------------------------------------


def risk_extremes(risk_rate):
    """(en düşük, en yüksek) modül-sunum satırı; eşitlikte modül, sunum adı."""
    stacked = risk_rate.stack().rename("at_risk_rate").reset_index()
    stacked["code_module"] = stacked["code_module"].astype(str)
    stacked["code_presentation"] = stacked["code_presentation"].astype(str)
    low = stacked.sort_values(
        ["at_risk_rate", "code_module", "code_presentation"],
        kind="mergesort",
    ).iloc[0]
    high = stacked.sort_values(
        ["at_risk_rate", "code_module", "code_presentation"],
        ascending=[False, True, True],
        kind="mergesort",
    ).iloc[0]
    return low, high
