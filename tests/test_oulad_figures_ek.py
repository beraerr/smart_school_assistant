"""Ek analiz grafikleri: veri yalnız ek_metrics.json'dan okunur (küçük sahte JSON)."""

from __future__ import annotations

import copy
import json
import re

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.colors import to_rgba

from data_science.oulad import figures

CUTOFFS = [14, 30, 60, 90, 120]
CAUSAL_WORDS = ("çünkü", "neden", "sebep", "yüzünden", "because", "causes", "caused", "due to", "leads to")


def _cell(auc: float) -> dict:
    return {"n": 100, "n_positive": 40, "roc_auc": {"estimate": auc, "low": auc - 0.01, "high": auc + 0.01}}


def _pair(validation: float, test: float) -> dict:
    return {"hgb": {"validation": _cell(validation), "test": _cell(test)}}


def _view_pair(validation: float, test: float) -> dict:
    return {"hgb": {figures._EK_VIEW: {"validation": _cell(validation), "test": _cell(test)}}}


def _fake_report() -> dict:
    e1 = {
        "NOT": _pair(0.77, 0.71),
        "TESLİM": _pair(0.76, 0.735),
        "ETKİNLİK": _pair(0.74, 0.73),
        "NOT_TESLİM": _pair(0.82, 0.78),
        "GENERAL": _pair(0.83, 0.80),
    }
    kaldi = {"GENERAL": _pair(0.84, 0.81), "NOT": _pair(0.78, 0.72), "TESLİM": _pair(0.77, 0.74),
             "ETKİNLİK": _pair(0.77, 0.74)}
    birakti = {"GENERAL": _pair(0.80, 0.77), "NOT": _pair(0.70, 0.66), "TESLİM": _pair(0.71, 0.67),
               "ETKİNLİK": _pair(0.66, 0.69)}
    counts = {
        "KALDI": {"validation_2014B": {"n": 5000, "n_positive": 1578}, "test_2014J": {"n": 8000, "n_positive": 1798}},
        "BIRAKTI": {"validation_2014B": {"n": 5000, "n_positive": 945}, "test_2014J": {"n": 8000, "n_positive": 1329}},
        "referans": {"validation_2014B": {"n": 5403, "n_positive": 2523}, "test_2014J": {"n": 8140, "n_positive": 3127}},
    }
    blocks = {}
    for index, cutoff in enumerate(CUTOFFS):
        blocks[str(cutoff)] = {
            "targets": {
                "referans": {
                    "results": {
                        "GENERAL": _view_pair(0.66 + 0.04 * index, 0.67 + 0.035 * index),
                        "ETKİNLİK": _view_pair(0.64 + 0.03 * index, 0.65 + 0.025 * index),
                    }
                },
                "KALDI": {"results": {"GENERAL": _view_pair(0.70 + 0.03 * index, 0.69 + 0.03 * index)}},
                "BIRAKTI": {"results": {"GENERAL": _view_pair(0.60 + 0.03 * index, 0.59 + 0.03 * index)}},
            }
        }
    results = ["tuttu", "belirsiz", "tuttu", "tutmadı", "tutmadı", "belirsiz", "tutmadı"]
    return {
        "protocol": {"validation_presentation": "2014B", "test_presentation": "2014J", "flag_fraction": 0.2},
        "e1": {"results": e1},
        "e2": {
            "counts": counts,
            "targets": {"referans": {"results": {k: e1[k] for k in figures._E2_ORDER}},
                        "KALDI": {"results": kaldi}, "BIRAKTI": {"results": birakti}},
        },
        "b7_rule2_hits": {
            "validation": {"n_hit": 956, "n_fail": 671, "n_withdrawn": 285},
            "test": {"n_hit": 1245, "n_fail": 742, "n_withdrawn": 503},
        },
        "expectations": {f"B{i + 1}": {"result": value} for i, value in enumerate(results)},
        "e3": {
            "cutoffs": CUTOFFS,
            "cohort": {"cutoff": 120, "n_students": 14059, "n_by_period": {"validation": 5798, "test": 8261}},
            "cutoff_results": blocks,
            "expectations": {"B8": {"result": "tuttu"}, "B9": {"result": "tuttu"}, "B10": {"result": "tuttu"}},
        },
    }


FIG01 = {
    "dosya": "fig01_sinyal_kesinlik",
    "başlık_tr": "Eski başlık",
    "başlık_en": "Old title",
    "alt_tr": "eski alt",
    "alt_en": "old alt",
}


MD5_TEXT = (
    f"{'a' * 32}  docs/ek_analizler_on_kayit.md\nczw, 5 lis 2026, 17:04:25 CET\n"
    f"{'b' * 32}  docs/ek_analizler_on_kayit_eki.md\nczw, 5 lis 2026, 17:39:24 CET\n"
    f"{'c' * 32}  docs/ek_analizler_on_kayit_eki.md\nczw, 5 lis 2026, 17:41:55 CET\n"
    f"{'d' * 32}  docs/ek_analizler_on_kayit_eki2.md\nczw, 5 lis 2026, 18:49:07 CET\n"
)


def _md5_file(tmp_path):
    path = tmp_path / "on_kayit_md5.txt"
    path.write_text(MD5_TEXT, encoding="utf-8")
    return path


def _run(tmp_path, report=None):
    report = _fake_report() if report is None else report
    source = tmp_path / "ek_metrics.json"
    source.write_text(json.dumps(report), encoding="utf-8")
    dest = tmp_path / "week11"
    dest.mkdir()
    (dest / "figures.json").write_text(json.dumps([FIG01], ensure_ascii=False), encoding="utf-8")
    entries = figures.write_ek_figures(source, dest, _md5_file(tmp_path))
    return dest, entries


def _by_name(entries) -> dict:
    return {entry["dosya"]: entry for entry in entries}


def _fake_rule2() -> dict:
    def total(n, positive, precision, hit):
        return {"n": n, "n_positive": positive, "precision": precision, "n_hit": hit}

    def period(presentation, role, shift):
        return {
            "presentation": presentation,
            "role": role,
            "total": [
                {"method": "rule", **total(5000, 2000, 0.60 + shift, 600)},
                {"method": "rule2", **total(5000, 2000, 0.65 + shift, 650)},
                {"method": "general_hgb", **total(5000, 2000, 0.70 + shift, 700)},
            ],
        }

    return {
        "flag_rate": 0.2,
        "signals": {"rule": ["a", "b", "c"], "rule2": ["a", "b"]},
        "periods": [period("2014B", "validation", 0.0), period("2014J", "test", 0.02)],
    }


def _write_rule2(tmp_path, dest):
    source = tmp_path / "rule2_metrics.json"
    source.write_text(json.dumps(_fake_rule2()), encoding="utf-8")
    return figures.write_rule2_figures(source, dest)


def _ek(tmp_path, dest):
    source = tmp_path / "ek_metrics.json"
    source.write_text(json.dumps(_fake_report()), encoding="utf-8")
    return figures.write_ek_figures(source, dest, _md5_file(tmp_path))


def _catalog(dest) -> dict:
    items = json.loads((dest / "figures.json").read_text(encoding="utf-8"))
    names = [item["dosya"] for item in items]
    assert len(names) == len(set(names))
    return {item["dosya"]: item for item in items}


@pytest.mark.parametrize("ek_first", [True, False])
def test_rule2_and_ek_writes_keep_each_others_records(tmp_path, ek_first):
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference_entry,) = _write_rule2(tmp_path, reference)
    reference_pngs = {lang: (reference / f"fig01_sinyal_kesinlik_{lang}.png").read_bytes() for lang in ("tr", "en")}

    dest = tmp_path / "week11"
    dest.mkdir()
    if ek_first:
        ek_entries = _ek(tmp_path, dest)
        _write_rule2(tmp_path, dest)
    else:
        _write_rule2(tmp_path, dest)
        ek_entries = _ek(tmp_path, dest)

    catalog = _catalog(dest)
    assert set(catalog) == {"fig01_sinyal_kesinlik", *figures.EK_FIGURE_FILES}
    assert catalog["fig01_sinyal_kesinlik"] == reference_entry
    for entry in ek_entries:
        assert catalog[entry["dosya"]] == entry
    for lang in ("tr", "en"):
        assert (dest / f"fig01_sinyal_kesinlik_{lang}.png").read_bytes() == reference_pngs[lang]
    for name in figures.EK_FIGURE_FILES:
        for lang in ("tr", "en"):
            assert (dest / f"{name}_{lang}.png").stat().st_size > 0


def test_rule2_rewrite_replaces_only_its_own_record(tmp_path):
    dest = tmp_path / "week11"
    dest.mkdir()
    _ek(tmp_path, dest)
    (dest / "figures.json").write_text(
        json.dumps([FIG01, *_catalog(dest).values()], ensure_ascii=False), encoding="utf-8"
    )
    before = _catalog(dest)
    assert before["fig01_sinyal_kesinlik"] == FIG01
    _write_rule2(tmp_path, dest)
    after = _catalog(dest)
    assert after["fig01_sinyal_kesinlik"] != FIG01
    for name in figures.EK_FIGURE_FILES:
        assert after[name] == before[name]


def test_each_figure_has_tr_and_en_png(tmp_path):
    dest, _ = _run(tmp_path)
    for name in figures.EK_FIGURE_FILES:
        for lang in ("tr", "en"):
            assert (dest / f"{name}_{lang}.png").stat().st_size > 0


def test_catalog_gets_seven_new_records_and_old_one_is_unchanged(tmp_path):
    dest, entries = _run(tmp_path)
    catalog = json.loads((dest / "figures.json").read_text(encoding="utf-8"))
    assert len(entries) == 7
    assert len(catalog) == 8
    assert catalog[0] == FIG01
    assert [item["dosya"] for item in catalog[1:]] == list(figures.EK_FIGURE_FILES)
    for item in catalog[1:]:
        for key in ("başlık_tr", "başlık_en", "alt_tr", "alt_en"):
            assert item[key].strip()
        assert "ek analiz (keşifsel)" in item["alt_tr"]
        assert "exploratory" in item["alt_en"]
        for word in CAUSAL_WORDS:
            assert word not in item["alt_tr"].lower()
            assert word not in item["alt_en"].lower()


def test_rerun_replaces_new_records_without_duplicates(tmp_path):
    dest, _ = _run(tmp_path)
    figures.write_ek_figures(tmp_path / "ek_metrics.json", dest, _md5_file(tmp_path))
    catalog = json.loads((dest / "figures.json").read_text(encoding="utf-8"))
    assert [item["dosya"] for item in catalog] == [FIG01["dosya"], *figures.EK_FIGURE_FILES]
    assert catalog[0] == FIG01


def test_fig07_title_counts_come_from_expectations(tmp_path):
    _, entries = _run(tmp_path)
    fig07 = _by_name(entries)["fig07_beklentiler"]
    assert fig07["başlık_tr"] == "Önceden yazılan 10 beklenti: 5 tuttu, 3 tutmadı, 2 belirsiz"
    changed = _fake_report()
    changed["expectations"]["B3"]["result"] = "tutmadı"
    again = tmp_path / "again"
    again.mkdir()
    _, entries = _run(again, changed)
    fig07 = _by_name(entries)["fig07_beklentiler"]
    assert fig07["başlık_tr"] == "Önceden yazılan 10 beklenti: 4 tuttu, 4 tutmadı, 2 belirsiz"
    assert "4 held, 4 did not hold, 2 inconclusive" in fig07["başlık_en"]


def test_chart_values_come_from_json(tmp_path):
    report = _fake_report()
    # GENERAL'i yükseltmek fig02 başlık iddiasını (tek grup GENERAL'e ulaşmaz) bozmaz.
    # NOT_TESLİM de yükselir: fig02 alt başlık iddiası (fark < 0,03) da bozulmaz.
    report["e1"]["results"]["GENERAL"] = _pair(0.85, 0.9012)
    report["e1"]["results"]["NOT_TESLİM"] = _pair(0.84, 0.89)
    _, entries = _run(tmp_path, report)
    assert "GENERAL 0,901" in entries[0]["alt_tr"]
    assert "GENERAL 0.901" in entries[0]["alt_en"]
    fig = figures._draw_ek_signals(report, "tr")
    try:
        # x ekseni üst sınırı = en yüksek aralık ucu (0.9012 + 0.01) + 0.02
        assert fig.axes[0].get_xlim()[1] == pytest.approx(0.9012 + 0.01 + 0.02)
    finally:
        plt.close(fig)


def test_rule_bar_labels_use_counts_from_json():
    fig = figures._draw_ek_rule(_fake_report(), "tr")
    try:
        texts = [text.get_text() for text in fig.axes[0].texts]
    finally:
        plt.close(fig)
    assert texts.count("%42,5 · 671 / 1.578") == 1
    assert "%30,2 · 285 / 945" in texts and "%41,3 · 742 / 1.798" in texts and "%37,8 · 503 / 1.329" in texts
    fig = figures._draw_ek_rule(_fake_report(), "en")
    try:
        texts = [text.get_text() for text in fig.axes[0].texts]
    finally:
        plt.close(fig)
    assert "42.5% · 671 / 1,578" in texts


def test_expectation_cards_show_id_name_and_result_text():
    fig = figures._draw_ek_expectations(_fake_report(), "tr")
    try:
        texts = [[t.get_text() for t in ax.texts] for ax in fig.axes]
    finally:
        plt.close(fig)
    assert len(texts) == 10
    assert texts[0][0] == "B1" and texts[0][-1] == "Tuttu"
    assert texts[3][-1] == "Tutmadı"
    assert texts[1][-1] == "Belirsiz"


def test_fig06_note_is_under_the_chart():
    for lang in ("tr", "en"):
        fig = figures._draw_ek_early_targets(_fake_report(), lang)
        try:
            label = fig.axes[0].get_xlabel()
        finally:
            plt.close(fig)
        assert figures._EK_LABELS[lang]["late_note"] in label


def test_expectation_count_must_be_ten():
    report = _fake_report()
    del report["e3"]["expectations"]["B10"]
    with pytest.raises(ValueError, match="10 beklenti"):
        figures._ek_expectations(report)


def test_missing_value_stops_instead_of_guessing(tmp_path):
    report = _fake_report()
    report["e1"]["results"]["GENERAL"]["hgb"]["test"]["roc_auc"]["estimate"] = None
    with pytest.raises(ValueError, match="ROC AUC yok"):
        _run(tmp_path, report)


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda r: r["e1"]["results"]["NOT"]["hgb"]["test"]["roc_auc"].update(estimate=0.9), "fig02"),
        (lambda r: r["e1"]["results"]["NOT_TESLİM"]["hgb"]["test"]["roc_auc"].update(estimate=0.70),
         "fig02 alt basligi"),
        (lambda r: r["e1"]["results"]["NOT_TESLİM"]["hgb"]["validation"]["roc_auc"].update(estimate=0.70),
         "fig02 alt basligi"),
        (lambda r: r["e2"]["targets"]["BIRAKTI"]["results"]["GENERAL"]["hgb"]["test"]["roc_auc"].update(estimate=0.95),
         "fig03"),
        (lambda r: r["b7_rule2_hits"]["test"].update(n_fail=100, n_withdrawn=1145), "fig04"),
        (lambda r: r["e3"]["cutoff_results"]["30"]["targets"]["BIRAKTI"]["results"]["GENERAL"]["hgb"][
            figures._EK_VIEW]["test"]["roc_auc"].update(estimate=0.99), "fig06"),
    ],
)
def test_title_claims_that_data_contradicts_stop_the_run(tmp_path, mutate, message):
    report = copy.deepcopy(_fake_report())
    mutate(report)
    with pytest.raises(ValueError, match=message):
        _run(tmp_path, report)


# --- Görsel düzeltmeler: sayı biçimi, fig02/04/05/06/07/07a -------------------
RESULT_WORDS = ("Tuttu", "Tutmadı", "Belirsiz", "Held", "Did not hold", "Inconclusive")


def test_tr_formatter():
    assert figures._format_number(0.85, "tr") == "0,85"
    assert figures._format_number(0.5, "tr", percent=True) == "%50"
    assert figures._format_number(1578, "tr") == "1.578"
    assert figures._format_number(0.425, "tr", digits=1, percent=True) == "%42,5"
    assert figures._format_number(1234567.5, "tr", digits=1) == "1.234.567,5"


def test_en_formatter():
    assert figures._format_number(0.85, "en") == "0.85"
    assert figures._format_number(0.5, "en", percent=True) == "50%"
    assert figures._format_number(1578, "en") == "1,578"
    assert figures._format_number(0.425, "en", digits=1, percent=True) == "42.5%"


def test_formatter_never_prints_negative_zero():
    assert figures._format_number(-1e-17, "tr", digits=2) == "0,00"


def _tick_and_label_texts(fig):
    fig.canvas.draw()
    ax = fig.axes[0]
    low, high = ax.get_ylim()
    ticks = [
        label.get_text()
        for location, label in zip(ax.get_yticks(), ax.get_yticklabels())
        if low - 1e-9 <= location <= high + 1e-9 and label.get_text()
    ]
    return ticks, [t.get_text() for t in ax.texts]


def test_fig01_labels_and_axis_are_percent_in_both_languages():
    report = _fake_rule2()
    fig = figures._draw_rule2(report, "tr")
    try:
        ticks, labels = _tick_and_label_texts(fig)
    finally:
        plt.close(fig)
    assert ticks[0] == "%0" and ticks[-1] == "%100" and all(t.startswith("%") for t in ticks)
    assert {"%60,0", "%65,0", "%70,0", "%62,0", "%67,0", "%72,0"} <= set(labels)
    fig = figures._draw_rule2(report, "en")
    try:
        ticks, labels = _tick_and_label_texts(fig)
    finally:
        plt.close(fig)
    assert ticks[0] == "0%" and ticks[-1] == "100%" and all(t.endswith("%") for t in ticks)
    assert {"60.0%", "65.0%", "70.0%", "62.0%", "67.0%", "72.0%"} <= set(labels)


def test_fig01_title_subtitle_and_catalog_record(tmp_path):
    report = _fake_rule2()
    for lang, expected in (
        ("tr", "Sınıf içi ilk %20 bayrakta kesinlik; 3 sinyal, 2 sinyal ve model"),
        ("en", "Precision at the within-class top 20%; 3 signals, 2 signals and the model"),
    ):
        fig = figures._draw_rule2(report, lang)
        try:
            assert fig.axes[0].get_title(loc="left") == expected
        finally:
            plt.close(fig)
    dest = tmp_path / "week11"
    dest.mkdir()
    (dest / "figures.json").write_text(json.dumps([FIG01]), encoding="utf-8")
    (entry,) = _write_rule2(tmp_path, dest)
    assert entry["başlık_tr"] == "Şeffaf kural, modelin birkaç puan gerisinde kalıyor"
    assert entry["başlık_en"] == "The transparent rule stays a few points behind the model"
    assert "kesinlik=%65,0" in entry["alt_tr"]
    catalog = _catalog(dest)
    assert catalog["fig01_sinyal_kesinlik"] == entry  # merge ile yerine konur


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda r: _set_precision(r, 0, "general_hgb", 0.60), "iki kuraldan yuksek degil"),
        (lambda r: _set_precision(r, 1, "general_hgb", 0.64), "iki kuraldan yuksek degil"),
        (lambda r: _set_precision(r, 0, "general_hgb", 0.80), "farki"),
        (lambda r: _set_precision(r, 1, "general_hgb", 0.90), "farki"),
    ],
)
def test_fig01_title_guard_raises_when_claim_fails(tmp_path, mutate, message):
    report = _fake_rule2()
    mutate(report)
    source = tmp_path / "rule2_metrics.json"
    source.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        figures.write_rule2_figures(source, tmp_path / "out")
    assert not (tmp_path / "out" / "fig01_sinyal_kesinlik_tr.png").exists()


def _set_precision(report, period_index, method, value):
    row = next(r for r in report["periods"][period_index]["total"] if r["method"] == method)
    row["precision"] = value


def test_fig01_alt_text_tr_numbers_and_en_unchanged():
    spec = figures._rule2_spec(_fake_rule2())
    assert "kesinlik=%60,0" in spec["alt_tr"] and "n=5.000" in spec["alt_tr"]
    assert "precision=60.0%" in spec["alt_en"] and "n=5,000" in spec["alt_en"]


DECIMALS_OVER_FOUR = re.compile(r"\d+[.,]\d{5,}")


def test_alt_texts_have_readable_precision_in_both_languages(tmp_path):
    dest, entries = _run(tmp_path)
    # fig01 de aynı sözleşmeyle (sahte rule2 kesinlikleri 6 ondalıklı olsa bile)
    rule2 = _fake_rule2()
    rule2["periods"][0]["total"][0]["precision"] = 0.6123456789
    source = tmp_path / "rule2_metrics.json"
    source.write_text(json.dumps(rule2), encoding="utf-8")
    fig01 = figures.write_rule2_figures(source, dest)[0]
    records = [*entries, fig01]
    assert len(records) == 8
    for record in records:
        for key in ("alt_tr", "alt_en"):
            assert not DECIMALS_OVER_FOUR.search(record[key]), (record["dosya"], key)
    by_name = _by_name(records)
    assert "kesinlik=%61,2" in by_name["fig01_sinyal_kesinlik"]["alt_tr"]
    assert "precision=61.2%" in by_name["fig01_sinyal_kesinlik"]["alt_en"]
    # ROC AUC üç ondalık, sayımlar binlik ayraçlı
    assert "GENERAL 0,800" in by_name["fig02_sinyal_gruplari"]["alt_tr"]
    assert "GENERAL 0.800" in by_name["fig02_sinyal_gruplari"]["alt_en"]
    assert "%42,5" in by_name["fig04_kural_yakalama"]["alt_tr"] and "1.578" in by_name["fig04_kural_yakalama"]["alt_tr"]
    assert "42.5%" in by_name["fig04_kural_yakalama"]["alt_en"] and "1,578" in by_name["fig04_kural_yakalama"]["alt_en"]
    assert "14.059" in by_name["fig05_erkenlik"]["alt_tr"] and "14,059" in by_name["fig05_erkenlik"]["alt_en"]


def test_fig02_axis_comma_subtitle_and_legend_outside_highlight():
    for lang in ("tr", "en"):
        fig = figures._draw_ek_signals(_fake_report(), lang)
        try:
            fig.canvas.draw()
            ax = fig.axes[0]
            assert ax.get_title(loc="left") == figures._EK_LABELS[lang]["subtitle_signals"]
            ticks = [t.get_text() for t in ax.get_xticklabels() if t.get_text()]
            if lang == "tr":
                assert any("," in t for t in ticks) and all("." not in t for t in ticks)
            else:
                assert any("." in t for t in ticks)
            box = ax.get_legend().get_window_extent(fig.canvas.get_renderer())
            (_, y_a), (_, y_b) = ax.transData.inverted().transform([(box.x0, box.y0), (box.x1, box.y1)])
            assert max(y_a, y_b) < figures._E1_ORDER.index("GENERAL") - 0.45
        finally:
            plt.close(fig)


def test_fig02_subtitle_texts():
    assert figures._EK_LABELS["tr"]["subtitle_signals"] == "Not ve teslim birlikte tam modele yaklaşıyor"
    assert (
        figures._EK_LABELS["en"]["subtitle_signals"]
        == "Grades and submissions together come close to the full model"
    )


def test_fig04_new_titles_and_legends(tmp_path):
    _, entries = _run(tmp_path)
    fig04 = _by_name(entries)["fig04_kural_yakalama"]
    assert fig04["başlık_tr"] == "Kural, başarısız olacakları bırakacaklardan biraz daha yüksek oranda yakalıyor"
    assert fig04["başlık_en"] == (
        "The rule catches students who will fail at a somewhat higher rate than those who will withdraw"
    )
    for lang, expected in (
        ("tr", ["Başarısız olacaklar (Fail)", "Bırakacaklar (Withdrawn)"]),
        ("en", ["Will fail (Fail)", "Will withdraw (Withdrawn)"]),
    ):
        fig = figures._draw_ek_rule(_fake_report(), lang)
        try:
            assert [t.get_text() for t in fig.axes[0].get_legend().get_texts()] == expected
        finally:
            plt.close(fig)


def test_fig04_percent_axis_formats():
    for lang, check in (("tr", lambda t: t.startswith("%")), ("en", lambda t: t.endswith("%"))):
        fig = figures._draw_ek_rule(_fake_report(), lang)
        try:
            fig.canvas.draw()
            ticks = [t.get_text() for t in fig.axes[0].get_yticklabels() if t.get_text()]
        finally:
            plt.close(fig)
        assert ticks and all(check(t) for t in ticks)


def _line_key(line):
    # Lejant çizgi parçasında işaret ayrı bir nesnedir; renk, çizgi stili ve kalınlık karşılaştırılır.
    return (line.get_color(), str(line.get_linestyle()), line.get_linewidth())


@pytest.mark.parametrize("drawer", ["_draw_ek_early", "_draw_ek_early_targets"])
def test_legend_line_styles_match_drawing(drawer):
    for lang in ("tr", "en"):
        fig = getattr(figures, drawer)(_fake_report(), lang)
        try:
            ax = fig.axes[0]
            drawn = {_line_key(line) for line in ax.lines}
            kinds = set()
            for line in ax.get_legend().get_lines():
                assert _line_key(line) in drawn
                kinds.add("solid" if str(line.get_linestyle()) == "-" else "dashed")
            assert kinds == {"solid", "dashed"}
        finally:
            plt.close(fig)


def test_fig05_label_sits_inside_band_without_touching_lines():
    for lang in ("tr", "en"):
        fig = figures._draw_ek_early(_fake_report(), lang)
        try:
            ax = fig.axes[0]
            label = next(t for t in ax.texts if t.get_text() == figures._EK_LABELS[lang]["contribution"])
            cx, cy = label.get_position()
            data = [line for line in ax.lines if len(line.get_xdata()) == len(CUTOFFS)]
            # çizim sırası: GENERAL test, ETKİNLİK test, GENERAL doğrulama, ETKİNLİK doğrulama
            x = np.asarray(data[0].get_xdata(), float)
            general_test, activity_test, general_val, activity_val = (
                np.asarray(line.get_ydata(), float) for line in data
            )
            assert np.interp(cx, x, np.minimum(general_test, activity_test)) < cy
            assert cy < np.interp(cx, x, np.maximum(general_test, activity_test))
            fig.canvas.draw()
            box = label.get_window_extent(fig.canvas.get_renderer())
            (x0, y0), (x1, y1) = ax.transData.inverted().transform([(box.x0, box.y0), (box.x1, box.y1)])
            samples = np.linspace(x0, x1, 25)
            for values in (general_test, activity_test, general_val, activity_val):
                curve = np.interp(samples, x, values)
                assert not np.any((curve > min(y0, y1)) & (curve < max(y0, y1)))
            assert not (x0 <= 60 <= x1)
        finally:
            plt.close(fig)


def test_fig05_stops_when_label_cannot_be_placed():
    report = _fake_report()
    for cutoff in CUTOFFS:  # iki test çizgisi neredeyse üst üste: taralı alana sığmaz
        results = report["e3"]["cutoff_results"][str(cutoff)]["targets"]["referans"]["results"]
        general = results["GENERAL"]["hgb"][figures._EK_VIEW]["test"]["roc_auc"]["estimate"]
        results["ETKİNLİK"]["hgb"][figures._EK_VIEW]["test"]["roc_auc"]["estimate"] = general - 0.0005
    with pytest.raises(ValueError, match="fig05"):
        figures._draw_ek_early(report, "tr")


def test_fig07_description_text_is_larger_and_cards_are_lower():
    fig = figures._draw_ek_expectations(_fake_report(), "tr")
    try:
        ax = fig.axes[0]
        assert ax.texts[1].get_fontsize() >= 8.5 * 1.4  # açıklama yazısı (önceki 8,5 pt)
        assert ax.get_box_aspect() is not None and ax.get_box_aspect() < 1.0
    finally:
        plt.close(fig)


def test_fig07a_has_no_result_text_and_gray_strip(tmp_path):
    for lang in ("tr", "en"):
        fig = figures._draw_ek_expectations_pending(_fake_report(), lang)
        try:
            assert len(fig.axes) == 10
            for ax in fig.axes:
                texts = [t.get_text() for t in ax.texts]
                assert len(texts) == 3 and texts[-1] == "?"
                assert not any(word in text for text in texts for word in RESULT_WORDS)
                assert ax.patches[0].get_facecolor() == to_rgba(figures.PENDING_GREY)
        finally:
            plt.close(fig)
    dest, entries = _run(tmp_path)
    entry = _by_name(entries)["fig07a_beklentiler_once"]
    assert entry["başlık_tr"] == "Koşmadan önce yazılan 10 beklenti"
    assert entry["başlık_en"] == "10 expectations written before the run"
    for lang in ("tr", "en"):
        assert (dest / f"fig07a_beklentiler_once_{lang}.png").stat().st_size > 0
    assert "ön kayıt md5 ile mühürlendi" in entry["alt_tr"]
    for digest in ("a" * 32, "c" * 32, "d" * 32):  # ek dosyası için SON kayıt (c); ilk kayıt (b) değil
        assert digest in entry["alt_tr"] and digest in entry["alt_en"]
    assert "b" * 32 not in entry["alt_tr"]
    for key in ("başlık_tr", "başlık_en", "alt_tr", "alt_en"):
        assert not any(word in entry[key] for word in RESULT_WORDS)


@pytest.mark.parametrize("drawer", ["_draw_ek_expectations", "_draw_ek_expectations_pending"])
def test_fig07_card_gaps_are_equal_and_top_gap_is_narrow(drawer):
    for lang in ("tr", "en"):
        fig = getattr(figures, drawer)(_fake_report(), lang)
        try:
            width, height = fig.get_size_inches()
            boxes = [ax.get_position() for ax in fig.axes]
            assert len(boxes) == 10
            horizontal = (boxes[1].x0 - boxes[0].x1) * width
            vertical = (boxes[0].y0 - boxes[5].y1) * height
            assert horizontal == pytest.approx(vertical, abs=1e-6)
            columns = {round(box.x0, 6) for box in boxes}
            assert len(columns) == 5  # iki sıra aynı sütunlarda
            top_gap = (1.0 - boxes[0].y1) * height
            assert top_gap <= 0.7
            # Yükseklik içerikten; kartların altındaki boşluk = üst kenar boşluğu (başlığın üstü).
            assert height == pytest.approx(figures._CARD_FIG_HEIGHT)
            assert width == pytest.approx(10.0)
            bottom_gap = boxes[5].y0 * height
            figures._title(fig, "Test başlığı", fig.title_y)
            fig.canvas.draw()
            title_box = fig._suptitle.get_window_extent(fig.canvas.get_renderer())
            top_margin = height - title_box.y1 / fig.dpi
            assert bottom_gap == pytest.approx(top_margin, abs=0.05)
            assert bottom_gap == pytest.approx((1.0 - fig.title_y) * height, abs=0.05)
        finally:
            plt.close(fig)


def test_fig07_png_height_follows_content(tmp_path):
    dest, _ = _run(tmp_path)
    for name in figures._CARD_FIGURES:
        for lang in ("tr", "en"):
            image = plt.imread(dest / f"{name}_{lang}.png")
            assert image.shape[1] == 2000
            assert abs(image.shape[0] - figures._CARD_FIG_HEIGHT * 200) <= 1
    other = plt.imread(dest / "fig02_sinyal_gruplari_tr.png")
    assert other.shape[:2] == (1120, 2000)  # diğer grafikler 10 x 5,6 kalır


def test_cli_dispatch(monkeypatch):
    calls = []
    monkeypatch.setattr(figures, "main", lambda: calls.append("week10"))
    monkeypatch.setattr(figures, "main_rule2", lambda: calls.append("rule2"))
    monkeypatch.setattr(figures, "main_ek", lambda: calls.append("ek"))
    figures.cli([])
    figures.cli(["--ek"])
    figures.cli(["--rule2"])
    figures.cli(["--rule2", "--ek"])
    assert calls == ["week10", "ek", "rule2", "rule2", "ek"]


def test_catalog_has_eight_records(tmp_path):
    dest, _ = _run(tmp_path)
    catalog = json.loads((dest / "figures.json").read_text(encoding="utf-8"))
    assert len(catalog) == 8
    assert "fig07a_beklentiler_once" in {item["dosya"] for item in catalog}
