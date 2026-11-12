"""Sınıf içi dikkat bayrağı.

Not ortalaması (düşük = riskli) ve mazeretsiz devamsızlık (yüksek = riskli)
için yüzdelik sıra, data_science kullanmadan, ortalama sıra / sonlu gözlem
sayısı olarak hesaplanır. Sıralama skoru ve olasılık döndürülmez.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

_ABSENT = "absent"
_YASAK_ALANLAR = frozenset(
    {
        "score",
        "probability",
        "olasilik",
        "olasılık",
        "rule_score",
        "risk_score",
    }
)


def _alan(row: Any, name: str) -> Any:
    if isinstance(row, Mapping):
        return row.get(name)
    return getattr(row, name, None)


def _sayi(value: Any) -> float:
    if value is None or isinstance(value, bool):
        return math.nan
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    if not math.isfinite(number):
        return math.nan
    return number


def _sonlu(value: float) -> bool:
    return math.isfinite(value)


def _sira_araliklari(
    values: Sequence[float], ascending: bool
) -> list[tuple[float, int, int] | None]:
    """Sonlu her değer için (ortalama sıra, ilk sıra, son sıra).

    Eşit değerler kapladıkları 1 tabanlı sıraları paylaşır. Sonlu olmayanlar None kalır.
    """
    ordered = [index for index, value in enumerate(values) if _sonlu(value)]
    ordered.sort(key=lambda index: values[index], reverse=not ascending)
    spans: list[tuple[float, int, int] | None] = [None] * len(values)
    start = 0
    count = len(ordered)
    while start < count:
        end = start + 1
        while end < count and values[ordered[end]] == values[ordered[start]]:
            end += 1
        lo = start + 1
        hi = end
        average = (lo + hi) / 2.0
        for position in range(start, end):
            spans[ordered[position]] = (average, lo, hi)
        start = end
    return spans


def _ortalama_sira(values: Sequence[float], ascending: bool) -> list[float]:
    """1 tabanlı ortalama sıra. Eşit değerler kapladıkları sıraların ortalamasını alır.

    Sonlu olmayan değerler NaN kalır ve paydadaki gözlem sayısına girmez.
    """
    return [
        span[0] if span is not None else math.nan
        for span in _sira_araliklari(values, ascending)
    ]


def rank_pct(
    values: Sequence[float],
    higher_is_better: bool,
    groups: Sequence[Any] | None = None,
) -> list[float]:
    """Grup içi yüzdelik sıra: ortalama sıra / grupta sonlu gözlem sayısı.

    higher_is_better True iken büyük değerin yüzdeliği büyüktür. NaN NaN kalır.
    """
    numbers = [_sayi(value) for value in values]
    if groups is not None and len(groups) != len(numbers):
        raise ValueError("grup sayısı değer sayısına eşit değil")
    if groups is None:
        return _rank_pct_grup(numbers, higher_is_better)
    buckets: dict[Any, list[int]] = {}
    for index, group in enumerate(groups):
        buckets.setdefault(group, []).append(index)
    out = [math.nan] * len(numbers)
    for indexes in buckets.values():
        part = _rank_pct_grup([numbers[index] for index in indexes], higher_is_better)
        for offset, index in enumerate(indexes):
            out[index] = part[offset]
    return out


def _rank_pct_grup(values: Sequence[float], higher_is_better: bool) -> list[float]:
    ranks = _ortalama_sira(values, ascending=higher_is_better)
    finite = sum(1 for value in values if _sonlu(value))
    if finite == 0:
        return [math.nan] * len(values)
    return [rank / finite if _sonlu(rank) else math.nan for rank in ranks]


_DILLER = frozenset({"tr", "en"})
_ESIT = {"tr": "(eşit)", "en": "(tie)"}


def _sira_metni(lo: int, hi: int, total: int, lang: str) -> str:
    """Tek sıra '1/4'. Eşit aralık '1–2/4 (eşit)' ya da '1–2/4 (tie)'."""
    if lo == hi:
        return f"{lo}/{total}"
    return f"{lo}–{hi}/{total} {_ESIT[lang]}"


def _iki_ondalik(value: float) -> float:
    return float(f"{value:.2f}")


def _gerekce(
    class_name: str,
    flagged: bool,
    grade_average: float | None,
    unexcused_absences: int,
    grade_rank: str | None,
    absence_rank: str,
    sinifta_not_var: bool,
    lang: str,
) -> str:
    if not sinifta_not_var:
        if lang == "en":
            return f"No attention flag was produced because class {class_name} has no grades."
        return f"{class_name} sınıfında not kaydı olmadığı için dikkat bayrağı üretilmedi."
    yok = "none" if lang == "en" else "yok"
    if grade_average is None or grade_rank is None:
        ortalama = yok
        not_sira = yok
    else:
        ortalama = f"{grade_average:.2f}"
        not_sira = grade_rank
    if lang == "en":
        baslik = "Attention flag" if flagged else "No attention flag"
        return (
            f"{baslik}: in class {class_name}, grade average {ortalama} "
            f"(concern rank {not_sira}), unexcused absences {unexcused_absences} "
            f"(concern rank {absence_rank})."
        )
    baslik = "Dikkat bayrağı var" if flagged else "Dikkat bayrağı yok"
    return (
        f"{baslik}: {class_name} sınıfında not ortalaması {ortalama} "
        f"(risk sırası {not_sira}), mazeretsiz devamsızlık {unexcused_absences} "
        f"(risk sırası {absence_rank})."
    )


def assess_risk(
    students: Sequence[Any],
    grades: Sequence[Any],
    attendance: Sequence[Any],
    *,
    lang: str,
) -> list[dict[str, Any]]:
    """Öğrenci, not ve devamsızlık satırlarından sınıf içi dikkat bayrağı üretir.

    Çıktıda sıralama skoru ve olasılık yoktur. Gerekçe ve eşitlik etiketi lang
    ("tr" ya da "en") dilindedir; başka bir değer hata verir.
    """
    if lang not in _DILLER:
        raise ValueError(f"desteklenmeyen dil: {lang!r}")
    grade_lists: dict[int, list[float]] = {}
    for row in grades:
        student_id = _alan(row, "student_id")
        value = _sayi(_alan(row, "grade"))
        if student_id is None or not _sonlu(value):
            continue
        grade_lists.setdefault(int(student_id), []).append(value)

    absence_counts: dict[int, int] = {}
    for row in attendance:
        if str(_alan(row, "status")) != _ABSENT:
            continue
        student_id = _alan(row, "student_id")
        if student_id is None:
            continue
        key = int(student_id)
        absence_counts[key] = absence_counts.get(key, 0) + 1

    prepared: list[dict[str, Any]] = []
    for student in students:
        student_id = _alan(student, "id")
        if student_id is None:
            continue
        key = int(student_id)
        grade_values = grade_lists.get(key, [])
        average = sum(grade_values) / len(grade_values) if grade_values else math.nan
        name = _alan(student, "name")
        prepared.append(
            {
                "student_id": key,
                "name": "" if name is None else str(name),
                "class_name": str(_alan(student, "class_name") or ""),
                "grade_average": average,
                "unexcused_absences": absence_counts.get(key, 0),
            }
        )
    prepared.sort(key=lambda row: (row["class_name"], row["student_id"]))

    groups = [row["class_name"] for row in prepared]
    grade_values = [row["grade_average"] for row in prepared]
    absence_values = [float(row["unexcused_absences"]) for row in prepared]
    grade_pct = rank_pct(grade_values, higher_is_better=False, groups=groups)
    absence_pct = rank_pct(absence_values, higher_is_better=True, groups=groups)

    by_class: dict[str, list[int]] = {}
    for index, class_name in enumerate(groups):
        by_class.setdefault(class_name, []).append(index)

    flagged = [False] * len(prepared)
    grade_ranks: list[str | None] = [None] * len(prepared)
    absence_ranks: list[str] = [""] * len(prepared)
    class_has_grades: dict[str, bool] = {}

    for class_name, indexes in by_class.items():
        class_grades = [grade_values[index] for index in indexes]
        class_absences = [absence_values[index] for index in indexes]
        finite_grades = sum(1 for value in class_grades if _sonlu(value))
        has_grades = finite_grades > 0
        class_has_grades[class_name] = has_grades
        n = len(indexes)
        grade_spans = _sira_araliklari(class_grades, ascending=True)
        absence_spans = _sira_araliklari(class_absences, ascending=False)
        for offset, index in enumerate(indexes):
            grade_span = grade_spans[offset]
            if grade_span is not None:
                grade_ranks[index] = _sira_metni(
                    grade_span[1], grade_span[2], finite_grades, lang
                )
            absence_span = absence_spans[offset]
            if absence_span is not None:
                absence_ranks[index] = _sira_metni(
                    absence_span[1], absence_span[2], n, lang
                )

        if not has_grades or n < 1:
            continue
        k = math.ceil(0.2 * n)
        if k < 1:
            continue
        scores: list[tuple[int, float]] = []
        for index in indexes:
            grade_part = grade_pct[index]
            absence_part = absence_pct[index]
            if not _sonlu(grade_part) or not _sonlu(absence_part):
                continue
            scores.append((index, (grade_part + absence_part) / 2.0))
        if not scores:
            continue
        scores.sort(key=lambda item: item[1], reverse=True)
        threshold = scores[min(k, len(scores)) - 1][1]
        for index, score in scores:
            if score >= threshold:
                flagged[index] = True

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(prepared):
        average = row["grade_average"]
        grade_average = _iki_ondalik(float(average)) if _sonlu(average) else None
        item = {
            "student_id": row["student_id"],
            "name": row["name"],
            "class_name": row["class_name"],
            "flagged": flagged[index],
            "grade_average": grade_average,
            "unexcused_absences": row["unexcused_absences"],
            "grade_rank": grade_ranks[index],
            "absence_rank": absence_ranks[index],
            "reason": _gerekce(
                row["class_name"],
                flagged[index],
                grade_average,
                row["unexcused_absences"],
                grade_ranks[index],
                absence_ranks[index],
                class_has_grades[row["class_name"]],
                lang,
            ),
        }
        if _YASAK_ALANLAR.intersection(item):
            raise RuntimeError("dikkat bayrağı skoru veya olasılığı taşımamalı")
        rows.append(item)
    return rows
