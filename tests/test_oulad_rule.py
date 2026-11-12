"""Sabit kural kontrolleri. Ağ yok."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from data_science.oulad.rule import score_frame


def _rows(presentation: str, values: list[tuple[float, float, float]], expected: float = 1.0) -> list[dict]:
    rows = []
    for index, (unsubmitted, score, active) in enumerate(values):
        rows.append(
            {
                "code_module": "AAA" if presentation == "2014B" else "BBB",
                "code_presentation": presentation,
                "n_unsubmitted": unsubmitted,
                "score_mean": score,
                "vle_active_days": active,
                "n_expected": expected,
                "at_risk": index % 2,
            }
        )
    return rows


def test_rule_score_ignores_at_risk():
    frame = pd.DataFrame(_rows("2014B", [(0, 80, 5), (1, 40, 2), (2, 10, 1), (1, 60, 4)]))
    base = score_frame(frame)["rule_score"].to_numpy()
    flipped = frame.copy()
    flipped["at_risk"] = 1 - flipped["at_risk"]
    again = score_frame(flipped)["rule_score"].to_numpy()
    assert np.allclose(base, again, equal_nan=True)


def test_zero_expected_has_no_flag_and_nan_score():
    rows = _rows("2014B", [(0, 80, 5), (2, 10, 1)], expected=0.0)
    rows.extend(_rows("2014J", [(1, 50, 3), (0, 70, 4)], expected=1.0))
    scored = score_frame(pd.DataFrame(rows))
    held = scored["code_presentation"].eq("2014B")
    assert scored.loc[held, "rule_score"].isna().all()
    assert not scored.loc[held, "flagged"].any()
    assert scored.loc[~held, "rule_score"].notna().all()


def test_missing_score_is_the_most_risky_rank():
    frame = pd.DataFrame(_rows("2014B", [(0, 80.0, 4), (1, 40.0, 3), (1, 10.0, 2), (2, np.nan, 1)]))
    scored = score_frame(frame)
    missing = scored["p_score"].iloc[3]
    assert missing == scored["p_score"].max()
    assert missing > scored["p_score"].iloc[2]


def test_each_presentation_flags_ceil_of_eligible():
    rows = _rows("2014B", [(i, 10.0 * i, i) for i in range(6)], expected=1.0)
    rows.extend(
        {
            "code_module": "BBB",
            "code_presentation": "2014J",
            "n_unsubmitted": index,
            "score_mean": 20.0 * index,
            "vle_active_days": index + 1,
            "n_expected": 1.0,
            "at_risk": 0,
        }
        for index in range(4)
    )
    rows.extend(
        {
            "code_module": "CCC",
            "code_presentation": "2013J",
            "n_unsubmitted": 1,
            "score_mean": 5.0,
            "vle_active_days": 1,
            "n_expected": 0.0,
            "at_risk": 1,
        }
        for _ in range(5)
    )
    scored = score_frame(pd.DataFrame(rows))
    eligible_n = {"2014B": 6, "2014J": 4, "2013J": 0}
    for presentation, n_eligible in eligible_n.items():
        block = scored["code_presentation"].eq(presentation)
        assert int(scored.loc[block, "rule_score"].notna().sum()) == n_eligible
        expected_flags = math.ceil(0.2 * n_eligible) if n_eligible else 0
        assert int(scored.loc[block, "flagged"].sum()) == expected_flags


def test_other_presentation_does_not_change_scores():
    frame = pd.DataFrame(
        _rows("2014B", [(0, 70, 5), (1, 30, 2), (2, 10, 1)])
        + [
            {
                "code_module": "BBB",
                "code_presentation": "2014J",
                "n_unsubmitted": 0,
                "score_mean": 90.0,
                "vle_active_days": 8,
                "n_expected": 1.0,
                "at_risk": 0,
            },
            {
                "code_module": "BBB",
                "code_presentation": "2014J",
                "n_unsubmitted": 3,
                "score_mean": 15.0,
                "vle_active_days": 1,
                "n_expected": 1.0,
                "at_risk": 1,
            },
        ]
    )
    before = score_frame(frame)
    changed = frame.copy()
    mask = changed["code_presentation"].eq("2014J")
    changed.loc[mask, "n_unsubmitted"] = 9
    changed.loc[mask, "score_mean"] = 0.0
    changed.loc[mask, "vle_active_days"] = 0
    after = score_frame(changed)
    kept = before["code_presentation"].eq("2014B").to_numpy()
    assert np.allclose(before.loc[kept, "rule_score"], after.loc[kept, "rule_score"], equal_nan=True)
    assert not np.allclose(
        before.loc[~kept, "rule_score"],
        after.loc[~kept, "rule_score"],
        equal_nan=True,
    )
