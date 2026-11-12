"""pivot_grades: öğrenci satır, ders sütun, hücrede o dersin bütün notları. Risk tablosu yardımcıları."""

import pandas as pd

from frontend.view import (
    AMBER_BG,
    AMBER_TEXT,
    bayrak_stili,
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


def test_tarihsiz_tek_not_baslik_yalniz_ders() -> None:
    df = pd.DataFrame(
        [
            {"name": "Ali", "subject": "Matematik", "grade": 90},
            {"name": "Ali", "subject": "Fen", "grade": 80},
            {"name": "Ayşe", "subject": "Matematik", "grade": 70},
            {"name": "Ayşe", "subject": "Fen", "grade": 85.5},
        ]
    )
    tablo, numarali = pivot_grades(df)
    assert numarali is False
    assert list(tablo.columns) == ["name", "Fen", "Matematik"]
    assert tablo.to_dict("records") == [
        {"name": "Ali", "Fen": "80", "Matematik": "90"},
        {"name": "Ayşe", "Fen": "85.5", "Matematik": "70"},
    ]
    assert list(df.columns) == ["name", "subject", "grade"]


def test_ortak_tarihler_baslikta_ve_tarih_sirasiyla() -> None:
    df = pd.DataFrame(
        [
            {"name": "Ali", "subject": "Fizik", "date": "2026-10-20", "grade": 75.62},
            {"name": "Ali", "subject": "Fizik", "date": "2026-09-29", "grade": 69.9},
            {"name": "Ece", "subject": "Fizik", "date": "2026-09-29", "grade": 76.83},
            {"name": "Ece", "subject": "Fizik", "date": "2026-10-20", "grade": 76.03},
            {"name": "Ali", "subject": "Kimya", "date": "2026-09-28", "grade": 83.33},
            {"name": "Ece", "subject": "Kimya", "date": "2026-09-28", "grade": 74.16},
        ]
    )
    tablo, numarali = pivot_grades(df)
    assert numarali is False
    assert list(tablo.columns) == ["name", "Fizik 29.09", "Fizik 20.10", "Kimya 28.09"]
    assert tablo.to_dict("records") == [
        {"name": "Ali", "Fizik 29.09": "69.9", "Fizik 20.10": "75.62", "Kimya 28.09": "83.33"},
        {"name": "Ece", "Fizik 29.09": "76.83", "Fizik 20.10": "76.03", "Kimya 28.09": "74.16"},
    ]


def test_farkli_tarihlerde_numarali_baslik_ve_eksik_tire() -> None:
    df = pd.DataFrame(
        [
            {"name": "Ali", "subject": "Matematik", "date": "2026-10-15", "grade": 70},
            {"name": "Ali", "subject": "Matematik", "date": "2026-09-15", "grade": 90},
            {"name": "Ece", "subject": "Matematik", "date": "2026-09-16", "grade": 65.28},
        ]
    )
    tablo, numarali = pivot_grades(df)
    assert numarali is True
    assert tablo.to_dict("records") == [
        {"name": "Ali", "Matematik 1": "90", "Matematik 2": "70"},
        {"name": "Ece", "Matematik 1": "65.28", "Matematik 2": "—"},
    ]


def test_ayni_tarihte_iki_not_numarali_ve_ikisi_de_gorunur() -> None:
    df = pd.DataFrame(
        [
            {"name": "Ali", "subject": "Matematik", "date": "2024-01-15", "grade": 90},
            {"name": "Ali", "subject": "Matematik", "date": "2024-01-15", "grade": 70},
        ]
    )
    tablo, numarali = pivot_grades(df)
    assert numarali is True
    assert tablo.to_dict("records") == [{"name": "Ali", "Matematik 1": "90", "Matematik 2": "70"}]


def test_farkli_yillarda_tarih_yil_ile() -> None:
    df = pd.DataFrame(
        [
            {"name": "Ali", "subject": "Tarih", "date": "2025-12-20", "grade": 60},
            {"name": "Ali", "subject": "Tarih", "date": "2026-01-10", "grade": 72},
        ]
    )
    tablo, _ = pivot_grades(df)
    assert list(tablo.columns) == ["name", "Tarih 20.12.2025", "Tarih 10.01.2026"]


def test_sinif_satir_anahtari_ve_notu_olmayan_ders_tire() -> None:
    df = pd.DataFrame(
        [
            {"name": "Ali", "class_name": "9-A", "subject": "Fizik", "grade": 75.3},
            {"name": "Ece", "class_name": "10-B", "subject": "Kimya", "grade": 88},
        ]
    )
    tablo, _ = pivot_grades(df)
    assert list(tablo.columns) == ["class_name", "name", "Fizik", "Kimya"]
    assert tablo.to_dict("records") == [
        {"class_name": "10-B", "name": "Ece", "Fizik": "—", "Kimya": "88"},
        {"class_name": "9-A", "name": "Ali", "Fizik": "75.3", "Kimya": "—"},
    ]


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
