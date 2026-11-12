"""Araştırma paketi: model.*, rule.roc_auc, figures.captions.week11 ve ek.* (belirtim v2 bölüm 2.3 + ek analizler).

test_arastirma_paketi.py'deki fixture'lar ve yardımcılar yeniden kullanılır. Beklenen değerler
kaynak JSON'lardan, ham öznitelik parquet'inden, docs/on_kayit_md5.txt'ten ve diskteki ön kayıt
dosyalarından okunur; testte elle yazılmış beklenen sayı yalnızca görevin açıkça istediği üçüdür:
hist_rate_distinct_train == 8, test_metrics 5 set x 2 model, ek.summary 5/3/2.

Notebook 03 tabloları: yalnızca pakette karşılığı olan basılı tablolar karşılaştırılır. Karşılığı
olmayanlar (özellik sütun listesi, modül başına n_expected_zero, GGG sunum tablosu, rule_metrics
total/rows tabloları, OZET'teki kural kesinlikleri) bu dosyada sınanmaz.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import test_arastirma_paketi as ana  # noqa: E402  (aynı dizindeki testler)

from data_science.oulad import PROCESSED_OULAD_DIR  # noqa: E402
from data_science.oulad.dataset import FEATURES_NAME  # noqa: E402

paketi = ana.paketi
disk = ana.disk
taze = ana.taze

NOTEBOOK03 = ["03_oulad_model.ipynb", "03_oulad_model_eng.ipynb"]
DONEMLER = ("validation", "test")


def _kaynak_json(ad: str):
    return ana._json(paketi.GIRDILER[ad])


@pytest.fixture(scope="module")
def ek_kaynak() -> dict:
    return _kaynak_json("ek_metrics")


@pytest.fixture(scope="module")
def model_kaynak() -> dict:
    return _kaynak_json("model_metrics")


@pytest.fixture(scope="module")
def ozellik() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_OULAD_DIR / FEATURES_NAME, engine="pyarrow")


# --- Paket: model.* ve rule.roc_auc -------------------------------------------------------------


def test_model_json_alanlari_aynen(disk, model_kaynak):
    m = disk["model"]
    assert m["selected_params"] == model_kaynak["selected_params"]
    assert m["test_metrics"] == model_kaynak["test_metrics"]
    assert m["paired"] == model_kaynak["paired_differences"]
    assert m["validation_rows"] == model_kaynak["validation"]["rows"]
    assert m["calibration"] == model_kaynak["calibration"]
    assert m["lomo"] == model_kaynak["lomo"]
    assert m["within_module"] == model_kaynak["within_module"]
    assert disk["rule"]["roc_auc"] == _kaynak_json("rule_metrics")["roc_auc"]


def test_model_test_metrics_bes_set_iki_model_alti_metrik(disk):
    tm = disk["model"]["test_metrics"]
    assert len(tm) == 5
    for set_adi, modeller in tm.items():
        assert len(modeller) == 2, set_adi
        for model_adi, metrikler in modeller.items():
            assert len(metrikler) == 6, (set_adi, model_adi)
            assert all(set(v) == {"estimate", "low", "high"} for v in metrikler.values())


def test_model_paired_bes_karsilastirma_iki_model_uc_metrik(disk):
    paired = disk["model"]["paired"]
    assert len(paired) == 2
    for model_adi, karsilastirmalar in paired.items():
        assert len(karsilastirmalar) == 5, model_adi
        for ad, metrikler in karsilastirmalar.items():
            assert len(metrikler) == 3, (model_adi, ad)
            assert all(set(v) == {"estimate", "low", "high"} for v in metrikler.values())


def test_model_module_roc_kaynakla_ayni(disk, model_kaynak):
    satirlar = disk["model"]["module_roc"]
    assert all(set(r) == {"set", "module", "period", "n", "n_positive", "roc_auc"} for r in satirlar)
    dogrulama = [r for r in satirlar if r["period"] == "validation"]
    test = [r for r in satirlar if r["period"] == "test"]
    assert len(dogrulama) + len(test) == len(satirlar)
    assert [(r["set"], r["module"], r["n"], r["n_positive"], r["roc_auc"]) for r in dogrulama] == [
        (r["set"], r["code_module"], r["n"], r["n_positive"], r["roc_auc"])
        for r in model_kaynak["validation"]["modules"]["rows"]
    ]
    beklenen = [
        (set_adi, r["code_module"], r["n"], r["n_positive"], deger)
        for r in model_kaynak["modules"]["rows"]
        for set_adi, deger in r["roc_auc"].items()
    ]
    assert [(r["set"], r["module"], r["n"], r["n_positive"], r["roc_auc"]) for r in test] == beklenen


def test_model_presentations_ham_veriyle_bagimsiz_sayim(disk, ozellik):
    beklenen = []
    for sunum in sorted(ozellik["code_presentation"].astype(str).unique()):
        parca = ozellik.loc[ozellik["code_presentation"].astype(str) == sunum]
        bolumler = set(parca["split"].astype(str))
        assert len(bolumler) == 1
        beklenen.append(
            {
                "presentation": sunum,
                "split": bolumler.pop(),
                "n": len(parca),
                "n_positive": int((parca["at_risk"] == 1).sum()),
            }
        )
    assert disk["model"]["presentations"] == beklenen
    assert sum(p["n"] for p in beklenen) == len(ozellik)
    if "oulad" in disk:
        assert sum(p["n"] for p in beklenen) == disk["oulad"]["n_rows_sample"]


def test_model_base_rate_ve_hist_rate_distinct_train(disk, ozellik):
    m = disk["model"]
    assert m["hist_rate_distinct_train"] == 8
    train = ozellik.loc[ozellik["split"].astype(str) == "train"]
    assert m["hist_rate_distinct_train"] == pd.to_numeric(train["hist_module_risk_rate"], errors="coerce").nunique()
    test = ozellik.loc[ozellik["split"].astype(str) == "test"]
    satirlar = m["base_rate"]
    assert [r["module"] for r in satirlar] == sorted(test["code_module"].astype(str).unique())
    for r in satirlar:
        t = test.loc[test["code_module"].astype(str) == r["module"]]
        tr = train.loc[train["code_module"].astype(str) == r["module"]]
        assert r["n"] == len(t)
        assert r["n_positive"] == int((t["at_risk"] == 1).sum())
        assert r["positive_rate"] == float(t["at_risk"].mean())
        assert r["train_n"] == len(tr)
        assert r["train_n_positive"] == int(tr["at_risk"].sum())
    assert sum(r["n"] for r in satirlar) == len(test)


def test_model_ve_ek_deterministik_ve_diskle_senkron(disk, taze):
    ikinci = paketi.build_package(oulad=None)
    for yol in ("model", "ek", "rule", "figures"):
        assert taze[yol] == ikinci[yol], f"deterministik degil: {yol}"
        assert disk[yol] == taze[yol], f"diskle senkron degil: {yol}"
    assert paketi.render(taze) == paketi.render(ikinci)
    yazilan = json.loads(paketi.render(taze))
    for yol in ("model", "ek"):
        assert yazilan[yol] == taze[yol]


# --- Paket: figures.captions.week11 -------------------------------------------------------------


def test_figures_captions_week11(disk):
    kayitlar = disk["figures"]["captions"]["week11"]
    assert kayitlar == ana._json(paketi.GIRDILER["figures_week11"])
    assert [k["dosya"].split("_")[0] for k in kayitlar] == [
        "fig01", "fig02", "fig03", "fig04", "fig05", "fig06", "fig07", "fig07a",
    ]
    for kayit in kayitlar:
        assert set(kayit) == {"dosya", "başlık_tr", "başlık_en", "alt_tr", "alt_en"}
        assert all(isinstance(v, str) and v.strip() for v in kayit.values()), kayit["dosya"]


# --- Paket: ek.* --------------------------------------------------------------------------------


def _bir(satirlar: list[dict], **kriter) -> dict:
    bulunan = [s for s in satirlar if all(s[k] == v for k, v in kriter.items())]
    assert len(bulunan) == 1, (kriter, len(bulunan))
    return bulunan[0]


def _blok_ile_karsilastir(satir: dict, blok: dict) -> None:
    if blok.get("undefined") is True:
        assert satir["undefined"] is True
        assert satir["reason"] == blok["reason"]
        assert not {"roc_auc", "n", "precision_20"} & set(satir)
        return
    w = blok["within_module_20"]
    assert satir["undefined"] is False
    assert satir["n"] == blok["n"] and satir["n_positive"] == blok["n_positive"]
    assert satir["roc_auc"] == blok["roc_auc"]
    assert satir["module_mean_roc_auc"] == blok["module_mean_roc_auc"]["roc_auc"]
    assert (satir["n_flagged"], satir["n_hit"]) == (w["n_flagged"], w["n_hit"])
    assert (satir["precision_20"], satir["recall_20"]) == (w["precision"], w["recall"])


def test_ek_e1(disk, ek_kaynak):
    e1, src = disk["ek"]["e1"], ek_kaynak["e1"]
    assert e1["target"] == src["target"] and e1["counts"] == src["counts"]
    assert e1["group_of"] == ek_kaynak["group_of"]
    beklenen_sayi = 0
    for set_adi, modeller in src["results"].items():
        for model_adi, girdi in modeller.items():
            for donem in DONEMLER:
                _blok_ile_karsilastir(_bir(e1["rows"], set=set_adi, model=model_adi, period=donem), girdi[donem])
                beklenen_sayi += 1
    assert len(e1["rows"]) == beklenen_sayi
    esli = 0
    for model_adi, karsilastirmalar in src["paired_vs_general"].items():
        for ad, donemler in karsilastirmalar.items():
            for donem in DONEMLER:
                for metrik, deger in donemler[donem].items():
                    satir = _bir(e1["paired_vs_general"], model=model_adi, comparison=ad, period=donem, metric=metrik)
                    assert (satir["estimate"], satir["low"], satir["high"]) == (
                        deger["estimate"], deger["low"], deger["high"])
                    esli += 1
    assert len(e1["paired_vs_general"]) == esli


def test_ek_e2(disk, ek_kaynak):
    e2, src = disk["ek"]["e2"], ek_kaynak["e2"]
    assert e2["counts"] == src["counts"]
    assert e2["b7_rule2_hits"] == ek_kaynak["b7_rule2_hits"]
    assert set(src["targets"]) == set(src["counts"])
    sayi = 0
    for hedef, blok in src["targets"].items():
        for set_adi, modeller in blok["results"].items():
            for model_adi, girdi in modeller.items():
                for donem in DONEMLER:
                    _blok_ile_karsilastir(
                        _bir(e2["rows"], target=hedef, set=set_adi, model=model_adi, period=donem), girdi[donem])
                    sayi += 1
    assert len(e2["rows"]) == sayi
    esli = 0
    for hedef, blok in src["targets"].items():
        for model_adi, karsilastirmalar in blok.get("paired_vs_general", {}).items():
            for ad, donemler in karsilastirmalar.items():
                for donem in DONEMLER:
                    for metrik, deger in donemler[donem].items():
                        satir = _bir(e2["paired_vs_general"], target=hedef, model=model_adi, comparison=ad,
                                     period=donem, metric=metrik)
                        assert satir["estimate"] == deger["estimate"]
                        esli += 1
    assert len(e2["paired_vs_general"]) == esli


def test_ek_e3_satirlar_cohort_ve_ikincil(disk, ek_kaynak):
    e3, src = disk["ek"]["e3"], ek_kaynak["e3"]
    assert e3["cohort"] == src["cohort"]
    assert e3["cutoffs"] == src["cutoffs"] and e3["views"] == src["views"]
    sayi = 0
    for anahtar, blok in src["cutoff_results"].items():
        kesim = int(anahtar)
        for hedef, hedef_blok in blok["targets"].items():
            assert _bir(e3["counts"], cutoff=kesim, target=hedef)["counts"] == hedef_blok["counts"]
            for gorunum in src["views"]:
                for set_adi, modeller in hedef_blok["results"].items():
                    for model_adi, girdi in modeller.items():
                        for donem in DONEMLER:
                            satir = _bir(e3["rows"], cutoff=kesim, view=gorunum, target=hedef, set=set_adi,
                                         model=model_adi, period=donem)
                            _blok_ile_karsilastir(satir, girdi[gorunum][donem])
                            sayi += 1
        ikincil = _bir(e3["secondary"], cutoff=kesim)
        assert ikincil["status"] == blok["secondary"]["status"]
        assert ikincil["reason"] == blok["secondary"].get("reason")
        assert ikincil["counts"] == blok["secondary"]["counts"]
        for set_adi, modeller in blok["secondary"]["results"].items():
            for model_adi, girdi in modeller.items():
                for donem in DONEMLER:
                    _blok_ile_karsilastir(
                        _bir(ikincil["rows"], set=set_adi, model=model_adi, period=donem), girdi[donem])
    assert len(e3["rows"]) == sayi


def test_ek_e3_tanimsiz_ikincil_undefined_ve_nedeni(disk, ek_kaynak):
    tanimsiz = [
        (s["cutoff"], r)
        for s in disk["ek"]["e3"]["secondary"]
        for r in s["rows"]
        if r["undefined"]
    ]
    kaynak_tanimsiz = [
        (int(k), set_adi, donem)
        for k, blok in ek_kaynak["e3"]["cutoff_results"].items()
        for set_adi, modeller in blok["secondary"]["results"].items()
        for girdi in modeller.values()
        for donem in DONEMLER
        if girdi[donem].get("undefined") is True
    ]
    assert tanimsiz, "ek_metrics.json'da tanımsız ikincil sonuç beklenir (kesim 14, test)"
    assert sorted((k, r["set"], r["period"]) for k, r in tanimsiz) == sorted(kaynak_tanimsiz)
    assert all(isinstance(r["reason"], str) and r["reason"] for _, r in tanimsiz)


def test_ek_e3_60_gun_ikincil_general_e1_ile_ayni(disk):
    ek = disk["ek"]
    ikincil = next(s for s in ek["e3"]["secondary"] if s["cutoff"] == 60)
    for donem in DONEMLER:
        a = _bir(ikincil["rows"], set="GENERAL", model="hgb", period=donem)
        b = _bir(ek["e1"]["rows"], set="GENERAL", model="hgb", period=donem)
        assert a["undefined"] is False and b["undefined"] is False
        a_ve_b = {k: v for k, v in a.items() if k not in ("cutoff",)}
        assert a_ve_b == b, donem


def test_ek_beklentiler(disk, ek_kaynak):
    beklentiler = disk["ek"]["expectations"]
    assert [b["id"] for b in beklentiler] == [f"B{i}" for i in range(1, 11)]
    kaynak = {**ek_kaynak["expectations"], **ek_kaynak["e3"]["expectations"]}
    assert set(kaynak) == {b["id"] for b in beklentiler}
    for b in beklentiler:
        k = kaynak[b["id"]]
        assert set(b) == {"id", "expectation", "criterion", "validation", "test", "result"}
        assert (b["expectation"], b["criterion"], b["result"]) == (k["expectation"], k["criterion"], k["result"])
        assert b["validation"] == k["validation"] and b["test"] == k["test"]
        assert all(isinstance(b[d]["holds"], bool) for d in DONEMLER)
        # Karar kuralı (ek_metrics.json notes): ikisinde sağlanırsa tuttu, ikisinde de değilse tutmadı, aksi belirsiz.
        v, t = b["validation"]["holds"], b["test"]["holds"]
        assert b["result"] == ("tuttu" if v and t else "tutmadı" if not v and not t else "belirsiz"), b["id"]


def test_ek_summary_5_3_2(disk, ek_kaynak):
    summary = disk["ek"]["summary"]
    assert summary == {"tuttu": 5, "tutmadı": 3, "belirsiz": 2, "total": 10}
    kaynak = {**ek_kaynak["expectations"], **ek_kaynak["e3"]["expectations"]}
    sayim = Counter(b["result"] for b in kaynak.values())
    assert {k: v for k, v in summary.items() if k != "total"} == dict(sayim)
    assert summary["total"] == sum(sayim.values()) == len(disk["ek"]["expectations"])


def test_ek_recall_by_outcome_kaynaktan(disk, ek_kaynak):
    satirlar = disk["ek"]["recall_by_outcome"]
    assert [s["period"] for s in satirlar] == list(DONEMLER)
    protocol, counts, b7 = ek_kaynak["protocol"], ek_kaynak["e2"]["counts"], ek_kaynak["b7_rule2_hits"]
    for s in satirlar:
        donem = s["period"]
        sunum = protocol[f"{donem}_presentation"]
        assert s["presentation"] == sunum
        fail_pozitif = counts["KALDI"][f"{donem}_{sunum}"]["n_positive"]
        cikis_pozitif = counts["BIRAKTI"][f"{donem}_{sunum}"]["n_positive"]
        assert (s["n_fail"], s["n_positive_fail"]) == (b7[donem]["n_fail"], fail_pozitif)
        assert (s["n_withdrawn"], s["n_positive_withdrawn"]) == (b7[donem]["n_withdrawn"], cikis_pozitif)
        assert s["recall_fail"] == b7[donem]["n_fail"] / fail_pozitif
        assert s["recall_withdrawn"] == b7[donem]["n_withdrawn"] / cikis_pozitif
        assert (s["n_flagged"], s["n_hit"]) == (b7[donem]["n_flagged"], b7[donem]["n_hit"])
        assert 0 < s["recall_fail"] < 1 and 0 < s["recall_withdrawn"] < 1


def test_ek_recall_by_outcome_fig04_alt_metniyle_tutarli(disk):
    """fig04 alt metni (figures.json, aynı kaynaktan üretilmiş) aynı sayıları taşır."""
    alt = next(k for k in disk["figures"]["captions"]["week11"] if k["dosya"].startswith("fig04"))["alt_en"]
    for s in disk["ek"]["recall_by_outcome"]:
        assert f"Fail {s['n_fail']:,} / {s['n_positive_fail']:,}" in alt
        assert f"Withdrawn {s['n_withdrawn']:,} / {s['n_positive_withdrawn']:,}" in alt


def test_ek_pre_registration(disk, ek_kaynak):
    kayit = disk["ek"]["pre_registration"]
    assert len(kayit) >= 3
    for ad, blok in kayit.items():
        diskte = hashlib.md5((ROOT / "docs" / ad).read_bytes()).hexdigest()
        assert blok["md5"] == diskte, ad
        assert blok["history"][-1]["md5"] == diskte, ad
        assert all(set(h) == {"md5", "time"} for h in blok["history"]), ad
    # on_kayit_md5.txt'ten bağımsız ayrıştırma: 'md5  yol' satırı + zaman satırı, dosya sırasıyla.
    satirlar = (ROOT / "docs" / "on_kayit_md5.txt").read_text(encoding="utf-8").splitlines()
    beklenen: dict[str, list[dict]] = {}
    for i in range(0, len(satirlar) - 1, 2):
        md5, yol = satirlar[i].split()
        beklenen.setdefault(Path(yol).name, []).append({"md5": md5, "time": satirlar[i + 1].strip()})
    assert {ad: blok["history"] for ad, blok in kayit.items()} == beklenen
    assert kayit == ek_kaynak["pre_registration_md5"]


# --- Notebook 03 (TR ve EN) basılan tablolar paketle aynı ----------------------------------------


def _bicim(deger) -> str:
    if deger is None:
        return "NaN"
    if isinstance(deger, bool):
        return str(deger)
    if isinstance(deger, int):
        return str(deger)
    if isinstance(deger, float):
        return f"{deger:.6f}"
    return str(deger)


def _nb_tablo(metin: str, kolonlar: list[str]) -> list[list[str]]:
    """Başlığı `kolonlar` olan show_table çıktısının veri satırları (başlık hücrede tek olmalı)."""
    satirlar = metin.splitlines()
    basliklar = [i for i, s in enumerate(satirlar) if s.split() == kolonlar]
    assert len(basliklar) == 1, f"başlık {kolonlar} {len(basliklar)} kez geçiyor"
    n_yeri = kolonlar.index("n")
    sonuc = []
    for s in satirlar[basliklar[0] + 1:]:
        parcalar = s.split()
        if len(parcalar) != len(kolonlar) or not parcalar[n_yeri].isdigit():
            break
        sonuc.append(parcalar)
    assert sonuc, f"tablo boş: {kolonlar}"
    return sonuc


def _eslestir(notebook: list[list[str]], beklenen: list[list[str]]) -> None:
    assert sorted(notebook) == sorted(beklenen)


def _test_n(m: dict) -> tuple[int, int]:
    """Notebook TEST_N, TEST_N_POSITIVE: test modül satırlarının toplamı (set başına aynı)."""
    toplamlar = set()
    for set_adi in m["selected_params"]:
        satirlar = [r for r in m["module_roc"] if r["period"] == "test" and r["set"] == set_adi]
        toplamlar.add((sum(r["n"] for r in satirlar), sum(r["n_positive"] for r in satirlar)))
    assert len(toplamlar) == 1
    return toplamlar.pop()


def _val_n(m: dict) -> tuple[int, int]:
    """Notebook VAL_N, VAL_N_POSITIVE: GENERAL doğrulama modül satırlarının toplamı."""
    satirlar = [r for r in m["module_roc"] if r["period"] == "validation" and r["set"] == "GENERAL"]
    return sum(r["n"] for r in satirlar), sum(r["n_positive"] for r in satirlar)


@pytest.mark.parametrize("ad", NOTEBOOK03)
def test_notebook03_sunumlar_ve_secilen_ayarlar(ad, disk):
    m = disk["model"]
    metin = ana._oulad_hucre(ad, "show_table(presentation_counts(frame))")
    _eslestir(
        _nb_tablo(metin, ["code_presentation", "split", "n", "n_positive"]),
        [[p["presentation"], p["split"], str(p["n"]), str(p["n_positive"])] for p in m["presentations"]],
    )
    val_n, val_pos = _val_n(m)
    beklenen = []
    for set_adi, modeller in m["selected_params"].items():
        for model_adi, secim in modeller.items():
            params = ",".join(f"{k}={v}" for k, v in secim["params"].items())
            beklenen.append(
                [set_adi, model_adi, "validation", str(val_n), str(val_pos), _bicim(secim["val_log_loss"]), params]
            )
    notebook = _nb_tablo(metin, ["set", "model", "scope", "n", "n_positive", "val_log_loss", "params"])
    assert len(notebook) == 10
    _eslestir(notebook, beklenen)


@pytest.mark.parametrize("ad", NOTEBOOK03)
def test_notebook03_test_metrikleri_ve_esli_farklar(ad, disk):
    m = disk["model"]
    n, pos = _test_n(m)
    metin = ana._oulad_hucre(ad, 'report["test_metrics"][set_name][model_name]')
    beklenen = [
        [set_adi, model_adi, metrik, _bicim(d["estimate"]), _bicim(d["low"]), _bicim(d["high"]), str(n), str(pos)]
        for set_adi, modeller in m["test_metrics"].items()
        for model_adi, metrikler in modeller.items()
        for metrik, d in metrikler.items()
    ]
    notebook = _nb_tablo(metin, ["set", "model", "metric", "estimate", "low", "high", "n", "n_positive"])
    assert len(notebook) == 60
    _eslestir(notebook, beklenen)
    beklenen = [
        [model_adi, karsilastirma, metrik, _bicim(d["estimate"]), _bicim(d["low"]), _bicim(d["high"]), str(n), str(pos)]
        for model_adi, karsilastirmalar in m["paired"].items()
        for karsilastirma, metrikler in karsilastirmalar.items()
        for metrik, d in metrikler.items()
    ]
    notebook = _nb_tablo(metin, ["model", "contrast", "metric", "estimate", "low", "high", "n", "n_positive"])
    assert len(notebook) == 30
    _eslestir(notebook, beklenen)


@pytest.mark.parametrize("ad", NOTEBOOK03)
def test_notebook03_iki_donem(ad, disk):
    m = disk["model"]
    n, pos = _test_n(m)
    val_n, val_pos = _val_n(m)
    metin = ana._oulad_hucre(ad, 'show_figure("fig01_roc_egim")')
    kolonlar = ["set", "model", "n", "n_positive", "validation_n", "validation_n_positive",
                "validation_roc_auc", "test_roc_auc", "test_roc_auc_low", "test_roc_auc_high"]
    beklenen = []
    for set_adi in m["selected_params"]:
        dogrulama = next(r["roc_auc"] for r in m["validation_rows"] if r["set"] == set_adi and r["model"] == "hgb")
        test = m["test_metrics"][set_adi]["hgb"]["roc_auc"]
        beklenen.append([set_adi, "hgb", str(n), str(pos), str(val_n), str(val_pos), _bicim(dogrulama),
                         _bicim(test["estimate"]), _bicim(test["low"]), _bicim(test["high"])])
    notebook = _nb_tablo(metin, kolonlar)
    assert len(notebook) == 5
    _eslestir(notebook, beklenen)
    # Notebook satırları test ROC AUC'ye göre azalan sıralıdır.
    assert [float(s[7]) for s in notebook] == sorted((float(s[7]) for s in notebook), reverse=True)


@pytest.mark.parametrize("ad", NOTEBOOK03)
def test_notebook03_taban_oran(ad, disk, model_kaynak):
    m = disk["model"]
    metin = ana._oulad_hucre(ad, 'show_figure("fig02_oran_kaymasi")')
    (ozet,) = _nb_tablo(metin, ["split", "n", "n_positive", "n_distinct_hist_module_risk_rate"])
    train = [p for p in m["presentations"] if p["split"] == "train"]
    assert ozet[0] == "train"
    assert int(ozet[1]) == sum(p["n"] for p in train)
    assert int(ozet[2]) == sum(p["n_positive"] for p in train)
    assert int(ozet[3]) == m["hist_rate_distinct_train"] == 8

    kolonlar = ["code_module", "n", "n_positive", "hist_module_risk_rate", "positive_rate",
                "test_n_distinct_hist_module_risk_rate", "train_n", "train_n_positive",
                "train_n_distinct_hist_module_risk_rate"]
    beklenen = [
        [r["module"], str(r["n"]), str(r["n_positive"]), _bicim(r["hist_module_risk_rate"]), _bicim(r["positive_rate"]),
         str(r["test_n_distinct_hist_module_risk_rate"]), str(r["train_n"]), str(r["train_n_positive"]),
         str(r["train_n_distinct_hist_module_risk_rate"])]
        for r in m["base_rate"]
    ]
    assert _nb_tablo(metin, kolonlar) == beklenen

    sets = list(m["selected_params"])
    kolonlar = ["model", "code_module", "n", "n_positive", *sets]
    beklenen = []
    for modul in dict.fromkeys(r["module"] for r in m["module_roc"] if r["period"] == "test"):
        satirlar = [r for r in m["module_roc"] if r["period"] == "test" and r["module"] == modul]
        assert [r["set"] for r in satirlar] == sets
        beklenen.append([model_kaynak["modules"]["model"], modul, str(satirlar[0]["n"]), str(satirlar[0]["n_positive"]),
                         *(_bicim(r["roc_auc"]) for r in satirlar)])
    assert _nb_tablo(metin, kolonlar) == beklenen


@pytest.mark.parametrize("ad", NOTEBOOK03)
def test_notebook03_lomo(ad, disk):
    lomo = disk["model"]["lomo"]
    metin = ana._oulad_hucre(ad, 'show_figure("fig03_gorulmemis_ders")')
    kolonlar = list(lomo["rows"][0])
    assert all(list(r) == kolonlar for r in lomo["rows"])
    beklenen = [[_bicim(r[k]) for k in kolonlar] for r in lomo["rows"]]
    assert _nb_tablo(metin, kolonlar) == beklenen
    beklenen = [
        [set_adi, _bicim(d["n"]), _bicim(d["n_positive"]), _bicim(d["roc_auc"]), _bicim(d["brier"])]
        for set_adi, d in lomo["mean"].items()
    ]
    assert _nb_tablo(metin, ["set", "n", "n_positive", "roc_auc", "brier"]) == beklenen


@pytest.mark.parametrize("ad", NOTEBOOK03)
def test_notebook03_shap_kapasite_ve_sinif_ici(ad, disk):
    m = disk["model"]
    n, pos = _test_n(m)
    metin = ana._oulad_hucre(ad, 'show_figure("fig05_shap")')
    kolonlar = ["set", "model", "feature", "mean_abs_shap", "n", "n_positive", "n_explained"]
    notebook = _nb_tablo(metin, kolonlar)
    assert [(s[2], s[3]) for s in notebook] == [
        (f["feature"], _bicim(f["mean_abs_shap"])) for f in disk["shap"]["features"]]
    assert all(s[4] == str(n) and s[5] == str(pos) for s in notebook)

    metin = ana._oulad_hucre(ad, 'show_figure("fig04_kapasite")')
    kolonlar = ["set", "model", "presentation", "flag_rate", "ranking", "n", "n_positive", "n_flagged", "n_hit",
                "precision", "recall"]
    beklenen = [
        [_bicim(satir["flag_rate"]), siralama,
         *(_bicim(satir[siralama][k]) for k in ("n", "n_positive", "n_flagged", "n_hit", "precision", "recall"))]
        for satir in disk["capacity"]
        for siralama in ("global", "within_module")
    ]
    assert [s[3:] for s in _nb_tablo(metin, kolonlar)] == beklenen

    wm = m["within_module"]
    kolonlar = ["model", "set", "code_module", "n", "n_positive", "n_flagged", "n_hit", "precision", "recall"]
    beklenen = [
        [wm["model"], r["set"], r["code_module"], *(_bicim(r[k]) for k in kolonlar[3:])]
        for r in wm["rows"]
        if r["set"] == "GENERAL"
    ]
    assert _nb_tablo(metin, kolonlar) == beklenen
    kolonlar = ["model", "set", "n", "n_positive", "n_flagged", "n_hit", "precision", "recall"]
    beklenen = [
        [wm["model"], r["set"], *(_bicim(r[k]) for k in kolonlar[2:])]
        for r in wm["total"]
        if r["set"] == "GENERAL"
    ]
    assert _nb_tablo(metin, kolonlar) == beklenen


@pytest.mark.parametrize("ad", NOTEBOOK03)
def test_notebook03_ozet(ad, disk):
    m = disk["model"]
    metin = ana._oulad_hucre(ad, 'print("OZET")')
    kv = dict(s.partition("=")[::2] for s in metin.splitlines() if "=" in s)
    secili = m["within_module"]["model"]

    def aralik(d):
        return f"{d['estimate']:.6f} [{d['low']:.6f}, {d['high']:.6f}]"

    dogrulama_rel = next(r["roc_auc"] for r in m["validation_rows"]
                         if r["set"] == "GENERAL_REL" and r["model"] == secili)
    toplam = next(r for r in m["within_module"]["total"] if r["set"] == "GENERAL")
    assert kv["selected_model"] == secili
    assert kv["test_set"] == "GENERAL"
    assert kv["test_roc_auc"] == aralik(m["test_metrics"]["GENERAL"][secili]["roc_auc"])
    assert kv["history_minus_general_roc_auc"] == aralik(m["paired"][secili]["HISTORY-GENERAL"]["roc_auc"])
    assert kv["general_rel_validation_roc_auc"] == _bicim(dogrulama_rel)
    assert kv["general_rel_test_roc_auc"] == aralik(m["test_metrics"]["GENERAL_REL"][secili]["roc_auc"])
    assert kv["precision_at_20_global"] == _bicim(m["test_metrics"]["GENERAL"][secili]["precision_at_20"]["estimate"])
    assert kv["precision_at_20_within_module"] == _bicim(toplam["precision"])
