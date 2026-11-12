"""Araştırma sayfasının paketini üretir: frontend/assets/arastirma/arastirma.json.

Belirtim: docs/arastirma_sayfasi_spec.md bölüm 2 ve docs/arastirma_raporu_spec_v2.md
bölüm 2.1 (uci.* eklemeleri; ham UCI verisi data_science/data/raw altından okunur) ve 2.2 (oulad.*
eklemeleri; notebook 02'nin çağırdığı data_science.oulad.eda fonksiyonları). Her sayı data_science
raporlarından okunur; formülle türetilen alanlar burada hesaplanır. Ham sayılar
yuvarlanmaz. OULAD sayıları data_science.oulad içindeki mevcut fonksiyonlarla
hesaplanır; veri diskte yoksa betik durur. 2.3 (model.* ve rule.roc_auc): JSON'daki alanlar
olduğu gibi okunur; yalnızca notebook 03'te satır içi olan tablolar (presentations, base_rate,
hist_rate_distinct_train) data_science.oulad.model_tables fonksiyonlarıyla öznitelik parquet'inden
gelir. "ek" bölümü (belirtimde yok; görev P3 ek analizler) yalnızca ek_metrics.json ve
docs/on_kayit_md5.txt'ten okunur.

Grafik dosyaları (S1b): week10 fig01–fig05 ve week11 fig01–fig07a PNG'leri (TR/EN) olduğu gibi,
notebook 01 ve 02'nin (TR ve EN) image/png çıktıları ayıklanarak frontend/assets/arastirma/figurler/
altına yazılır. Hangi görselin hangi grafik kimliği olduğu aşağıdaki HAFTA_ESLEME ve
NOTEBOOK_ESLEME tablolarında AÇIKÇA yazılıdır; tabloda olmayan ya da tabloda olup bulunamayan
bir görsel varsa betik durur. Paketin `figures.charts` satırları (kimlik, dil, yol, başlık, alt
metin, kaynak, md5) ve `kaynaklar` girişleri aynı tablolardan üretilir. Başlık ve alt metin
week10/week11 için figures.json'dan, notebook görselleri için notebook'taki markdown hücrelerinden
alınır; hiçbiri uydurulmaz (alt metin yoksa `alt` null olur).

Çıktı deterministiktir: anahtar sırası sabit, ensure_ascii=False, indent=1.

Proje kökünden:
    python scripts/arastirma_paketi.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from data_science.config import PASS_GRADE_100, PASS_THRESHOLD_20
from data_science.eda import (
    correlation_matrix_payload,
    g3_histogram,
    g3_zero_by_subject,
    grade_records,
)
from data_science.features import feature_columns
from data_science.load import load_students
from data_science.oulad import PROCESSED_OULAD_DIR, RAW_OULAD_DIR
from data_science.oulad.dataset import (
    CUTOFF_DAY,
    FEATURES_NAME,
    PRESENTATION_ORDER,
    SPLIT_BY_PRESENTATION,
    prepare_sample,
)
from data_science.oulad import ek as oulad_ek
from data_science.oulad import eda as oulad_eda
from data_science.oulad.download import ZIP_SHA256
from data_science.oulad.load import TABLE_FILES, load_tables
from data_science.oulad.rule import FLAG_RATE
from data_science.oulad.model_tables import (
    base_rate_table,
    presentation_counts,
    train_hist_rate_summary,
)
from data_science.oulad.validate import student_vle_facts
from data_science.oulad.vle import DAILY_NAME, STUDENT_VLE_NAME

CIKTI = _PROJECT_ROOT / "frontend" / "assets" / "arastirma" / "arastirma.json"

GIRDILER = {
    "eda_summary": "data_science/reports/eda_summary.json",
    "model_metrics": "data_science/oulad/reports/model_metrics.json",
    "explain": "data_science/oulad/reports/explain.json",
    "rule_metrics": "data_science/oulad/reports/rule_metrics.json",
    "rule2_metrics": "data_science/oulad/reports/rule2_metrics.json",
    "figures_week10": "data_science/oulad/reports/figures/week10/figures.json",
    "figures_week11": "data_science/oulad/reports/figures/week11/figures.json",
    "ek_metrics": "data_science/oulad/reports/ek_metrics.json",
}
# JSON olmayan girdiler: yalnızca okunur, kaynaklar listesinde md5 ile yer alır.
METIN_GIRDILERI = {
    "on_kayit_md5": "docs/on_kayit_md5.txt",
}

TOHUM = 42
ORNEK_BOYUTU = 3000
# Kuralın kullandığı bayrak oranı sabitinin kendisi (kopya değil): hem capacity satır seçimi hem
# paketteki `rule.flag_rate` buradan gelir.
KAPASITE_ORANI = FLAG_RATE


def oulad_ham_veri_var() -> bool:
    """OULAD sayıları için gereken ham dosyalar diskte mi?"""
    names = [*TABLE_FILES.values(), STUDENT_VLE_NAME]
    return all((RAW_OULAD_DIR / name).is_file() for name in names)


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(root: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for name, rel in GIRDILER.items():
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        data[name] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _sources(root: Path) -> list[dict[str, str]]:
    return [{"yol": rel, "md5": _md5(root / rel)} for rel in (*GIRDILER.values(), *METIN_GIRDILERI.values())]


# --- Grafik dosyaları (S1b) -------------------------------------------------------------------

ASSET_KOKU = _PROJECT_ROOT / "frontend" / "assets" / "arastirma"
FIGUR_REL = "figurler"  # ASSET_KOKU'na göre
DILLER = ("tr", "en")
PNG_IMZASI = b"\x89PNG\r\n\x1a\n"

HAFTA_KAYNAK = {
    "week10": "data_science/oulad/reports/figures/week10",
    "week11": "data_science/oulad/reports/figures/week11",
}

# (grafik kimliği, varyant, hafta, figures.json "dosya"). Dosya adı: <dosya>_<dil>.png.
# Varyant: aynı kimliğin birden çok görseli varsa hangisi olduğu (P1: kartlar önce / sonuçlar).
HAFTA_ESLEME: tuple[tuple[str, str | None, str, str], ...] = (
    ("M4", None, "week10", "fig01_roc_egim"),
    ("M6", None, "week10", "fig02_oran_kaymasi"),
    ("M8", None, "week10", "fig03_gorulmemis_ders"),
    ("K1", None, "week10", "fig04_kapasite"),
    ("M9", None, "week10", "fig05_shap"),
    ("R1", None, "week11", "fig01_sinyal_kesinlik"),
    ("X3", None, "week11", "fig02_sinyal_gruplari"),
    ("X1", None, "week11", "fig03_hedef_ayristirma"),
    ("X2", None, "week11", "fig04_kural_yakalama"),
    ("X4", None, "week11", "fig05_erkenlik"),
    ("X5", None, "week11", "fig06_erkenlik_hedef"),
    ("P1", "sonuc", "week11", "fig07_beklentiler"),
    ("P1", "once", "week11", "fig07a_beklentiler_once"),
)

NOTEBOOK_DOSYALARI = {
    "01_uci_eda": {"tr": "01_uci_eda.ipynb", "en": "01_uci_eda_eng.ipynb"},
    "02_oulad_eda": {"tr": "02_oulad_eda.ipynb", "en": "02_oulad_eda_eng.ipynb"},
}


@dataclass(frozen=True)
class NotebookEslemesi:
    """Bir notebook görselinin AÇIK eşlemesi. Hücre sıraları 0 tabanlıdır ve TR ile EN
    notebook'larda aynıdır (ikisinde de aynı yapı; `isaret` her iki dilde hücreyi doğrular).

    hucre: görseli üreten kod hücresi; cikti: o hücredeki image/png çıktılarının sırası.
    isaret: hücre kaynağında geçmesi gereken dize (eşleme yanlışsa betik durur).
    baslik_hucre: başlığın alındığı markdown hücresi (ilk satır, `#` işaretleri atılır).
    alt_hucre: alt metnin alındığı markdown hücresi (varsa başlık satırı atılır).
    grup_baslik_hucre: atıf başlığı görselin kendi başlığı değil, bir grup başlığıysa o hücre.
    """

    notebook: str
    hucre: int
    cikti: int
    kimlik: str
    varyant: str | None
    isaret: str
    baslik_hucre: int
    alt_hucre: int
    grup_baslik_hucre: int | None = None


NOTEBOOK_ESLEME: tuple[NotebookEslemesi, ...] = (
    # Notebook 01 (UCI). Başlık ve alt metin, kod hücresinden hemen önceki markdown hücresindedir.
    NotebookEslemesi("01_uci_eda", 4, 0, "U1", None, "ax.bar(subject, rate", 3, 3),
    NotebookEslemesi("01_uci_eda", 6, 0, "U2", None, "ax.hist(", 5, 5),
    NotebookEslemesi("01_uci_eda", 8, 0, "U3", None, "ax.barh(", 7, 7),
    NotebookEslemesi("01_uci_eda", 9, 0, "U4", None, "ax.imshow(matrix", 7, 7),
    NotebookEslemesi("01_uci_eda", 11, 0, "U5", None, "grade_points(students)", 10, 10),
    NotebookEslemesi("01_uci_eda", 13, 0, "U6", None, "absence_pass_table", 12, 12),
    # Notebook 02 (OULAD). Başlık hücresi koddan önce, alt metin hücresi koddan sonra gelir.
    NotebookEslemesi("02_oulad_eda", 10, 0, "O1", None, "ax.imshow(masked", 9, 11),
    NotebookEslemesi("02_oulad_eda", 13, 0, "O2", None, 'LABELS["scatter_title"]', 12, 14),
    NotebookEslemesi("02_oulad_eda", 16, 0, "O3", None, 'LABELS["slot_title"]', 15, 17),
    NotebookEslemesi(
        "02_oulad_eda", 20, 0, "O4", "n_unsubmitted", 'signal_table(train, "n_unsubmitted"', 19, 21, 18
    ),
    NotebookEslemesi(
        "02_oulad_eda", 23, 0, "O4", "vle_clicks", 'signal_table(train, "vle_clicks"', 22, 24, 18
    ),
    NotebookEslemesi(
        "02_oulad_eda", 26, 0, "O4", "score_mean", 'signal_table(train, "score_mean"', 25, 27, 18
    ),
    NotebookEslemesi(
        "02_oulad_eda", 29, 0, "O4", "score_vs_hist", 'signal_table(train, "score_vs_hist"', 28, 30, 18
    ),
)


def _png_mi(veri: bytes) -> bool:
    return veri[: len(PNG_IMZASI)] == PNG_IMZASI


def _satir_birlestir(deger: Any) -> str:
    return "".join(deger) if isinstance(deger, list) else str(deger)


def notebook_gorselleri(yol: Path) -> dict[tuple[int, int], bytes]:
    """Notebook'taki bütün image/png çıktıları: {(hücre sırası, hücre içi sıra): PNG baytları}.

    Çıktı hangi türde olursa olsun (`display_data`, `execute_result`) `data` altındaki `image/png`
    sayılır. Base64 doğrulanarak çözülür; PNG imzası taşımayan veri hata verir.
    """
    defter = json.loads(yol.read_text(encoding="utf-8"))
    bulunan: dict[tuple[int, int], bytes] = {}
    for sira, hucre in enumerate(defter["cells"]):
        if hucre["cell_type"] != "code":
            continue
        ic_sira = 0
        for cikti in hucre.get("outputs", []):
            veri = cikti.get("data", {})
            if "image/png" not in veri:
                continue
            metin = "".join(_satir_birlestir(veri["image/png"]).split())
            baytlar = base64.b64decode(metin, validate=True)
            if not _png_mi(baytlar):
                raise ValueError(f"{yol.name}: hücre {sira}, çıktı {ic_sira} PNG değil")
            bulunan[(sira, ic_sira)] = baytlar
            ic_sira += 1
    return bulunan


def _markdown(defter: dict[str, Any], sira: int, ad: str) -> str:
    hucre = defter["cells"][sira]
    if hucre["cell_type"] != "markdown":
        raise ValueError(f"{ad}: hücre {sira} markdown değil")
    return _satir_birlestir(hucre["source"])


def _baslik_metni(metin: str, ad: str, sira: int) -> str:
    ilk = metin.lstrip().splitlines()[0] if metin.strip() else ""
    if not ilk.startswith("#"):
        raise ValueError(f"{ad}: hücre {sira} bir başlıkla başlamıyor")
    baslik = ilk.lstrip("#").strip()
    if not baslik:
        raise ValueError(f"{ad}: hücre {sira} başlığı boş")
    return baslik


def _alt_metni(metin: str) -> str | None:
    """Başlık satırı varsa atılır; kalan boşsa None (alt metin eksik; uydurulmaz)."""
    satirlar = metin.strip().splitlines()
    if satirlar and satirlar[0].startswith("#"):
        satirlar = satirlar[1:]
    kalan = "\n".join(satirlar).strip()
    return kalan or None


def _kayit(
    kimlik: str,
    varyant: str | None,
    dil: str,
    yol: str,
    baslik: str,
    alt: str | None,
    atif_basligi: str,
    kaynak: str,
    veri: bytes,
) -> dict[str, Any]:
    return {
        "id": kimlik,
        "variant": varyant,
        "lang": dil,
        "path": yol,
        "title": baslik,
        "alt": alt,
        "cite_title": atif_basligi,
        "source": kaynak,
        "md5": hashlib.md5(veri).hexdigest(),
    }


def _hafta_gorselleri(
    root: Path, kayitlar: dict[str, list[dict[str, Any]]]
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    satirlar: list[dict[str, Any]] = []
    dosyalar: dict[str, bytes] = {}
    for hafta, kaynak_dizini in HAFTA_KAYNAK.items():
        eslenen = {dosya for _, _, h, dosya in HAFTA_ESLEME if h == hafta}
        json_dosyalari = {k["dosya"] for k in kayitlar[hafta]}
        if json_dosyalari != eslenen:
            raise ValueError(
                f"{hafta}/figures.json ile HAFTA_ESLEME ayrışıyor: {sorted(json_dosyalari ^ eslenen)}"
            )
        beklenen = sorted(f"{d}_{dil}.png" for d in eslenen for dil in DILLER)
        diskte = sorted(p.name for p in (root / kaynak_dizini).glob("*.png"))
        if diskte != beklenen:
            raise ValueError(f"{hafta}: eşlemesiz ya da eksik PNG: {sorted(set(diskte) ^ set(beklenen))}")
    for kimlik, varyant, hafta, dosya in HAFTA_ESLEME:
        kayit = next(k for k in kayitlar[hafta] if k["dosya"] == dosya)
        for dil in DILLER:
            baslik, alt = kayit[f"başlık_{dil}"], kayit[f"alt_{dil}"]
            if not isinstance(baslik, str) or not baslik.strip():
                raise ValueError(f"{hafta}/{dosya}: başlık_{dil} boş")
            kaynak = f"{HAFTA_KAYNAK[hafta]}/{dosya}_{dil}.png"
            veri = (root / kaynak).read_bytes()
            if not _png_mi(veri):
                raise ValueError(f"{kaynak} PNG değil")
            yol = f"{FIGUR_REL}/{hafta}/{dosya}_{dil}.png"
            dosyalar[yol] = veri
            satirlar.append(
                _kayit(
                    kimlik, varyant, dil, yol, baslik, (alt or "").strip() or None, baslik, kaynak, veri
                )
            )
    return satirlar, dosyalar


def _notebook_gorselleri_paket(root: Path) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    satirlar: list[dict[str, Any]] = []
    dosyalar: dict[str, bytes] = {}
    # Önce her dil ve notebook için tam doğrulama: eşlemesiz görsel ya da bulunamayan eşleme DURDURUR.
    cozulen: dict[tuple[str, str], tuple[dict[str, Any], dict[tuple[int, int], bytes]]] = {}
    for ad, diller in NOTEBOOK_DOSYALARI.items():
        eslemeler = [e for e in NOTEBOOK_ESLEME if e.notebook == ad]
        for dil, dosya in diller.items():
            yol = root / "notebooks" / dosya
            gorseller = notebook_gorselleri(yol)
            anahtarlar = {(e.hucre, e.cikti) for e in eslemeler}
            if len(anahtarlar) != len(eslemeler):
                raise ValueError(f"{ad}: NOTEBOOK_ESLEME'de yinelenen (hücre, çıktı)")
            if set(gorseller) != anahtarlar:
                raise ValueError(
                    f"{dosya}: eşlemesiz görsel {sorted(set(gorseller) - anahtarlar)}, "
                    f"görselsiz eşleme {sorted(anahtarlar - set(gorseller))}"
                )
            defter = json.loads(yol.read_text(encoding="utf-8"))
            for e in eslemeler:
                kaynak = "".join(defter["cells"][e.hucre]["source"])
                if e.isaret not in kaynak:
                    raise ValueError(f"{dosya}: hücre {e.hucre} kaynağında {e.isaret!r} yok")
            cozulen[(ad, dil)] = (defter, gorseller)
    for e in NOTEBOOK_ESLEME:
        for dil in DILLER:
            defter, gorseller = cozulen[(e.notebook, dil)]
            dosya = NOTEBOOK_DOSYALARI[e.notebook][dil]
            baslik = _baslik_metni(_markdown(defter, e.baslik_hucre, dosya), dosya, e.baslik_hucre)
            alt = _alt_metni(_markdown(defter, e.alt_hucre, dosya))
            atif = (
                baslik
                if e.grup_baslik_hucre is None
                else _baslik_metni(
                    _markdown(defter, e.grup_baslik_hucre, dosya), dosya, e.grup_baslik_hucre
                )
            )
            veri = gorseller[(e.hucre, e.cikti)]
            ek = f"_{e.varyant}" if e.varyant else ""
            yol = f"{FIGUR_REL}/notebook/{e.notebook}_{dil}_{e.kimlik.lower()}{ek}.png"
            dosyalar[yol] = veri
            satirlar.append(
                _kayit(
                    e.kimlik, e.varyant, dil, yol, baslik, alt, atif,
                    f"notebooks/{dosya}#hucre={e.hucre},cikti={e.cikti}", veri,
                )
            )
    return satirlar, dosyalar


def gorseller(
    root: Path, kayitlar: dict[str, list[dict[str, Any]]]
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    """`figures.charts` satırları ve yazılacak dosyalar ({ASSET_KOKU'na göre yol: baytlar})."""
    hafta_satir, hafta_dosya = _hafta_gorselleri(root, kayitlar)
    nb_satir, nb_dosya = _notebook_gorselleri_paket(root)
    ortak = set(hafta_dosya) & set(nb_dosya)
    if ortak:
        raise ValueError(f"çakışan hedef yolu: {sorted(ortak)}")
    return [*hafta_satir, *nb_satir], {**hafta_dosya, **nb_dosya}


def _gorsel_kaynaklari(satirlar: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "yol": f"frontend/assets/arastirma/{s['path']}",
            "md5": s["md5"],
            "kaynak": s["source"],
        }
        for s in satirlar
    ]


def gorselleri_yaz(root: Path = _PROJECT_ROOT) -> int:
    """Görselleri frontend/assets/arastirma/figurler/ altına yazar; yazılan dosya sayısını döner."""
    src = _read(root)
    _, dosyalar = gorseller(root, {"week10": src["figures_week10"], "week11": src["figures_week11"]})
    for yol, veri in dosyalar.items():
        hedef = ASSET_KOKU / yol
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(veri)
    return len(dosyalar)


def _float_or_none(value: Any) -> float | None:
    """Eksik değer (NaN/NA) JSON'da null olur; başka hiçbir değer dönüştürülmez."""
    return None if pd.isna(value) else float(value)


def _oulad_tables(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    vle_rows, vle_cols = oulad_eda.student_vle_shape()
    return [
        {"table": s["table"], "rows": int(s["rows"]), "cols": int(s["cols"])}
        for s in oulad_eda.table_shapes(tables, vle_rows, vle_cols)
    ]


def _oulad_sample(tables: dict[str, pd.DataFrame]) -> dict[str, int]:
    counts = oulad_eda.sample_counts(tables)
    return {
        "cutoff_day": int(counts["cutoff_day"]),
        "rows_before": int(counts["rows_before"]),
        "rows_removed": int(counts["rows_removed"]),
        "rows_kept": int(counts["rows_kept"]),
    }


def _oulad_final_result(tables: dict[str, pd.DataFrame], features: pd.DataFrame) -> list[dict[str, Any]]:
    mapping = oulad_eda.final_result_mapping(features, tables["studentInfo"])
    rows = []
    for row in mapping.itertuples(index=False):
        if row.at_risk_min != row.at_risk_max:
            raise ValueError(f"final_result tek at_risk degerine eslenmiyor: {row.final_result}")
        rows.append({"final_result": str(row.final_result), "n": int(row.n), "at_risk": int(row.at_risk_min)})
    return rows


def _oulad_risk_pivot(features: pd.DataFrame) -> list[dict[str, Any]]:
    """Oranlar notebook'un ısı haritası pivotundan; n, aynı modül-sunum satırının notebook'taki
    sayısından (hist_vs_current_points). Pivotta boş kesişim yazılmaz."""
    pivot = oulad_eda.risk_rate_pivot(features)
    counts = {
        (str(r.code_module), str(r.code_presentation)): int(r.n)
        for r in oulad_eda.hist_vs_current_points(features).itertuples(index=False)
    }
    rows = []
    for module in pivot.index:
        for presentation in pivot.columns:
            rate = pivot.loc[module, presentation]
            if pd.isna(rate):
                continue
            rows.append(
                {
                    "module": str(module),
                    "presentation": str(presentation),
                    "n": counts[(str(module), str(presentation))],
                    "rate": float(rate),
                }
            )
    if {(r["module"], r["presentation"]) for r in rows} != set(counts):
        raise ValueError("risk_pivot ve hist_vs_current modül-sunum kümeleri farklı")
    return rows


def _oulad_hist_vs_current(features: pd.DataFrame) -> list[dict[str, Any]]:
    points = oulad_eda.hist_vs_current_points(features)
    return [
        {
            "module": str(r.code_module),
            "presentation": str(r.code_presentation),
            "n": int(r.n),
            "rate": float(r.at_risk_rate),
            "hist_rate": _float_or_none(r.hist_module_risk_rate),
        }
        for r in points.itertuples(index=False)
    ]


def _oulad_slot_means(tables: dict[str, pd.DataFrame], features: pd.DataFrame) -> list[dict[str, Any]]:
    slot_means = oulad_eda.slot_means_table(tables, features)
    return [
        {
            "module": str(r.code_module),
            "presentation": str(r.code_presentation),
            "assessment_type": str(r.assessment_type),
            "slot": int(r.slot),
            "n": int(r.n),
            "mean_score": float(r.mean_score),
        }
        for r in slot_means.itertuples(index=False)
    ]


def _oulad_signals(features: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    """Yalnız train; dilim sınırları ve etiketleri notebook'taki gibi. Eksik dilimi ayrı satır;
    etiketi TR notebook'taki (LABELS_BY_LANG['tr']['missing'])."""
    train = oulad_eda.train_rows(features)
    missing_label = oulad_eda.LABELS_BY_LANG["tr"]["missing"]
    signals: dict[str, list[dict[str, Any]]] = {}
    for name in oulad_eda.SIGNAL_QUANTILES:
        table = oulad_eda.signal_table(train, name, missing_label)
        signals[name] = [
            {"bin": str(r.bin), "n": int(r.n), "rate": _float_or_none(r.at_risk_rate)}
            for r in table.itertuples(index=False)
        ]
    return signals


def _oulad_data_notes(tables: dict[str, pd.DataFrame], features: pd.DataFrame) -> dict[str, Any]:
    ggg = oulad_eda.ggg_cutoff_summary(features)
    return {
        "ggg": [
            {
                "presentation": str(r.code_presentation),
                "n_rows": int(r.n_rows),
                "n_expected_min": int(r.n_expected_min),
                "n_expected_max": int(r.n_expected_max),
                "score_mean_missing": int(r.score_mean_missing),
                "vle_clicks_positive": int(r.vle_clicks_positive),
            }
            for r in ggg.itertuples(index=False)
        ],
        "bbb_zero_weight": int(oulad_eda.bbb_zero_weight_summary(tables, features)["only_zero_weight_score"]),
    }


def _oulad_feature_map() -> list[dict[str, str]]:
    """Yalnızca model özellikleri: tanımlayıcı ve hedef satırları katalogda kalır, pakete girmez."""
    catalog = oulad_eda.sorted_feature_catalog()
    features = catalog.loc[~catalog["school_tr"].isin(oulad_eda.NON_MODEL_SCHOOL_TR)]
    return [
        {
            "feature": str(r.column),
            "group": str(r.group),
            "school_tr": str(r.school_tr),
            "school_en": str(r.school_en),
        }
        for r in features.itertuples(index=False)
    ]


def oulad_sayilari() -> dict[str, Any]:
    """OULAD ham sayıları: yalnızca data_science.oulad fonksiyonları."""
    if not oulad_ham_veri_var():
        raise FileNotFoundError(f"OULAD ham verisi yok: {RAW_OULAD_DIR}")
    daily_path = PROCESSED_OULAD_DIR / DAILY_NAME
    if not daily_path.is_file():
        raise FileNotFoundError(f"OULAD günlük etkinlik özeti yok: {daily_path}")
    tables = load_tables()
    info = tables["studentInfo"]
    courses = tables["courses"].loc[:, ["code_module", "code_presentation"]].drop_duplicates()
    sample = prepare_sample(info, tables["studentRegistration"], CUTOFF_DAY)
    vle_rows = student_vle_facts(RAW_OULAD_DIR / STUDENT_VLE_NAME)[0]

    split = []
    for part in dict.fromkeys(SPLIT_BY_PRESENTATION.values()):
        presentations = [p for p in PRESENTATION_ORDER if SPLIT_BY_PRESENTATION[p] == part]
        rows = sample.loc[sample["code_presentation"].isin(presentations)]
        split.append(
            {
                "part": part,
                "presentations": presentations,
                "rows": int(len(rows)),
                "risk_rate": float(rows["at_risk"].mean()),
                # Bölümde geçmişi olan satırların payı (0..1); bölüm içinde karışık olabilir.
                "has_history": float(rows["has_history"].mean()),
            }
        )
    features = oulad_eda.load_features(tables)
    return {
        "n_rows_raw": int(len(info)),
        "n_rows_sample": int(len(sample)),
        "n_vle_rows": int(vle_rows),
        "n_courses": int(len(courses)),
        "split": split,
        # Belirtim v2, bölüm 2.2: notebook 02'nin kullandığı data_science.oulad.eda fonksiyonlarıyla.
        "zip_sha256": ZIP_SHA256,
        "tables": _oulad_tables(tables),
        "sample": _oulad_sample(tables),
        "final_result": _oulad_final_result(tables, features),
        "risk_pivot": _oulad_risk_pivot(features),
        "hist_vs_current": _oulad_hist_vs_current(features),
        "slot_means": _oulad_slot_means(tables, features),
        "signals": _oulad_signals(features),
        "data_notes": _oulad_data_notes(tables, features),
        "feature_map": _oulad_feature_map(),
    }


def _uci(eda: dict[str, Any], root: Path) -> dict[str, Any]:
    """UCI bölümü. Sayılar eda_summary.json'dan; v2 eklemeleri (belirtim 2.1) notebook 01'in
    çağırdığı data_science fonksiyonlarıyla ham UCI verisinden hesaplanır."""
    corr = {row["feature"]: row["correlation"] for row in eda["top_abs_correlation_with_g3"]}
    absence = eda["absence"]
    students = load_students(raw_dir=root / "data_science" / "data" / "raw")
    return {
        "total": eda["row_counts"]["total"],
        "mat": eda["row_counts"]["mat"],
        "por": eda["row_counts"]["por"],
        "pass_mat": eda["pass_rate_by_subject"]["mat"],
        "pass_por": eda["pass_rate_by_subject"]["por"],
        "g3_zero": eda["g3_zero_count"],
        "corr_g1": corr["G1"],
        "corr_g2": corr["G2"],
        "corr_failures": corr["failures"],
        "absence": {
            "pearson_all": absence["pearson_all"],
            "pearson_excl": absence["pearson_excl"],
            "spearman_all": absence["spearman_all"],
            "spearman_excl": absence["spearman_excl"],
            "buckets": absence["buckets"],
        },
        "pass_threshold_20": PASS_THRESHOLD_20,
        "pass_grade_100": PASS_GRADE_100,
        "g3_zero_by_subject": g3_zero_by_subject(students),
        "g3_hist": g3_histogram(students),
        "top_corr": eda["top_abs_correlation_with_g3"],
        "corr_matrix": correlation_matrix_payload(students),
        "grades": grade_records(students),
        "feature_sets": {
            "early": feature_columns("early"),
            "midterm": feature_columns("midterm"),
        },
    }


def _test_block(model: dict[str, Any], explain: dict[str, Any]) -> dict[str, Any]:
    cap = [r for r in explain["capacity"]["rows"] if r["flag_rate"] == KAPASITE_ORANI]
    if len(cap) != 1:
        raise ValueError(f"capacity.rows flag_rate={KAPASITE_ORANI}: {len(cap)} satır")
    glob = cap[0]["global"]
    rates = {
        r["code_module"]: r["positive_rate"]
        for r in model["calibration"]["rows"]
        if r["set"] == "GENERAL"
    }
    lowest = min(rates, key=lambda m: (rates[m], m))
    highest = max(rates, key=lambda m: (rates[m], m))
    return {
        "n": glob["n"],
        "n_positive": glob["n_positive"],
        "module_rates": rates,
        "module_rate_min": rates[lowest],
        "module_rate_min_module": lowest,
        "module_rate_max": rates[highest],
        "module_rate_max_module": highest,
    }


def _sets(model: dict[str, Any]) -> dict[str, Any]:
    roc_val: dict[str, dict[str, float]] = {}
    for row in model["validation"]["rows"]:
        roc_val.setdefault(row["set"], {})[row["model"]] = row["roc_auc"]
    roc_test = {
        name: {m: block["roc_auc"] for m, block in models.items()}
        for name, models in model["test_metrics"].items()
    }
    paired = {m: diffs["HISTORY-GENERAL"]["roc_auc"] for m, diffs in model["paired_differences"].items()}

    by_set: dict[str, list[float]] = {}
    for row in model["validation"]["modules"]["rows"]:
        by_set.setdefault(row["set"], []).append(row["roc_auc"])
    within = {
        name: {
            "validation": sum(values) / len(values),
            "test": model["modules"]["mean"][name]["roc_auc"],
        }
        for name, values in by_set.items()
    }
    return {
        "roc_val": roc_val,
        "roc_test": roc_test,
        "paired": {"HISTORY_GENERAL": paired},
        "within_module_mean": within,
    }


def ornek_indeksleri(n: int, size: int = ORNEK_BOYUTU, seed: int = TOHUM) -> list[int]:
    """Yerine koymadan örnek; indeksler artan sırada."""
    rng = np.random.default_rng(seed)
    return sorted(int(i) for i in rng.choice(n, size=size, replace=False))


def _dependence(explain: dict[str, Any]) -> dict[str, Any]:
    features = []
    for item in explain["shap"]["dependence"]:
        values, shap = item["value"], item["shap"]
        if len(values) != len(shap):
            raise ValueError(f"dependence uzunluk uyumsuz: {item['feature']}")
        index = ornek_indeksleri(len(values))
        features.append(
            {
                "feature": item["feature"],
                "n_total": len(values),
                "n_sample": len(index),
                "index": index,
                "value": [values[i] for i in index],
                "shap": [shap[i] for i in index],
            }
        )
    return {"seed": TOHUM, "sample_size": ORNEK_BOYUTU, "features": features}


def _rule(rule: dict[str, Any], rule2: dict[str, Any]) -> dict[str, Any]:
    capture: dict[str, float] = {}
    gap: dict[str, float] = {}
    for period in rule2["periods"]:
        totals = {row["method"]: row for row in period["total"]}
        model_row, rule2_row = totals["general_hgb"], totals["rule2"]
        name = period["presentation"]
        capture[name] = rule2_row["n_hit"] / model_row["n_hit"]
        gap[name] = (model_row["precision"] - rule2_row["precision"]) * 100
    return {
        "periods": rule2["periods"],
        "capture_rule2": capture,
        "gap_rule2": gap,
        "excluded": rule["excluded"],
        # Sınıf içi bayrak oranı (0,20): data_science.oulad.rule.FLAG_RATE'in kendisi.
        "flag_rate": FLAG_RATE,
        # Belirtim v2, bölüm 2.3: rule_metrics.json roc_auc, olduğu gibi.
        "roc_auc": rule["roc_auc"],
    }


# --- Belirtim v2, bölüm 2.3: model.* ---------------------------------------------------------


def model_cercevesi() -> pd.DataFrame:
    """Notebook 03'ün `frame` değişkeni: öznitelik parquet'i (aynı okuma çağrısı)."""
    path = PROCESSED_OULAD_DIR / FEATURES_NAME
    if not path.is_file():
        raise FileNotFoundError(f"OULAD öznitelik dosyası yok: {path}")
    return pd.read_parquet(path, engine="pyarrow")


def _model_presentations(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {"presentation": str(r.code_presentation), "split": str(r.split), "n": int(r.n), "n_positive": int(r.n_positive)}
        for r in presentation_counts(frame).itertuples(index=False)
    ]


def _model_base_rate(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "module": str(r.code_module),
            "n": int(r.n),
            "n_positive": int(r.n_positive),
            "hist_module_risk_rate": _float_or_none(r.hist_module_risk_rate),
            "positive_rate": float(r.positive_rate),
            "test_n_distinct_hist_module_risk_rate": int(r.test_n_distinct_hist_module_risk_rate),
            "train_n": int(r.train_n),
            "train_n_positive": int(r.train_n_positive),
            "train_n_distinct_hist_module_risk_rate": int(r.train_n_distinct_hist_module_risk_rate),
        }
        for r in base_rate_table(frame).itertuples(index=False)
    ]


def _model_module_roc(model: dict[str, Any]) -> list[dict[str, Any]]:
    """Doğrulama: validation.modules.rows (set başına satır). Test: modules.rows'taki set sözlüğü satırlara açılır."""
    rows = [
        {
            "set": r["set"],
            "module": r["code_module"],
            "period": "validation",
            "n": r["n"],
            "n_positive": r["n_positive"],
            "roc_auc": r["roc_auc"],
        }
        for r in model["validation"]["modules"]["rows"]
    ]
    for r in model["modules"]["rows"]:
        for set_name, value in r["roc_auc"].items():
            rows.append(
                {
                    "set": set_name,
                    "module": r["code_module"],
                    "period": "test",
                    "n": r["n"],
                    "n_positive": r["n_positive"],
                    "roc_auc": value,
                }
            )
    return rows


def _model(model: dict[str, Any], frame: pd.DataFrame) -> dict[str, Any]:
    """Yalnızca presentations, base_rate ve hist_rate_distinct_train notebook fonksiyonlarından
    (data_science.oulad.model_tables); gerisi model_metrics.json'dan olduğu gibi."""
    summary = train_hist_rate_summary(frame)
    return {
        "presentations": _model_presentations(frame),
        "selected_params": model["selected_params"],
        "test_metrics": model["test_metrics"],
        "paired": model["paired_differences"],
        "validation_rows": model["validation"]["rows"],
        "module_roc": _model_module_roc(model),
        "base_rate": _model_base_rate(frame),
        "hist_rate_distinct_train": int(summary["n_distinct_hist_module_risk_rate"].iloc[0]),
        "calibration": model["calibration"],
        "lomo": model["lomo"],
        "within_module": model["within_module"],
    }


# --- Ek analizler: ek.* (yalnızca ek_metrics.json ve on_kayit_md5.txt) -----------------------


def _ek_metrics(block: dict[str, Any]) -> dict[str, Any]:
    """Bir değerlendirme bloğu (set × model × dönem). Tanımsız blok 'undefined' ve nedeniyle yazılır;
    'undefined' anahtarı yalnızca tanımsız bloklarda bulunur (bu yüzden .get)."""
    if block.get("undefined") is True:
        return {"undefined": True, "reason": block["reason"]}
    within = block["within_module_20"]
    return {
        "undefined": False,
        "n": block["n"],
        "n_positive": block["n_positive"],
        "roc_auc": block["roc_auc"],
        "module_mean_roc_auc": block["module_mean_roc_auc"]["roc_auc"],
        "n_flagged": within["n_flagged"],
        "n_hit": within["n_hit"],
        "precision_20": within["precision"],
        "recall_20": within["recall"],
    }


def _ek_rows(
    results: dict[str, Any], ident: dict[str, Any], view: str | None = None
) -> list[dict[str, Any]]:
    rows = []
    for set_name, models in results.items():
        for model_name, entry in models.items():
            block = entry if view is None else entry[view]
            for period in oulad_ek.PERIODS:
                rows.append(
                    {**ident, "set": set_name, "model": model_name, "period": period, **_ek_metrics(block[period])}
                )
    return rows


def _ek_paired(paired: dict[str, Any], ident: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for model_name, comparisons in paired.items():
        for comparison, periods in comparisons.items():
            for period in oulad_ek.PERIODS:
                for metric, value in periods[period].items():
                    rows.append(
                        {
                            **ident,
                            "model": model_name,
                            "comparison": comparison,
                            "period": period,
                            "metric": metric,
                            "estimate": value["estimate"],
                            "low": value["low"],
                            "high": value["high"],
                        }
                    )
    return rows


def _ek_e1(src: dict[str, Any]) -> dict[str, Any]:
    e1 = src["e1"]
    return {
        "target": e1["target"],
        "counts": e1["counts"],
        "group_of": src["group_of"],
        "rows": _ek_rows(e1["results"], {}),
        "paired_vs_general": _ek_paired(e1["paired_vs_general"], {}),
    }


def _ek_e2(src: dict[str, Any]) -> dict[str, Any]:
    e2 = src["e2"]
    rows: list[dict[str, Any]] = []
    paired: list[dict[str, Any]] = []
    for target, block in e2["targets"].items():
        rows += _ek_rows(block["results"], {"target": target})
        if "paired_vs_general" in block:  # referans hedefte eşli fark E1'dedir
            paired += _ek_paired(block["paired_vs_general"], {"target": target})
    return {
        "counts": e2["counts"],
        "rows": rows,
        "paired_vs_general": paired,
        "b7_rule2_hits": src["b7_rule2_hits"],
    }


def _ek_e3(src: dict[str, Any]) -> dict[str, Any]:
    e3 = src["e3"]
    cutoffs = [int(key) for key in e3["cutoff_results"]]
    if cutoffs != list(e3["cutoffs"]):
        raise ValueError(f"e3 kesim sırası tutarsız: {cutoffs} != {e3['cutoffs']}")
    rows: list[dict[str, Any]] = []
    counts: list[dict[str, Any]] = []
    info: list[dict[str, Any]] = []
    secondary: list[dict[str, Any]] = []
    for key, block in e3["cutoff_results"].items():
        cutoff = int(key)
        info.append(
            {
                "cutoff": cutoff,
                "n_rows": block["n_rows"],
                "no_graded_assignment_presentations": block["no_graded_assignment_presentations"],
            }
        )
        for target, target_block in block["targets"].items():
            counts.append({"cutoff": cutoff, "target": target, "counts": target_block["counts"]})
            for view in e3["views"]:
                rows += _ek_rows(target_block["results"], {"cutoff": cutoff, "view": view, "target": target}, view=view)
        sec = block["secondary"]
        secondary.append(
            {
                "cutoff": cutoff,
                "definition": sec["definition"],
                "status": sec["status"],
                # 'reason' yalnızca kısmen tanımsız ikincil bloklarda var.
                "reason": sec.get("reason"),
                "excluded_presentations": sec["excluded_presentations"],
                "counts": sec["counts"],
                "rows": _ek_rows(sec["results"], {"cutoff": cutoff}),
            }
        )
    return {
        "label": e3["label"],
        "cutoffs": e3["cutoffs"],
        "views": e3["views"],
        "cohort": e3["cohort"],
        "notes": e3["notes"],
        "cutoff_info": info,
        "counts": counts,
        "rows": rows,
        "secondary": secondary,
    }


def _ek_expectations(src: dict[str, Any]) -> list[dict[str, Any]]:
    """B1–B7 ek_metrics.expectations'ta, B8–B10 e3.expectations'ta durur; kimliğe göre birleştirilir."""
    first, second = src["expectations"], src["e3"]["expectations"]
    if set(first) & set(second):
        raise ValueError(f"beklenti kimlikleri çakışıyor: {sorted(set(first) & set(second))}")
    merged = {**first, **second}
    return [
        {
            "id": key,
            "expectation": merged[key]["expectation"],
            "criterion": merged[key]["criterion"],
            "validation": merged[key]["validation"],
            "test": merged[key]["test"],
            "result": merged[key]["result"],
        }
        for key in sorted(merged, key=lambda name: int(name[1:]))
    ]


EK_SONUCLAR = ("tuttu", "tutmadı", "belirsiz")


def _ek_summary(expectations: list[dict[str, Any]]) -> dict[str, int]:
    sayim = {name: 0 for name in EK_SONUCLAR}
    for item in expectations:
        if item["result"] not in sayim:
            raise ValueError(f"bilinmeyen beklenti sonucu: {item['id']} {item['result']!r}")
        sayim[item["result"]] += 1
    return {**sayim, "total": len(expectations)}


def _ek_recall_by_outcome(src: dict[str, Any]) -> list[dict[str, Any]]:
    """Kuralın %20 bayraklarındaki isabetler final_result'a göre (b7_rule2_hits), pozitifler e2.counts'tan."""
    protocol, e2 = src["protocol"], src["e2"]
    rows = []
    for period in oulad_ek.PERIODS:
        presentation = protocol[f"{period}_presentation"]
        key = f"{period}_{presentation}"
        hits = src["b7_rule2_hits"][period]
        if hits["n_fail"] + hits["n_withdrawn"] != hits["n_hit"]:
            raise ValueError(f"b7 isabet toplamı tutarsız: {period}")
        if hits["n_hit"] + hits["n_pass_distinction"] != hits["n_flagged"]:
            raise ValueError(f"b7 bayrak toplamı tutarsız: {period}")
        fail_positive = e2["counts"]["KALDI"][key]["n_positive"]
        withdrawn_positive = e2["counts"]["BIRAKTI"][key]["n_positive"]
        rows.append(
            {
                "period": period,
                "presentation": presentation,
                "n_flagged": hits["n_flagged"],
                "n_hit": hits["n_hit"],
                "n_fail": hits["n_fail"],
                "n_positive_fail": fail_positive,
                "recall_fail": hits["n_fail"] / fail_positive,
                "n_withdrawn": hits["n_withdrawn"],
                "n_positive_withdrawn": withdrawn_positive,
                "recall_withdrawn": hits["n_withdrawn"] / withdrawn_positive,
            }
        )
    return rows


def _ek_pre_registration(root: Path) -> dict[str, Any]:
    """Dosya başına son md5 ve sıralı geçmiş (docs/on_kayit_md5.txt). Her dosyanın diskteki md5 değeri
    son kayıtla aynı değilse ek.check_pre_registration hata verir; hiçbir dosya yazılmaz."""
    docs = root / "docs"
    histories = oulad_ek.check_pre_registration(
        md5_path=docs / "on_kayit_md5.txt",
        paths=tuple(docs / path.name for path in oulad_ek.PRE_REGISTRATION_PATHS),
    )
    return oulad_ek.registration_block(histories)


def _ek(src: dict[str, Any], root: Path) -> dict[str, Any]:
    expectations = _ek_expectations(src)
    return {
        "label": src["label"],
        "protocol": src["protocol"],
        "notes": src["notes"],
        "excluded_presentations": src["excluded_presentations"],
        "e1": _ek_e1(src),
        "e2": _ek_e2(src),
        "e3": _ek_e3(src),
        "expectations": expectations,
        "recall_by_outcome": _ek_recall_by_outcome(src),
        "pre_registration": _ek_pre_registration(root),
        "summary": _ek_summary(expectations),
    }


def build_package(
    root: Path = _PROJECT_ROOT,
    oulad: dict[str, Any] | None = None,
    frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Paketi kurar. oulad=None ise 'oulad' anahtarı yazılmaz (yalnızca testler için).
    frame=None ise notebook 03'ün öznitelik çerçevesi diskten okunur (model.presentations, model.base_rate)."""
    src = _read(root)
    model, explain = src["model_metrics"], src["explain"]
    frame = model_cercevesi() if frame is None else frame
    grafik_satirlari, _ = gorseller(root, {"week10": src["figures_week10"], "week11": src["figures_week11"]})
    package: dict[str, Any] = {
        "kaynaklar": [*_sources(root), *_gorsel_kaynaklari(grafik_satirlari)],
        "uci": _uci(src["eda_summary"], root),
    }
    if oulad is not None:
        package["oulad"] = oulad
    package["test"] = _test_block(model, explain)
    package["sets"] = _sets(model)
    package["model"] = _model(model, frame)
    package["calibration"] = model["calibration"]["rows"]
    package["lomo"] = {"rows": model["lomo"]["rows"], "mean": model["lomo"]["mean"]}
    package["capacity"] = explain["capacity"]["rows"]
    package["shap"] = {"features": explain["shap"]["features"], "dependence": _dependence(explain)}
    package["rule"] = _rule(src["rule_metrics"], src["rule2_metrics"])
    package["figures"] = {
        "captions": {"week10": src["figures_week10"], "week11": src["figures_week11"]},
        "charts": grafik_satirlari,
    }
    package["ek"] = _ek(src["ek_metrics"], root)
    return package


def render(package: dict[str, Any]) -> bytes:
    return (json.dumps(package, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def main() -> None:
    package = build_package(oulad=oulad_sayilari())
    sayi = gorselleri_yaz()
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_bytes(render(package))
    print(f"yazildi: {sayi} gorsel, frontend/assets/arastirma/{FIGUR_REL}/")
    print(f"yazildi: {CIKTI.relative_to(_PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
