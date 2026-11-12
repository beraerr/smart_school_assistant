"""Sentetik studentVle parçaları. Ağ yok."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_science.oulad.load import load_table, read_typed_csv
from data_science.oulad.vle import (
    GROUP_COLUMNS,
    STUDENT_VLE_DTYPES,
    aggregate_student_vle,
    write_student_vle_daily,
)


def _write(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


def _raw_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "oulad"
    _write(
        raw,
        "vle.csv",
        '"id_site","code_module","code_presentation","activity_type","week_from","week_to"\n'
        '"10","AAA","2013J","forumng","1","1"\n'
        '"11","AAA","2013J","?","?","?"\n'
        '"12","BBB","2013J","resource","",""\n',
    )
    _write(
        raw,
        "studentVle.csv",
        '"code_module","code_presentation","id_student","id_site","date","sum_click"\n'
        '"AAA","2013J","1","10","-5","1"\n'
        '"AAA","2013J","1","10","-5","4"\n'
        '"AAA","2013J","1","11","0","3"\n'
        '"AAA","2013J","1","10","-5","2"\n'
        '"BBB","2013J","2","12","1","?"\n'
        '"AAA","2013J","1","10","0","7"\n',
    )
    return raw


def _sort(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in ("code_module", "code_presentation", "activity_type"):
        out[column] = out[column].astype("string")
    out["id_student"] = pd.to_numeric(out["id_student"]).astype("int64")
    out["date"] = pd.to_numeric(out["date"]).astype("Int64")
    out["sum_click"] = pd.to_numeric(out["sum_click"]).astype("Int64")
    out["n_rows"] = pd.to_numeric(out["n_rows"]).astype("int64")
    return out.sort_values(list(GROUP_COLUMNS), kind="mergesort", na_position="last").reset_index(
        drop=True
    )


def test_chunked_sum_matches_single_groupby(tmp_path: Path):
    raw = _raw_dir(tmp_path)
    vle = load_table("vle", raw)
    source = read_typed_csv(raw / "studentVle.csv", STUDENT_VLE_DTYPES)
    chunked = aggregate_student_vle(raw / "studentVle.csv", vle, chunksize=2)
    merged = source.merge(vle.loc[:, ["id_site", "activity_type"]], on="id_site", how="left")
    expected = (
        merged.groupby(list(GROUP_COLUMNS), dropna=False, sort=False)
        .agg(sum_click=("sum_click", "sum"), n_rows=("id_student", "size"))
        .reset_index()
    )
    pd.testing.assert_frame_equal(_sort(chunked), _sort(expected))

    split = chunked.loc[
        (chunked["code_module"] == "AAA")
        & (chunked["id_student"] == 1)
        & (chunked["date"] == -5)
    ]
    assert len(split) == 1
    assert split["activity_type"].iloc[0] == "forumng"
    assert int(split["sum_click"].iloc[0]) == 7
    assert int(split["n_rows"].iloc[0]) == 3
    assert (chunked["date"] < 0).any()
    assert int(chunked["n_rows"].sum()) == len(source)
    assert int(chunked["sum_click"].sum()) == int(source["sum_click"].sum())

    unknown = chunked.loc[chunked["id_student"] == 1].loc[lambda frame: frame["date"] == 0]
    missing_activity = unknown.loc[unknown["activity_type"].isna()]
    assert len(missing_activity) == 1
    assert int(missing_activity["sum_click"].iloc[0]) == 3
    assert pd.api.types.is_numeric_dtype(chunked["date"])
    assert pd.api.types.is_numeric_dtype(chunked["sum_click"])
    assert pd.api.types.is_integer_dtype(chunked["id_student"])
    assert pd.api.types.is_string_dtype(vle["activity_type"])
    assert pd.isna(vle.loc[vle["id_site"] == 11, "activity_type"]).all()

    dest = tmp_path / "student_vle_daily.parquet"
    write_student_vle_daily(raw, chunksize=2, dest=dest)
    daily = pd.read_parquet(dest, engine="pyarrow")
    assert int(daily["n_rows"].sum()) == len(source)
    assert int(daily["sum_click"].sum()) == int(source["sum_click"].sum())


def test_activity_type_join_keeps_question_mark_clicks(tmp_path: Path):
    raw = _raw_dir(tmp_path)
    vle = load_table("vle", raw)
    frame = aggregate_student_vle(raw / "studentVle.csv", vle, chunksize=2)
    row = frame.loc[frame["id_student"] == 2].iloc[0]
    assert row["activity_type"] == "resource"
    assert pd.isna(row["sum_click"]) or int(row["sum_click"]) == 0
    assert int(row["n_rows"]) == 1
    assert pd.api.types.is_numeric_dtype(frame["sum_click"])
