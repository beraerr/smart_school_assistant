"""Dikkat bayrağı: saf fonksiyon, yüzdelik tutarlılığı ve /risk yetkisi."""

import math
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.main import app
from backend.app.services.risk import assess_risk, rank_pct
from backend.tests import mock_veri
from data_science.oulad.relative import _rank_pct

client = TestClient(app)

_ALANLAR = {
    "student_id",
    "name",
    "class_name",
    "flagged",
    "grade_average",
    "unexcused_absences",
    "grade_rank",
    "absence_rank",
    "reason",
}
_YASAK = {
    "score",
    "probability",
    "olasilik",
    "olasılık",
    "rule_score",
    "risk_score",
    "p_score",
    "p_absence",
}


def _ogrenci(student_id: int, class_name: str, name: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=student_id,
        class_name=class_name,
        name=name or f"Ogrenci {student_id}",
    )


def _not(student_id: int, grade: float) -> SimpleNamespace:
    return SimpleNamespace(student_id=student_id, grade=grade)


def _devam(student_id: int, status: str) -> SimpleNamespace:
    return SimpleNamespace(student_id=student_id, status=status)


def _sinif(rows: list[dict], class_name: str) -> list[dict]:
    return [row for row in rows if row["class_name"] == class_name]


def _yapi(rows: list[dict]) -> None:
    assert rows
    for row in rows:
        assert set(row) == _ALANLAR
        assert _YASAK.isdisjoint(row)
        assert isinstance(row["flagged"], bool)
        assert isinstance(row["reason"], str) and row["reason"]
        metin = row["reason"].casefold()
        assert "olasılık" not in row["reason"]
        assert "olasilik" not in metin
        assert "skor" not in metin
        assert "score" not in metin
        assert "probability" not in metin
        assert "karar değildir" in row["reason"]
        if row["grade_average"] is not None:
            assert row["grade_average"] == float(f"{row['grade_average']:.2f}")
        if row["grade_rank"] is not None:
            assert "." not in row["grade_rank"]
            _sira(row["grade_rank"])
        assert "." not in row["absence_rank"]
        _sira(row["absence_rank"])
        if "not kaydı olmadığı için" not in row["reason"]:
            assert f"(risk sırası {row['absence_rank']})" in row["reason"]
            if row["grade_rank"] is not None:
                assert f"(risk sırası {row['grade_rank']})" in row["reason"]


_SIRA = re.compile(r"^(?:(\d+)|(\d+)–(\d+))/(\d+)(?: \(eşit\))?$")


def _sira(label: str) -> tuple[float, int]:
    match = _SIRA.fullmatch(label)
    assert match is not None, label
    total = int(match.group(4))
    if match.group(1) is not None:
        assert "(eşit)" not in label
        return float(match.group(1)), total
    lo = int(match.group(2))
    hi = int(match.group(3))
    assert lo < hi
    assert label.endswith(" (eşit)")
    return (lo + hi) / 2.0, total


def test_ceil_kurali_benzersiz_skorda_tam_sayi() -> None:
    """Eşit skor yokken bayrak sayısı sınıf başına ceil(0.2 × n)."""
    students = []
    grades = []
    for class_name, n in (("9-A", 5), ("10-B", 6)):
        for offset in range(n):
            student_id = len(students) + 1
            students.append(_ogrenci(student_id, class_name))
            grades.append(_not(student_id, 10 + offset * 10))
            if offset == 0:
                grades.append(_not(student_id, 10))
    rows = assess_risk(students, grades, [])
    _yapi(rows)
    assert _sinif(rows, "9-A")[0]["grade_average"] == 10
    for class_name, n in (("9-A", 5), ("10-B", 6)):
        sinif = _sinif(rows, class_name)
        assert len(sinif) == n
        assert sum(row["flagged"] for row in sinif) == math.ceil(0.2 * n)
        en_dusuk = sorted(sinif, key=lambda row: row["grade_average"])
        k = math.ceil(0.2 * n)
        assert [row["flagged"] for row in en_dusuk[:k]] == [True] * k
        assert [row["flagged"] for row in en_dusuk[k:]] == [False] * (n - k)


def test_sinirda_esit_skorlarin_hepsi_bayraklanir() -> None:
    """Kesimdeki skor birden fazla öğrencideyse hepsi bayraklanır."""
    students = [_ogrenci(i, "9-A") for i in range(1, 7)]
    grades = [
        _not(1, 10),
        _not(2, 20),
        _not(3, 20),
        _not(4, 40),
        _not(5, 50),
        _not(6, 60),
    ]
    rows = assess_risk(students, grades, [])
    _yapi(rows)
    k = math.ceil(0.2 * len(rows))
    assert k == 2
    flagged = [row for row in rows if row["flagged"]]
    assert len(flagged) == 3
    assert {row["student_id"] for row in flagged} == {1, 2, 3}

    ayni = [_ogrenci(i, "10-B") for i in range(1, 5)]
    ayni_not = [_not(i, 50) for i in range(1, 5)]
    esit = assess_risk(ayni, ayni_not, [])
    _yapi(esit)
    assert math.ceil(0.2 * len(esit)) == 1
    assert all(row["flagged"] for row in esit)
    assert {row["grade_rank"] for row in esit} == {"1–4/4 (eşit)"}
    assert {row["absence_rank"] for row in esit} == {"1–4/4 (eşit)"}


def test_notsuz_sinifta_bayrak_yok() -> None:
    students = [_ogrenci(i, "9-A") for i in range(1, 5)]
    students.append(_ogrenci(5, "10-B"))
    attendance = [
        _devam(1, "absent"),
        _devam(2, "absent"),
        _devam(3, "absent"),
        _devam(4, "absent"),
        _devam(4, "absent"),
        _devam(5, "absent"),
    ]
    grades = [_not(5, 40)]
    rows = assess_risk(students, grades, attendance)
    _yapi(rows)
    notsuz = _sinif(rows, "9-A")
    assert notsuz
    assert all(row["grade_average"] is None for row in notsuz)
    assert all(row["grade_rank"] is None for row in notsuz)
    assert all(not row["flagged"] for row in notsuz)
    assert all("not kaydı olmadığı için" in row["reason"] for row in notsuz)
    assert _sinif(rows, "10-B")[0]["flagged"] is True


def test_notu_olmayan_ogrenci_sinifta_not_varken_bayraklanmaz() -> None:
    students = [_ogrenci(i, "9-A") for i in range(1, 5)]
    grades = [_not(1, 10), _not(2, 20), _not(3, 30)]
    attendance = [_devam(4, "absent") for _ in range(8)]
    rows = assess_risk(students, grades, attendance)
    _yapi(rows)
    notsuz = next(row for row in rows if row["student_id"] == 4)
    assert notsuz["grade_average"] is None
    assert notsuz["grade_rank"] is None
    assert notsuz["unexcused_absences"] == 8
    assert notsuz["absence_rank"] == "1/4"
    assert notsuz["flagged"] is False
    assert sum(row["flagged"] for row in rows) == 1
    assert next(row for row in rows if row["student_id"] == 1)["flagged"] is True


def test_excused_ve_present_sayilmaz() -> None:
    students = [_ogrenci(1, "9-A"), _ogrenci(2, "9-A"), _ogrenci(3, "9-A")]
    grades = [_not(1, 50), _not(2, 50), _not(3, 50)]
    attendance = [
        _devam(1, "absent"),
        _devam(1, "absent"),
        _devam(1, "excused"),
        _devam(1, "present"),
        _devam(1, "EXCUSED"),
        _devam(2, "absent"),
        _devam(2, "absent"),
        _devam(3, "excused"),
        _devam(3, "excused"),
        _devam(3, "present"),
    ]
    rows = assess_risk(students, grades, attendance)
    _yapi(rows)
    by_id = {row["student_id"]: row for row in rows}
    assert by_id[1]["unexcused_absences"] == 2
    assert by_id[2]["unexcused_absences"] == 2
    assert by_id[3]["unexcused_absences"] == 0
    assert by_id[1]["absence_rank"] == by_id[2]["absence_rank"] == "1–2/3 (eşit)"
    assert by_id[3]["absence_rank"] == "3/3"
    assert "1–2/3 (eşit)" in by_id[1]["reason"]


def test_ciktida_skor_ve_olasilik_yok() -> None:
    rows = assess_risk([_ogrenci(1, "9-A")], [_not(1, 15)], [_devam(1, "absent")])
    _yapi(rows)
    assert rows[0]["flagged"] is True
    assert "Dikkat bayrağı var" in rows[0]["reason"]


def test_esit_sira_aralik_olarak_yazilir() -> None:
    """Eşit sıra ortalama yerine kapladığı aralığı yazar; tek sıra düz kalır."""
    students = [_ogrenci(i, "9-A") for i in range(1, 5)]
    grades = [_not(1, 10), _not(2, 10), _not(3, 10), _not(4, 40)]
    attendance = [
        _devam(1, "absent"),
        _devam(1, "absent"),
        _devam(2, "absent"),
        _devam(2, "absent"),
    ]
    rows = assess_risk(students, grades, attendance)
    _yapi(rows)
    by_id = {row["student_id"]: row for row in rows}
    assert by_id[1]["grade_rank"] == "1–3/4 (eşit)"
    assert by_id[2]["grade_rank"] == "1–3/4 (eşit)"
    assert by_id[3]["grade_rank"] == "1–3/4 (eşit)"
    assert by_id[4]["grade_rank"] == "4/4"
    assert by_id[1]["absence_rank"] == "1–2/4 (eşit)"
    assert by_id[2]["absence_rank"] == "1–2/4 (eşit)"
    assert by_id[3]["absence_rank"] == "3–4/4 (eşit)"
    assert by_id[4]["absence_rank"] == "3–4/4 (eşit)"
    assert "1.5/4" not in by_id[1]["reason"]
    assert "2/4" not in by_id[1]["grade_rank"]
    assert "(risk sırası 1–3/4 (eşit))" in by_id[1]["reason"]
    assert "(risk sırası 1–2/4 (eşit))" in by_id[1]["reason"]
    assert "(risk sırası 3–4/4 (eşit))" in by_id[3]["reason"]
    assert "(risk sırası 4/4)" in by_id[4]["reason"]


def test_not_ortalamasi_iki_ondalik_bayragi_degistirmez() -> None:
    """Gösterilen ortalama 2 ondalıktır. Bayrak ham ortalamaya göre kalır."""
    students = [_ogrenci(i, "9-A") for i in range(1, 6)]
    grades = [
        _not(1, 10.001),
        _not(2, 10.004),
        _not(3, 50),
        _not(4, 60),
        _not(5, 70),
    ]
    rows = assess_risk(students, grades, [])
    _yapi(rows)
    by_id = {row["student_id"]: row for row in rows}
    assert by_id[1]["grade_average"] == 10.0
    assert by_id[2]["grade_average"] == 10.0
    assert by_id[1]["grade_rank"] == "1/5"
    assert by_id[2]["grade_rank"] == "2/5"
    assert by_id[1]["flagged"] is True
    assert by_id[2]["flagged"] is False
    assert sum(row["flagged"] for row in rows) == 1
    assert "10.00" in by_id[1]["reason"]
    assert "10.00" in by_id[2]["reason"]


def test_yuzdelik_sira_relative_ile_ayni() -> None:
    values = [10.0, 30.0, 30.0, 50.0, 20.0, float("nan"), 5.0, 5.0, 80.0]
    groups = np.array(["9-A", "9-A", "9-A", "9-A", "9-A", "9-A", "10-B", "10-B", "10-B"])
    for higher in (True, False):
        expected = _rank_pct(np.asarray(values, dtype=np.float64), groups, higher)
        got = np.asarray(rank_pct(values, higher_is_better=higher, groups=groups.tolist()))
        assert np.allclose(got, expected, equal_nan=True)

    students = [_ogrenci(i + 1, groups[i]) for i in range(len(values))]
    grades = [
        _not(i + 1, values[i]) for i in range(len(values)) if math.isfinite(values[i])
    ]
    absences = [0, 2, 2, 4, 1, 7, 1, 3, 3]
    attendance = [
        _devam(i + 1, "absent")
        for i, count in enumerate(absences)
        for _ in range(count)
    ]
    rows = assess_risk(students, grades, attendance)
    rows.sort(key=lambda row: row["student_id"])
    grade_input = [values[i] for i in range(len(values))]
    absence_input = [float(count) for count in absences]
    grade_expected = _rank_pct(
        np.asarray(grade_input, dtype=np.float64), groups, higher_is_better=False
    )
    absence_expected = _rank_pct(
        np.asarray(absence_input, dtype=np.float64), groups, higher_is_better=True
    )
    for index, row in enumerate(rows):
        if math.isnan(grade_expected[index]):
            assert row["grade_rank"] is None
        else:
            rank, total = _sira(row["grade_rank"])
            assert total == sum(
                1
                for other, group in zip(grade_input, groups)
                if group == groups[index] and math.isfinite(other)
            )
            assert math.isclose((total + 1 - rank) / total, float(grade_expected[index]))
        rank, total = _sira(row["absence_rank"])
        assert total == sum(1 for group in groups if group == groups[index])
        assert math.isclose((total + 1 - rank) / total, float(absence_expected[index]))


def _giris(username: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _risk(token: str, class_name: str | None = None):
    params = {} if class_name is None else {"class_name": class_name}
    return client.get(
        "/risk",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
    )


def _bayrak_yapisi(rows: list[dict]) -> None:
    gruplar: dict[str, list[dict]] = {}
    for row in rows:
        assert set(row) == _ALANLAR
        assert _YASAK.isdisjoint(row)
        assert isinstance(row["flagged"], bool)
        gruplar.setdefault(row["class_name"], []).append(row)
    for sinif in gruplar.values():
        n = len(sinif)
        with_grade = [row for row in sinif if row["grade_average"] is not None]
        flagged = sum(row["flagged"] for row in sinif)
        assert all(not row["flagged"] for row in sinif if row["grade_average"] is None)
        if not with_grade:
            assert flagged == 0
        else:
            k = math.ceil(0.2 * n)
            if len(with_grade) <= k:
                assert flagged == len(with_grade)
            else:
                assert k <= flagged <= len(with_grade)
        for row in with_grade:
            _rank, total = _sira(row["grade_rank"])
            assert total == len(with_grade)
        for row in sinif:
            _rank, total = _sira(row["absence_rank"])
            assert total == n
        if with_grade:
            for left in with_grade:
                for right in with_grade:
                    if left["grade_average"] < right["grade_average"]:
                        assert _sira(left["grade_rank"])[0] < _sira(right["grade_rank"])[0]


def test_risk_principal_tum_siniflar_teacher_yalniz_kendi_sinifi() -> None:
    principal = _giris("principal", "admin123")
    teacher_login = client.post(
        "/auth/login",
        json={"username": "teacher1", "password": "teacher123"},
    )
    assert teacher_login.status_code == 200
    teacher_body = teacher_login.json()
    teacher_class = teacher_body["user"]["related_class"]
    teacher = teacher_body["access_token"]

    principal_rows = _risk(principal).json()
    teacher_rows = _risk(teacher).json()
    principal_classes = {row["class_name"] for row in principal_rows}
    teacher_classes = {row["class_name"] for row in teacher_rows}
    assert principal_classes == set(mock_veri.siniflar())
    assert teacher_classes == {teacher_class}
    assert {row["student_id"] for row in teacher_rows} == {
        row["student_id"]
        for row in principal_rows
        if row["class_name"] == teacher_class
    }
    _bayrak_yapisi(principal_rows)
    _bayrak_yapisi(teacher_rows)

    filtre = _risk(principal, class_name=teacher_class)
    assert filtre.status_code == 200
    assert {row["class_name"] for row in filtre.json()} == {teacher_class}

    diger = next(name for name in principal_classes if name != teacher_class)
    baska = _risk(teacher, class_name=diger)
    assert baska.status_code == 200
    assert baska.json() == []


@pytest.mark.parametrize(
    ("username", "password"),
    [("parent1", "parent123"), ("student1", "student123")],
)
def test_risk_parent_ve_student_403(username: str, password: str) -> None:
    token = _giris(username, password)
    response = _risk(token)
    assert response.status_code == 403
