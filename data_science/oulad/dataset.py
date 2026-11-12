"""Kesim gününe kadar olan özellikleri, ders geçmişini ve sunum bölmesini (train/test) hesaplar."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from data_science.oulad import PROCESSED_OULAD_DIR
from data_science.oulad.load import load_tables
from data_science.oulad.vle import DAILY_NAME

CUTOFF_DAY = 60
FEATURES_NAME = "features_cutoff60.parquet"
FEATURE_LIST_PATH = Path(__file__).resolve().parent / "feature_list.md"

PRESENTATION_ORDER = ("2013B", "2013J", "2014B", "2014J")
PRESENTATION_RANK = {name: rank for rank, name in enumerate(PRESENTATION_ORDER)}
SPLIT_BY_PRESENTATION = {
    "2013B": "history",
    "2013J": "train",
    "2014B": "train",
    "2014J": "test",
}

STUDENT_KEY = ("code_module", "code_presentation", "id_student")
AT_RISK_POSITIVE = frozenset({"Fail", "Withdrawn"})
AT_RISK_NEGATIVE = frozenset({"Pass", "Distinction"})

HISTORY_VALUE_COLUMNS = (
    "hist_slot_mean",
    "hist_slot_submit_rate",
    "score_vs_hist",
    "hist_module_risk_rate",
)

# tanım şablonunda {cutoff} kesim günüdür. kapsam.
FEATURE_DOCS: dict[str, tuple[str, str]] = {
    "code_module": ("Modül kodu.", "genel"),
    "code_presentation": ("Sunum kodu.", "genel"),
    "id_student": ("Öğrenci kimliği.", "genel"),
    "at_risk": (
        "final_result Fail veya Withdrawn ise 1, Pass veya Distinction ise 0.",
        "genel",
    ),
    "split": (
        "2013B history, 2013J ve 2014B train, 2014J test.",
        "genel",
    ),
    "date_registration": ("Kayıt günü (modül başlangıcına göre).", "genel"),
    "n_expected": (
        "Tarihi gün <= {cutoff} olan ve türü Exam olmayan ödev sayısı.",
        "genel",
    ),
    "n_submitted": (
        "Bu ödevlerden date_submitted gün <= {cutoff} olan teslim sayısı.",
        "genel",
    ),
    "n_unsubmitted": ("n_expected eksi n_submitted.", "genel"),
    "score_mean": (
        "Kesim penceresindeki teslimlerin ağırlıksız ortalama notu. Not yoksa boş.",
        "genel",
    ),
    "score_weighted_mean": (
        "Aynı teslimlerin ağırlıklı ortalama notu. Ağırlık toplamı 0 ise boş.",
        "genel",
    ),
    "delay_mean": (
        "Aynı teslimlerde ortalama (date_submitted - date).",
        "genel",
    ),
    "n_banked": (
        "Kesim penceresindeki teslimlerde is_banked = 1 satır sayısı. Bu satırlar silinmez.",
        "genel",
    ),
    "vle_clicks": (
        "student_vle_daily içinde gün <= {cutoff} toplam sum_click.",
        "genel",
    ),
    "vle_active_days": (
        "Gün <= {cutoff} olan farklı aktivite günü sayısı.",
        "genel",
    ),
    "vle_days_to_cutoff": (
        "Kesim günü eksi son aktivite günü. Aktivite yoksa boş.",
        "genel",
    ),
    "has_history": (
        "Aynı code_module içinde sıraca önceki sunum varsa 1, yoksa 0.",
        "geçmiş",
    ),
    "hist_slot_mean": (
        "Öğrencinin kesimdeki ödev yuvalarının geçmiş ortalama notunun ortalaması. "
        "Yuva anahtarı (code_module, assessment_type, tür içinde tarihe göre sıra; eşit tarihte id_assessment). "
        "Yalnızca aynı modülün önceki sunumları. Eşleşen yuva yoksa boş.",
        "geçmiş",
    ),
    "hist_slot_submit_rate": (
        "Aynı yuvaların geçmiş teslim oranının ortalaması. Eşleşen yuva yoksa boş.",
        "geçmiş",
    ),
    "score_vs_hist": (
        "Öğrenci notu eksi yuvanın geçmiş ortalama notu; notu ve geçmişi olan "
        "yuvaların öğrenci bazında ortalaması. Doldurulmaz.",
        "geçmiş",
    ),
    "hist_module_risk_rate": (
        "Önceki sunumların, aynı örneklem tanımıyla at_risk oranı. "
        "Önceki örneklem yoksa boş.",
        "geçmiş",
    ),
}

IDENTIFIER_COLUMNS = ("code_module", "code_presentation", "id_student", "split")
TARGET_COLUMN = "at_risk"

SCHOOL_IDENTIFIER = ("Tanımlayıcı; modele girmez", "Identifier; not a model input")
SCHOOL_TARGET = ("Hedef; özellik değil", "Target; not a feature")
SCHOOL_GRADE = ("Not ortalaması (var)", "Grade average (available)")
SCHOOL_SUBMISSION = (
    "Ödev teslim kaydı (okulda yok)",
    "Assignment submission record (not in the school data)",
)
SCHOOL_ABSENCE = ("Mazeretsiz devamsızlık (yaklaşık)", "Unexcused absence (approximate)")
SCHOOL_NONE = ("Okulda karşılığı yok", "No school counterpart")
SCHOOL_HISTORY_GRADES = (
    "Geçmiş dönem notları (okulda henüz yok)",
    "Past-term grades (not yet in the school data)",
)
SCHOOL_HISTORY_OUTCOMES = (
    "Geçmiş dönem sonuçları (okulda yok)",
    "Past-term outcomes (not in the school data)",
)

# sütun -> (okul karşılığı TR, EN). vle_click_* için önek kuralı school_counterpart içindedir.
SCHOOL_COUNTERPART: dict[str, tuple[str, str]] = {
    **{column: SCHOOL_IDENTIFIER for column in IDENTIFIER_COLUMNS},
    TARGET_COLUMN: SCHOOL_TARGET,
    "score_mean": SCHOOL_GRADE,
    "score_weighted_mean": SCHOOL_GRADE,
    "n_expected": SCHOOL_SUBMISSION,
    "n_submitted": SCHOOL_SUBMISSION,
    "n_unsubmitted": SCHOOL_SUBMISSION,
    "n_banked": SCHOOL_SUBMISSION,
    "delay_mean": SCHOOL_SUBMISSION,
    "vle_clicks": SCHOOL_ABSENCE,
    "vle_active_days": SCHOOL_ABSENCE,
    "vle_days_to_cutoff": SCHOOL_ABSENCE,
    "date_registration": SCHOOL_NONE,
    "has_history": SCHOOL_HISTORY_GRADES,
    "hist_slot_mean": SCHOOL_HISTORY_GRADES,
    "hist_slot_submit_rate": SCHOOL_HISTORY_GRADES,
    "score_vs_hist": SCHOOL_HISTORY_GRADES,
    "hist_module_risk_rate": SCHOOL_HISTORY_OUTCOMES,
}


def school_counterpart(column: str) -> tuple[str, str]:
    if column.startswith("vle_click_"):
        return SCHOOL_ABSENCE
    if column not in SCHOOL_COUNTERPART:
        raise ValueError(f"okul karşılığı tanımsız: {column}")
    return SCHOOL_COUNTERPART[column]


def feature_group(column: str, scope: str) -> str:
    """GENERAL sütunları için ek.GROUP_OF değeri; geçmiş sütunları GEÇMİŞ; tanımlayıcı ve hedef boş."""
    # ek.py bu modülü içe aktarır; döngüyü önlemek için çağrı anında içe aktarılır.
    from data_science.oulad.ek import GROUP_OF

    if column in IDENTIFIER_COLUMNS or column == TARGET_COLUMN:
        return ""
    if scope == "geçmiş":
        return "GEÇMİŞ"
    if column.startswith("vle_click_"):
        # Ön kayıt: vle_* → ETKİNLİK. Dinamik activity_type sütunları ve
        # "vle_click_<activity_type>" yer tutucusu önek üzerinden vle_clicks ile aynı grupta.
        return GROUP_OF["vle_clicks"]
    if column not in GROUP_OF:
        raise ValueError(f"grupsuz sütun: {column}")
    return GROUP_OF[column]


def _require(frame: pd.DataFrame, columns: tuple[str, ...], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} eksik sutunlar: {missing}")


def _string(series: pd.Series) -> pd.Series:
    return series.astype("string")


def _int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("float64")


def _check_presentations(series: pd.Series) -> None:
    found = {str(value) for value in series.dropna().unique()}
    unknown = sorted(found - set(PRESENTATION_ORDER))
    if unknown:
        raise ValueError(f"bilinmeyen code_presentation: {unknown}")


def prepare_sample(info: pd.DataFrame, registration: pd.DataFrame, cutoff: int) -> pd.DataFrame:
    """studentInfo ve studentRegistration tablolarından kesim gününe göre öğrenci örneğini hazırlar."""
    return _prepare_sample(info, registration, cutoff)


def _prepare_sample(info: pd.DataFrame, registration: pd.DataFrame, cutoff: int) -> pd.DataFrame:
    _require(
        info,
        ("code_module", "code_presentation", "id_student", "final_result"),
        "studentInfo",
    )
    _require(
        registration,
        ("code_module", "code_presentation", "id_student", "date_registration", "date_unregistration"),
        "studentRegistration",
    )
    students = info.loc[:, ["code_module", "code_presentation", "id_student", "final_result"]].copy()
    students["code_module"] = _string(students["code_module"])
    students["code_presentation"] = _string(students["code_presentation"])
    students["id_student"] = _int(students["id_student"]).astype("int64")
    students["final_result"] = _string(students["final_result"])
    _check_presentations(students["code_presentation"])
    duplicated = students.duplicated(list(STUDENT_KEY))
    if duplicated.any():
        raise ValueError("studentInfo anahtari tekil degil")

    registered = registration.loc[
        :,
        [
            "code_module",
            "code_presentation",
            "id_student",
            "date_registration",
            "date_unregistration",
        ],
    ].copy()
    registered["code_module"] = _string(registered["code_module"])
    registered["code_presentation"] = _string(registered["code_presentation"])
    registered["id_student"] = _int(registered["id_student"]).astype("int64")
    registered["date_registration"] = _int(registered["date_registration"])
    registered["date_unregistration"] = _int(registered["date_unregistration"])

    base = students.merge(registered, on=list(STUDENT_KEY), how="left")
    early_exit = base["date_unregistration"].notna() & (base["date_unregistration"] < cutoff)
    sample = base.loc[~early_exit.fillna(False)].copy()

    positive = sample["final_result"].isin(AT_RISK_POSITIVE)
    negative = sample["final_result"].isin(AT_RISK_NEGATIVE)
    if (~(positive | negative)).any():
        raise ValueError("bilinmeyen final_result")
    sample["at_risk"] = positive.astype("int64")
    sample["split"] = _string(sample["code_presentation"].map(SPLIT_BY_PRESENTATION))
    sample["pres_rank"] = sample["code_presentation"].map(PRESENTATION_RANK).astype("int64")
    sample = sample.merge(_has_history(students), on=["code_module", "code_presentation"], how="left")
    sample["has_history"] = sample["has_history"].fillna(0).astype("int64")
    keep = [
        "code_module",
        "code_presentation",
        "id_student",
        "date_registration",
        "at_risk",
        "split",
        "pres_rank",
        "has_history",
    ]
    return sample.loc[:, keep].reset_index(drop=True)


def _has_history(students: pd.DataFrame) -> pd.DataFrame:
    presentations = students.loc[:, ["code_module", "code_presentation"]].drop_duplicates()
    presentations["pres_rank"] = presentations["code_presentation"].map(PRESENTATION_RANK).astype("int64")
    earlier = presentations.merge(presentations, on="code_module", suffixes=("", "_earlier"))
    earlier = earlier.loc[earlier["pres_rank_earlier"] < earlier["pres_rank"]]
    flagged = earlier.loc[:, ["code_module", "code_presentation"]].drop_duplicates()
    flagged["has_history"] = 1
    return flagged


def _prepare_assessments(assessments: pd.DataFrame, cutoff: int) -> pd.DataFrame:
    _require(
        assessments,
        (
            "code_module",
            "code_presentation",
            "id_assessment",
            "assessment_type",
            "date",
            "weight",
        ),
        "assessments",
    )
    frame = assessments.loc[
        :,
        [
            "code_module",
            "code_presentation",
            "id_assessment",
            "assessment_type",
            "date",
            "weight",
        ],
    ].copy()
    frame["code_module"] = _string(frame["code_module"])
    frame["code_presentation"] = _string(frame["code_presentation"])
    frame["id_assessment"] = _int(frame["id_assessment"])
    frame["assessment_type"] = _string(frame["assessment_type"])
    frame["date"] = _int(frame["date"])
    frame["weight"] = _float(frame["weight"])
    _check_presentations(frame["code_presentation"])
    keep = frame["assessment_type"].notna() & (frame["assessment_type"] != "Exam")
    keep = keep & frame["date"].notna() & (frame["date"] <= cutoff) & frame["id_assessment"].notna()
    frame = frame.loc[keep].copy()
    frame["id_assessment"] = frame["id_assessment"].astype("int64")
    frame = frame.sort_values(
        ["code_module", "code_presentation", "assessment_type", "date", "id_assessment"],
        kind="mergesort",
    )
    frame = frame.drop_duplicates("id_assessment", keep="first")
    frame["slot"] = (
        frame.groupby(
            ["code_module", "code_presentation", "assessment_type"],
            sort=False,
        ).cumcount()
        + 1
    ).astype("int64")
    return frame.reset_index(drop=True)


def _prepare_submissions(
    student_assessment: pd.DataFrame,
    assessments: pd.DataFrame,
    sample: pd.DataFrame,
    cutoff: int,
) -> pd.DataFrame:
    _require(
        student_assessment,
        ("id_assessment", "id_student", "date_submitted", "is_banked", "score"),
        "studentAssessment",
    )
    columns = ["id_assessment", "id_student", "date_submitted", "is_banked", "score"]
    if student_assessment.empty or assessments.empty or sample.empty:
        return pd.DataFrame(columns=columns)
    frame = student_assessment.loc[:, columns].copy()
    frame["id_assessment"] = _int(frame["id_assessment"])
    frame["id_student"] = _int(frame["id_student"])
    frame["date_submitted"] = _int(frame["date_submitted"])
    frame["is_banked"] = _int(frame["is_banked"])
    frame["score"] = _float(frame["score"])
    frame = frame.loc[
        frame["id_assessment"].notna()
        & frame["id_student"].notna()
        & frame["date_submitted"].notna()
        & (frame["date_submitted"] <= cutoff)
    ].copy()
    frame["id_assessment"] = frame["id_assessment"].astype("int64")
    frame["id_student"] = frame["id_student"].astype("int64")
    frame = frame.merge(
        assessments.loc[:, ["id_assessment", "code_module", "code_presentation"]],
        on="id_assessment",
        how="inner",
    )
    frame = frame.merge(
        sample.loc[:, list(STUDENT_KEY)],
        on=list(STUDENT_KEY),
        how="inner",
    )
    frame = frame.sort_values(
        ["id_assessment", "id_student", "date_submitted"],
        kind="mergesort",
    )
    frame = frame.drop_duplicates(["id_assessment", "id_student"], keep="last")
    return frame.loc[:, columns].reset_index(drop=True)


def _cohort(sample: pd.DataFrame) -> pd.DataFrame:
    if sample.empty:
        return pd.DataFrame(
            columns=["code_module", "code_presentation", "pres_rank", "n_students", "n_at_risk"]
        )
    grouped = sample.groupby(
        ["code_module", "code_presentation", "pres_rank"],
        as_index=False,
        sort=False,
    ).agg(n_students=("id_student", "size"), n_at_risk=("at_risk", "sum"))
    grouped["n_students"] = grouped["n_students"].astype("int64")
    grouped["n_at_risk"] = grouped["n_at_risk"].astype("int64")
    return grouped


def _slot_outcomes(
    sample: pd.DataFrame,
    assessments: pd.DataFrame,
    submissions: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "code_module",
        "code_presentation",
        "pres_rank",
        "assessment_type",
        "slot",
        "expected_n",
        "n_submitted",
        "score_sum",
        "score_n",
    ]
    if assessments.empty or sample.empty:
        return pd.DataFrame(columns=columns)
    cohort = _cohort(sample)
    slots = assessments.loc[
        :,
        ["code_module", "code_presentation", "assessment_type", "slot"],
    ].drop_duplicates()
    slots = slots.merge(cohort, on=["code_module", "code_presentation"], how="inner")
    slots = slots.rename(columns={"n_students": "expected_n"})
    if submissions.empty:
        submitted = pd.DataFrame(columns=["code_module", "code_presentation", "assessment_type", "slot", "id_student", "score"])
    else:
        submitted = submissions.merge(
            assessments.loc[:, ["id_assessment", "code_module", "code_presentation", "assessment_type", "slot"]],
            on="id_assessment",
            how="inner",
        )
    if submitted.empty:
        counts = pd.DataFrame(columns=["code_module", "code_presentation", "assessment_type", "slot", "n_submitted", "score_sum", "score_n"])
    else:
        scored = submitted.loc[submitted["score"].notna()]
        counts = submitted.groupby(
            ["code_module", "code_presentation", "assessment_type", "slot"],
            as_index=False,
            sort=False,
        ).agg(n_submitted=("id_student", "nunique"))
        if scored.empty:
            counts["score_sum"] = 0.0
            counts["score_n"] = 0
        else:
            score_part = scored.groupby(
                ["code_module", "code_presentation", "assessment_type", "slot"],
                as_index=False,
                sort=False,
            ).agg(score_sum=("score", "sum"), score_n=("score", "size"))
            counts = counts.merge(
                score_part,
                on=["code_module", "code_presentation", "assessment_type", "slot"],
                how="left",
            )
    slots = slots.merge(
        counts,
        on=["code_module", "code_presentation", "assessment_type", "slot"],
        how="left",
    )
    slots["n_submitted"] = pd.to_numeric(slots["n_submitted"], errors="coerce").fillna(0).astype("int64")
    slots["score_n"] = pd.to_numeric(slots["score_n"], errors="coerce").fillna(0).astype("int64")
    slots["score_sum"] = pd.to_numeric(slots["score_sum"], errors="coerce").fillna(0.0).astype("float64")
    slots["expected_n"] = slots["expected_n"].astype("int64")
    return slots.loc[:, columns].reset_index(drop=True)


def _history_by_slot(outcomes: pd.DataFrame, presentations: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "code_module",
        "code_presentation",
        "assessment_type",
        "slot",
        "hist_mean",
        "hist_rate",
    ]
    if outcomes.empty or presentations.empty:
        return pd.DataFrame(columns=columns)
    sources = outcomes.rename(
        columns={"code_presentation": "source_presentation", "pres_rank": "source_rank"}
    )
    paired = presentations.merge(sources, on="code_module", how="inner")
    paired = paired.loc[paired["source_rank"] < paired["pres_rank"]]
    if paired.empty:
        return pd.DataFrame(columns=columns)
    grouped = paired.groupby(
        ["code_module", "code_presentation", "assessment_type", "slot"],
        as_index=False,
        sort=False,
    ).agg(
        expected_n=("expected_n", "sum"),
        n_submitted=("n_submitted", "sum"),
        score_sum=("score_sum", "sum"),
        score_n=("score_n", "sum"),
    )
    grouped["hist_mean"] = pd.Series(pd.NA, index=grouped.index, dtype="Float64")
    grouped["hist_rate"] = pd.Series(pd.NA, index=grouped.index, dtype="Float64")
    scored = grouped["score_n"] > 0
    grouped.loc[scored, "hist_mean"] = (
        grouped.loc[scored, "score_sum"] / grouped.loc[scored, "score_n"]
    ).astype("float64")
    expected = grouped["expected_n"] > 0
    grouped.loc[expected, "hist_rate"] = (
        grouped.loc[expected, "n_submitted"] / grouped.loc[expected, "expected_n"]
    ).astype("float64")
    return grouped.loc[:, columns]


def _history_risk(sample: pd.DataFrame, presentations: pd.DataFrame) -> pd.DataFrame:
    columns = ["code_module", "code_presentation", "hist_module_risk_rate"]
    cohort = _cohort(sample)
    if cohort.empty or presentations.empty:
        return pd.DataFrame(columns=columns)
    sources = cohort.rename(
        columns={"code_presentation": "source_presentation", "pres_rank": "source_rank"}
    )
    paired = presentations.merge(sources, on="code_module", how="inner")
    paired = paired.loc[paired["source_rank"] < paired["pres_rank"]]
    if paired.empty:
        return pd.DataFrame(columns=columns)
    grouped = paired.groupby(["code_module", "code_presentation"], as_index=False, sort=False).agg(
        n_students=("n_students", "sum"),
        n_at_risk=("n_at_risk", "sum"),
    )
    grouped = grouped.loc[grouped["n_students"] > 0].copy()
    grouped["hist_module_risk_rate"] = grouped["n_at_risk"] / grouped["n_students"]
    return grouped.loc[:, columns]


def _assignment_features(
    sample: pd.DataFrame,
    assessments: pd.DataFrame,
    submissions: pd.DataFrame,
    slot_history: pd.DataFrame,
    risk_history: pd.DataFrame,
) -> pd.DataFrame:
    grid = sample.loc[:, list(STUDENT_KEY)].merge(
        assessments.loc[
            :,
            [
                "code_module",
                "code_presentation",
                "id_assessment",
                "assessment_type",
                "date",
                "weight",
                "slot",
            ],
        ],
        on=["code_module", "code_presentation"],
        how="left",
    )
    if submissions.empty:
        grid["date_submitted"] = pd.Series(pd.NA, index=grid.index, dtype="Int64")
        grid["is_banked"] = pd.Series(pd.NA, index=grid.index, dtype="Int64")
        grid["score"] = pd.Series(pd.NA, index=grid.index, dtype="Float64")
    else:
        grid = grid.merge(
            submissions,
            on=["id_assessment", "id_student"],
            how="left",
        )
    if slot_history.empty:
        grid["hist_mean"] = pd.Series(pd.NA, index=grid.index, dtype="Float64")
        grid["hist_rate"] = pd.Series(pd.NA, index=grid.index, dtype="Float64")
    else:
        grid = grid.merge(
            slot_history,
            on=["code_module", "code_presentation", "assessment_type", "slot"],
            how="left",
        )
    usable = grid.loc[grid["id_assessment"].notna()].copy()
    base = sample.loc[:, list(STUDENT_KEY)].copy()
    if usable.empty:
        base["n_expected"] = 0
        base["n_submitted"] = 0
        base["n_unsubmitted"] = 0
        base["score_mean"] = pd.Series(pd.NA, index=base.index, dtype="Float64")
        base["score_weighted_mean"] = pd.Series(pd.NA, index=base.index, dtype="Float64")
        base["delay_mean"] = pd.Series(pd.NA, index=base.index, dtype="Float64")
        base["n_banked"] = 0
        for column in ("hist_slot_mean", "hist_slot_submit_rate", "score_vs_hist"):
            base[column] = pd.Series(pd.NA, index=base.index, dtype="Float64")
    else:
        usable["submitted"] = usable["date_submitted"].notna()
        usable["score_in"] = usable["score"].where(usable["submitted"])
        usable["delay"] = pd.Series(pd.NA, index=usable.index, dtype="Float64")
        submitted = usable["submitted"]
        usable.loc[submitted, "delay"] = (
            usable.loc[submitted, "date_submitted"].astype("float64")
            - usable.loc[submitted, "date"].astype("float64")
        )
        banked = submitted & usable["is_banked"].fillna(0).astype("int64").eq(1)
        usable["banked_hit"] = banked.astype("int64")
        usable["score_gap"] = pd.Series(pd.NA, index=usable.index, dtype="Float64")
        comparable = submitted & usable["score"].notna() & usable["hist_mean"].notna()
        usable.loc[comparable, "score_gap"] = (
            usable.loc[comparable, "score"].astype("float64")
            - usable.loc[comparable, "hist_mean"].astype("float64")
        )
        counts = usable.groupby(list(STUDENT_KEY), as_index=False, sort=False).agg(
            n_expected=("id_assessment", "size"),
            n_submitted=("submitted", "sum"),
            score_mean=("score_in", "mean"),
            delay_mean=("delay", "mean"),
            n_banked=("banked_hit", "sum"),
            hist_slot_mean=("hist_mean", "mean"),
            hist_slot_submit_rate=("hist_rate", "mean"),
            score_vs_hist=("score_gap", "mean"),
        )
        weighted_rows = usable.loc[submitted & usable["score"].notna() & usable["weight"].notna()].copy()
        if weighted_rows.empty:
            weighted = pd.DataFrame(columns=list(STUDENT_KEY) + ["score_weighted_mean"])
        else:
            weighted_rows["weighted_score"] = (
                weighted_rows["score"].astype("float64") * weighted_rows["weight"].astype("float64")
            )
            weighted = weighted_rows.groupby(list(STUDENT_KEY), as_index=False, sort=False).agg(
                weighted_score=("weighted_score", "sum"),
                weight_sum=("weight", "sum"),
            )
            weighted["score_weighted_mean"] = pd.Series(pd.NA, index=weighted.index, dtype="Float64")
            positive = weighted["weight_sum"] > 0
            weighted.loc[positive, "score_weighted_mean"] = (
                weighted.loc[positive, "weighted_score"] / weighted.loc[positive, "weight_sum"]
            )
            weighted = weighted.loc[:, list(STUDENT_KEY) + ["score_weighted_mean"]]
        counts = counts.merge(weighted, on=list(STUDENT_KEY), how="left")
        base = base.merge(counts, on=list(STUDENT_KEY), how="left")
        for column in ("n_expected", "n_submitted", "n_banked"):
            base[column] = base[column].fillna(0).astype("int64")
        base["n_unsubmitted"] = (base["n_expected"] - base["n_submitted"]).astype("int64")
    base = base.merge(risk_history, on=["code_module", "code_presentation"], how="left")
    if "hist_module_risk_rate" not in base.columns:
        base["hist_module_risk_rate"] = pd.Series(pd.NA, index=base.index, dtype="Float64")
    return base


def _activity_column(activity_type: str) -> str:
    cleaned = "".join(char if char.isalnum() or char == "_" else "_" for char in activity_type)
    return f"vle_click_{cleaned}"


def _top_activity_types(daily: pd.DataFrame, cutoff: int) -> list[str]:
    if daily.empty:
        return []
    window = daily.loc[daily["date"].notna() & (daily["date"] <= cutoff) & daily["activity_type"].notna()]
    if window.empty:
        return []
    ranked = window.copy()
    ranked["activity_type"] = _string(ranked["activity_type"])
    ranked["n_rows"] = _float(ranked["n_rows"]).fillna(0)
    ranked["sum_click"] = _float(ranked["sum_click"]).fillna(0)
    totals = ranked.groupby("activity_type", as_index=False, sort=False).agg(
        n_rows=("n_rows", "sum"),
        sum_click=("sum_click", "sum"),
    )
    totals["activity_name"] = totals["activity_type"].astype(str)
    totals = totals.sort_values(
        ["n_rows", "sum_click", "activity_name"],
        ascending=[False, False, True],
        kind="mergesort",
    )
    return totals["activity_name"].head(5).tolist()


def _vle_features(
    daily: pd.DataFrame,
    sample: pd.DataFrame,
    cutoff: int,
) -> tuple[pd.DataFrame, list[str]]:
    _require(
        daily,
        ("code_module", "code_presentation", "id_student", "date", "activity_type", "sum_click", "n_rows"),
        "student_vle_daily",
    )
    top_types = _top_activity_types(daily, cutoff)
    type_columns = [_activity_column(name) for name in top_types]
    frame = sample.loc[:, list(STUDENT_KEY)].copy()
    if daily.empty:
        frame["vle_clicks"] = 0
        frame["vle_active_days"] = 0
        frame["vle_days_to_cutoff"] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
        for column in type_columns:
            frame[column] = 0
        return frame, type_columns

    window = daily.copy()
    window["code_module"] = _string(window["code_module"])
    window["code_presentation"] = _string(window["code_presentation"])
    window["id_student"] = _int(window["id_student"])
    window["date"] = _int(window["date"])
    window["activity_type"] = _string(window["activity_type"])
    window["sum_click"] = _float(window["sum_click"])
    window = window.loc[
        window["code_module"].notna()
        & window["code_presentation"].notna()
        & window["id_student"].notna()
        & window["date"].notna()
        & (window["date"] <= cutoff)
    ].copy()
    window["id_student"] = window["id_student"].astype("int64")
    window["sum_click"] = window["sum_click"].fillna(0)
    if window.empty:
        totals = pd.DataFrame(columns=list(STUDENT_KEY) + ["vle_clicks", "vle_active_days", "vle_days_to_cutoff"])
    else:
        totals = window.groupby(list(STUDENT_KEY), as_index=False, sort=False).agg(
            vle_clicks=("sum_click", "sum"),
            vle_active_days=("date", "nunique"),
            last_date=("date", "max"),
        )
        totals["vle_days_to_cutoff"] = (cutoff - totals["last_date"].astype("int64")).astype("Int64")
        totals = totals.drop(columns="last_date")
    frame = frame.merge(totals, on=list(STUDENT_KEY), how="left")
    frame["vle_clicks"] = frame["vle_clicks"].fillna(0).round().astype("int64")
    frame["vle_active_days"] = frame["vle_active_days"].fillna(0).astype("int64")
    frame["vle_days_to_cutoff"] = frame["vle_days_to_cutoff"].astype("Int64")

    for column in type_columns:
        frame[column] = 0
    if top_types and not window.empty:
        named = window.loc[window["activity_type"].notna()].copy()
        named["activity_name"] = named["activity_type"].astype(str)
        named = named.loc[named["activity_name"].isin(top_types)]
        if not named.empty:
            named["column"] = named["activity_name"].map(_activity_column)
            wide = named.groupby(list(STUDENT_KEY) + ["column"], as_index=False, sort=False).agg(
                sum_click=("sum_click", "sum")
            )
            wide = wide.pivot_table(
                index=list(STUDENT_KEY),
                columns="column",
                values="sum_click",
                aggfunc="sum",
                fill_value=0,
            ).reset_index()
            wide.columns.name = None
            value_columns = [column for column in type_columns if column in wide.columns]
            frame = frame.drop(columns=value_columns).merge(
                wide.loc[:, list(STUDENT_KEY) + value_columns],
                on=list(STUDENT_KEY),
                how="left",
            )
            for column in type_columns:
                if column not in frame.columns:
                    frame[column] = 0
                frame[column] = frame[column].fillna(0).round().astype("int64")
    return frame, type_columns


def _presentations_of(sample: pd.DataFrame) -> pd.DataFrame:
    if sample.empty:
        return pd.DataFrame(columns=["code_module", "code_presentation", "pres_rank"])
    return sample.loc[:, ["code_module", "code_presentation", "pres_rank"]].drop_duplicates()


def build_features(
    tables: dict[str, pd.DataFrame],
    daily: pd.DataFrame,
    cutoff: int = CUTOFF_DAY,
) -> pd.DataFrame:
    """Orneklem, kesim ozellikleri, onceki sunum gecmisi ve split.

    date_unregistration < cutoff olan satirlar yok. Gecmis yalnizca ayni
    modulun daha onceki sunumlarindan gelir; bos gecmis 0 ile doldurulmaz.
    """
    sample = _prepare_sample(tables["studentInfo"], tables["studentRegistration"], cutoff)
    assessments = _prepare_assessments(tables["assessments"], cutoff)
    submissions = _prepare_submissions(
        tables["studentAssessment"],
        assessments,
        sample,
        cutoff,
    )
    presentations = _presentations_of(sample)
    outcomes = _slot_outcomes(sample, assessments, submissions)
    slot_history = _history_by_slot(outcomes, presentations)
    risk_history = _history_risk(sample, presentations)
    assigned = _assignment_features(sample, assessments, submissions, slot_history, risk_history)
    clicks, type_columns = _vle_features(daily, sample, cutoff)

    frame = sample.merge(assigned, on=list(STUDENT_KEY), how="left")
    frame = frame.merge(clicks, on=list(STUDENT_KEY), how="left")
    for column in ("n_expected", "n_submitted", "n_unsubmitted", "n_banked", "vle_clicks", "vle_active_days"):
        frame[column] = frame[column].fillna(0).astype("int64")
    for column in type_columns:
        frame[column] = frame[column].fillna(0).astype("int64")
    no_history = frame["has_history"].eq(0)
    for column in HISTORY_VALUE_COLUMNS:
        frame.loc[no_history, column] = pd.NA

    ordered = [
        "code_module",
        "code_presentation",
        "id_student",
        "at_risk",
        "split",
        "date_registration",
        "n_expected",
        "n_submitted",
        "n_unsubmitted",
        "score_mean",
        "score_weighted_mean",
        "delay_mean",
        "n_banked",
        "vle_clicks",
        "vle_active_days",
        "vle_days_to_cutoff",
        *type_columns,
        "has_history",
        *HISTORY_VALUE_COLUMNS,
    ]
    missing = [column for column in ordered if column not in frame.columns]
    if missing:
        raise ValueError(f"eksik ozellik: {missing}")
    frame = frame.loc[:, ordered]
    frame = frame.sort_values(
        ["code_module", "code_presentation", "id_student"],
        kind="mergesort",
    ).reset_index(drop=True)
    frame["code_module"] = _string(frame["code_module"])
    frame["code_presentation"] = _string(frame["code_presentation"])
    frame["split"] = _string(frame["split"])
    frame["date_registration"] = _int(frame["date_registration"])
    frame["vle_days_to_cutoff"] = _int(frame["vle_days_to_cutoff"])
    for column in (
        "score_mean",
        "score_weighted_mean",
        "delay_mean",
        *HISTORY_VALUE_COLUMNS,
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Float64")
    return frame


def _vle_doc(column: str, cutoff: int) -> tuple[str, str]:
    activity = column.removeprefix("vle_click_")
    subject = "seçilen activity_type" if activity.startswith("<") else f"activity_type={activity}"
    text = (
        f"Gün <= {cutoff} için {subject} tıklama toplamı. "
        "Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır "
        "(sıra: n_rows, eşitlikte sum_click, sonra ad)."
    )
    return text, "genel"


def render_feature_list(columns: list[str], cutoff: int = CUTOFF_DAY) -> str:
    lines = [
        f"# Kesim günü {cutoff} özellik listesi",
        "",
        "Satır birimi (code_module, code_presentation, id_student). "
        f"date_unregistration < {cutoff} örneklemde yoktur. "
        "Sosyo-demografik sütunlar, num_of_prev_attempts ve studied_credits yoktur.",
        "",
        "| sütun | tanım | kapsam | okul karşılığı | school counterpart | grup |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    def row(column: str, definition: str, scope: str) -> str:
        school_tr, school_en = school_counterpart(column)
        group = feature_group(column, scope)
        return f"| {column} | {definition} | {scope} | {school_tr} | {school_en} | {group} |"

    seen: set[str] = set()
    has_activity_column = any(column.startswith("vle_click_") for column in columns)
    for column in columns:
        if column in seen:
            continue
        seen.add(column)
        if column.startswith("vle_click_"):
            definition, scope = _vle_doc(column, cutoff)
        elif column in FEATURE_DOCS:
            template, scope = FEATURE_DOCS[column]
            definition = template.format(cutoff=cutoff)
        else:
            raise ValueError(f"tanimsiz sutun: {column}")
        lines.append(row(column, definition, scope))
        if column == "vle_days_to_cutoff" and not has_activity_column:
            definition, scope = _vle_doc("vle_click_<activity_type>", cutoff)
            lines.append(row("vle_click_<activity_type>", definition, scope))
    lines.append("")
    return "\n".join(lines)


def write_features(
    frame: pd.DataFrame,
    cutoff: int = CUTOFF_DAY,
    dest: Path | None = None,
    feature_list: Path | None = None,
) -> Path:
    out = PROCESSED_OULAD_DIR / FEATURES_NAME if dest is None else Path(dest)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, engine="pyarrow", index=False)
    list_path = FEATURE_LIST_PATH if feature_list is None else Path(feature_list)
    list_path.write_text(render_feature_list(list(frame.columns), cutoff), encoding="utf-8")
    return out


def write_feature_list_only(
    cutoff: int = CUTOFF_DAY,
    source: Path | None = None,
    feature_list: Path | None = None,
) -> Path:
    """feature_list.md'yi mevcut parquet'in sütunlarından yeniden yazar; parquet'e yazmaz."""
    src = PROCESSED_OULAD_DIR / FEATURES_NAME if source is None else Path(source)
    if not src.is_file():
        raise FileNotFoundError(src)
    columns = list(pd.read_parquet(src, engine="pyarrow").columns)
    list_path = FEATURE_LIST_PATH if feature_list is None else Path(feature_list)
    list_path.write_text(render_feature_list(columns, cutoff), encoding="utf-8")
    return list_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feature-list-only",
        action="store_true",
        help="yalnızca feature_list.md'yi mevcut parquet'ten yeniden yaz; parquet'e yazma",
    )
    args = parser.parse_args(argv)
    if args.feature_list_only:
        path = write_feature_list_only(cutoff=CUTOFF_DAY)
        print(f"feature_list path={path}")
        return
    tables = load_tables()
    daily_path = PROCESSED_OULAD_DIR / DAILY_NAME
    if not daily_path.is_file():
        raise FileNotFoundError(daily_path)
    daily = pd.read_parquet(daily_path, engine="pyarrow")
    frame = build_features(tables, daily, cutoff=CUTOFF_DAY)
    path = write_features(frame, cutoff=CUTOFF_DAY)
    print(f"features rows={len(frame)} cols={frame.shape[1]}")
    print(f"path={path}")


if __name__ == "__main__":
    main()
