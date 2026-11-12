"""Sentetik OULAD tablolari. Ag yok."""

from __future__ import annotations

import pandas as pd
import pytest

from data_science.oulad.dataset import (
    CUTOFF_DAY,
    HISTORY_VALUE_COLUMNS,
    build_features,
    render_feature_list,
)
from data_science.oulad.load import SOCIO_COLUMNS

FORBIDDEN = list(SOCIO_COLUMNS) + ["num_of_prev_attempts", "studied_credits"]
HISTORY_COLUMNS = ("has_history", *HISTORY_VALUE_COLUMNS)


def _daily(rows: list[dict] | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(rows or [])
    for column in (
        "code_module",
        "code_presentation",
        "id_student",
        "date",
        "activity_type",
        "sum_click",
        "n_rows",
    ):
        if column not in frame.columns:
            frame[column] = pd.Series(dtype="object")
    return frame


def _tables(
    info: list[dict],
    registration: list[dict],
    assessments: list[dict],
    submissions: list[dict],
) -> dict[str, pd.DataFrame]:
    info_frame = pd.DataFrame(info)
    for column in FORBIDDEN:
        if column not in info_frame.columns:
            info_frame[column] = "x"
    submitted = pd.DataFrame(submissions)
    for column in ("id_assessment", "id_student", "date_submitted", "is_banked", "score"):
        if column not in submitted.columns:
            submitted[column] = pd.Series(dtype="object")
    return {
        "studentInfo": info_frame,
        "studentRegistration": pd.DataFrame(registration),
        "assessments": pd.DataFrame(assessments),
        "studentAssessment": submitted,
    }


def _student(frame: pd.DataFrame, student_id: int) -> pd.Series:
    part = frame.loc[frame["id_student"] == student_id]
    assert len(part) == 1
    return part.iloc[0]


def _history_inputs(mutate: bool) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    info = [
        {"code_module": "AAA", "code_presentation": "2013B", "id_student": 1, "final_result": "Pass"},
        {"code_module": "AAA", "code_presentation": "2013B", "id_student": 2, "final_result": "Fail"},
        {"code_module": "AAA", "code_presentation": "2013B", "id_student": 3, "final_result": "Withdrawn"},
        {"code_module": "AAA", "code_presentation": "2013J", "id_student": 4, "final_result": "Pass"},
        {
            "code_module": "AAA",
            "code_presentation": "2013J",
            "id_student": 5,
            "final_result": "Pass" if mutate else "Fail",
        },
        {
            "code_module": "AAA",
            "code_presentation": "2014B",
            "id_student": 6,
            "final_result": "Fail" if mutate else "Distinction",
        },
        {
            "code_module": "AAA",
            "code_presentation": "2014J",
            "id_student": 7,
            "final_result": "Pass" if mutate else "Withdrawn",
        },
        {
            "code_module": "BBB",
            "code_presentation": "2014J",
            "id_student": 9,
            "final_result": "Fail",
        },
    ]
    registration = [
        {"code_module": "AAA", "code_presentation": "2013B", "id_student": 1, "date_registration": -12, "date_unregistration": None},
        {"code_module": "AAA", "code_presentation": "2013B", "id_student": 2, "date_registration": -4, "date_unregistration": None},
        {"code_module": "AAA", "code_presentation": "2013B", "id_student": 3, "date_registration": -8, "date_unregistration": 5},
        {"code_module": "AAA", "code_presentation": "2013J", "id_student": 4, "date_registration": -6, "date_unregistration": None},
        {"code_module": "AAA", "code_presentation": "2013J", "id_student": 5, "date_registration": 1, "date_unregistration": None},
        {"code_module": "AAA", "code_presentation": "2014B", "id_student": 6, "date_registration": -3, "date_unregistration": None},
        {
            "code_module": "AAA",
            "code_presentation": "2014J",
            "id_student": 7,
            "date_registration": -1,
            "date_unregistration": None if mutate else 80,
        },
        {"code_module": "BBB", "code_presentation": "2014J", "id_student": 9, "date_registration": 2, "date_unregistration": None},
    ]
    assessments = [
        {"code_module": "AAA", "code_presentation": "2013B", "id_assessment": 1, "assessment_type": "Exam", "date": 5, "weight": 100},
        {"code_module": "AAA", "code_presentation": "2013B", "id_assessment": 2, "assessment_type": "TMA", "date": 15, "weight": 10},
        {"code_module": "AAA", "code_presentation": "2013J", "id_assessment": 3, "assessment_type": "TMA", "date": 15, "weight": 10},
        {"code_module": "AAA", "code_presentation": "2013J", "id_assessment": 4, "assessment_type": "CMA", "date": 20, "weight": 10},
        {"code_module": "AAA", "code_presentation": "2014B", "id_assessment": 5, "assessment_type": "TMA", "date": 15, "weight": 10},
        {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 6, "assessment_type": "TMA", "date": 15, "weight": 10},
        {"code_module": "BBB", "code_presentation": "2014J", "id_assessment": 7, "assessment_type": "TMA", "date": 15, "weight": 10},
    ]
    submissions = [
        {"id_assessment": 1, "id_student": 1, "date_submitted": 5, "is_banked": 0, "score": 0},
        {"id_assessment": 2, "id_student": 1, "date_submitted": 14, "is_banked": 0, "score": 90},
        {"id_assessment": 2, "id_student": 2, "date_submitted": 80, "is_banked": 0, "score": 30},
        {"id_assessment": 2, "id_student": 3, "date_submitted": 4, "is_banked": 0, "score": 100},
        {"id_assessment": 3, "id_student": 4, "date_submitted": 15, "is_banked": 0, "score": 70},
        {"id_assessment": 4, "id_student": 4, "date_submitted": 20, "is_banked": 0, "score": 100},
        {
            "id_assessment": 5,
            "id_student": 6,
            "date_submitted": 10,
            "is_banked": 0,
            "score": 0 if mutate else 80,
        },
        {
            "id_assessment": 6,
            "id_student": 7,
            "date_submitted": 12,
            "is_banked": 0,
            "score": 100 if mutate else 50,
        },
        {
            "id_assessment": 7,
            "id_student": 9,
            "date_submitted": 10,
            "is_banked": 0,
            "score": 99 if mutate else 5,
        },
    ]
    if mutate:
        submissions.extend(
            [
                {"id_assessment": 3, "id_student": 5, "date_submitted": 10, "is_banked": 0, "score": 0},
                {"id_assessment": 4, "id_student": 5, "date_submitted": 10, "is_banked": 0, "score": 0},
            ]
        )
    daily_rows = [
        {"code_module": "AAA", "code_presentation": "2013J", "id_student": 4, "date": 10, "activity_type": "forumng", "sum_click": 3, "n_rows": 1},
    ]
    if mutate:
        daily_rows.extend(
            [
                {"code_module": "AAA", "code_presentation": "2013J", "id_student": 5, "date": 12, "activity_type": "forumng", "sum_click": 400, "n_rows": 20},
                {"code_module": "AAA", "code_presentation": "2014B", "id_student": 6, "date": 90, "activity_type": "oucontent", "sum_click": 800, "n_rows": 30},
                {"code_module": "AAA", "code_presentation": "2014J", "id_student": 7, "date": 15, "activity_type": "quiz", "sum_click": 250, "n_rows": 12},
                {"code_module": "BBB", "code_presentation": "2014J", "id_student": 9, "date": 15, "activity_type": "resource", "sum_click": 90, "n_rows": 4},
            ]
        )
    return _tables(info, registration, assessments, submissions), _daily(daily_rows)


def test_cutoff_excludes_later_assessments_and_clicks():
    assert CUTOFF_DAY == 60
    tables = _tables(
        [
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "final_result": "Pass"},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 2, "final_result": "Pass"},
        ],
        [
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "date_registration": -8, "date_unregistration": None},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 2, "date_registration": 0, "date_unregistration": None},
        ],
        [
            {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 1, "assessment_type": "TMA", "date": 20, "weight": 10},
            {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 2, "assessment_type": "TMA", "date": 40, "weight": 30},
            {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 3, "assessment_type": "TMA", "date": 60, "weight": 10},
            {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 4, "assessment_type": "TMA", "date": 61, "weight": 100},
            {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 5, "assessment_type": "TMA", "date": 30, "weight": 10},
            {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 6, "assessment_type": "Exam", "date": 10, "weight": 100},
        ],
        [
            {"id_assessment": 1, "id_student": 1, "date_submitted": 25, "is_banked": 0, "score": 80},
            {"id_assessment": 2, "id_student": 1, "date_submitted": 35, "is_banked": 1, "score": 40},
            {"id_assessment": 3, "id_student": 1, "date_submitted": 60, "is_banked": 0, "score": 100},
            {"id_assessment": 4, "id_student": 1, "date_submitted": 50, "is_banked": 0, "score": 0},
            {"id_assessment": 5, "id_student": 1, "date_submitted": 70, "is_banked": 1, "score": 100},
            {"id_assessment": 6, "id_student": 1, "date_submitted": 10, "is_banked": 1, "score": 5},
        ],
    )
    daily = _daily(
        [
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "date": 20, "activity_type": "forumng", "sum_click": 4, "n_rows": 1},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "date": 20, "activity_type": "quiz", "sum_click": 6, "n_rows": 2},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "date": 60, "activity_type": "resource", "sum_click": 1, "n_rows": 1},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "date": 61, "activity_type": "forumng", "sum_click": 1000, "n_rows": 50},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "date": 61, "activity_type": "late_type", "sum_click": 500, "n_rows": 40},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 2, "date": 90, "activity_type": "forumng", "sum_click": 50, "n_rows": 5},
        ]
    )
    frame = build_features(tables, daily, cutoff=60)
    assert set(FORBIDDEN).isdisjoint(frame.columns)
    row = _student(frame, 1)
    assert int(row["date_registration"]) == -8
    assert int(row["n_expected"]) == 4
    assert int(row["n_submitted"]) == 3
    assert int(row["n_unsubmitted"]) == 1
    assert float(row["score_mean"]) == pytest.approx(220 / 3)
    assert float(row["score_weighted_mean"]) == pytest.approx(60)
    assert float(row["delay_mean"]) == pytest.approx(0)
    assert int(row["n_banked"]) == 1
    assert int(row["vle_clicks"]) == 11
    assert int(row["vle_active_days"]) == 2
    assert int(row["vle_days_to_cutoff"]) == 0
    assert int(row["vle_click_forumng"]) == 4
    assert int(row["vle_click_quiz"]) == 6
    assert int(row["vle_click_resource"]) == 1
    assert "vle_click_late_type" not in frame.columns
    quiet = _student(frame, 2)
    assert int(quiet["vle_clicks"]) == 0
    assert int(quiet["vle_active_days"]) == 0
    assert pd.isna(quiet["vle_days_to_cutoff"])
    assert int(quiet["n_submitted"]) == 0
    assert pd.isna(quiet["score_mean"])

    earlier = build_features(tables, daily, cutoff=30)
    tighter = _student(earlier, 1)
    assert int(tighter["n_expected"]) == 2
    assert int(tighter["n_submitted"]) == 1
    assert float(tighter["score_mean"]) == pytest.approx(80)
    assert int(tighter["vle_clicks"]) == 10
    assert int(tighter["vle_days_to_cutoff"]) == 10
    assert "vle_click_resource" not in earlier.columns
    text = render_feature_list(list(frame.columns), cutoff=60)
    assert "| n_expected |" in text
    assert "gender" not in text
    assert "geçmiş" in text


def test_early_unregistration_removed_later_withdrawal_is_at_risk():
    tables = _tables(
        [
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "final_result": "Fail"},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 2, "final_result": "Withdrawn"},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 3, "final_result": "Withdrawn"},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 4, "final_result": "Pass"},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 5, "final_result": "Distinction"},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 6, "final_result": "Fail"},
        ],
        [
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "date_registration": -10, "date_unregistration": 59},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 2, "date_registration": -10, "date_unregistration": 61},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 3, "date_registration": -10, "date_unregistration": 60},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 4, "date_registration": -10, "date_unregistration": None},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 5, "date_registration": -10, "date_unregistration": None},
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 6, "date_registration": -10, "date_unregistration": None},
        ],
        [
            {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 1, "assessment_type": "TMA", "date": 20, "weight": 10},
        ],
        [],
    )
    frame = build_features(tables, _daily(), cutoff=CUTOFF_DAY)
    assert 1 not in set(frame["id_student"])
    kept = _student(frame, 2)
    assert int(kept["at_risk"]) == 1
    assert kept["split"] == "test"
    boundary = _student(frame, 3)
    assert int(boundary["at_risk"]) == 1
    assert int(_student(frame, 4)["at_risk"]) == 0
    assert int(_student(frame, 5)["at_risk"]) == 0
    assert int(_student(frame, 6)["at_risk"]) == 1


def test_history_ignores_current_and_later_presentations():
    base_tables, base_daily = _history_inputs(False)
    changed_tables, changed_daily = _history_inputs(True)
    base = build_features(base_tables, base_daily, cutoff=CUTOFF_DAY)
    changed = build_features(changed_tables, changed_daily, cutoff=CUTOFF_DAY)

    assert set(base["id_student"]) == {1, 2, 4, 5, 6, 7, 9}
    assert _student(base, 1)["split"] == "history"
    assert _student(base, 4)["split"] == "train"
    assert _student(base, 6)["split"] == "train"
    assert _student(base, 7)["split"] == "test"
    assert int(_student(base, 1)["n_expected"]) == 1
    assert float(_student(base, 1)["score_mean"]) == pytest.approx(90)
    assert float(_student(base, 1)["score_weighted_mean"]) == pytest.approx(90)
    assert int(_student(base, 2)["n_submitted"]) == 0
    assert pd.isna(_student(base, 2)["score_mean"])

    current = _student(base, 4)
    assert int(current["has_history"]) == 1
    assert float(current["hist_slot_mean"]) == pytest.approx(90)
    assert float(current["hist_slot_submit_rate"]) == pytest.approx(0.5)
    assert float(current["hist_module_risk_rate"]) == pytest.approx(0.5)
    assert float(current["score_vs_hist"]) == pytest.approx(-20)
    untouched = _student(base, 5)
    assert float(untouched["hist_slot_mean"]) == pytest.approx(90)
    assert pd.isna(untouched["score_vs_hist"])
    assert int(untouched["at_risk"]) == 1

    later = _student(base, 6)
    assert float(later["hist_slot_mean"]) == pytest.approx(80)
    assert float(later["hist_slot_submit_rate"]) == pytest.approx(0.5)
    assert float(later["hist_module_risk_rate"]) == pytest.approx(0.5)
    assert float(later["score_vs_hist"]) == pytest.approx(0)
    holdout = _student(base, 7)
    assert float(holdout["hist_slot_mean"]) == pytest.approx(80)
    assert float(holdout["hist_slot_submit_rate"]) == pytest.approx(0.6)
    assert float(holdout["hist_module_risk_rate"]) == pytest.approx(0.4)
    assert float(holdout["score_vs_hist"]) == pytest.approx(-30)

    other_module = _student(base, 9)
    assert int(other_module["has_history"]) == 0
    for column in HISTORY_VALUE_COLUMNS:
        assert pd.isna(other_module[column])

    left = base.loc[base["id_student"] == 4, list(HISTORY_COLUMNS)].reset_index(drop=True)
    right = changed.loc[changed["id_student"] == 4, list(HISTORY_COLUMNS)].reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right)
    first = base.loc[base["id_student"] == 1, list(HISTORY_COLUMNS)].reset_index(drop=True)
    first_changed = changed.loc[changed["id_student"] == 1, list(HISTORY_COLUMNS)].reset_index(drop=True)
    pd.testing.assert_frame_equal(first, first_changed)
    assert float(_student(changed, 6)["hist_slot_mean"]) != pytest.approx(80)


def test_has_history_zero_keeps_history_columns_nan():
    tables = _tables(
        [
            {"code_module": "AAA", "code_presentation": "2013B", "id_student": 1, "final_result": "Fail"},
        ],
        [
            {"code_module": "AAA", "code_presentation": "2013B", "id_student": 1, "date_registration": -3, "date_unregistration": None},
        ],
        [
            {"code_module": "AAA", "code_presentation": "2013B", "id_assessment": 1, "assessment_type": "TMA", "date": 10, "weight": 20},
        ],
        [
            {"id_assessment": 1, "id_student": 1, "date_submitted": 10, "is_banked": 0, "score": 40},
        ],
    )
    frame = build_features(tables, _daily(), cutoff=CUTOFF_DAY)
    row = _student(frame, 1)
    assert row["split"] == "history"
    assert int(row["has_history"]) == 0
    assert float(row["score_mean"]) == pytest.approx(40)
    for column in HISTORY_VALUE_COLUMNS:
        assert pd.isna(row[column])


def test_exam_assessments_are_excluded():
    tables = _tables(
        [
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "final_result": "Fail"},
        ],
        [
            {"code_module": "AAA", "code_presentation": "2014J", "id_student": 1, "date_registration": -2, "date_unregistration": None},
        ],
        [
            {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 1, "assessment_type": "Exam", "date": 10, "weight": 100},
            {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 2, "assessment_type": "Exam", "date": None, "weight": 100},
            {"code_module": "AAA", "code_presentation": "2014J", "id_assessment": 3, "assessment_type": "TMA", "date": 20, "weight": 10},
        ],
        [
            {"id_assessment": 1, "id_student": 1, "date_submitted": 10, "is_banked": 1, "score": 0},
            {"id_assessment": 2, "id_student": 1, "date_submitted": 10, "is_banked": 0, "score": 0},
            {"id_assessment": 3, "id_student": 1, "date_submitted": 18, "is_banked": 0, "score": 80},
        ],
    )
    row = _student(build_features(tables, _daily(), cutoff=CUTOFF_DAY), 1)
    assert int(row["n_expected"]) == 1
    assert int(row["n_submitted"]) == 1
    assert int(row["n_banked"]) == 0
    assert float(row["score_mean"]) == pytest.approx(80)
    assert float(row["score_weighted_mean"]) == pytest.approx(80)


def test_slot_key_is_within_assessment_type_by_date():
    tables = _tables(
        [
            {"code_module": "AAA", "code_presentation": "2013B", "id_student": 1, "final_result": "Pass"},
            {"code_module": "AAA", "code_presentation": "2013J", "id_student": 2, "final_result": "Pass"},
        ],
        [
            {"code_module": "AAA", "code_presentation": "2013B", "id_student": 1, "date_registration": -5, "date_unregistration": None},
            {"code_module": "AAA", "code_presentation": "2013J", "id_student": 2, "date_registration": -5, "date_unregistration": None},
        ],
        [
            {"code_module": "AAA", "code_presentation": "2013B", "id_assessment": 5, "assessment_type": "Exam", "date": 1, "weight": 100},
            {"code_module": "AAA", "code_presentation": "2013B", "id_assessment": 1, "assessment_type": "CMA", "date": 5, "weight": 1},
            {"code_module": "AAA", "code_presentation": "2013B", "id_assessment": 30, "assessment_type": "TMA", "date": 10, "weight": 1},
            {"code_module": "AAA", "code_presentation": "2013B", "id_assessment": 10, "assessment_type": "TMA", "date": 40, "weight": 1},
            {"code_module": "AAA", "code_presentation": "2013J", "id_assessment": 31, "assessment_type": "TMA", "date": 11, "weight": 1},
            {"code_module": "AAA", "code_presentation": "2013J", "id_assessment": 11, "assessment_type": "TMA", "date": 20, "weight": 1},
            {"code_module": "AAA", "code_presentation": "2013J", "id_assessment": 32, "assessment_type": "CMA", "date": 50, "weight": 1},
        ],
        [
            {"id_assessment": 5, "id_student": 1, "date_submitted": 1, "is_banked": 0, "score": 0},
            {"id_assessment": 1, "id_student": 1, "date_submitted": 5, "is_banked": 0, "score": 20},
            {"id_assessment": 30, "id_student": 1, "date_submitted": 10, "is_banked": 0, "score": 100},
            {"id_assessment": 10, "id_student": 1, "date_submitted": 40, "is_banked": 0, "score": 50},
            {"id_assessment": 31, "id_student": 2, "date_submitted": 11, "is_banked": 0, "score": 80},
            {"id_assessment": 32, "id_student": 2, "date_submitted": 50, "is_banked": 0, "score": 20},
        ],
    )
    frame = build_features(tables, _daily(), cutoff=CUTOFF_DAY)
    earlier = _student(frame, 1)
    assert int(earlier["n_expected"]) == 3
    assert float(earlier["score_mean"]) == pytest.approx(170 / 3)
    current = _student(frame, 2)
    assert int(current["has_history"]) == 1
    assert float(current["hist_slot_mean"]) == pytest.approx(170 / 3)
    assert float(current["hist_slot_submit_rate"]) == pytest.approx(1)
    assert float(current["score_vs_hist"]) == pytest.approx(-10)
    assert float(current["hist_module_risk_rate"]) == pytest.approx(0)
