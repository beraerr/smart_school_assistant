"""Araştırma paketi: deterministik, kaynaklarla senkron, belirtimdeki anahtarlar, türetilmiş alanlar.

OULAD ham verisi yoksa yalnızca OULAD sayı testleri skip olur. model.presentations ve
model.base_rate için öznitelik parquet'i (features_cutoff60.parquet) diskte olmalıdır; yoksa
build_package FileNotFoundError ile durur.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_science.config import PASS_GRADE_100, PASS_THRESHOLD_20  # noqa: E402
from data_science.eda import build_summary  # noqa: E402
from data_science.features import feature_columns  # noqa: E402
from data_science.load import NUMERIC_COLUMNS, load_students  # noqa: E402
from data_science.oulad.eda import LABELS_BY_LANG, sorted_feature_catalog  # noqa: E402
from data_science.oulad.ek import GROUP_OF  # noqa: E402

_SPEC = importlib.util.spec_from_file_location("arastirma_paketi", ROOT / "scripts" / "arastirma_paketi.py")
assert _SPEC is not None and _SPEC.loader is not None
paketi = importlib.util.module_from_spec(_SPEC)
sys.modules["arastirma_paketi"] = paketi
_SPEC.loader.exec_module(paketi)

OULAD_VAR = paketi.oulad_ham_veri_var()
OULAD_YOK = pytest.mark.skipif(not OULAD_VAR, reason="OULAD ham verisi diskte yok")

# Hafta 9 raporu.
HAFTA9 = {
    "n_rows_raw": 32593,
    "n_rows_sample": 26403,
    "n_vle_rows": 10655280,
    "n_courses": 22,
}
HAFTA9_SPLIT = {"history": ("2013B", 3927), "train": ("2013J+2014B", 13639), "test": ("2014J", 8837)}

# Belirtim bölüm 2 tablosundaki anahtarlar (noktalı yol).
SPEC_ANAHTARLAR = [
    "uci.total", "uci.mat", "uci.por",
    "uci.pass_mat", "uci.pass_por",
    "uci.g3_zero",
    "uci.corr_g1", "uci.corr_g2", "uci.corr_failures",
    "uci.absence.pearson_all", "uci.absence.pearson_excl",
    "uci.absence.spearman_all", "uci.absence.spearman_excl",
    "uci.absence.buckets",
    # Belirtim v2, bölüm 2.1.
    "uci.pass_threshold_20", "uci.pass_grade_100",
    "uci.g3_zero_by_subject.mat", "uci.g3_zero_by_subject.por",
    "uci.g3_hist", "uci.top_corr",
    "uci.corr_matrix.columns", "uci.corr_matrix.values",
    "uci.grades",
    "uci.feature_sets.early", "uci.feature_sets.midterm",
    "oulad.n_rows_raw", "oulad.n_rows_sample", "oulad.n_vle_rows", "oulad.n_courses",
    "oulad.split",
    # Belirtim v2, bölüm 2.2.
    "oulad.zip_sha256", "oulad.tables", "oulad.sample", "oulad.final_result",
    "oulad.risk_pivot", "oulad.hist_vs_current", "oulad.slot_means",
    "oulad.signals.n_unsubmitted", "oulad.signals.vle_clicks",
    "oulad.signals.score_mean", "oulad.signals.score_vs_hist",
    "oulad.data_notes.ggg", "oulad.data_notes.bbb_zero_weight",
    "oulad.feature_map",
    "test.n", "test.n_positive",
    "test.module_rates",
    "test.module_rate_min", "test.module_rate_min_module",
    "test.module_rate_max", "test.module_rate_max_module",
    "sets.roc_val", "sets.roc_test", "sets.paired.HISTORY_GENERAL", "sets.within_module_mean",
    "calibration",
    "lomo.rows", "lomo.mean",
    "capacity",
    "shap.features", "shap.dependence",
    "rule.periods", "rule.capture_rule2", "rule.gap_rule2", "rule.excluded",
    "figures.captions",
    "kaynaklar",
    # Belirtim v2, bölüm 2.3.
    "model.presentations", "model.selected_params", "model.test_metrics", "model.paired",
    "model.validation_rows", "model.module_roc", "model.base_rate", "model.hist_rate_distinct_train",
    "model.calibration", "model.lomo", "model.within_module",
    "rule.roc_auc",
    # Ek analizler (belirtimde yok; görev P3 ek analizler).
    "ek.e1.rows", "ek.e1.paired_vs_general", "ek.e1.group_of",
    "ek.e2.rows", "ek.e2.counts", "ek.e2.b7_rule2_hits",
    "ek.e3.rows", "ek.e3.cohort", "ek.e3.secondary",
    "ek.expectations", "ek.recall_by_outcome", "ek.pre_registration", "ek.summary",
]


def _json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _get(package: dict, dotted: str):
    node = package
    for part in dotted.split("."):
        assert isinstance(node, dict) and part in node, f"eksik anahtar: {dotted} ({part})"
        node = node[part]
    return node


@pytest.fixture(scope="module")
def oulad():
    """OULAD sayıları bir kez hesaplanır (studentVle büyük)."""
    if not OULAD_VAR:
        pytest.skip("OULAD ham verisi diskte yok")
    return paketi.oulad_sayilari()


@pytest.fixture(scope="module")
def oulad_ya_da_none(request):
    return request.getfixturevalue("oulad") if OULAD_VAR else None


@pytest.fixture(scope="module")
def disk() -> dict:
    assert paketi.CIKTI.is_file(), f"paket yok: {paketi.CIKTI} (once scripts/arastirma_paketi.py calistirilmali)"
    return json.loads(paketi.CIKTI.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def taze() -> dict:
    """Kaynaklardan yeniden üretilen paket, OULAD sayıları olmadan."""
    return paketi.build_package(oulad=None)


def test_deterministik(oulad_ya_da_none):
    ilk = paketi.render(paketi.build_package(oulad=oulad_ya_da_none))
    ikinci = paketi.render(paketi.build_package(oulad=oulad_ya_da_none))
    assert ilk == ikinci


def test_senkron_oulad_haric(disk, taze):
    diskten = {k: v for k, v in disk.items() if k != "oulad"}
    assert diskten == taze
    assert list(diskten) == list(taze)


@OULAD_YOK
def test_senkron_oulad_dahil_bayt(oulad):
    beklenen = paketi.render(paketi.build_package(oulad=oulad))
    assert paketi.CIKTI.read_bytes() == beklenen


@pytest.mark.parametrize("dotted", SPEC_ANAHTARLAR)
def test_spec_anahtari_var(disk, dotted):
    _get(disk, dotted)


def test_kaynaklar_yol_ve_md5(disk):
    import hashlib

    yollar = [k["yol"] for k in disk["kaynaklar"]]
    # S1b: girdilerden sonra her görsel (figures.charts sırasıyla), kendi kaynağı ve md5'iyle.
    gorsel_yollari = [f"frontend/assets/arastirma/{s['path']}" for s in disk["figures"]["charts"]]
    assert yollar == [*paketi.GIRDILER.values(), *paketi.METIN_GIRDILERI.values(), *gorsel_yollari]
    gorsel_kayitlari = disk["kaynaklar"][len(yollar) - len(gorsel_yollari):]
    assert [(k["kaynak"], k["md5"]) for k in gorsel_kayitlari] == [
        (s["source"], s["md5"]) for s in disk["figures"]["charts"]
    ]
    for kayit in disk["kaynaklar"]:
        data = (ROOT / kayit["yol"]).read_bytes()
        assert kayit["md5"] == hashlib.md5(data).hexdigest()


def test_turetilmis_capture_ve_gap(disk):
    rule2 = _json(paketi.GIRDILER["rule2_metrics"])
    donem = next(p for p in rule2["periods"] if p["presentation"] == "2014J")
    toplam = {r["method"]: r for r in donem["total"]}
    assert disk["rule"]["capture_rule2"]["2014J"] == toplam["rule2"]["n_hit"] / toplam["general_hgb"]["n_hit"]
    assert disk["rule"]["gap_rule2"]["2014J"] == (
        toplam["general_hgb"]["precision"] - toplam["rule2"]["precision"]
    ) * 100
    assert set(disk["rule"]["capture_rule2"]) == {p["presentation"] for p in rule2["periods"]}
    assert set(disk["rule"]["gap_rule2"]) == {p["presentation"] for p in rule2["periods"]}


def test_turetilmis_modul_oranlari(disk):
    model = _json(paketi.GIRDILER["model_metrics"])
    rates = {r["code_module"]: r["positive_rate"] for r in model["calibration"]["rows"] if r["set"] == "GENERAL"}
    test = disk["test"]
    assert test["module_rates"] == rates
    assert test["module_rate_min"] == min(rates.values())
    assert test["module_rate_max"] == max(rates.values())
    assert rates[test["module_rate_min_module"]] == test["module_rate_min"]
    assert rates[test["module_rate_max_module"]] == test["module_rate_max"]
    assert test["module_rate_min_module"] == "AAA"
    assert test["module_rate_max_module"] == "CCC"


@OULAD_YOK
def test_oulad_sayilari_hafta9(oulad, disk):
    for paket in (oulad, disk["oulad"]):
        for anahtar, deger in HAFTA9.items():
            assert paket[anahtar] == deger, anahtar
        split = {s["part"]: s for s in paket["split"]}
        assert set(split) == set(HAFTA9_SPLIT)
        for part, (sunumlar, satir) in HAFTA9_SPLIT.items():
            assert "+".join(split[part]["presentations"]) == sunumlar
            assert split[part]["rows"] == satir
            assert 0.0 <= split[part]["risk_rate"] <= 1.0
            assert 0.0 <= split[part]["has_history"] <= 1.0
        assert sum(s["rows"] for s in split.values()) == HAFTA9["n_rows_sample"]


def test_dependence_ornekleri(disk):
    kaynak = {d["feature"]: d for d in _json(paketi.GIRDILER["explain"])["shap"]["dependence"]}
    dep = disk["shap"]["dependence"]
    assert dep["sample_size"] == 3000
    assert dep["seed"] == 42
    assert {f["feature"] for f in dep["features"]} == set(kaynak)
    for f in dep["features"]:
        src = kaynak[f["feature"]]
        assert f["n_total"] == len(src["value"])
        assert f["n_sample"] == 3000
        assert len(f["index"]) == len(set(f["index"])) == 3000
        assert len(f["value"]) == len(f["shap"]) == 3000
        assert all(0 <= i < f["n_total"] for i in f["index"])
        assert f["value"] == [src["value"][i] for i in f["index"]]
        assert f["shap"] == [src["shap"][i] for i in f["index"]]


# --- Belirtim v2, bölüm 2.1: uci.* eklemeleri -------------------------------------------------

UCI_V2_ANAHTARLAR = [
    "pass_threshold_20", "pass_grade_100", "g3_zero_by_subject", "g3_hist",
    "top_corr", "corr_matrix", "grades", "feature_sets",
]
NOTEBOOKLAR = ["01_uci_eda.ipynb", "01_uci_eda_eng.ipynb"]


@pytest.fixture(scope="module")
def ogrenciler():
    return load_students()


def test_uci_v2_deterministik_ve_senkron(disk, taze):
    ikinci = paketi.build_package(oulad=None)
    for anahtar in UCI_V2_ANAHTARLAR:
        assert anahtar in taze["uci"], anahtar
        assert taze["uci"][anahtar] == ikinci["uci"][anahtar], f"deterministik degil: {anahtar}"
        assert disk["uci"][anahtar] == taze["uci"][anahtar], f"diskle senkron degil: {anahtar}"
    ilk_render = paketi.render(taze)
    assert ilk_render == paketi.render(ikinci)
    # render sonrasi JSON'a gidis-donus kayipsiz (NaN/Inf yok, anahtar sirasi korunur).
    assert list(json.loads(ilk_render)["uci"]) == list(taze["uci"])


def test_uci_esik_alanlari(disk):
    uci = disk["uci"]
    assert uci["pass_threshold_20"] == PASS_THRESHOLD_20
    assert uci["pass_grade_100"] == PASS_GRADE_100
    assert uci["pass_grade_100"] == uci["pass_threshold_20"] * 5


def test_g3_hist_toplamlar(disk):
    uci = disk["uci"]
    hist = uci["g3_hist"]
    assert all(set(r) == {"subject", "g3", "n"} for r in hist)
    assert sum(r["n"] for r in hist) == uci["total"]
    for ders in ("mat", "por"):
        assert sum(r["n"] for r in hist if r["subject"] == ders) == uci[ders]


def test_g3_hist_her_not_satir_olarak_var(disk):
    hist = disk["uci"]["g3_hist"]
    for ders in ("mat", "por"):
        notlar = [r["g3"] for r in hist if r["subject"] == ders]
        assert notlar == list(range(21))
    assert len(hist) == 42


def test_g3_hist_ham_veriyle_bagimsiz_sayim(disk, ogrenciler):
    sayim = ogrenciler.groupby("subject")["G3"].value_counts()
    for r in disk["uci"]["g3_hist"]:
        beklenen = int(sayim.get((r["subject"], r["g3"]), 0))
        assert r["n"] == beklenen, (r["subject"], r["g3"])


def test_g3_sifir_ders_bazinda(disk):
    uci = disk["uci"]
    sifir = uci["g3_zero_by_subject"]
    assert set(sifir) == {"mat", "por"}
    hist_sifir = {r["subject"]: r["n"] for r in uci["g3_hist"] if r["g3"] == 0}
    assert hist_sifir == sifir
    assert sum(sifir.values()) == uci["g3_zero"]
    assert sum(hist_sifir.values()) == uci["g3_zero"]


def test_corr_matrix_kare_kosegen_ve_korelasyonlar(disk):
    uci = disk["uci"]
    kolonlar = uci["corr_matrix"]["columns"]
    degerler = uci["corr_matrix"]["values"]
    assert kolonlar == list(NUMERIC_COLUMNS)
    assert len(degerler) == len(kolonlar)
    assert all(len(satir) == len(kolonlar) for satir in degerler)
    assert all(math.isfinite(h) for satir in degerler for h in satir)
    for i in range(len(kolonlar)):
        assert math.isclose(degerler[i][i], 1.0, rel_tol=1e-12, abs_tol=0), kolonlar[i]
    # Pearson simetrik.
    for i in range(len(kolonlar)):
        for j in range(i):
            assert math.isclose(degerler[i][j], degerler[j][i], rel_tol=1e-12, abs_tol=0), (
                kolonlar[i], kolonlar[j])
    g1, g2, g3 = kolonlar.index("G1"), kolonlar.index("G2"), kolonlar.index("G3")
    # DataFrame.corr ve Series.corr farkli yollardan hesaplar; fark 1e-12 bagil toleransin altinda kalmali.
    assert math.isclose(degerler[g1][g3], uci["corr_g1"], rel_tol=1e-12, abs_tol=0)
    assert math.isclose(degerler[g2][g3], uci["corr_g2"], rel_tol=1e-12, abs_tol=0)


def test_top_corr_hesaplanan_ozetle_ayni(disk, ogrenciler):
    top = disk["uci"]["top_corr"]
    assert top == build_summary(ogrenciler)["top_abs_correlation_with_g3"]
    assert top == _json(paketi.GIRDILER["eda_summary"])["top_abs_correlation_with_g3"]
    assert [abs(r["correlation"]) for r in top] == sorted((abs(r["correlation"]) for r in top), reverse=True)


def test_grades_satirlar_ve_sutunlar(disk):
    uci = disk["uci"]
    grades = uci["grades"]
    assert len(grades) == uci["total"]
    assert all(set(r) == {"subject", "g1", "g2", "g3"} for r in grades)
    assert {r["subject"] for r in grades} == {"mat", "por"}
    for ders in ("mat", "por"):
        assert sum(r["subject"] == ders for r in grades) == uci[ders]
    assert all(isinstance(r[k], int) and 0 <= r[k] <= 20 for r in grades for k in ("g1", "g2", "g3"))


def test_grades_g3_dagilimi_g3_hist_ile_tutarli(disk):
    uci = disk["uci"]
    for r in uci["g3_hist"]:
        sayi = sum(1 for g in uci["grades"] if g["subject"] == r["subject"] and g["g3"] == r["g3"])
        assert sayi == r["n"], (r["subject"], r["g3"])


def test_feature_sets(disk):
    sets = disk["uci"]["feature_sets"]
    assert set(sets) == {"early", "midterm"}
    early, midterm = sets["early"], sets["midterm"]
    assert not {"G1", "G2", "G3"} & set(early)
    assert "G1" in midterm
    assert "G2" not in midterm and "G3" not in midterm
    # Paketteki sira: modulun sirasi.
    assert early == list(feature_columns("early"))
    assert midterm == list(feature_columns("midterm"))
    assert len(early) == len(set(early)) and len(midterm) == len(set(midterm))


# --- Notebook 01 ciktisi paketle ayni (notebook ciktisindan okunur) ----------------------------


def _hucreler(ad: str) -> list[dict]:
    nb = json.loads((ROOT / "notebooks" / ad).read_text(encoding="utf-8"))
    return [c for c in nb["cells"] if c["cell_type"] == "code"]


def _kaynak(hucre: dict) -> str:
    return "".join(hucre["source"])


def _cikti(hucre: dict) -> str:
    return "".join(
        "".join(o.get("text", [])) for o in hucre.get("outputs", []) if o.get("output_type") == "stream"
    )


def _bul(ad: str, parca: str) -> list[dict]:
    bulunan = [h for h in _hucreler(ad) if parca in _kaynak(h)]
    assert bulunan, f"{ad}: kaynakta {parca!r} geçen hücre yok"
    for h in bulunan:
        assert _cikti(h).strip(), f"{ad}: {parca!r} hücresinin çıktısı boş (notebook çalıştırılmamış)"
    return bulunan


def _anahtar_deger(metin: str) -> dict[str, str]:
    sonuc = {}
    for satir in metin.splitlines():
        parcalar = satir.split(None, 1)
        if len(parcalar) == 2:
            sonuc[parcalar[0]] = parcalar[1].strip()
    return sonuc


@pytest.mark.parametrize("ad", NOTEBOOKLAR)
def test_notebook_esik_ve_gecme_oranlari(ad, disk):
    uci = disk["uci"]
    (hucre,) = _bul(ad, 'print("pass_threshold_20"')
    kv = _anahtar_deger(_cikti(hucre))
    assert int(kv["pass_threshold_20"]) == uci["pass_threshold_20"]
    assert int(kv["equivalent_pass_grade_100"]) == uci["pass_grade_100"]
    assert float(kv["pass_rate_mat"]) == uci["pass_mat"]
    assert float(kv["pass_rate_por"]) == uci["pass_por"]


@pytest.mark.parametrize("ad", NOTEBOOKLAR)
def test_notebook_g3_sifir(ad, disk):
    uci = disk["uci"]
    (hucre,) = _bul(ad, 'print("g3_zero_count"')
    kv = _anahtar_deger(_cikti(hucre))
    assert int(kv["g3_zero_count"]) == uci["g3_zero"]
    assert int(kv["g3_zero_mat"]) == uci["g3_zero_by_subject"]["mat"]
    assert int(kv["g3_zero_por"]) == uci["g3_zero_by_subject"]["por"]


@pytest.mark.parametrize("ad", NOTEBOOKLAR)
def test_notebook_ozellik_kumeleri(ad, disk):
    sets = disk["uci"]["feature_sets"]
    (hucre,) = _bul(ad, 'print("EARLY"')
    satirlar = _cikti(hucre).splitlines()
    i_early = next(i for i, s in enumerate(satirlar) if s.startswith("EARLY "))
    i_mid = next(i for i, s in enumerate(satirlar) if s.startswith("MIDTERM "))
    bitis = next(i for i, s in enumerate(satirlar) if s.startswith("early_preprocessor_shape"))
    assert i_early < i_mid < bitis
    early = [s.strip() for s in satirlar[i_early + 1:i_mid]]
    midterm = [s.strip() for s in satirlar[i_mid + 1:bitis]]
    assert int(satirlar[i_early].split()[1]) == len(sets["early"])
    assert int(satirlar[i_mid].split()[1]) == len(sets["midterm"])
    assert early == sets["early"]
    assert midterm == sets["midterm"]


@pytest.mark.parametrize("ad", NOTEBOOKLAR)
def test_notebook_en_guclu_korelasyonlar_ve_g1_g2(ad, disk):
    uci = disk["uci"]
    (top_hucre,) = _bul(ad, "top.itertuples")
    okunan = []
    for satir in _cikti(top_hucre).splitlines():
        parcalar = satir.split()
        if len(parcalar) == 2:
            try:
                okunan.append({"feature": parcalar[0], "correlation": float(parcalar[1])})
            except ValueError:
                continue
    # Notebook yalnızca feature ve correlation basar; karşılaştırma bu alanlarla sınırlı.
    assert len(okunan) == len(uci["top_corr"])
    for notebook_satiri, paket_satiri in zip(okunan, uci["top_corr"]):
        assert notebook_satiri["feature"] == paket_satiri["feature"]
        assert notebook_satiri["correlation"] == paket_satiri["correlation"]
    # abs_correlation paket alanı ayrıca doğrulanır.
    for paket_satiri in uci["top_corr"]:
        assert paket_satiri["abs_correlation"] == abs(paket_satiri["correlation"])
    (hucre,) = _bul(ad, 'print("g1_g3_correlation"')
    kv = _anahtar_deger(_cikti(hucre))
    assert float(kv["g1_g3_correlation"]) == uci["corr_g1"]
    assert float(kv["g2_g3_correlation"]) == uci["corr_g2"]


def _tablo_satirlari(metin: str, baslik: str, adet: int) -> list[list[str]]:
    """Başlık satırı + sütun başlığı satırından sonraki `adet` veri satırı."""
    satirlar = metin.splitlines()
    i = satirlar.index(baslik)
    return [satir.split() for satir in satirlar[i + 2:i + 2 + adet]]


@pytest.mark.parametrize("ad", NOTEBOOKLAR)
def test_notebook_ozet_devamsizlik_degerleri(ad, disk):
    ab = disk["uci"]["absence"]
    hucreler = _bul(ad, 'print("pearson_all"')
    assert len(hucreler) >= 1
    for hucre in hucreler:
        kv = _anahtar_deger(_cikti(hucre))
        assert float(kv["pearson_all"]) == ab["pearson_all"]
        assert float(kv["pearson_excl_g3_zero"]) == ab["pearson_excl"]
        assert float(kv["spearman_all"]) == ab["spearman_all"]
        assert float(kv["spearman_excl_g3_zero"]) == ab["spearman_excl"]
        adet = len(ab["buckets"])
        tum = _tablo_satirlari(_cikti(hucre), "absence_buckets_all", adet)
        haric = _tablo_satirlari(_cikti(hucre), "absence_buckets_excl_g3_zero", adet)
        assert len(tum) == len(haric) == adet
        for satir_tum, satir_haric, kova in zip(tum, haric, ab["buckets"]):
            # Sütunlar: indeks, etiket, n, oran.
            assert satir_tum[1] == satir_haric[1] == kova["bucket"]
            assert satir_tum[-1] == f"{kova['pass_all']:.6f}"
            assert int(satir_haric[2]) == kova["n_excl"]
            assert satir_haric[-1] == f"{kova['pass_excl']:.6f}"


@pytest.mark.parametrize("ad", NOTEBOOKLAR)
def test_notebook_sonuc_cumleleri(ad, disk):
    import re

    uci = disk["uci"]
    (hucre,) = _bul(ad, "1. Rows:")
    metin = _cikti(hucre)
    assert f"1. Rows: {uci['total']} (mat {uci['mat']}, por {uci['por']})." in metin
    assert f"2. At G3 >= {uci['pass_threshold_20']} (100-point pass grade {uci['pass_grade_100']}), " in metin
    oranlar = {"mat": uci["pass_mat"], "por": uci["pass_por"]}
    yuksek = max(oranlar, key=oranlar.get)
    alcak = min(oranlar, key=oranlar.get)
    assert (
        f"pass rate is {oranlar[yuksek]:.4f} in {yuksek} and {oranlar[alcak]:.4f} in {alcak}." in metin
    )
    birinci, ikinci = uci["top_corr"][0], uci["top_corr"][1]
    assert (
        f"3. Strongest Pearson link with G3 is {birinci['feature']} ({birinci['correlation']:.4f}), "
        f"then {ikinci['feature']} ({ikinci['correlation']:.4f}). "
        f"G1-G3 is {uci['corr_g1']:.4f} and G2-G3 is {uci['corr_g2']:.4f}. "
    ) in metin
    sets = uci["feature_sets"]
    assert (
        f"EARLY contains G1={'G1' in sets['early']}, G2={'G2' in sets['early']}; "
        f"MIDTERM contains G1={'G1' in sets['midterm']}, G2={'G2' in sets['midterm']}; "
        f"G3 is in a feature set={'G3' in sets['early'] or 'G3' in sets['midterm']}."
    ) in metin
    ab = uci["absence"]
    assert (
        f"4. G3=0 rows: {uci['g3_zero']}. "
        f"absences-G3 Pearson {ab['pearson_all']:.4f} with zeros and {ab['pearson_excl']:.4f} without; "
        f"Spearman {ab['spearman_all']:.4f} with zeros and {ab['spearman_excl']:.4f} without."
    ) in metin
    # 5. cümle: sıfırlar dahil/hariç, en düşük ve en yüksek geçme oranlı kovalar.
    kovalar = [k for k in ab["buckets"] if not math.isnan(k["pass_all"])]
    alt_tum = min(kovalar, key=lambda k: k["pass_all"])
    ust_tum = max(kovalar, key=lambda k: k["pass_all"])
    alt_haric = min(kovalar, key=lambda k: k["pass_excl"])
    ust_haric = max(kovalar, key=lambda k: k["pass_excl"])
    kalip = re.compile(
        r"5\. With zeros kept.*?(\d\.\d{4}) \(([^,()]+), n=(\d+)\).*?(\d\.\d{4}) \(([^,()]+), n=(\d+)\)"
        r".*?(\d\.\d{4}) \(([^,()]+), n=(\d+)\).*?(\d\.\d{4}) \(([^,()]+), n=(\d+)\)",
        re.S,
    )
    eslesme = kalip.search(metin)
    assert eslesme, "Sonuç 5. cümlesi beklenen biçimde değil"
    g = eslesme.groups()
    # "Sıfırlar dahil" yarısındaki n paketin absence bölümünde yok (yalnız n_excl var); orası karşılaştırılmaz.
    assert (g[0], g[1]) == (f"{alt_tum['pass_all']:.4f}", alt_tum["bucket"])
    assert (g[3], g[4]) == (f"{ust_tum['pass_all']:.4f}", ust_tum["bucket"])
    assert (g[6], g[7], int(g[8])) == (f"{alt_haric['pass_excl']:.4f}", alt_haric["bucket"], alt_haric["n_excl"])
    assert (g[9], g[10], int(g[11])) == (f"{ust_haric['pass_excl']:.4f}", ust_haric["bucket"], ust_haric["n_excl"])


# --- Belirtim v2, bölüm 2.2: oulad.* eklemeleri -----------------------------------------------

OULAD_V2_ANAHTARLAR = [
    "zip_sha256", "tables", "sample", "final_result", "risk_pivot", "hist_vs_current",
    "slot_means", "signals", "data_notes", "feature_map",
]
OULAD_NOTEBOOKLAR = [("02_oulad_eda.ipynb", "tr"), ("02_oulad_eda_eng.ipynb", "en")]
SINYALLER = ["n_unsubmitted", "vle_clicks", "score_mean", "score_vs_hist"]

# Hafta 9 raporu: tablo boyutları.
HAFTA9_TABLOLAR = {
    "studentInfo": 32593,
    "studentVle": 10655280,
    "courses": 22,
    "assessments": 206,
    "studentAssessment": 173912,
    "vle": 6364,
    "studentRegistration": 32593,
}
HAFTA9_ORNEK = {"rows_before": 32593, "rows_removed": 6190, "rows_kept": 26403}
GGG_N = {"2014B": 790, "2014J": 697}
BBB_SIFIR_AGIRLIK = 177


def _stdout(hucre: dict) -> str:
    """Hücrenin stdout akışları sırayla birleştirilir (akış parçalanmasından bağımsız)."""
    return "".join(
        "".join(o.get("text", []))
        for o in hucre.get("outputs", [])
        if o.get("output_type") == "stream" and o.get("name", "stdout") == "stdout"
    )


def _oulad_hucre(ad: str, parca: str) -> str:
    bulunan = [h for h in _hucreler(ad) if parca in _kaynak(h)]
    assert len(bulunan) == 1, f"{ad}: {parca!r} geçen hücre sayısı {len(bulunan)} (1 olmalı)"
    metin = _stdout(bulunan[0])
    assert metin.strip(), f"{ad}: {parca!r} hücresinin çıktısı boş (notebook çalıştırılmamış)"
    return metin


def _metin_satirlari(metin: str, baslangic: str, bitis: str | None = None) -> list[str]:
    """`baslangic` satırından sonra (başlık satırı dahil değil), `bitis` satırına kadar."""
    satirlar = metin.splitlines()
    i = satirlar.index(baslangic)
    j = len(satirlar)
    if bitis is not None:
        j = next(k for k in range(i + 1, len(satirlar)) if satirlar[k].startswith(bitis))
    return satirlar[i + 1:j]


def _dilim_satirlari(metin: str) -> list[tuple[str, int, str]]:
    """Dilim tablosu satırları (bin, n, oran). Bin etiketi boşluk içerebilir."""
    kalip = re.compile(r"^\s*(\S.*?)\s+(\d+)\s+(\d\.\d{6}|NaN)\s*$")
    return [(m.group(1), int(m.group(2)), m.group(3)) for s in metin.splitlines() if (m := kalip.match(s))]


@pytest.fixture(scope="module")
def oulad_disk(disk) -> dict:
    assert "oulad" in disk, "paket oulad bölümsüz (scripts/arastirma_paketi.py çalıştırılmalı)"
    return disk["oulad"]


@OULAD_YOK
def test_oulad_v2_anahtarlar_diskte(oulad_disk):
    for anahtar in OULAD_V2_ANAHTARLAR:
        assert anahtar in oulad_disk, anahtar
    assert set(oulad_disk["signals"]) == set(SINYALLER)
    assert set(oulad_disk["data_notes"]) == {"ggg", "bbb_zero_weight"}


@OULAD_YOK
def test_oulad_v2_deterministik_ve_senkron(oulad, oulad_disk):
    ikinci = paketi.oulad_sayilari()
    for anahtar in OULAD_V2_ANAHTARLAR:
        assert json.dumps(oulad[anahtar], ensure_ascii=False) == json.dumps(ikinci[anahtar], ensure_ascii=False), (
            f"deterministik degil: {anahtar}")
        assert oulad_disk[anahtar] == oulad[anahtar], f"diskle senkron degil: {anahtar}"
    assert paketi.render(paketi.build_package(oulad=oulad)) == paketi.render(paketi.build_package(oulad=ikinci))
    assert list(oulad_disk) == list(oulad)


@OULAD_YOK
def test_oulad_v2_json_gidis_donus(oulad_disk):
    yazilan = json.loads(paketi.render({"oulad": oulad_disk}))
    assert yazilan["oulad"] == oulad_disk


@OULAD_YOK
def test_oulad_tablolar_ornek_ve_toplamlar_hafta9(oulad_disk):
    tablolar = {t["table"]: t["rows"] for t in oulad_disk["tables"]}
    assert tablolar == HAFTA9_TABLOLAR
    assert len(oulad_disk["tables"]) == len(HAFTA9_TABLOLAR)
    assert all(isinstance(t["cols"], int) and t["cols"] > 0 for t in oulad_disk["tables"])
    assert {k: oulad_disk["sample"][k] for k in HAFTA9_ORNEK} == HAFTA9_ORNEK
    assert oulad_disk["sample"]["cutoff_day"] == 60
    assert set(oulad_disk["sample"]) == {"cutoff_day", *HAFTA9_ORNEK}
    kept = oulad_disk["sample"]["rows_kept"]
    assert oulad_disk["sample"]["rows_before"] - oulad_disk["sample"]["rows_removed"] == kept
    assert kept == oulad_disk["n_rows_sample"]
    assert sum(r["n"] for r in oulad_disk["final_result"]) == kept
    assert all(set(r) == {"final_result", "n", "at_risk"} for r in oulad_disk["final_result"])
    assert {r["final_result"]: r["at_risk"] for r in oulad_disk["final_result"]} == {
        "Distinction": 0, "Fail": 1, "Pass": 0, "Withdrawn": 1}
    assert sum(r["n"] for r in oulad_disk["risk_pivot"]) == kept
    assert all(set(r) == {"module", "presentation", "n", "rate"} for r in oulad_disk["risk_pivot"])
    assert sum(r["n"] for r in oulad_disk["hist_vs_current"]) == kept
    assert len(oulad_disk["hist_vs_current"]) == len(oulad_disk["risk_pivot"])
    assert all(
        set(r) == {"module", "presentation", "n", "rate", "hist_rate"} for r in oulad_disk["hist_vs_current"])
    assert all(
        set(r) == {"module", "presentation", "assessment_type", "slot", "n", "mean_score"}
        for r in oulad_disk["slot_means"])
    assert oulad_disk["zip_sha256"] == "f2ed1902616c1fe8d2824d872c0b7d2d72be435bf0124d077044fe4be2c6d3e4"


@OULAD_YOK
def test_oulad_signals_toplamlar_train(oulad_disk):
    train = next(s for s in oulad_disk["split"] if s["part"] == "train")["rows"]
    for ad in SINYALLER:
        satirlar = oulad_disk["signals"][ad]
        assert all(set(r) == {"bin", "n", "rate"} for r in satirlar), ad
        assert sum(r["n"] for r in satirlar) == train, ad
        assert len({r["bin"] for r in satirlar}) == len(satirlar), ad
    # "eksik" dilimi (TR etiketi) ayrı satır, en sonda; teslim sayısında eksik yok.
    eksik = LABELS_BY_LANG["tr"]["missing"]
    assert eksik == "eksik"
    assert all(r["bin"] != eksik for r in oulad_disk["signals"]["n_unsubmitted"])
    assert all(r["bin"] != eksik for r in oulad_disk["signals"]["vle_clicks"])
    for ad in ("score_mean", "score_vs_hist"):
        assert oulad_disk["signals"][ad][-1]["bin"] == eksik, ad
        assert [r["bin"] for r in oulad_disk["signals"][ad]].count(eksik) == 1, ad
    assert len(oulad_disk["signals"]["vle_clicks"]) == 5


@OULAD_YOK
def test_oulad_veri_notlari(oulad_disk):
    ggg = oulad_disk["data_notes"]["ggg"]
    assert len(ggg) == 2
    assert {r["presentation"]: r["n_rows"] for r in ggg} == GGG_N
    assert [r["n_rows"] for r in ggg] == [790, 697]
    assert all(
        set(r) == {"presentation", "n_rows", "n_expected_min", "n_expected_max",
                   "score_mean_missing", "vle_clicks_positive"} for r in ggg)
    assert oulad_disk["data_notes"]["bbb_zero_weight"] == BBB_SIFIR_AGIRLIK


@OULAD_YOK
def test_oulad_feature_map_katalogla_ayni(oulad_disk):
    satirlar = oulad_disk["feature_map"]
    assert all(set(r) == {"feature", "group", "school_tr", "school_en"} for r in satirlar)
    assert len({r["feature"] for r in satirlar}) == len(satirlar)
    # Tanımlayıcı ve hedef pakette yok; her model özelliğinin iki dildeki karşılığı dolu.
    assert not {"at_risk", "code_module", "code_presentation", "id_student", "split"} & {
        r["feature"] for r in satirlar}
    assert all(r["school_tr"].strip() and r["school_en"].strip() for r in satirlar)
    katalog = {r.column: r for r in sorted_feature_catalog().itertuples(index=False)}
    model = {c: r for c, r in katalog.items() if r.school_tr not in {"Tanımlayıcı; modele girmez", "Hedef; özellik değil"}}
    assert [r["feature"] for r in satirlar] == list(model)
    for r in satirlar:
        k = katalog[r["feature"]]
        assert (r["group"], r["school_tr"], r["school_en"]) == (k.group, k.school_tr, k.school_en)


def test_katalog_hedef_tanimlayici_ve_grup_degerleri():
    katalog = {r.column: r for r in sorted_feature_catalog().itertuples(index=False)}
    assert katalog["at_risk"].school_tr.startswith("Hedef")
    assert katalog["at_risk"].group == ""
    for sutun in ("code_module", "code_presentation", "id_student", "split"):
        assert katalog[sutun].school_tr.startswith("Tanımlayıcı"), sutun
        assert katalog[sutun].group == "", sutun
    genel = {c: r for c, r in katalog.items() if c in GROUP_OF}
    assert set(genel) == set(GROUP_OF)
    assert all(r.group == GROUP_OF[c] for c, r in genel.items())
    gecmis = {c for c, r in katalog.items() if r.scope == "geçmiş"}
    assert gecmis and all(katalog[c].group == "GEÇMİŞ" for c in gecmis)
    assert all(r.school_tr.strip() and r.school_en.strip() for r in katalog.values())


# --- Notebook 02 (TR ve EN) metin çıktıları paketle aynı -----------------------------------


@OULAD_YOK
@pytest.mark.parametrize("ad,dil", OULAD_NOTEBOOKLAR)
def test_notebook02_veri_ve_ornek(ad, dil, oulad_disk):
    metin = _oulad_hucre(ad, 'print("zip_sha256"')
    kv = _anahtar_deger(metin)
    assert kv["zip_sha256"] == oulad_disk["zip_sha256"]
    tablolar = [(t, int(r), int(c)) for t, r, c in re.findall(r"^table=(\w+) rows=(\d+) cols=(\d+)$", metin, re.M)]
    assert tablolar == [(t["table"], t["rows"], t["cols"]) for t in oulad_disk["tables"]]
    assert {t: r for t, r, _ in tablolar} == HAFTA9_TABLOLAR
    assert int(kv["feature_rows"]) == oulad_disk["sample"]["rows_kept"]
    assert int(kv["duplicate_row_keys"]) == 0

    metin = _oulad_hucre(ad, 'print("cutoff_day"')
    kv = _anahtar_deger(metin)
    ornek = oulad_disk["sample"]
    assert int(kv["cutoff_day"]) == ornek["cutoff_day"]
    assert int(kv["rows_before_cutoff_filter"]) == ornek["rows_before"]
    assert int(kv["rows_removed_before_cutoff"]) == ornek["rows_removed"]
    assert int(kv["rows_kept"]) == ornek["rows_kept"]
    assert int(kv["feature_rows"]) == ornek["rows_kept"]
    okunan = [
        (m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        for s in metin.splitlines()
        if (m := re.match(r"^\s*([A-Za-z]+)\s+(\d+)\s+([01])\s+([01])\s*$", s))
    ]
    assert okunan == [(r["final_result"], r["n"], r["at_risk"], r["at_risk"]) for r in oulad_disk["final_result"]]


@OULAD_YOK
@pytest.mark.parametrize("ad,dil", OULAD_NOTEBOOKLAR)
def test_notebook02_bolme(ad, dil, oulad_disk):
    metin = _oulad_hucre(ad, 'print("split_by_presentation")')
    okunan = [
        (m.group(1), int(m.group(2)), m.group(3), m.group(4))
        for s in metin.splitlines()
        if (m := re.match(r"^\s*(history|train|test)\s+(\d+)\s+(\d\.\d{6})\s+(\d\.\d{6})\s*$", s))
    ]
    beklenen = [
        (s["part"], s["rows"], f"{s['risk_rate']:.6f}", f"{s['has_history']:.6f}") for s in oulad_disk["split"]
    ]
    assert okunan == beklenen


@OULAD_YOK
@pytest.mark.parametrize("ad,dil", OULAD_NOTEBOOKLAR)
def test_notebook02_risk_pivot_ve_gecmis(ad, dil, oulad_disk):
    metin = _oulad_hucre(ad, "risk_rate = risk_rate_pivot(features)")
    satirlar = metin.splitlines()
    assert satirlar[0].split()[0] == "code_presentation"
    sunumlar = satirlar[0].split()[1:]
    assert satirlar[1].strip() == "code_module"
    notebook = {}
    for s in satirlar[2:]:
        parcalar = s.split()
        assert len(parcalar) == 1 + len(sunumlar), s
        for sunum, deger in zip(sunumlar, parcalar[1:]):
            if deger != "NaN":
                notebook[(parcalar[0], sunum)] = deger
    paket = {(r["module"], r["presentation"]): f"{r['rate']:.6f}" for r in oulad_disk["risk_pivot"]}
    assert notebook == paket
    assert [(r["module"], r["presentation"]) for r in oulad_disk["risk_pivot"]] == [
        (m, s) for m in sorted({k[0] for k in notebook}) for s in sunumlar if (m, s) in notebook]

    metin = _oulad_hucre(ad, "points = hist_vs_current_points(features)")
    satirlar = metin.splitlines()
    assert satirlar[0].split() == ["code_module", "code_presentation", "n", "at_risk_rate", "hist_module_risk_rate"]
    notebook = [tuple(s.split()) for s in satirlar[1:]]
    paket = [
        (r["module"], r["presentation"], str(r["n"]), f"{r['rate']:.6f}",
         "<NA>" if r["hist_rate"] is None else f"{r['hist_rate']:.6f}")
        for r in oulad_disk["hist_vs_current"]
    ]
    assert notebook == paket
    assert all(len(satir) == 5 for satir in notebook)


@OULAD_YOK
@pytest.mark.parametrize("ad,dil", OULAD_NOTEBOOKLAR)
def test_notebook02_yuva_ortalamalari(ad, dil, oulad_disk):
    metin = _oulad_hucre(ad, "slot_means = slot_means_table(")
    satirlar = metin.splitlines()
    assert satirlar[0].split() == ["code_module", "code_presentation", "assessment_type", "slot", "n", "mean_score"]
    son = next(i for i, s in enumerate(satirlar) if s.startswith("modules_without_scored_slot"))
    notebook = [tuple(s.split()) for s in satirlar[1:son]]
    paket = [
        (r["module"], r["presentation"], r["assessment_type"], str(r["slot"]), str(r["n"]), f"{r['mean_score']:.6f}")
        for r in oulad_disk["slot_means"]
    ]
    assert notebook == paket
    modullerde = {r["module"] for r in oulad_disk["risk_pivot"]}
    yuvali = {r["module"] for r in oulad_disk["slot_means"]}
    assert satirlar[son].split()[1:] == [",".join(sorted(modullerde - yuvali))]
    assert sum(r["n"] for r in oulad_disk["slot_means"]) == sum(int(s[4]) for s in notebook)


@OULAD_YOK
@pytest.mark.parametrize("ad,dil", OULAD_NOTEBOOKLAR)
@pytest.mark.parametrize("sinyal", SINYALLER)
def test_notebook02_sinyaller(ad, dil, sinyal, oulad_disk):
    metin = _oulad_hucre(ad, f'signal_table(train, "{sinyal}"')
    kv = _anahtar_deger(metin)
    assert "split=train" in metin.splitlines()
    train = next(s for s in oulad_disk["split"] if s["part"] == "train")["rows"]
    assert int(kv["rows"]) == train
    eksik_nb = LABELS_BY_LANG[dil]["missing"]
    eksik_paket = LABELS_BY_LANG["tr"]["missing"]
    okunan = [(eksik_paket if b == eksik_nb else b, n, o) for b, n, o in _dilim_satirlari(metin)]
    paket = [(r["bin"], r["n"], f"{r['rate']:.6f}") for r in oulad_disk["signals"][sinyal]]
    assert okunan == paket
    assert sum(n for _, n, _ in okunan) == train


@OULAD_YOK
@pytest.mark.parametrize("ad,dil", OULAD_NOTEBOOKLAR)
def test_notebook02_veri_notlari_ve_katalog(ad, dil, oulad_disk):
    metin = _oulad_hucre(ad, 'print("ggg_cutoff_window")')
    satirlar = _metin_satirlari(metin, "ggg_cutoff_window", "ggg_non_exam_in_window")
    assert satirlar[0].split() == [
        "code_presentation", "n_rows", "n_expected_min", "n_expected_max", "score_mean_missing",
        "vle_clicks_positive"]
    notebook = [tuple(s.split()) for s in satirlar[1:]]
    paket = [
        (r["presentation"], str(r["n_rows"]), str(r["n_expected_min"]), str(r["n_expected_max"]),
         str(r["score_mean_missing"]), str(r["vle_clicks_positive"]))
        for r in oulad_disk["data_notes"]["ggg"]
    ]
    assert notebook == paket
    kv = _anahtar_deger(metin)
    assert int(kv["bbb_2014j_only_zero_weight_score"]) == oulad_disk["data_notes"]["bbb_zero_weight"]

    metin = _oulad_hucre(ad, 'print("sociocultural_columns")')
    satirlar = _metin_satirlari(metin, metin.splitlines()[0], "sociocultural_columns")
    notebook = []
    for s in satirlar:
        m = re.match(r"^\s*(\S+)\s+(.+?)\s*$", s)
        assert m, s
        notebook.append((m.group(1), m.group(2)))
    # Notebook kataloğun tüm satırlarını (tanımlayıcı ve hedef dahil) dil karşılığıyla basar (notebook
    # yeniden çalıştırıldıktan sonra); paket yalnızca model özelliklerini taşır, aynı sırayla.
    alan = f"school_{dil}"
    katalog = [(r.column, getattr(r, alan)) for r in sorted_feature_catalog().itertuples(index=False)]
    assert notebook == katalog
    model = [(r["feature"], r[alan]) for r in oulad_disk["feature_map"]]
    assert model == [satir for satir in katalog if satir[0] in {r["feature"] for r in oulad_disk["feature_map"]}]


# --- S1b: grafik dosyaları (figures.charts) -----------------------------------------------------
# Beklenen eşlemeler paketleyiciden okunmaz; burada ayrıca ve açıkça yazılıdır.

ASSET = ROOT / "frontend" / "assets" / "arastirma"
FIGURLER = ASSET / "figurler"
DILLER = ("tr", "en")

# (kimlik, varyant) -> (hafta, figures.json dosya adı)
BEKLENEN_HAFTA = {
    ("M4", None): ("week10", "fig01_roc_egim"),
    ("M6", None): ("week10", "fig02_oran_kaymasi"),
    ("M8", None): ("week10", "fig03_gorulmemis_ders"),
    ("K1", None): ("week10", "fig04_kapasite"),
    ("M9", None): ("week10", "fig05_shap"),
    ("R1", None): ("week11", "fig01_sinyal_kesinlik"),
    ("X3", None): ("week11", "fig02_sinyal_gruplari"),
    ("X1", None): ("week11", "fig03_hedef_ayristirma"),
    ("X2", None): ("week11", "fig04_kural_yakalama"),
    ("X4", None): ("week11", "fig05_erkenlik"),
    ("X5", None): ("week11", "fig06_erkenlik_hedef"),
    ("P1", "sonuc"): ("week11", "fig07_beklentiler"),
    ("P1", "once"): ("week11", "fig07a_beklentiler_once"),
}
# (kimlik, varyant) -> (notebook ailesi, hücre, çıktı, başlık hücresi, alt metin hücresi)
BEKLENEN_NOTEBOOK = {
    ("U1", None): ("01_uci_eda", 4, 0, 3, 3),
    ("U2", None): ("01_uci_eda", 6, 0, 5, 5),
    ("U3", None): ("01_uci_eda", 8, 0, 7, 7),
    ("U4", None): ("01_uci_eda", 9, 0, 7, 7),
    ("U5", None): ("01_uci_eda", 11, 0, 10, 10),
    ("U6", None): ("01_uci_eda", 13, 0, 12, 12),
    ("O1", None): ("02_oulad_eda", 10, 0, 9, 11),
    ("O2", None): ("02_oulad_eda", 13, 0, 12, 14),
    ("O3", None): ("02_oulad_eda", 16, 0, 15, 17),
    ("O4", "n_unsubmitted"): ("02_oulad_eda", 20, 0, 19, 21),
    ("O4", "vle_clicks"): ("02_oulad_eda", 23, 0, 22, 24),
    ("O4", "score_mean"): ("02_oulad_eda", 26, 0, 25, 27),
    ("O4", "score_vs_hist"): ("02_oulad_eda", 29, 0, 28, 30),
}
NOTEBOOK_DOSYALARI = {
    "01_uci_eda": {"tr": "01_uci_eda.ipynb", "en": "01_uci_eda_eng.ipynb"},
    "02_oulad_eda": {"tr": "02_oulad_eda.ipynb", "en": "02_oulad_eda_eng.ipynb"},
}
# Alt metni notebook'ta bulunamayan görseller (uydurulmaz, burada listelenir). Şu an yok.
ALT_METIN_EKSIK: list[tuple[str, str | None, str]] = []


def _png_ciktilari(ad: str) -> list[tuple[int, int, bytes]]:
    """Notebook'taki image/png çıktıları: pakete ve paketleyiciye bakmadan, doğrudan JSON'dan."""
    import base64

    defter = json.loads((ROOT / "notebooks" / ad).read_text(encoding="utf-8"))
    sonuc = []
    for i, hucre in enumerate(defter["cells"]):
        sira = 0
        for cikti in hucre.get("outputs", []):
            png = cikti.get("data", {}).get("image/png")
            if png is not None:
                metin = "".join(png) if isinstance(png, list) else png
                sonuc.append((i, sira, base64.b64decode("".join(metin.split()), validate=True)))
                sira += 1
    return sonuc


def _satirlar(disk: dict, kimlik: str, varyant: str | None, dil: str) -> list[dict]:
    return [
        s for s in disk["figures"]["charts"]
        if (s["id"], s["variant"], s["lang"]) == (kimlik, varyant, dil)
    ]


def test_gorsel_kimlikleri_ve_toplam_satir(disk):
    satirlar = disk["figures"]["charts"]
    beklenen = {*BEKLENEN_HAFTA, *BEKLENEN_NOTEBOOK}
    assert {(s["id"], s["variant"]) for s in satirlar} == beklenen
    assert len(satirlar) == 2 * len(beklenen)
    assert len({s["path"] for s in satirlar}) == len(satirlar)
    for anahtar in beklenen:
        for dil in DILLER:
            assert len(_satirlar(disk, *anahtar, dil)) == 1, (anahtar, dil)
    assert all(set(s) == {"id", "variant", "lang", "path", "title", "alt", "cite_title", "source", "md5"}
               for s in satirlar)


@pytest.mark.parametrize("dil", DILLER)
@pytest.mark.parametrize("anahtar", sorted(BEKLENEN_HAFTA, key=str))
def test_hafta_gorselleri_kopya_ve_figures_json(disk, anahtar, dil):
    hafta, dosya = BEKLENEN_HAFTA[anahtar]
    (satir,) = _satirlar(disk, *anahtar, dil)
    kaynak = ROOT / "data_science" / "oulad" / "reports" / "figures" / hafta / f"{dosya}_{dil}.png"
    assert satir["source"] == f"data_science/oulad/reports/figures/{hafta}/{dosya}_{dil}.png"
    hedef = ASSET / satir["path"]
    assert hedef.is_file(), f"görsel kopyalanmamış: {hedef}"
    assert hedef.read_bytes() == kaynak.read_bytes()
    assert hashlib.md5(hedef.read_bytes()).hexdigest() == satir["md5"] == hashlib.md5(kaynak.read_bytes()).hexdigest()
    kayit = next(k for k in _json(f"data_science/oulad/reports/figures/{hafta}/figures.json") if k["dosya"] == dosya)
    assert satir["title"] == kayit[f"başlık_{dil}"]
    assert satir["alt"] == kayit[f"alt_{dil}"]
    assert satir["cite_title"] == satir["title"]


@pytest.mark.parametrize("dil", DILLER)
@pytest.mark.parametrize("anahtar", sorted(BEKLENEN_NOTEBOOK, key=str))
def test_notebook_gorselleri_cikarilmis_ve_baslik_alt_notebooktan(disk, anahtar, dil):
    aile, hucre, cikti, baslik_hucre, alt_hucre = BEKLENEN_NOTEBOOK[anahtar]
    ad = NOTEBOOK_DOSYALARI[aile][dil]
    (satir,) = _satirlar(disk, *anahtar, dil)
    assert satir["source"] == f"notebooks/{ad}#hucre={hucre},cikti={cikti}"
    ciktilar = {(h, s): b for h, s, b in _png_ciktilari(ad)}
    hedef = ASSET / satir["path"]
    assert hedef.is_file(), f"görsel çıkarılmamış: {hedef}"
    assert hedef.read_bytes() == ciktilar[(hucre, cikti)]
    assert hashlib.md5(ciktilar[(hucre, cikti)]).hexdigest() == satir["md5"]
    defter = json.loads((ROOT / "notebooks" / ad).read_text(encoding="utf-8"))
    baslik_md = "".join(defter["cells"][baslik_hucre]["source"])
    alt_md = "".join(defter["cells"][alt_hucre]["source"])
    assert defter["cells"][baslik_hucre]["cell_type"] == "markdown"
    assert baslik_md.lstrip().splitlines()[0].lstrip("#").strip() == satir["title"]
    if satir["alt"] is not None:
        assert satir["alt"] in alt_md and satir["alt"].strip()
    else:
        assert (anahtar[0], anahtar[1], dil) in ALT_METIN_EKSIK


@pytest.mark.parametrize("aile", sorted(NOTEBOOK_DOSYALARI))
@pytest.mark.parametrize("dil", DILLER)
def test_notebook_gorsel_sayisi_ciktilardakiyle_ayni(disk, aile, dil):
    ad = NOTEBOOK_DOSYALARI[aile][dil]
    satirlar = [s for s in disk["figures"]["charts"] if s["source"].startswith(f"notebooks/{ad}#")]
    assert len(satirlar) == len(_png_ciktilari(ad))
    assert len(satirlar) == sum(1 for (a, *_) in BEKLENEN_NOTEBOOK.values() if a == aile)


def test_notebook_atif_basligi_o4_grup_basligi_digerleri_kendi_basligi(disk):
    for dil in DILLER:
        o4 = {s["cite_title"] for s in disk["figures"]["charts"] if s["id"] == "O4" and s["lang"] == dil}
        assert len(o4) == 1
        assert o4 != {s["title"] for s in disk["figures"]["charts"] if s["id"] == "O4" and s["lang"] == dil}
        for s in disk["figures"]["charts"]:
            if s["id"] != "O4":
                assert s["cite_title"] == s["title"]


def test_gorsel_basliklari_ve_alt_yazilari_dolu_eksikler_listede(disk):
    satirlar = disk["figures"]["charts"]
    assert all(isinstance(s["title"], str) and s["title"].strip() for s in satirlar)
    assert all(isinstance(s["cite_title"], str) and s["cite_title"].strip() for s in satirlar)
    eksik = [(s["id"], s["variant"], s["lang"]) for s in satirlar if s["alt"] is None]
    assert eksik == ALT_METIN_EKSIK, f"alt metni eksik görseller: {eksik}"
    assert all(s["alt"].strip() for s in satirlar if s["alt"] is not None)


def test_figurler_dizini_tam_olarak_paketteki_gorseller(disk):
    diskte = {str(p.relative_to(ASSET)) for p in FIGURLER.rglob("*") if p.is_file()}
    assert diskte == {s["path"] for s in disk["figures"]["charts"]}
    for s in disk["figures"]["charts"]:
        assert hashlib.md5((ASSET / s["path"]).read_bytes()).hexdigest() == s["md5"], s["path"]


def test_paketleyici_eslemesiz_goruntude_durur(tmp_path):
    """Eşlemede olmayan bir görsel varsa paketleyici sessizce geçmez, hata verir."""
    import shutil

    kopya = tmp_path / "notebooks"
    kopya.mkdir()
    ad = "01_uci_eda.ipynb"
    defter = json.loads((ROOT / "notebooks" / ad).read_text(encoding="utf-8"))
    ek = next(c for c in defter["cells"] if c["cell_type"] == "code" and c.get("outputs"))
    ek["outputs"].append(
        {"output_type": "display_data", "data": {"image/png": next(
            o["data"]["image/png"] for c in defter["cells"] for o in c.get("outputs", []) if "data" in o
            and "image/png" in o["data"])}, "metadata": {}}
    )
    (kopya / ad).write_text(json.dumps(defter), encoding="utf-8")
    shutil.copy(ROOT / "notebooks" / "01_uci_eda_eng.ipynb", kopya / "01_uci_eda_eng.ipynb")
    for dosya in ("02_oulad_eda.ipynb", "02_oulad_eda_eng.ipynb"):
        shutil.copy(ROOT / "notebooks" / dosya, kopya / dosya)
    with pytest.raises(ValueError, match="eşlemesiz görsel"):
        paketi._notebook_gorselleri_paket(tmp_path)
