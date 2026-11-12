"""Sabit kural kontrolleri. Ağ yok."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from data_science.oulad.rule import DEFAULT_SIGNALS, RULE2_SIGNALS, score_frame


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


def test_default_signals_match_the_original_three():
    assert DEFAULT_SIGNALS == ("n_unsubmitted", "score_mean", "vle_active_days")
    frame = pd.DataFrame(_rows("2014B", [(0, 80, 5), (1, 40, 2), (2, 10, 1), (1, 60, 4)]))
    default = score_frame(frame)
    explicit = score_frame(frame, signals=["vle_active_days", "n_unsubmitted", "score_mean"])
    for column in ("p_unsub", "p_score", "p_active", "rule_score"):
        assert np.allclose(default[column], explicit[column], equal_nan=True)
    assert default["flagged"].tolist() == explicit["flagged"].tolist()
    assert np.allclose(
        default["rule_score"],
        (default["p_unsub"] + default["p_score"] + default["p_active"]) / 3.0,
        equal_nan=True,
    )
    changed = frame.copy()
    changed["n_unsubmitted"] = [4, 0, 3, 1]
    moved = score_frame(changed)
    assert not np.allclose(default["rule_score"], moved["rule_score"], equal_nan=True)


def test_two_signal_rule_uses_inverted_score_and_active_days():
    assert RULE2_SIGNALS == ("score_mean", "vle_active_days")
    frame = pd.DataFrame(_rows("2014B", [(0, 80, 5), (1, 40, 2), (2, 10, 1), (3, 60, 4)]))
    base = score_frame(frame)
    scored = score_frame(frame, signals=("vle_active_days", "score_mean"))
    assert scored["p_unsub"].isna().all()
    assert np.allclose(scored["p_score"], base["p_score"], equal_nan=True)
    assert np.allclose(scored["p_active"], base["p_active"], equal_nan=True)
    assert np.allclose(
        scored["rule_score"],
        (scored["p_score"] + scored["p_active"]) / 2.0,
        equal_nan=True,
    )
    assert scored["p_score"].iloc[2] == scored["p_score"].max()
    assert scored["p_active"].iloc[2] == scored["p_active"].max()
    assert int(scored["flagged"].sum()) == math.ceil(0.2 * len(frame))
    picked = np.flatnonzero(scored["flagged"].to_numpy())
    assert frame.iloc[picked]["score_mean"].iloc[0] == frame["score_mean"].min()
    assert frame.iloc[picked]["vle_active_days"].iloc[0] == frame["vle_active_days"].min()
    flipped = frame.copy()
    flipped["at_risk"] = 1 - flipped["at_risk"]
    again = score_frame(flipped, signals=RULE2_SIGNALS)
    assert np.allclose(scored["rule_score"], again["rule_score"], equal_nan=True)
    untouched = frame.copy()
    untouched["n_unsubmitted"] = [9, 0, 4, 1]
    held = score_frame(untouched, signals=RULE2_SIGNALS)
    assert np.allclose(scored["rule_score"], held["rule_score"], equal_nan=True)
    assert scored["flagged"].tolist() == held["flagged"].tolist()
    rescored = frame.copy()
    rescored["score_mean"] = [10.0, 90.0, 20.0, 70.0]
    assert not np.allclose(
        scored["rule_score"],
        score_frame(rescored, signals=RULE2_SIGNALS)["rule_score"],
        equal_nan=True,
    )
    reactive = frame.copy()
    reactive["vle_active_days"] = [1, 9, 2, 8]
    assert not np.allclose(
        scored["rule_score"],
        score_frame(reactive, signals=RULE2_SIGNALS)["rule_score"],
        equal_nan=True,
    )
    missing = pd.DataFrame(_rows("2014B", [(0, 80.0, 4), (1, 40.0, 3), (1, 10.0, 2), (2, np.nan, 1)]))
    scored_missing = score_frame(missing, signals=RULE2_SIGNALS)
    assert scored_missing["p_score"].iloc[3] == scored_missing["p_score"].max()
    assert scored_missing["p_score"].iloc[3] > scored_missing["p_score"].iloc[2]


def test_two_signal_zero_expected_has_no_flag():
    eligible_rows = _rows(
        "2014B",
        [(0, 90, 5), (1, 70, 4), (2, 50, 3), (3, 30, 2), (4, 10, 1)],
        expected=1.0,
    )
    zero_rows = _rows("2014B", [(9, 0, 0), (8, 1, 1)], expected=0.0)
    other = _rows("2014J", [(1, 10, 1), (0, 80, 6)], expected=0.0)
    scored = score_frame(pd.DataFrame(eligible_rows + zero_rows + other), signals=RULE2_SIGNALS)
    assert scored["rule_score"].iloc[len(eligible_rows) :].isna().all()
    assert not scored["flagged"].iloc[len(eligible_rows) :].any()
    assert int(scored["rule_score"].iloc[: len(eligible_rows)].notna().sum()) == len(eligible_rows)
    assert int(scored["flagged"].sum()) == math.ceil(0.2 * len(eligible_rows))
    only = score_frame(pd.DataFrame(eligible_rows), signals=RULE2_SIGNALS)
    assert np.allclose(
        scored["rule_score"].iloc[: len(eligible_rows)],
        only["rule_score"],
        equal_nan=True,
    )
    assert scored["flagged"].iloc[: len(eligible_rows)].tolist() == only["flagged"].tolist()


def test_unknown_signal_is_rejected():
    frame = pd.DataFrame(_rows("2014B", [(0, 80, 5), (1, 40, 2)]))
    rejected = False
    try:
        score_frame(frame, signals=("vle_clicks",))
    except ValueError:
        rejected = True
    assert rejected
    rejected = False
    try:
        score_frame(frame, signals=())
    except ValueError:
        rejected = True
    assert rejected
