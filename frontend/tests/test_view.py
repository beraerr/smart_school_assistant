"""pivot_grades: name satır, subject sütun, grade değer."""

import pandas as pd

from frontend.view import (
    AMBER_BG,
    AMBER_TEXT,
    bayrak_stili,
    has_duplicate_grades,
    pivot_grades,
    risk_filtre,
    risk_kart_html,
    risk_kartlari,
    risk_siniflari,
    risk_stili,
    risk_tablosu,
)

_BASLIK = {
    "student": "Öğrenci",
    "class_name": "Sınıf",
    "grade_average": "Not ortalaması",
    "absences": "Mazeretsiz devamsızlık",
    "grade_rank": "Not sırası",
    "absence_rank": "Devamsızlık sırası",
    "flag": "Bayrak",
}


def test_pivot_grades() -> None:
    df = pd.DataFrame(
        [
            {"name": "Ali", "subject": "Matematik", "grade": 90},
            {"name": "Ali", "subject": "Fen", "grade": 80},
            {"name": "Ayşe", "subject": "Matematik", "grade": 70},
            {"name": "Ayşe", "subject": "Fen", "grade": 85},
        ]
    )
    tablo = pivot_grades(df)
    assert list(tablo.index) == ["Ali", "Ayşe"]
    assert set(tablo.columns) == {"Fen", "Matematik"}
    assert tablo.loc["Ali", "Matematik"] == 90
    assert tablo.loc["Ali", "Fen"] == 80
    assert tablo.loc["Ayşe", "Matematik"] == 70
    assert tablo.loc["Ayşe", "Fen"] == 85
    assert list(df.columns) == ["name", "subject", "grade"]


def test_farkli_tarihler_ayri_satir_kalir() -> None:
    df = pd.DataFrame(
        [
            {"name": "Ali", "subject": "Matematik", "date": "2024-01-15", "grade": 90},
            {"name": "Ali", "subject": "Matematik", "date": "2024-02-15", "grade": 70},
        ]
    )
    tablo = pivot_grades(df)
    assert tablo.loc[("Ali", "2024-01-15"), "Matematik"] == 90
    assert tablo.loc[("Ali", "2024-02-15"), "Matematik"] == 70
    assert list(tablo.index) == [("Ali", "2024-01-15"), ("Ali", "2024-02-15")]
    assert 80 not in set(tablo["Matematik"])
    assert not has_duplicate_grades(df)


def test_ayni_tarihte_birden_fazla_not() -> None:
    df = pd.DataFrame(
        [
            {"name": "Ali", "subject": "Matematik", "date": "2024-01-15", "grade": 90},
            {"name": "Ali", "subject": "Matematik", "date": "2024-01-15", "grade": 70},
        ]
    )
    assert has_duplicate_grades(df)
    tablo = pivot_grades(df)
    assert tablo.loc[("Ali", "2024-01-15"), "Matematik"] == 90


def test_risk_tablosu_bayrakli_ustte_ve_amber() -> None:
    rows = [
        {
            "student_id": 1,
            "name": "Ayşe Demir",
            "class_name": "9-A",
            "flagged": False,
            "grade_average": 80,
            "unexcused_absences": 0,
            "grade_rank": "2/2",
            "absence_rank": "2/2",
            "reason": "Dikkat bayrağı yok.",
            "score": 0.9,
            "probability": 0.4,
        },
        {
            "student_id": 2,
            "name": "Ali Yılmaz",
            "class_name": "10-B",
            "flagged": True,
            "grade_average": 10.5,
            "unexcused_absences": 4,
            "grade_rank": "1/2",
            "absence_rank": "1–2/2 (eşit)",
            "reason": "Dikkat bayrağı var.",
        },
        {
            "student_id": 3,
            "name": "Can Kaya",
            "class_name": "9-A",
            "flagged": True,
            "grade_average": None,
            "unexcused_absences": 1,
            "grade_rank": None,
            "absence_rank": "1/2",
            "reason": "Dikkat bayrağı var.",
        },
    ]
    tablo = risk_tablosu(rows, _BASLIK, "Dikkat")
    assert list(tablo.columns) == [
        "Öğrenci",
        "Sınıf",
        "Not ortalaması",
        "Mazeretsiz devamsızlık",
        "Not sırası",
        "Devamsızlık sırası",
        "Bayrak",
    ]
    assert list(tablo["Öğrenci"]) == ["Ali Yılmaz", "Can Kaya", "Ayşe Demir"]
    assert list(tablo["Bayrak"]) == ["Dikkat", "Dikkat", ""]
    assert tablo["Not ortalaması"].dtype.kind == "f"
    assert tablo["Not ortalaması"].iloc[0] == 10.5
    assert pd.isna(tablo["Not ortalaması"].iloc[1])
    assert tablo["Not ortalaması"].iloc[2] == 80
    assert "Gerekçe" not in tablo.columns
    assert "reason" not in tablo.columns
    assert "score" not in tablo.columns
    assert "probability" not in tablo.columns
    assert "student_id" not in tablo.columns
    kartlar = risk_kartlari(rows)
    assert [kart["name"] for kart in kartlar] == ["Ali Yılmaz", "Can Kaya"]
    assert kartlar[0]["class_name"] == "10-B"
    assert kartlar[0]["reason"] == "Dikkat bayrağı var."
    assert kartlar[1]["reason"] == "Dikkat bayrağı var."
    kart_html = risk_kart_html(
        {"name": "<Ali>", "class_name": "10-B", "reason": "not 10.50 & sıra"}
    )
    assert "border-left: 4px solid #8A5200" in kart_html
    assert AMBER_BG in kart_html
    assert AMBER_TEXT in kart_html
    assert "&lt;Ali&gt;" in kart_html
    assert "<Ali>" not in kart_html
    assert "not 10.50 &amp; sıra" in kart_html
    assert "red" not in kart_html.casefold()
    assert "#ff0000" not in kart_html.casefold()
    assert risk_kartlari([{**rows[0], "flagged": False}]) == []
    assert bayrak_stili("Dikkat", "Dikkat") == (
        f"background-color: {AMBER_BG}; color: {AMBER_TEXT}; font-weight: 600"
    )
    assert AMBER_BG == "#FFF3E0"
    assert AMBER_TEXT == "#8A5200"
    assert bayrak_stili("", "Dikkat") == ""
    html = risk_stili(tablo, "Bayrak", "Dikkat").to_html().casefold()
    assert AMBER_BG.casefold() in html
    assert AMBER_TEXT.casefold() in html
    assert "red" not in html
    assert "#ff0000" not in html
    assert risk_siniflari(rows) == ["10-B", "9-A"]
    assert [row["name"] for row in risk_filtre(rows, "9-A")] == ["Ayşe Demir", "Can Kaya"]
    assert [row["name"] for row in risk_filtre(rows, "")] == [
        "Ayşe Demir",
        "Ali Yılmaz",
        "Can Kaya",
    ]
