"""Ek analiz (E1, E2) kontrolleri. Sentetik veri; ağ ve ham veri yok."""

from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from data_science.oulad import ek
from data_science.oulad.ek import (
    GROUP_NAMES,
    GROUP_OF,
    SET_GROUPS,
    TARGET_COLUMN,
    attach_final_result,
    evaluate_expectations,
    exclude_ggg,
    group_columns,
    prepare_frame,
    rule2_hits_by_final_result,
    run_target,
    set_columns,
    target_counts,
    target_frame,
)
from data_science.oulad.load import SOCIO_COLUMNS
from data_science.oulad.model import (
    SET_NAMES,
    _module_table,
    _target,
    bootstrap_indices,
    metric_intervals,
    paired_difference,
    select_hyperparameters,
)
from data_science.oulad.rule import _predict

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT = (
    "n_expected",
    "n_submitted",
    "n_unsubmitted",
    "score_mean",
    "score_weighted_mean",
    "delay_mean",
    "n_banked",
)
VLE = ("vle_clicks", "vle_active_days", "vle_days_to_cutoff")
VLE_CLICKS = (
    "vle_click_forumng",
    "vle_click_subpage",
    "vle_click_oucontent",
    "vle_click_homepage",
    "vle_click_resource",
)
PRESENTATIONS = (("2013B", "history"), ("2013J", "train"), ("2014B", "train"), ("2014J", "test"))
KEY = ["code_module", "code_presentation", "id_student"]


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
        *VLE_CLICKS,
        "has_history",
        "hist_slot_mean",
        "hist_slot_submit_rate",
        "score_vs_hist",
        "hist_module_risk_rate",
        *SOCIO_COLUMNS,
        "num_of_prev_attempts",
        "studied_credits",
    ]


def _synthetic(n_per: int = 40, seed: int = 0) -> pd.DataFrame:
    """AAA, BBB, GGG; GGG'nin 2014B ve 2014J'de notlu ödevi yok. final_result dahil."""
    rng = np.random.default_rng(seed)
    rows = []
    student = 0
    for module in ("AAA", "BBB", "GGG"):
        for presentation, split in PRESENTATIONS:
            expected = 0 if module == "GGG" and presentation in ("2014B", "2014J") else 3
            for _ in range(n_per):
                student += 1
                final = str(rng.choice(["Pass", "Distinction", "Fail", "Withdrawn"], p=[0.35, 0.15, 0.25, 0.25]))
                weak = final in ("Fail", "Withdrawn")
                submitted = int(rng.integers(0, expected + 1)) if weak else expected
                days = int(rng.poisson(3 if weak else 9))
                row = {
                    "code_module": module,
                    "code_presentation": presentation,
                    "id_student": student,
                    "final_result": final,
                    "at_risk": int(weak),
                    "split": split,
                    "date_registration": int(rng.integers(-60, 5)),
                    "n_expected": expected,
                    "n_submitted": submitted,
                    "n_unsubmitted": expected - submitted,
                    "score_mean": float(rng.normal(40 if weak else 65, 10)) if submitted else np.nan,
                    "score_weighted_mean": float(rng.normal(40 if weak else 65, 10)) if submitted else np.nan,
                    "delay_mean": float(rng.normal(2, 1)) if submitted else np.nan,
                    "n_banked": int(rng.integers(0, 2)),
                    "vle_clicks": days * 12,
                    "vle_active_days": days,
                    "vle_days_to_cutoff": 60 - min(days, 59),
                }
                for column in VLE_CLICKS:
                    row[column] = int(rng.poisson(days))
                rows.append(row)
    return pd.DataFrame(rows)


def _features(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.drop(columns=["final_result"])


def _info(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[:, [*KEY, "final_result"]].copy()


def _doc_table(path: Path) -> dict[str, str]:
    table = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 3 and cells[0] not in ("sütun", "---"):
            table[cells[0]] = cells[1]
    return table


# --- grup ataması -----------------------------------------------------------
def test_groups_partition_general_columns_completely_and_disjointly():
    from data_science.oulad.model import feature_columns

    general = feature_columns("GENERAL", _available())
    groups = group_columns(_available())
    assert tuple(groups) == GROUP_NAMES
    flat = [column for columns in groups.values() for column in columns]
    assert len(flat) == len(set(flat))
    assert set(flat) == set(general)
    assert len(flat) == len(general)
    for name, columns in groups.items():
        assert all(GROUP_OF[column] == name for column in columns)


def test_group_dictionary_matches_pre_registration_addendum():
    table = _doc_table(ROOT / "docs" / "ek_analizler_on_kayit_eki.md")
    assert table == GROUP_OF


def test_group_dictionary_matches_general_columns_of_feature_list():
    general = set()
    for line in (ROOT / "data_science" / "oulad" / "feature_list.md").read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 6 and cells[2] == "genel":
            general.add(cells[0])
    general -= {"code_module", "code_presentation", "id_student", "at_risk", "split"}
    assert general == set(GROUP_OF)


def test_unassigned_general_column_stops_the_run():
    available = [*_available(), "vle_click_quiz"]
    with pytest.raises(ValueError, match="grupsuz"):
        group_columns(available)
    with pytest.raises(ValueError, match="grupsuz"):
        set_columns(available)


def test_no_set_contains_socio_or_forbidden_columns():
    sets = set_columns(_available())
    forbidden = set(SOCIO_COLUMNS) | {
        "num_of_prev_attempts",
        "studied_credits",
        "code_module",
        "code_presentation",
        "id_student",
        "at_risk",
        "split",
        "final_result",
        TARGET_COLUMN,
    }
    for columns in sets.values():
        assert forbidden.isdisjoint(columns)
        assert not any(column.startswith(("hist_", "rel_")) or column == "has_history" for column in columns)


def test_sets_are_built_from_groups():
    sets = set_columns(_available())
    groups = group_columns(_available())
    assert tuple(sets) == tuple(SET_GROUPS)
    assert sets["NOT"] == groups["NOT"]
    assert sets["TESLİM"] == groups["TESLİM"]
    assert sets["ETKİNLİK"] == groups["ETKİNLİK"]
    assert set(sets["NOT_TESLİM"]) == set(groups["NOT"]) | set(groups["TESLİM"])
    assert set(sets["GENERAL"]) == {column for columns in groups.values() for column in columns}
    assert "date_registration" in sets["GENERAL"]
    for name in ("NOT", "TESLİM", "ETKİNLİK", "NOT_TESLİM"):
        assert "date_registration" not in sets[name]
    assert "n_banked" in sets["TESLİM"]
    assert "n_banked" not in sets["NOT"]


# --- veri hazırlığı ve hedefler --------------------------------------------
def test_attach_final_result_checks_keys_and_consistency():
    frame = _synthetic()
    attached = attach_final_result(_features(frame), _info(frame))
    assert attached["final_result"].tolist() == frame["final_result"].tolist()
    short = _info(frame).iloc[1:]
    with pytest.raises(ValueError, match="bulunamayan"):
        attach_final_result(_features(frame), short)
    duplicated = pd.concat([_info(frame), _info(frame).iloc[:1]], ignore_index=True)
    with pytest.raises(ValueError, match="tekil"):
        attach_final_result(_features(frame), duplicated)
    wrong = _info(frame)
    wrong.loc[0, "final_result"] = "Unknown"
    with pytest.raises(ValueError, match="bilinmeyen"):
        attach_final_result(_features(frame), wrong)
    flipped = _features(frame)
    flipped.loc[0, "at_risk"] = 1 - flipped.loc[0, "at_risk"]
    with pytest.raises(ValueError, match="tutarsiz"):
        attach_final_result(flipped, _info(frame))


def test_ggg_is_excluded_only_in_evaluation_periods():
    frame = _synthetic()
    kept, excluded = exclude_ggg(frame)
    assert sorted((item["code_module"], item["code_presentation"]) for item in excluded) == [
        ("GGG", "2014B"),
        ("GGG", "2014J"),
    ]
    ggg = kept["code_module"].eq("GGG")
    assert set(kept.loc[ggg, "code_presentation"]) == {"2013B", "2013J"}
    assert len(kept) == len(frame) - 2 * 40
    other = frame.loc[frame["code_module"] != "GGG"]
    assert kept.loc[~ggg, "id_student"].tolist() == other["id_student"].tolist()


def test_ggg_exclusion_stops_when_assumption_fails():
    frame = _synthetic()
    eligible_ggg = frame.copy()
    eligible_ggg.loc[
        eligible_ggg["code_module"].eq("GGG") & eligible_ggg["code_presentation"].eq("2014J"),
        "n_expected",
    ] = 3
    with pytest.raises(ValueError, match="GGG"):
        exclude_ggg(eligible_ggg)
    foreign = frame.copy()
    foreign.loc[
        foreign["code_module"].eq("AAA") & foreign["code_presentation"].eq("2014J"),
        "n_expected",
    ] = 0
    with pytest.raises(ValueError, match="GGG"):
        exclude_ggg(foreign)


def test_targets_exclude_other_class_and_counts_match_final_result():
    frame = _synthetic()
    prepared, _ = prepare_frame(_features(frame), _info(frame))
    assert set(prepared["split"]) == {"train", "test"}
    final = prepared["final_result"]
    counts = final.value_counts().to_dict()

    failed = target_frame(prepared, "KALDI")
    assert not failed["final_result"].eq("Withdrawn").any()
    assert int(failed[TARGET_COLUMN].sum()) == counts["Fail"]
    assert len(failed) == counts["Fail"] + counts["Pass"] + counts["Distinction"]
    assert failed.loc[failed[TARGET_COLUMN].eq(1), "final_result"].eq("Fail").all()

    left = target_frame(prepared, "BIRAKTI")
    assert not left["final_result"].eq("Fail").any()
    assert int(left[TARGET_COLUMN].sum()) == counts["Withdrawn"]
    assert len(left) == counts["Withdrawn"] + counts["Pass"] + counts["Distinction"]
    assert left.loc[left[TARGET_COLUMN].eq(1), "final_result"].eq("Withdrawn").all()

    reference = target_frame(prepared, "referans")
    assert len(reference) == len(prepared)
    assert int(reference[TARGET_COLUMN].sum()) == counts["Fail"] + counts["Withdrawn"]
    assert reference[TARGET_COLUMN].tolist() == prepared["at_risk"].tolist()

    for framed in (failed, left, reference):
        summary = target_counts(framed)
        assert summary["train"]["n"] == int(framed["split"].eq("train").sum())
        assert summary["test_2014J"]["n"] == int(framed["code_presentation"].eq("2014J").sum())
        assert summary["train"]["n_positive"] == int(framed.loc[framed["split"].eq("train"), TARGET_COLUMN].sum())
        assert summary["fit_2013J"]["n"] + summary["validation_2014B"]["n"] == summary["train"]["n"]
        assert summary["final_result"] == framed["final_result"].value_counts().sort_index().to_dict()
    with pytest.raises(ValueError, match="bilinmeyen hedef"):
        target_frame(prepared, "OTHER")


# --- B ölçütleri ------------------------------------------------------------
def _auc_base() -> dict:
    return {
        "referans": {
            "GENERAL": 0.80,
            "NOT": 0.70,
            "TESLİM": 0.75,
            "ETKİNLİK": 0.76,
            "NOT_TESLİM": 0.78,
        },
        "KALDI": {"GENERAL": 0.72, "NOT": 0.68, "TESLİM": 0.66, "ETKİNLİK": 0.60},
        "BIRAKTI": {"GENERAL": 0.90, "NOT": 0.66, "TESLİM": 0.80, "ETKİNLİK": 0.88},
    }


def _hits(n_hit: int = 100, n_withdrawn: int = 60) -> dict:
    return {
        "n": 500,
        "n_flagged": 120,
        "n_hit": n_hit,
        "n_fail": n_hit - n_withdrawn,
        "n_withdrawn": n_withdrawn,
        "n_pass_distinction": 120 - n_hit,
    }


def _evaluate(auc: dict | None = None, hits: dict | None = None, test_auc: dict | None = None, test_hits=None):
    validation_auc = auc if auc is not None else _auc_base()
    return evaluate_expectations(
        {"validation": validation_auc, "test": test_auc if test_auc is not None else validation_auc},
        {"validation": hits or _hits(), "test": test_hits or hits or _hits()},
    )


def test_all_expectations_hold_on_hand_built_example():
    report = _evaluate()
    assert list(report) == ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]
    for key, block in report.items():
        assert block["result"] == "tuttu", key
        assert block["validation"]["holds"] is True
        assert block["test"]["holds"] is True
        assert block["expectation"] and block["criterion"]
    b1 = report["B1"]["test"]["gap_to_general"]
    assert math.isclose(b1["NOT"], 0.10)
    assert math.isclose(b1["TESLİM"], 0.05)
    assert math.isclose(b1["ETKİNLİK"], 0.04)
    assert math.isclose(report["B3"]["test"]["gap"], 0.02)
    assert math.isclose(report["B4"]["test"]["difference"], 0.18)
    assert math.isclose(report["B5"]["test"]["gap_BIRAKTI"], 0.02)
    assert math.isclose(report["B5"]["test"]["gap_KALDI"], 0.12)
    assert math.isclose(report["B6"]["test"]["not_minus_activity_KALDI"], 0.08)
    assert math.isclose(report["B6"]["test"]["not_minus_activity_referans"], -0.06)
    assert report["B7"]["test"]["withdrawn_share"] == 0.6


def _failing(key: str):
    auc = copy.deepcopy(_auc_base())
    hits = _hits()
    if key == "B1":
        auc["referans"]["ETKİNLİK"] = 0.79
    elif key == "B2":
        auc["referans"]["NOT"] = 0.77
    elif key == "B3":
        auc["referans"]["NOT_TESLİM"] = 0.76
    elif key == "B4":
        auc["BIRAKTI"]["GENERAL"] = 0.73
    elif key == "B5":
        auc["BIRAKTI"]["ETKİNLİK"] = 0.70
    elif key == "B6":
        auc["KALDI"]["NOT"] = 0.50
    elif key == "B7":
        hits = _hits(100, 50)
    return auc, hits


@pytest.mark.parametrize("key", ["B1", "B2", "B3", "B4", "B5", "B6", "B7"])
def test_each_expectation_fails_alone(key):
    auc, hits = _failing(key)
    report = _evaluate(auc, hits)
    for other, block in report.items():
        expected = "tutmadı" if other == key else "tuttu"
        assert block["result"] == expected, (key, other)
        assert block["test"]["holds"] is (other != key)


def test_b7_needs_strictly_more_than_half():
    assert _evaluate(hits=_hits(10, 6))["B7"]["result"] == "tuttu"
    assert _evaluate(hits=_hits(10, 5))["B7"]["result"] == "tutmadı"
    assert _evaluate(hits=_hits(7, 3))["B7"]["result"] == "tutmadı"
    assert _evaluate(hits=_hits(7, 4))["B7"]["result"] == "tuttu"


def test_result_has_three_values_by_validation_and_test_agreement():
    base = _auc_base()
    # İki dönem de sağlar: hepsi tuttu.
    both_hold = _evaluate(auc=base, test_auc=copy.deepcopy(base))
    assert {block["result"] for block in both_hold.values()} == {"tuttu"}

    # İki dönem de sağlamaz: yalnız ilgili beklenti tutmadı.
    for key in ("B1", "B2", "B3", "B4", "B5", "B6", "B7"):
        failing_auc, failing_hits = _failing(key)
        neither = _evaluate(auc=failing_auc, hits=failing_hits)
        assert neither[key]["result"] == "tutmadı"
        assert neither[key]["validation"]["holds"] is False
        assert neither[key]["test"]["holds"] is False

    # Dönemler ayrışır: doğrulamada sağlar, testte sağlamaz ve tersi. Tek dönem karar vermez.
    for key in ("B1", "B2", "B3", "B4", "B5", "B6", "B7"):
        failing_auc, failing_hits = _failing(key)
        validation_only = _evaluate(auc=base, hits=_hits(), test_auc=failing_auc, test_hits=failing_hits)
        assert validation_only[key]["validation"]["holds"] is True
        assert validation_only[key]["test"]["holds"] is False
        assert validation_only[key]["result"] == "belirsiz"
        test_only = _evaluate(auc=failing_auc, hits=failing_hits, test_auc=base, test_hits=_hits())
        assert test_only[key]["validation"]["holds"] is False
        assert test_only[key]["test"]["holds"] is True
        assert test_only[key]["result"] == "belirsiz"
        for other, block in validation_only.items():
            if other != key:
                assert block["result"] == "tuttu"


def _md5_of(path: Path) -> str:
    return ek._md5(path)


def _registry(tmp_path: Path, records: list[tuple[str, str, str]]) -> Path:
    """records: (dosya adı, md5, zaman). Gerçek on_kayit_md5.txt biçimi."""
    lines = []
    for name, digest, stamp in records:
        lines.extend([f"{digest}  docs/{name}", stamp])
    path = tmp_path / "on_kayit_md5.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_last_registration_is_valid_when_a_file_has_two_records(tmp_path):
    main_file = tmp_path / "ana.md"
    addendum = tmp_path / "eki.md"
    main_file.write_text("ana", encoding="utf-8")
    addendum.write_text("ek ilk", encoding="utf-8")
    first = _md5_of(addendum)
    addendum.write_text("ek ikinci", encoding="utf-8")
    second = _md5_of(addendum)
    registry = _registry(
        tmp_path,
        [
            ("ana.md", _md5_of(main_file), "17:04"),
            ("eki.md", first, "17:39"),
            ("eki.md", second, "17:41"),
        ],
    )
    histories = ek.check_pre_registration(registry, (main_file, addendum))
    assert [item["md5"] for item in histories["eki.md"]] == [first, second]
    assert [item["time"] for item in histories["eki.md"]] == ["17:39", "17:41"]
    assert len(histories["ana.md"]) == 1


def test_stale_last_registration_stops_even_if_an_earlier_one_matches(tmp_path):
    addendum = tmp_path / "eki.md"
    addendum.write_text("ek ilk", encoding="utf-8")
    first = _md5_of(addendum)
    addendum.write_text("ek ikinci", encoding="utf-8")
    registry = _registry(tmp_path, [("eki.md", "0" * 32, "17:39"), ("eki.md", first, "17:41")])
    with pytest.raises(ValueError, match="son kayittan sonra degismis"):
        ek.check_pre_registration(registry, (addendum,))
    # İlk kayıt dosyayla uyuşsa bile son kayıt uyuşmuyorsa hata.
    addendum.write_text("ek ilk", encoding="utf-8")
    registry = _registry(tmp_path, [("eki.md", first, "17:39"), ("eki.md", "f" * 32, "17:41")])
    with pytest.raises(ValueError, match="son kayittan sonra degismis"):
        ek.check_pre_registration(registry, (addendum,))


def test_file_without_any_record_stops(tmp_path):
    main_file = tmp_path / "ana.md"
    other = tmp_path / "eki.md"
    main_file.write_text("ana", encoding="utf-8")
    other.write_text("eki", encoding="utf-8")
    registry = _registry(tmp_path, [("ana.md", _md5_of(main_file), "17:04")])
    with pytest.raises(ValueError, match="kayitli md5 yok"):
        ek.check_pre_registration(registry, (main_file, other))


def test_record_without_time_line_stops():
    text = "a" * 32 + "  docs/eki.md\n" + "b" * 32 + "  docs/eki.md\nczw 17:41\n"
    with pytest.raises(ValueError, match="zaman satiri yok"):
        ek.registration_history(text, "eki.md")


def test_registration_history_is_written_to_report_in_order(tmp_path):
    text = (
        "a" * 32 + "  docs/ana.md\nczw 17:04\n"
        + "b" * 32 + "  docs/eki.md\nczw 17:39\n"
        + "c" * 32 + "  docs/eki.md\nczw 17:41\n"
    )
    histories = {name: ek.registration_history(text, name) for name in ("ana.md", "eki.md")}
    block = ek.registration_block(histories)
    assert block["ana.md"] == {"md5": "a" * 32, "history": [{"md5": "a" * 32, "time": "czw 17:04"}]}
    assert block["eki.md"]["md5"] == "c" * 32
    assert block["eki.md"]["history"] == [
        {"md5": "b" * 32, "time": "czw 17:39"},
        {"md5": "c" * 32, "time": "czw 17:41"},
    ]


def test_decision_rules_are_written_in_addendum():
    text = (ROOT / "docs" / "ek_analizler_on_kayit_eki.md").read_text(encoding="utf-8")
    assert "## Karar kuralları" in text
    assert "belirsiz" in text
    assert "NOT_TESLİM setinde KAYIT yok; B3'teki fark ETKİNLİK ile birlikte KAYIT'ı da kapsar." in text


def test_expectations_stop_on_missing_values():
    auc = copy.deepcopy(_auc_base())
    auc["KALDI"]["NOT"] = None
    with pytest.raises(ValueError, match="ROC AUC yok"):
        _evaluate(auc)
    auc = copy.deepcopy(_auc_base())
    auc["BIRAKTI"]["GENERAL"] = float("nan")
    with pytest.raises(ValueError, match="ROC AUC yok"):
        _evaluate(auc)
    with pytest.raises(ValueError, match="isabet"):
        _evaluate(hits=_hits(0, 0))


def _rule_rows(finals: list[str]) -> pd.DataFrame:
    n = len(finals)
    return pd.DataFrame(
        {
            "code_module": ["AAA"] * n,
            "code_presentation": ["2014J"] * n,
            "n_unsubmitted": [0] * n,
            "n_expected": [1.0] * n,
            "score_mean": [10.0 * (index + 1) for index in range(n)],
            "vle_active_days": [index + 1 for index in range(n)],
            "final_result": finals,
        }
    )


def test_rule2_hits_split_by_final_result_on_small_example():
    # n=10 -> ceil(0.2*10)=2 bayrak: en düşük not ve en az etkin gün, satır 0 ve 1.
    mixed = rule2_hits_by_final_result(_rule_rows(["Withdrawn", "Pass", *["Fail"] * 8]))
    assert mixed == {
        "n": 10,
        "n_flagged": 2,
        "n_hit": 1,
        "n_fail": 0,
        "n_withdrawn": 1,
        "n_pass_distinction": 1,
    }
    both = rule2_hits_by_final_result(_rule_rows(["Fail", "Withdrawn", *["Pass"] * 8]))
    assert both["n_hit"] == 2
    assert both["n_fail"] == 1
    assert both["n_withdrawn"] == 1
    assert both["n_pass_distinction"] == 0
    none = rule2_hits_by_final_result(_rule_rows(["Distinction", "Pass", *["Withdrawn"] * 8]))
    assert none["n_hit"] == 0
    assert none["n_pass_distinction"] == 2


# --- mevcut fonksiyonların varsayılan çağrısı ------------------------------
def test_extended_functions_keep_default_behaviour():
    frame = _synthetic()
    train = frame.loc[frame["split"].eq("train")].reset_index(drop=True)
    assert np.array_equal(_target(train), _target(train, "at_risk"))
    with pytest.raises(ValueError, match="at_risk yok"):
        _target(train.drop(columns=["at_risk"]))

    columns = ["score_mean", "vle_active_days", "date_registration"]
    default = select_hyperparameters(train, columns, "logreg")
    explicit = select_hyperparameters(train, columns, "logreg", "at_risk")
    renamed = select_hyperparameters(train.rename(columns={"at_risk": "alt"}), columns, "logreg", "alt")
    assert default == explicit == renamed
    with pytest.raises(ValueError, match="at_risk yok"):
        select_hyperparameters(train.rename(columns={"at_risk": "alt"}), columns, "logreg")

    y = np.array([1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0])
    proba = np.array([0.2, 0.8, 0.4, 0.1, 0.7, 0.6, 0.3, 0.9, 0.05, 0.55, 0.35, 0.15])
    other = np.array([0.3, 0.6, 0.5, 0.2, 0.4, 0.7, 0.1, 0.8, 0.15, 0.45, 0.25, 0.35])
    modules = np.array(["AAA"] * 4 + ["BBB"] * 4 + ["CCC"] * 4)
    indices = bootstrap_indices(modules, y, 20, 42)
    from data_science.oulad.model import _bootstrap_samples

    base = metric_intervals(y, proba, modules, n_boot=20, seed=42)
    cached = metric_intervals(
        y, proba, modules, indices=indices, samples=_bootstrap_samples(y, proba, indices)
    )
    assert base == cached
    paired = paired_difference(y, proba, other, modules, n_boot=20, seed=42)
    paired_cached = paired_difference(
        y,
        proba,
        other,
        modules,
        indices=indices,
        samples_left=_bootstrap_samples(y, proba, indices),
        samples_right=_bootstrap_samples(y, other, indices),
    )
    assert paired == paired_cached

    by_set = {name: proba for name in SET_NAMES}
    assert _module_table(modules, y, by_set, "hgb") == _module_table(modules, y, by_set, "hgb", SET_NAMES)
    assert list(_module_table(modules, y, by_set, "hgb", ("GENERAL",))["mean"]) == ["GENERAL"]

    from data_science.oulad.model import feature_columns

    params = {"learning_rate": 0.1, "max_leaf_nodes": 15, "max_iter": 20}
    fit = frame["code_presentation"].eq("2013J").to_numpy()
    predict = frame["code_presentation"].eq("2014B").to_numpy()
    general = feature_columns("GENERAL", list(frame.columns))
    assert np.array_equal(
        _predict(frame, params, fit, predict),
        _predict(frame, params, fit, predict, general, "hgb", "at_risk"),
    )


# --- uçtan uca küçük çalıştırma --------------------------------------------
def test_run_target_on_synthetic_frame_without_data_files():
    frame = _synthetic()
    prepared, _ = prepare_frame(_features(frame), _info(frame))
    sets = set_columns(list(prepared.columns))
    chosen = {name: sets[name] for name in ("NOT", "ETKİNLİK", "GENERAL")}
    framed = target_frame(prepared, "KALDI")
    out = run_target(framed, chosen, ("logreg",), n_boot=5, seed=42)
    assert list(out["results"]) == ["NOT", "ETKİNLİK", "GENERAL"]
    test_rows = framed["code_presentation"].eq("2014J")
    validation_rows = framed["code_presentation"].eq("2014B")
    for name, models in out["results"].items():
        entry = models["logreg"]
        assert set(entry) == {"columns", "selected", "validation", "test"}
        assert entry["columns"] == chosen[name]
        assert entry["test"]["n"] == int(test_rows.sum())
        assert entry["test"]["n_positive"] == int(framed.loc[test_rows, TARGET_COLUMN].sum())
        assert entry["validation"]["n"] == int(validation_rows.sum())
        roc = entry["test"]["roc_auc"]
        assert roc["low"] <= roc["high"]
        assert 0.0 <= roc["estimate"] <= 1.0
        assert entry["test"]["within_module_20"]["n"] == entry["test"]["n"]
    assert set(out["paired_vs_general"]["logreg"]) == {"NOT-GENERAL", "ETKİNLİK-GENERAL"}
    diff = out["paired_vs_general"]["logreg"]["NOT-GENERAL"]["test"]["roc_auc"]
    general = out["results"]["GENERAL"]["logreg"]["test"]["roc_auc"]["estimate"]
    single = out["results"]["NOT"]["logreg"]["test"]["roc_auc"]["estimate"]
    assert math.isclose(diff["estimate"], single - general)


def test_build_report_covers_all_expectations_on_synthetic_data(monkeypatch):
    # Hgb ızgarasını küçült: yalnız bu testte, rapor yapısını sınamak için.
    from data_science.oulad import model

    monkeypatch.setattr(model, "HGB_GRID", model.HGB_GRID[:1])
    frame = _synthetic()
    registration = {"eki.md": {"md5": "c" * 32, "history": [{"md5": "c" * 32, "time": "t"}]}}
    report = ek.build_report(_features(frame), _info(frame), n_boot=5, seed=42, registration=registration)
    assert report["pre_registration_md5"] == registration
    assert list(report["expectations"]) == ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]
    for block in report["expectations"].values():
        assert block["result"] in ("tuttu", "tutmadı", "belirsiz")
    counts = report["e2"]["counts"]
    for target in ("referans", "KALDI", "BIRAKTI"):
        assert counts[target]["train"]["n"] > 0
    assert set(report["e1"]["results"]) == set(SET_GROUPS)
    assert set(report["e2"]["targets"]["KALDI"]["results"]) == set(ek.E2_SETS)
    assert report["group_of"] == GROUP_OF


# --- E3 ---------------------------------------------------------------------
def _raw_tables() -> tuple[dict, pd.DataFrame]:
    students = [1, 2, 3, 4]
    tables = {
        "studentInfo": pd.DataFrame(
            {
                "code_module": ["AAA"] * 4,
                "code_presentation": ["2013J"] * 4,
                "id_student": students,
                "final_result": ["Pass", "Fail", "Withdrawn", "Distinction"],
            }
        ),
        "studentRegistration": pd.DataFrame(
            {
                "code_module": ["AAA"] * 4,
                "code_presentation": ["2013J"] * 4,
                "id_student": students,
                "date_registration": [-10, -5, 0, 3],
                "date_unregistration": [np.nan, 20.0, 100.0, np.nan],
            }
        ),
        "assessments": pd.DataFrame(
            {
                "code_module": ["AAA", "AAA"],
                "code_presentation": ["2013J", "2013J"],
                "id_assessment": [1, 2],
                "assessment_type": ["TMA", "TMA"],
                "date": [20, 100],
                "weight": [10.0, 20.0],
            }
        ),
        "studentAssessment": pd.DataFrame(
            {
                "id_assessment": [1, 1, 2],
                "id_student": [1, 3, 1],
                "date_submitted": [19, 22, 99],
                "is_banked": [0, 0, 0],
                "score": [80.0, 50.0, 70.0],
            }
        ),
    }
    daily = pd.DataFrame(
        {
            "code_module": ["AAA", "AAA", "AAA"],
            "code_presentation": ["2013J", "2013J", "2013J"],
            "id_student": [1, 1, 4],
            "date": [5, 30, 100],
            "activity_type": ["forumng", "homepage", "forumng"],
            "sum_click": [10, 4, 7],
            "n_rows": [2, 1, 1],
        }
    )
    return tables, daily


def test_build_features_cutoff_default_is_60_and_cutoff_changes_the_sample():
    from data_science.oulad.dataset import CUTOFF_DAY, build_features

    tables, daily = _raw_tables()
    assert CUTOFF_DAY == 60
    default = build_features(tables, daily)
    pd.testing.assert_frame_equal(default, build_features(tables, daily, cutoff=60))
    sizes = {cutoff: build_features(tables, daily, cutoff=cutoff) for cutoff in (14, 60, 120)}
    assert sorted(sizes[14]["id_student"]) == [1, 2, 3, 4]
    assert sorted(sizes[60]["id_student"]) == [1, 3, 4]
    assert sorted(sizes[120]["id_student"]) == [1, 4]
    # 120. günde kayıtlı olanlar her küçük kesimin örnekleminde de vardır.
    for cutoff in (14, 60):
        assert set(sizes[120]["id_student"]) <= set(sizes[cutoff]["id_student"])
    # kesim günü özellikleri de değişir: gün 22 teslimi 14. günde yok, 60. günde var.
    n_submitted_14 = sizes[14].set_index("id_student")["n_submitted"]
    n_submitted_60 = sizes[60].set_index("id_student")["n_submitted"]
    assert int(n_submitted_14.loc[3]) == 0
    assert int(n_submitted_60.loc[3]) == 1


def _e3_builder():
    """Kesim gününe göre örneklem: id % 7 == 0 gün 50'de, id % 11 == 0 gün 100'de kayıt siler."""
    base = _features(_synthetic())
    unregistered = pd.Series(
        np.where(base["id_student"] % 7 == 0, 50.0, np.where(base["id_student"] % 11 == 0, 100.0, np.nan))
    )

    def build(cutoff: int) -> pd.DataFrame:
        frame = base.loc[(unregistered.isna() | (unregistered >= cutoff)).to_numpy()].reset_index(drop=True).copy()
        if cutoff < 30:
            for column in ("n_expected", "n_submitted", "n_unsubmitted", "n_banked"):
                frame[column] = 0
            for column in ("score_mean", "score_weighted_mean", "delay_mean"):
                frame[column] = np.nan
        return frame

    return build


E3_TEST_CUTOFFS = (14, 60, 120)


def test_fixed_cohort_has_the_same_evaluation_rows_at_every_cutoff():
    builder = _e3_builder()
    info = _info(_synthetic())
    frames = {cutoff: ek.e3_frame(builder(cutoff), info) for cutoff in E3_TEST_CUTOFFS}
    cohort = ek.cohort_keys(frames[120])
    evaluation = frames[120]["code_presentation"].isin(["2014B", "2014J"])
    assert len(cohort) == int(evaluation.sum())
    assert {key[1] for key in cohort} == {"2014B", "2014J"}
    assert len(frames[14]) > len(frames[60]) > len(frames[120])
    for cutoff, frame in frames.items():
        mask = ek.cohort_mask(frame, cohort)
        rows = sorted(key for key, member in zip(ek._key_tuples(frame), mask) if member)
        assert rows == sorted(cohort), cutoff
    # kohort dışındaki öğrenci küçük kesimde vardır ama kohortta değildir.
    only_early = set(ek._key_tuples(frames[14])) - set(ek._key_tuples(frames[120]))
    assert only_early
    assert not (only_early & cohort)


def test_exclude_ineligible_drops_only_evaluation_presentations_and_stops_on_mixed():
    def rows(presentation: str, module: str, expected: list[float]) -> pd.DataFrame:
        n = len(expected)
        return pd.DataFrame(
            {
                "code_module": [module] * n,
                "code_presentation": [presentation] * n,
                "n_unsubmitted": [0] * n,
                "score_mean": [50.0] * n,
                "vle_active_days": [3] * n,
                "n_expected": expected,
            }
        )

    frame = pd.concat(
        [
            rows("2013J", "BBB", [0.0, 0.0]),
            rows("2014B", "AAA", [2.0, 2.0]),
            rows("2014B", "BBB", [0.0, 0.0, 0.0]),
            rows("2014J", "AAA", [2.0]),
            rows("2014J", "CCC", [0.0]),
        ],
        ignore_index=True,
    )
    kept, excluded = ek.exclude_ineligible(frame)
    assert sorted((item["code_module"], item["code_presentation"], item["n"]) for item in excluded) == [
        ("BBB", "2014B", 3),
        ("CCC", "2014J", 1),
    ]
    assert len(kept) == len(frame) - 4
    assert int(kept["code_presentation"].eq("2013J").sum()) == 2
    assert not ((kept["code_module"] == "BBB") & (kept["code_presentation"] == "2014B")).any()
    listing = ek.ineligible_listing(frame)
    roles = {(item["code_module"], item["code_presentation"]): item["role"] for item in listing}
    assert roles == {("BBB", "2013J"): "train", ("BBB", "2014B"): "validation", ("CCC", "2014J"): "test"}
    mixed = pd.concat([rows("2014J", "AAA", [2.0, 0.0])], ignore_index=True)
    with pytest.raises(ValueError, match="yalniz bir kismi"):
        ek.exclude_ineligible(mixed)


def test_run_target_views_and_empty_periods():
    frame = _synthetic()
    prepared, _ = prepare_frame(_features(frame), _info(frame))
    sets = set_columns(list(prepared.columns))
    chosen = {"GENERAL": sets["GENERAL"]}
    framed = target_frame(prepared, "referans")
    plain = run_target(framed, chosen, ("logreg",), n_boot=5, seed=42)
    mask = framed["id_student"].to_numpy() % 2 == 0
    viewed = run_target(framed, chosen, ("logreg",), n_boot=5, seed=42, eval_masks={"a": None, "b": mask})
    entry = viewed["results"]["GENERAL"]["logreg"]
    # (a) görünümü, görünümsüz çalıştırmayla aynıdır.
    for period in ("validation", "test"):
        assert entry["a"][period] == plain["results"]["GENERAL"]["logreg"][period]
    expected_test = int(np.sum(mask & framed["code_presentation"].eq("2014J").to_numpy()))
    assert entry["b"]["test"]["n"] == expected_test
    assert viewed["paired_vs_general"] == {}

    without_test = framed.loc[~framed["code_presentation"].eq("2014J")].reset_index(drop=True)
    with pytest.raises(ValueError, match="test bos"):
        run_target(without_test, chosen, ("logreg",), n_boot=5, seed=42)
    allowed = run_target(
        without_test, chosen, ("logreg",), n_boot=5, seed=42, allow_empty=True, empty_reason="neden"
    )
    cells = allowed["results"]["GENERAL"]["logreg"]
    assert cells["test"] == {"undefined": True, "reason": "neden"}
    assert "roc_auc" in cells["validation"]


def test_build_e3_on_synthetic_data_and_sixtieth_day_matches_e1(monkeypatch):
    from data_science.oulad import model

    monkeypatch.setattr(model, "HGB_GRID", model.HGB_GRID[:1])
    builder = _e3_builder()
    frame = _synthetic()
    info = _info(frame)
    registration = {"eki.md": {"md5": "c" * 32, "history": [{"md5": "c" * 32, "time": "t"}]}}
    e3 = ek.build_e3(
        builder, info, cutoffs=E3_TEST_CUTOFFS, n_boot=5, seed=42, registration=registration
    )
    assert e3["pre_registration_md5"] == registration
    assert list(e3["cutoff_results"]) == ["14", "60", "120"]
    assert e3["expectations"] == {}
    assert "B8" in e3["expectations_note"]

    cohort_counts = {}
    for cutoff, block in e3["cutoff_results"].items():
        referans = block["targets"]["referans"]["results"]
        assert set(referans) == {"GENERAL", "ETKİNLİK"}
        assert set(block["targets"]["KALDI"]["results"]) == {"GENERAL"}
        assert set(block["targets"]["BIRAKTI"]["results"]) == {"GENERAL"}
        for set_name, models in referans.items():
            own = models["hgb"][ek.VIEW_OWN]
            fixed = models["hgb"][ek.VIEW_COHORT]
            for period in ("validation", "test"):
                assert fixed[period]["n"] <= own[period]["n"]
                cohort_counts.setdefault((set_name, period), set()).add(
                    (fixed[period]["n"], fixed[period]["n_positive"])
                )
    # sabit kohortta değerlendirme satır ve pozitif sayıları kesimden bağımsızdır.
    assert all(len(values) == 1 for values in cohort_counts.values())
    assert e3["cohort"]["n_students"] == sum(e3["cohort"]["n_by_period"].values())

    # Kesime kadar notlu ödevi olmayan modül-dönemler listelenir, dışlanmaz.
    listing_14 = e3["cutoff_results"]["14"]["no_graded_assignment_presentations"]
    assert {item["role"] for item in listing_14} == {"train", "validation", "test"}
    assert len(listing_14) == 9
    listing_60 = e3["cutoff_results"]["60"]["no_graded_assignment_presentations"]
    assert sorted((item["code_module"], item["code_presentation"]) for item in listing_60) == [
        ("GGG", "2014B"),
        ("GGG", "2014J"),
    ]
    own_14 = e3["cutoff_results"]["14"]["targets"]["referans"]["results"]["GENERAL"]["hgb"][ek.VIEW_OWN]
    assert own_14["test"]["n"] == int(
        ek.e3_frame(builder(14), info)["code_presentation"].eq("2014J").sum()
    )

    # İkincil değer: 14. günde notlu ödevi olan modül-dönem kalmaz.
    secondary_14 = e3["cutoff_results"]["14"]["secondary"]
    assert secondary_14["status"] == "tanımsız"
    assert secondary_14["results"] == {}
    assert "tanımsız" in secondary_14["reason"]
    secondary_60 = e3["cutoff_results"]["60"]["secondary"]
    assert secondary_60["status"] == "tanımlı"

    # 60. günün ikincil değeri E1 GENERAL ve ETKİNLİK ile aynıdır.
    prepared, _ = prepare_frame(builder(60), info)
    sets = set_columns(list(prepared.columns))
    e1 = run_target(
        target_frame(prepared, "referans"),
        {name: sets[name] for name in ek.E3_SETS},
        ("hgb",),
        n_boot=5,
        seed=42,
    )
    ek.check_e3_matches_e1(e3, e1)
    for set_name in ek.E3_SETS:
        mine = secondary_60["results"][set_name]["hgb"]
        reference = e1["results"][set_name]["hgb"]
        assert mine["selected"] == reference["selected"]
        for period in ("validation", "test"):
            assert mine[period] == reference[period]

    tampered = copy.deepcopy(e1)
    tampered["results"]["GENERAL"]["hgb"]["test"]["roc_auc"]["estimate"] += 0.01
    with pytest.raises(ValueError, match="ROC AUC"):
        ek.check_e3_matches_e1(e3, tampered)
    changed = copy.deepcopy(e1)
    changed["results"]["ETKİNLİK"]["hgb"]["selected"]["params"]["max_iter"] += 1
    with pytest.raises(ValueError, match="ayari"):
        ek.check_e3_matches_e1(e3, changed)
    with pytest.raises(ValueError, match="kesim 30"):
        ek.check_e3_matches_e1(e3, e1, cutoff=30)


def test_build_e3_stops_on_ungrouped_column_or_missing_cohort_cutoff():
    builder = _e3_builder()
    info = _info(_synthetic())

    def with_new_column(cutoff: int) -> pd.DataFrame:
        frame = builder(cutoff)
        if cutoff == 14:
            frame["vle_click_quiz"] = 0
        return frame

    with pytest.raises(ValueError, match="grup atamasi durdu.*kesim 14"):
        ek.build_e3(with_new_column, info, cutoffs=E3_TEST_CUTOFFS, n_boot=5)
    with pytest.raises(ValueError, match="kohort kesimi"):
        ek.build_e3(builder, info, cutoffs=(14, 60), n_boot=5)


def _e3_auc(general: dict | None = None, activity_14: float = 0.69) -> dict:
    general = general or {14: 0.70, 30: 0.74, 60: 0.78, 90: 0.79, 120: 0.80}
    return {
        period: {
            cutoff: {"GENERAL": value, "ETKİNLİK": activity_14 if cutoff == 14 else 0.60}
            for cutoff, value in general.items()
        }
        for period in ("validation", "test")
    }


def test_b8_b9_b10_hold_on_hand_built_example():
    report = evaluate_expectations(e3_auc=_e3_auc())
    assert list(report) == ["B8", "B9", "B10"]
    for key, block in report.items():
        assert block["result"] == "tuttu", key
        assert block["expectation"] and block["criterion"]
    test = report["B8"]["test"]
    assert [(step["from"], step["to"]) for step in test["steps"]] == [(14, 30), (30, 60), (60, 90), (90, 120)]
    assert test["max_drop"] < 0
    assert math.isclose(report["B9"]["test"]["gain_14_60"], 0.08)
    assert math.isclose(report["B9"]["test"]["gain_60_120"], 0.02)
    assert math.isclose(report["B10"]["test"]["gap"], 0.01)


def test_b8_b9_b10_each_fail_alone():
    cases = {
        "B8": _e3_auc({14: 0.70, 30: 0.74, 60: 0.78, 90: 0.76, 120: 0.80}),
        "B9": _e3_auc({14: 0.70, 30: 0.74, 60: 0.78, 90: 0.79, 120: 0.90}),
        "B10": _e3_auc(activity_14=0.60),
    }
    for failing, auc in cases.items():
        report = evaluate_expectations(e3_auc=auc)
        for key, block in report.items():
            assert block["result"] == ("tutmadı" if key == failing else "tuttu"), (failing, key)


def test_b8_allows_a_drop_up_to_one_hundredth_but_not_more():
    exact = {14: 0.75, 30: 0.7421875, 60: 0.80, 90: 0.81, 120: 0.82}  # düşüş 0,0078125
    assert evaluate_expectations(e3_auc=_e3_auc(exact))["B8"]["result"] == "tuttu"
    larger = {14: 0.75, 30: 0.7265625, 60: 0.80, 90: 0.81, 120: 0.82}  # düşüş 0,0234375
    assert evaluate_expectations(e3_auc=_e3_auc(larger))["B8"]["result"] == "tutmadı"


def test_b10_uses_absolute_closeness():
    report = evaluate_expectations(e3_auc=_e3_auc(activity_14=0.75))
    assert math.isclose(report["B10"]["test"]["gap"], -0.05)
    assert report["B10"]["result"] == "tutmadı"


def test_b8_b9_b10_use_the_same_three_value_decision_rule():
    base = _e3_auc()
    failing_b9 = _e3_auc({14: 0.70, 30: 0.74, 60: 0.78, 90: 0.79, 120: 0.90})
    only_validation = evaluate_expectations(e3_auc={"validation": base["validation"], "test": failing_b9["test"]})
    assert only_validation["B9"]["validation"]["holds"] is True
    assert only_validation["B9"]["test"]["holds"] is False
    assert only_validation["B9"]["result"] == "belirsiz"
    assert only_validation["B8"]["result"] == "tuttu"
    only_test = evaluate_expectations(e3_auc={"validation": failing_b9["validation"], "test": base["test"]})
    assert only_test["B9"]["result"] == "belirsiz"
    both_fail = evaluate_expectations(e3_auc=failing_b9)
    assert both_fail["B9"]["result"] == "tutmadı"


def test_evaluate_expectations_argument_rules_and_missing_e3_values():
    with pytest.raises(ValueError, match="ne hgb_auc ne e3_auc"):
        evaluate_expectations()
    with pytest.raises(ValueError, match="b7 yok"):
        evaluate_expectations(_auc_base())
    missing = _e3_auc()
    missing["test"][14]["ETKİNLİK"] = None
    with pytest.raises(ValueError, match="ROC AUC yok"):
        evaluate_expectations(e3_auc=missing)
    combined = evaluate_expectations(
        {"validation": _auc_base(), "test": _auc_base()},
        {"validation": _hits(), "test": _hits()},
        _e3_auc(),
    )
    assert list(combined) == ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10"]


def test_addendum2_is_written_and_covered_by_the_md5_check():
    text = (ROOT / "docs" / "ek_analizler_on_kayit_eki2.md").read_text(encoding="utf-8")
    assert text.startswith("# Ön kayıt eki 2: E3 dışlama kuralı")
    assert "Bu ek, E3 koşulmadan **önce** yazıldı" in text
    assert "## Sabit kohort" in text
    assert "BBB 2014B" in text
    assert [path.name for path in ek.PRE_REGISTRATION_PATHS] == [
        "ek_analizler_on_kayit.md",
        "ek_analizler_on_kayit_eki.md",
        "ek_analizler_on_kayit_eki2.md",
    ]
    assert ek.E3_CUTOFFS == (14, 30, 60, 90, 120)
