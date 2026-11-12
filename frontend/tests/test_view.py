"""pivot_grades: name satır, subject sütun, grade değer."""

import pandas as pd

from frontend.view import has_duplicate_grades, pivot_grades


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
