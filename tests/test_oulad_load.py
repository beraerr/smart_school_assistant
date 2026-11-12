"""Sentetik OULAD CSV. Ağ yok."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_science.oulad import download
from data_science.oulad.load import KEY_COLUMNS, SOCIO_COLUMNS, load_tables


def _write(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


def _raw_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "oulad"
    _write(
        raw,
        "courses.csv",
        '"code_module","code_presentation","module_presentation_length"\n'
        '"AAA","2013J","268"\n',
    )
    _write(
        raw,
        "assessments.csv",
        '"code_module","code_presentation","id_assessment","assessment_type","date","weight"\n'
        '"AAA","2013J","1752","TMA","19","10"\n'
        '"AAA","2013J","1753","Exam","?","100"\n',
    )
    _write(
        raw,
        "vle.csv",
        '"id_site","code_module","code_presentation","activity_type","week_from","week_to"\n'
        '"10","AAA","2013J","forumng","1","1"\n'
        '"11","AAA","2013J","?","?","?"\n',
    )
    _write(
        raw,
        "studentInfo.csv",
        '"code_module","code_presentation","id_student","gender","region","highest_education",'
        '"imd_band","age_band","num_of_prev_attempts","studied_credits","disability","final_result"\n'
        '"AAA","2013J","1","M","Scotland","HE Qualification","?","35-55","0","60","N","Pass"\n'
        '"AAA","2013J","2","F","Scotland","A Level or Equivalent","0-10%","0-35","1","60","Y","Fail"\n',
    )
    _write(
        raw,
        "studentRegistration.csv",
        '"code_module","code_presentation","id_student","date_registration","date_unregistration"\n'
        '"AAA","2013J","1","-10","?"\n'
        '"AAA","2013J","2","","-5"\n',
    )
    _write(
        raw,
        "studentAssessment.csv",
        '"id_assessment","id_student","date_submitted","is_banked","score"\n'
        '"1752","1","18","0","78"\n'
        '"1752","2","20","0","?"\n',
    )
    return raw


def test_question_mark_becomes_na_and_dtypes(tmp_path: Path):
    tables = load_tables(_raw_dir(tmp_path))
    assert set(tables) == {
        "courses",
        "assessments",
        "vle",
        "studentInfo",
        "studentRegistration",
        "studentAssessment",
    }
    assert KEY_COLUMNS == (
        "code_module",
        "code_presentation",
        "id_student",
        "id_assessment",
        "id_site",
    )

    info = tables["studentInfo"]
    registration = tables["studentRegistration"]
    assessments = tables["assessments"]
    scores = tables["studentAssessment"]
    vle = tables["vle"]

    assert pd.api.types.is_numeric_dtype(assessments["date"])
    assert pd.api.types.is_numeric_dtype(registration["date_registration"])
    assert pd.api.types.is_numeric_dtype(registration["date_unregistration"])
    assert pd.api.types.is_numeric_dtype(scores["score"])
    assert pd.api.types.is_integer_dtype(info["id_student"])
    assert pd.api.types.is_integer_dtype(scores["id_assessment"])
    assert pd.api.types.is_integer_dtype(vle["id_site"])
    assert pd.api.types.is_string_dtype(info["gender"])

    assert pd.isna(assessments.loc[assessments["id_assessment"] == 1753, "date"]).all()
    assert int(assessments.loc[assessments["id_assessment"] == 1752, "date"].iloc[0]) == 19
    assert pd.isna(registration.loc[registration["id_student"] == 1, "date_unregistration"]).all()
    assert int(registration.loc[registration["id_student"] == 1, "date_registration"].iloc[0]) == -10
    assert pd.isna(registration.loc[registration["id_student"] == 2, "date_registration"]).all()
    assert int(registration.loc[registration["id_student"] == 2, "date_unregistration"].iloc[0]) == -5
    assert pd.isna(scores.loc[scores["id_student"] == 2, "score"]).all()
    assert int(scores.loc[scores["id_student"] == 1, "score"].iloc[0]) == 78
    assert pd.isna(vle.loc[vle["id_site"] == 11, "activity_type"]).all()
    assert pd.isna(vle.loc[vle["id_site"] == 11, "week_from"]).all()

    assert set(SOCIO_COLUMNS) <= set(info.columns)
    assert set(info["gender"].astype(str)) == {"M", "F"}
    assert pd.isna(info.loc[info["id_student"] == 1, "imd_band"]).all()
    assert info.loc[info["id_student"] == 2, "imd_band"].item() == "0-10%"
    assert len(info) == 2


def test_sha256_mismatch_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(download, "RAW_OULAD_DIR", tmp_path)
    for name in download.CSV_NAMES:
        (tmp_path / name).write_bytes(b"a\n")
    archive = tmp_path / download.ZIP_NAME
    archive.write_bytes(b"not-the-archive")
    monkeypatch.setattr(download, "ZIP_SHA256", "0" * 64)

    def _forbid(*args, **kwargs):
        raise AssertionError("ag kullanildi")

    monkeypatch.setattr(download, "_stream_download", _forbid)
    with pytest.raises(RuntimeError, match="beklenen"):
        download.ensure_dataset()

    with pytest.raises(RuntimeError, match="beklenen"):
        download.verify_sha256(archive, "f" * 64)
