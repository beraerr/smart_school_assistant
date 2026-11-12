"""Sorgu tablosunu derse göre sütunlara çevirir. Risk tablosunu sıralar."""

import html
import math
from collections.abc import Mapping, Sequence

import pandas as pd

AMBER_BG = "#FFF3E0"
AMBER_TEXT = "#8A5200"

_RISK_ALANLARI = (
    "student",
    "class_name",
    "grade_average",
    "absences",
    "grade_rank",
    "absence_rank",
    "flag",
)


_BOS_HUCRE = "—"


def _not_metni(value: object) -> str:
    """Notu sonuçtaki değeriyle yazar; tam sayıda ondalık eklemez, yuvarlamaz."""
    if isinstance(value, bool) or value is None:
        return str(value)
    if isinstance(value, (int, float)):
        number = float(value)
        if math.isfinite(number) and number.is_integer():
            return str(int(number))
        return repr(number)
    return str(value)


def _tarih_etiketi(tarihler: pd.Series) -> pd.Series:
    """Sütun başlığı için tarih. Tablodaki tarihler tek yıldaysa gün.ay, değilse gün.ay.yıl."""
    bicim = "%d.%m" if tarihler.dt.year.nunique() <= 1 else "%d.%m.%Y"
    return tarihler.dt.strftime(bicim)


def pivot_grades(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """Öğrenci satır; her ders, sınav başına bir sütun. Hücrede tek not.

    Bir dersteki notlar her öğrencide aynı tarihlere aitse başlık ders ve tarihtir
    ("Fizik 29.09"). Tarih yoksa, tarihler öğrenciler arasında farklıysa ya da bir
    tarih okunamıyorsa başlık ders ve tarih sırasındaki numaradır ("Fizik 1").
    İkinci değer bu numaralı başlıkların kullanılıp kullanılmadığıdır.
    Ortalama ya da başka bir hesap yapılmaz; sonuçtaki her not bir hücrede görünür.
    Sonuçta sınıf varsa sınıf da satır anahtarıdır. Notu olmayan hücre "—" gösterir.
    """
    anahtar = ["class_name", "name"] if "class_name" in df.columns else ["name"]
    calisma = df.copy()
    tarih_var = "date" in calisma.columns
    if tarih_var:
        calisma["_tarih"] = pd.to_datetime(calisma["date"], errors="coerce")
        calisma = calisma.sort_values("_tarih", kind="stable")
    calisma["_not"] = calisma["grade"].map(_not_metni)
    calisma["_sira"] = calisma.groupby([*anahtar, "subject"], sort=False).cumcount() + 1

    numarali = False
    basliklar: dict[tuple[str, int], str] = {}
    for ders, grup in calisma.groupby("subject", sort=False):
        en_cok = int(grup["_sira"].max())
        tarihle = False
        if tarih_var and grup["_tarih"].notna().all():
            diziler = {
                tuple(alt["_tarih"]) for _, alt in grup.groupby(anahtar, sort=False)
            }
            tek_dizi = next(iter(diziler))
            tarihle = len(diziler) == 1 and len(set(tek_dizi)) == len(tek_dizi)
        if tarihle:
            etiketler = _tarih_etiketi(pd.Series(tek_dizi))
            for sira, etiket in enumerate(etiketler, start=1):
                basliklar[(ders, sira)] = f"{ders} {etiket}"
        elif en_cok == 1:
            basliklar[(ders, 1)] = str(ders)
        else:
            numarali = True
            for sira in range(1, en_cok + 1):
                basliklar[(ders, sira)] = f"{ders} {sira}"

    calisma["_baslik"] = [
        basliklar[(ders, sira)] for ders, sira in zip(calisma["subject"], calisma["_sira"])
    ]
    tablo = calisma.pivot(index=anahtar, columns="_baslik", values="_not")
    sirali_basliklar = [
        basliklar[(ders, sira)]
        for ders, sira in sorted(basliklar, key=lambda kayit: (str(kayit[0]), kayit[1]))
    ]
    tablo = (
        tablo[sirali_basliklar]
        .fillna(_BOS_HUCRE)
        .sort_index()
        .reset_index()
        .rename_axis(columns=None)
    )
    return tablo, numarali


def risk_siniflari(rows: Sequence[Mapping]) -> list[str]:
    """Tablodaki sınıf adları, süzgeç listesi için sıralı."""
    return sorted(
        {str(row.get("class_name") or "") for row in rows if row.get("class_name")}
    )


def risk_filtre(rows: Sequence[Mapping], sinif: str) -> list[Mapping]:
    """Boş sınıf tüm satırları bırakır."""
    if not sinif:
        return list(rows)
    return [row for row in rows if row.get("class_name") == sinif]


def _sayi(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _risk_sirala(rows: Sequence[Mapping]) -> list[Mapping]:
    return sorted(
        rows,
        key=lambda row: (
            0 if row.get("flagged") else 1,
            str(row.get("class_name") or ""),
            str(row.get("name") or ""),
            int(row.get("student_id") or 0),
        ),
    )


def risk_kartlari(rows: Sequence[Mapping]) -> list[dict[str, str]]:
    """Bayraklı öğrenciler, tablo ile aynı sırada. Bayrak yoksa liste boştur."""
    kartlar = []
    for row in _risk_sirala(rows):
        if not row.get("flagged"):
            continue
        ad = row.get("name")
        gerekce = row.get("reason")
        kartlar.append(
            {
                "name": "" if ad is None else str(ad),
                "class_name": str(row.get("class_name") or ""),
                "reason": "" if gerekce is None else str(gerekce),
            }
        )
    return kartlar


def risk_kart_html(kart: Mapping[str, str]) -> str:
    """Risk kartını, sol kenarı amber çizgili HTML bloğu olarak üretir; öğrenci adı, sınıf ve gerekçe kaçışlanarak yazılır."""
    return (
        f'<div class="risk-card" style="border-left: 4px solid {AMBER_TEXT}; '
        f"background-color: {AMBER_BG}; color: {AMBER_TEXT}; "
        'padding: 0.75rem 0.95rem; margin-bottom: 0.6rem;">'
        f"<strong>{html.escape(str(kart.get('name') or ''))}</strong>"
        f"<div>{html.escape(str(kart.get('class_name') or ''))}</div>"
        f"<div>{html.escape(str(kart.get('reason') or ''))}</div>"
        "</div>"
    )


def bayrak_stili(deger: object, bayrak_evet: str) -> str:
    """Hücre değeri bayrak değerine eşitse amber hücre stilini, değilse boş stil döndürür."""
    if bayrak_evet and str(deger) == bayrak_evet:
        return f"background-color: {AMBER_BG}; color: {AMBER_TEXT}; font-weight: 600"
    return ""


def risk_tablosu(
    rows: Sequence[Mapping],
    basliklar: Mapping[str, str],
    bayrak_evet: str,
) -> pd.DataFrame:
    """Risk satırlarını bayraklılar üstte olacak biçimde sıralayıp tabloya çevirir; gerekçe sütunu içermez, not ortalaması sayısal tutulur."""
    kayitlar = []
    for row in _risk_sirala(rows):
        not_sirasi = row.get("grade_rank")
        devam_sirasi = row.get("absence_rank")
        ad = row.get("name")
        kayitlar.append(
            {
                basliklar["student"]: "" if ad is None else str(ad),
                basliklar["class_name"]: str(row.get("class_name") or ""),
                basliklar["grade_average"]: _sayi(row.get("grade_average")),
                basliklar["absences"]: int(row.get("unexcused_absences") or 0),
                basliklar["grade_rank"]: "" if not_sirasi is None else str(not_sirasi),
                basliklar["absence_rank"]: "" if devam_sirasi is None else str(devam_sirasi),
                basliklar["flag"]: bayrak_evet if row.get("flagged") else "",
            }
        )
    kolonlar = [basliklar[alan] for alan in _RISK_ALANLARI]
    tablo = pd.DataFrame(kayitlar, columns=kolonlar)
    tablo[basliklar["grade_average"]] = pd.to_numeric(
        tablo[basliklar["grade_average"]], errors="coerce"
    )
    return tablo


def risk_stili(df: pd.DataFrame, bayrak_sutunu: str, bayrak_evet: str):
    """Bayrak sütunundaki dikkat rozetini amber boyar."""
    if df.empty or bayrak_sutunu not in df.columns:
        return df.style

    def boya(sutun):
        return [bayrak_stili(deger, bayrak_evet) for deger in sutun]

    return df.style.apply(boya, subset=[bayrak_sutunu])
