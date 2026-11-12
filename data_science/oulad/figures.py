"""Hafta 10 grafikleri ve hafta 11 kural karşılaştırması.

Hafta 10 sayıları model_metrics.json ve explain.json içinden okunur.
Hafta 11 sayıları rule2_metrics.json içinden okunur.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

from data_science.oulad.model import REPORT_PATH as METRICS_PATH
from data_science.oulad.model import SET_NAMES
EXPLAIN_PATH = METRICS_PATH.parent / "explain.json"
FIGURES_DIR = METRICS_PATH.parent / "figures" / "week10"
WEEK11_DIR = METRICS_PATH.parent / "figures" / "week11"

NAVY = "#1E2761"
AMBER = "#E8A33D"
GREEN = "#2E8B57"
ICE = "#CADCFC"
GREY = "#5A6275"
RED = "#8B2E2E"
GRID = "#E3E6EE"
LIGHT_GREY = "#C5CAD6"

FIGURE_SPECS = (
    {
        "dosya": "fig01_roc_egim",
        "başlık_tr": "Doğrulama ve testte sıralama değişiyor: beş set için ROC AUC",
        "başlık_en": "Rankings change between validation and test: ROC AUC for five sets",
        "alt_tr": (
            "Her çizgi bir özellik setinin doğrulama ve test ROC AUC değerini birleştirir. "
            "Kalın çizgiler genel ve göreli genel setlerdir; diğerleri incedir. "
            "Yalnızca test noktasında yüzde doksan beş aralık vardır. Doğrulama noktasında aralık yoktur."
        ),
        "alt_en": (
            "Each line joins validation and test ROC AUC for one feature set. "
            "The thick lines are the general and relative general sets; the others are thin. "
            "Only the test point has a ninety-five percent interval. The validation point has no interval."
        ),
    },
    {
        "dosya": "fig02_oran_kaymasi",
        "başlık_tr": "Test döneminde modül bazında gerçek oran ve ortalama tahmin",
        "başlık_en": "Actual rate and mean prediction by module in the test period",
        "alt_tr": (
            "Her satır bir modüldür. Noktalar gerçek oranı ve genel, modül bilgili ve geçmişli "
            "setlerin ortalama tahminini gösterir. Noktalı çizgiler aynı modüldeki değerleri birleştirir."
        ),
        "alt_en": (
            "Each row is a module. Dots show the actual rate and the mean prediction for the "
            "general, module-aware, and history sets. Dotted lines join values in the same module."
        ),
    },
    {
        "dosya": "fig03_gorulmemis_ders",
        "başlık_tr": "Eğitimde görülmeyen derste ortalama tahmin ve gerçek oran",
        "başlık_en": "Mean prediction and actual rate for a course unseen in training",
        "alt_tr": (
            "Her satır, eğitimde hiç görülmeyen bir derstir. Noktalar gerçek oranı ve genel ile göreli "
            "genel setlerin ortalama tahminini gösterir. Vurgulu satır, kesim gününe kadar notlu ödevi olmayan derstir."
        ),
        "alt_en": (
            "Each row is a course never seen in training. Dots show the actual rate and the mean prediction "
            "for the general and relative general sets. The highlighted row is the course with no graded "
            "assessment before the cutoff day."
        ),
    },
    {
        "dosya": "fig04_kapasite",
        "başlık_tr": "Bayrak oranına göre kesinlik: genel ve sınıf içi sıralama",
        "başlık_en": "Precision by flag rate for global and within-class ranking",
        "alt_tr": (
            "Çizgiler bayrak oranı değiştikçe kesinliği gösterir. Biri öğrencileri birlikte sıralar, "
            "diğeri her modülün içinde sıralar. Kesikli çizgi seçilen bayrak oranını, açık bant sınıf içi "
            "sıralamanın önde olduğu aralığı gösterir."
        ),
        "alt_en": (
            "Lines show precision as the flag rate changes. One ranks students together and "
            "the other ranks inside each module. The dashed line shows the selected flag rate, and the "
            "pale band shows the range where within-class ranking is ahead."
        ),
    },
    {
        "dosya": "fig05_shap",
        "başlık_tr": "Modelin en çok dayandığı özellikler",
        "başlık_en": "Features the model relies on most",
        "alt_tr": (
            "Sol panel özelliklerin ortalama mutlak SHAP değerini karşılaştırır. Sağ panel en yüksek "
            "ortalama mutlak değere sahip özelliğin gözlenen değerini SHAP ile birlikte gösterir. "
            "Pozitif SHAP, modelin tahmini riski artırdığı yönü gösterir; nedensel bir etki değildir."
        ),
        "alt_en": (
            "The left panel compares mean absolute SHAP across features. The right panel shows "
            "observed values of the feature with the highest mean absolute SHAP together with SHAP. "
            "Positive SHAP shows the direction in which the model increases predicted risk; it is not a causal effect."
        ),
    },
)

_LABELS = {
    "tr": {
        "validation": "Doğrulama 2014B",
        "test": "Test 2014J",
        "roc": "ROC AUC",
        "module": "Modül",
        "rate": "Oran",
        "actual": "Gerçek oran",
        "flag": "Bayrak oranı (%)",
        "precision": "Kesinlik",
        "global": "Genel sıralama",
        "within": "Sınıf içi sıralama",
        "mean_abs": "Ortalama |SHAP|",
        "shap": "SHAP (log-odds)",
        "operating": "çalışma noktası",
        "ungraded": "60. güne kadar notlu ödev yok",
    },
    "en": {
        "validation": "Validation 2014B",
        "test": "Test 2014J",
        "roc": "ROC AUC",
        "module": "Module",
        "rate": "Rate",
        "actual": "Actual rate",
        "flag": "Flag rate (%)",
        "precision": "Precision",
        "global": "Global ranking",
        "within": "Within-class ranking",
        "mean_abs": "Mean |SHAP|",
        "shap": "SHAP (log-odds)",
        "operating": "operating point",
        "ungraded": "No graded assessment by day 60",
    },
}


def _configure_font() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    chosen = "Calibri" if "Calibri" in available else "DejaVu Sans"
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [chosen]
    plt.rcParams["axes.unicode_minus"] = False


def _style(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#C5CAD6")
    ax.spines["bottom"].set_color("#C5CAD6")
    ax.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(colors=GREY, labelsize=9)
    ax.xaxis.label.set_color(GREY)
    ax.yaxis.label.set_color(GREY)


def _new_figure(ncols: int = 1):
    fig, axes = plt.subplots(1, ncols, figsize=(10, 5.6), dpi=200, constrained_layout=True)
    if ncols == 1:
        _style(axes)
        return fig, axes
    for ax in axes:
        _style(ax)
    return fig, axes


def _title(fig, text: str, y: float | None = None) -> None:
    if y is None:
        fig.suptitle(text, color=NAVY, fontsize=13, x=0.02, ha="left")
    else:
        fig.suptitle(text, color=NAVY, fontsize=13, x=0.02, y=y, ha="left", va="top")


def _read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _number(value) -> float:
    if value is None:
        return float("nan")
    return float(value)


def _validation_auc(metrics: dict, set_name: str) -> float:
    for row in metrics["validation"]["rows"]:
        if row["set"] == set_name and row["model"] == "hgb":
            return _number(row["roc_auc"])
    raise KeyError(set_name)


def _test_auc(metrics: dict, set_name: str) -> tuple[float, float, float]:
    block = metrics["test_metrics"][set_name]["hgb"]["roc_auc"]
    return _number(block["estimate"]), _number(block["low"]), _number(block["high"])


def _line_style(set_name: str) -> tuple[str, float, float]:
    if set_name == "GENERAL":
        return NAVY, 2.6, 7.0
    if set_name == "GENERAL_REL":
        return AMBER, 2.6, 7.0
    return LIGHT_GREY, 1.05, 4.2


def _spread_label_y(values: list[float], gap: float) -> list[float]:
    if not values:
        return []
    order = sorted(range(len(values)), key=lambda index: values[index])
    placed = [values[index] for index in order]
    for index in range(1, len(placed)):
        if placed[index] - placed[index - 1] < gap:
            placed[index] = placed[index - 1] + gap
    original = [values[index] for index in order]
    shift = (sum(original) - sum(placed)) / len(placed)
    placed = [value + shift for value in placed]
    out = [0.0] * len(values)
    for index, value in zip(order, placed):
        out[index] = value
    return out


def _draw_slope(metrics: dict, lang: str):
    fig, ax = _new_figure()
    labels = _LABELS[lang]
    order = [name for name in SET_NAMES if name not in ("GENERAL", "GENERAL_REL")]
    order.extend(["GENERAL", "GENERAL_REL"])
    ends: list[tuple[float, str, str]] = []
    for set_name in order:
        validation = _validation_auc(metrics, set_name)
        estimate, low, high = _test_auc(metrics, set_name)
        color, width, marker = _line_style(set_name)
        thick = set_name in ("GENERAL", "GENERAL_REL")
        ax.plot(
            [0, 1],
            [validation, estimate],
            color=color,
            linewidth=width,
            marker="o",
            markersize=marker,
            markerfacecolor=color,
            markeredgecolor="white",
            markeredgewidth=0.6,
            zorder=3 if thick else 2,
        )
        ax.errorbar(
            [1],
            [estimate],
            yerr=[[max(0.0, estimate - low)], [max(0.0, high - estimate)]],
            fmt="none",
            ecolor=color,
            elinewidth=1.4 if thick else 0.9,
            capsize=3.5,
            zorder=4,
        )
        ends.append((estimate, set_name, NAVY if set_name == "GENERAL" else AMBER if thick else GREY))
    ax.set_xticks([0, 1])
    ax.set_xticklabels([labels["validation"], labels["test"]])
    ax.set_xlim(-0.12, 1.42)
    ax.set_ylabel(labels["roc"])
    ax.margins(y=0.22)
    low, high = ax.get_ylim()
    gap = (high - low) * (12 / (fig.get_size_inches()[1] * 72 * 0.7))
    spread = _spread_label_y([item[0] for item in ends], gap)
    ax.set_ylim(min(low, min(spread) - gap), max(high, max(spread) + gap))
    for y, (_estimate, name, color) in zip(spread, ends):
        ax.text(1.035, y, name, color=color, fontsize=8, ha="left", va="center", clip_on=False, zorder=5)
    return fig


def _grouped(rows: list[dict], sets: tuple[str, ...]) -> list[str]:
    return sorted({row["code_module"] for row in rows if row["set"] in sets})


def _lookup(rows: list[dict]) -> dict[tuple[str, str], dict]:
    return {(row["set"], row["code_module"]): row for row in rows}


def _draw_dumbbell(
    rows: list[dict],
    sets: tuple[str, ...],
    colors: tuple[str, ...],
    lang: str,
    highlight: str | None = None,
    xlim: tuple[float, float] | None = None,
    note: str | None = None,
):
    fig, ax = _new_figure()
    labels = _LABELS[lang]
    modules = _grouped(rows, sets)
    index = {name: position for position, name in enumerate(modules)}
    found = _lookup(rows)
    if highlight and highlight in index:
        center = index[highlight]
        ax.axhspan(center - 0.48, center + 0.48, color=ICE, zorder=0)
    span = 0.22 if len(sets) > 1 else 0.0
    offsets = [((position - (len(sets) - 1) / 2) * span) for position in range(len(sets))]
    for set_name, color, offset in zip(sets, colors, offsets):
        for module in modules:
            row = found[(set_name, module)]
            y = index[module] + offset
            actual = _number(row["positive_rate"])
            predicted = _number(row["mean_prediction"])
            size = 42 if module == highlight else 26
            ax.plot([actual, predicted], [y, y], linestyle=":", color=color, linewidth=1.4, zorder=2)
            ax.scatter([actual], [y], s=size, marker="D", color=GREY, zorder=3)
            ax.scatter([predicted], [y], s=size, marker="o", color=color, zorder=3)
    ax.set_yticks(list(index.values()))
    ax.set_yticklabels(modules)
    for tick in ax.get_yticklabels():
        if highlight and tick.get_text() == highlight:
            tick.set_color(RED)
            tick.set_fontweight("bold")
        else:
            tick.set_color(GREY)
    ax.set_xlim(*((-0.02, 1.02) if xlim is None else xlim))
    ax.set_ylim(-0.7, max(len(modules) - 0.3, 0.7))
    ax.invert_yaxis()
    ax.set_xlabel(labels["rate"])
    ax.set_ylabel(labels["module"])
    if note and highlight and highlight in index:
        left, right = ax.get_xlim()
        ax.text(
            left + (right - left) * 0.02,
            index[highlight] - 0.30,
            note,
            color=RED,
            fontsize=8,
            ha="left",
            va="center",
            zorder=4,
        )
    handles = [
        Line2D([0], [0], marker="D", color="none", markerfacecolor=GREY, markersize=6, label=labels["actual"])
    ]
    for set_name, color in zip(sets, colors):
        handles.append(
            Line2D(
                [0],
                [0],
                color=color,
                marker="o",
                linestyle=":",
                markerfacecolor=color,
                markersize=6,
                label=set_name,
            )
        )
    ax.legend(handles=handles, frameon=False, fontsize=8)
    return fig


def _draw_capacity(explain: dict, lang: str):
    fig, ax = _new_figure()
    labels = _LABELS[lang]
    rows = explain["capacity"]["rows"]
    rates = [_number(row["flag_rate"]) * 100 for row in rows]
    global_precision = [_number(row["global"]["precision"]) for row in rows]
    within_precision = [_number(row["within_module"]["precision"]) for row in rows]
    ax.axvspan(10, 35, color=ICE, alpha=0.35, linewidth=0, zorder=0)
    ax.axvline(20, color=GREY, linestyle="--", linewidth=1.0, zorder=1)
    ax.plot(rates, global_precision, color=NAVY, marker="o", linewidth=2.0, label=labels["global"], zorder=3)
    ax.plot(rates, within_precision, color=AMBER, marker="o", linewidth=2.0, label=labels["within"], zorder=3)
    ax.text(20.8, 0.54, labels["operating"], color=GREY, fontsize=8, ha="left", va="bottom", zorder=4)
    ax.set_xlabel(labels["flag"])
    ax.set_ylabel(labels["precision"])
    ax.set_ylim(0.5, 1.0)
    ax.legend(frameon=False, fontsize=8)
    return fig


def _draw_shap(explain: dict, lang: str):
    fig, axes = _new_figure(2)
    labels = _LABELS[lang]
    features = sorted(
        explain["shap"]["features"],
        key=lambda row: (-_number(row["mean_abs_shap"]), str(row["feature"])),
    )
    shown = list(reversed(features[:10]))
    names = [str(row["feature"]) for row in shown]
    values = [_number(row["mean_abs_shap"]) for row in shown]
    colors = [NAVY] * len(shown)
    if colors:
        colors[-1] = AMBER
    axes[0].barh(names, values, color=colors)
    axes[0].set_xlabel(labels["mean_abs"])
    strongest = features[0]["feature"]
    dependence = next(row for row in explain["shap"]["dependence"] if row["feature"] == strongest)
    bases: list[int] = []
    ys: list[float] = []
    for value, shap_value in zip(dependence["value"], dependence["shap"]):
        if value is None or shap_value is None:
            continue
        bases.append(int(round(float(value))))
        ys.append(float(shap_value))
    jitter = np.random.default_rng(42).uniform(-0.15, 0.15, size=len(bases))
    xs = [base + float(shift) for base, shift in zip(bases, jitter)]
    point_size = 14 if len(xs) < 400 else 8
    point_alpha = 0.55 if len(xs) < 400 else 0.2
    axes[1].scatter(xs, ys, s=point_size, color=AMBER, alpha=point_alpha, linewidths=0, zorder=3)
    axes[1].axhline(0, color=LIGHT_GREY, linewidth=0.8, zorder=1)
    ticks = sorted(set(bases))
    axes[1].xaxis.set_major_locator(FixedLocator(ticks))
    axes[1].xaxis.set_minor_locator(NullLocator())
    if ticks:
        axes[1].set_xlim(min(ticks) - 0.7, max(ticks) + 0.7)
    axes[1].set_xlabel(str(strongest))
    axes[1].set_ylabel(labels["shap"])
    low, high = axes[1].get_ylim()
    pad = (high - low) * 0.08 if high > low else 0.05
    axes[1].set_ylim(min(low, 0) - pad, max(high, 0) + pad)
    return fig


def _catalog_entry(spec: dict) -> dict:
    return {
        "dosya": spec["dosya"],
        "başlık_tr": spec["başlık_tr"],
        "başlık_en": spec["başlık_en"],
        "alt_tr": spec["alt_tr"],
        "alt_en": spec["alt_en"],
    }


def write_figures(metrics_path: Path, explain_path: Path, dest: Path) -> list[dict]:
    metrics = _read_json(metrics_path)
    explain = _read_json(explain_path)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    _configure_font()
    drawers = (
        lambda lang: _draw_slope(metrics, lang),
        lambda lang: _draw_dumbbell(
            metrics["calibration"]["rows"],
            ("GENERAL", "GENERAL_MODULE", "HISTORY"),
            (NAVY, AMBER, GREEN),
            lang,
            xlim=(0.2, 0.65),
        ),
        lambda lang: _draw_dumbbell(
            metrics["lomo"]["rows"],
            ("GENERAL", "GENERAL_REL"),
            (NAVY, AMBER),
            lang,
            highlight="GGG",
            note=_LABELS[lang]["ungraded"],
        ),
        lambda lang: _draw_capacity(explain, lang),
        lambda lang: _draw_shap(explain, lang),
    )
    catalog = []
    for spec, draw in zip(FIGURE_SPECS, drawers):
        for lang in ("tr", "en"):
            fig = draw(lang)
            _title(fig, spec[f"başlık_{lang}"])
            fig.set_size_inches(10, 5.6)
            path = dest / f"{spec['dosya']}_{lang}.png"
            try:
                fig.savefig(path, dpi=200)
            finally:
                plt.close(fig)
        catalog.append(_catalog_entry(spec))
    (dest / "figures.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return catalog


_ROLE_TEXT = {
    "tr": {"validation": "doğrulama", "test": "test"},
    "en": {"validation": "validation", "test": "test"},
}


def _format_number(value, lang: str, digits: int | None = None, percent: bool = False) -> str:
    """Tek sayı biçimleyici. TR: 0,85  %50  1.578. EN: 0.85  50%  1,578.

    percent=True ise value oran olarak verilir (0.5 -> %50). digits verilmezse
    en kısa gösterim kullanılır.
    """
    number = float(value)
    if percent:
        number *= 100.0
    if digits is not None:
        if round(number, digits) == 0:
            number = 0.0
        text = f"{number:,.{digits}f}"
    else:
        text = f"{number:,.10g}"
    if lang == "tr":
        text = text.translate({ord(","): ".", ord("."): ","})
        return "%" + text if percent else text
    return text + "%" if percent else text


def _tick_digits(axis, scale: float = 1.0) -> int:
    locations = [float(value) * scale for value in axis.get_majorticklocs()]
    for digits in range(7):
        if all(abs(value - round(value, digits)) < 1e-9 for value in locations):
            return digits
    return 6


def _localize_axis(axis, lang: str, percent: bool = False) -> None:
    """TR eksenlerde ondalık virgül; percent=True ise iki dilde de yüzde biçimi.

    EN sayısal eksen varsayılan biçimleyiciyle kalır (değişmez).
    """
    if lang != "tr" and not percent:
        return
    scale = 100.0 if percent else 1.0
    axis.set_major_formatter(
        FuncFormatter(
            lambda value, _position: _format_number(
                value, lang, digits=_tick_digits(axis, scale), percent=percent
            )
        )
    )


def _percent_text(value, lang: str) -> str:
    """Oran -> yüzde, tek ondalık (TR %90,0; EN 90.0%). Değer yoksa boş."""
    if value is None or np.isnan(float(value)):
        return ""
    return _format_number(value, lang, digits=1, percent=True)


def _flag_percent(report: dict) -> str:
    return str(int(round(float(report["flag_rate"]) * 100)))


def _method_row(period: dict, method: str) -> dict:
    for row in period["total"]:
        if row["method"] == method:
            return row
    raise KeyError(method)


def _rule2_spec(report: dict) -> dict:
    periods = report["periods"]
    n3 = len(report["signals"]["rule"])
    n2 = len(report["signals"]["rule2"])
    rate = _flag_percent(report)
    chunks = {"tr": [], "en": []}

    def count(value, lang: str) -> str:
        return _format_number(value, lang)

    for period in periods:
        rule = _method_row(period, "rule")
        rule2 = _method_row(period, "rule2")
        model = _method_row(period, "general_hgb")
        presentation = str(period["presentation"])
        chunks["tr"].append(
            f"{presentation} {_ROLE_TEXT['tr'][period['role']]}. "
            f"{n3} sinyal: n={count(rule['n'], 'tr')}, pozitif={count(rule['n_positive'], 'tr')}, "
            f"kesinlik={_percent_text(rule['precision'], 'tr')}, isabet={count(rule['n_hit'], 'tr')}. "
            f"{n2} sinyal: n={count(rule2['n'], 'tr')}, pozitif={count(rule2['n_positive'], 'tr')}, "
            f"kesinlik={_percent_text(rule2['precision'], 'tr')}, isabet={count(rule2['n_hit'], 'tr')}. "
            f"Model: n={count(model['n'], 'tr')}, pozitif={count(model['n_positive'], 'tr')}, "
            f"kesinlik={_percent_text(model['precision'], 'tr')}, isabet={count(model['n_hit'], 'tr')}."
        )
        chunks["en"].append(
            f"{presentation} {_ROLE_TEXT['en'][period['role']]}. "
            f"{n3} signals: n={count(rule['n'], 'en')}, positives={count(rule['n_positive'], 'en')}, "
            f"precision={_percent_text(rule['precision'], 'en')}, hits={count(rule['n_hit'], 'en')}. "
            f"{n2} signals: n={count(rule2['n'], 'en')}, positives={count(rule2['n_positive'], 'en')}, "
            f"precision={_percent_text(rule2['precision'], 'en')}, hits={count(rule2['n_hit'], 'en')}. "
            f"Model: n={count(model['n'], 'en')}, positives={count(model['n_positive'], 'en')}, "
            f"precision={_percent_text(model['precision'], 'en')}, hits={count(model['n_hit'], 'en')}."
        )
    return {
        "dosya": "fig01_sinyal_kesinlik",
        "başlık_tr": "Şeffaf kural, modelin birkaç puan gerisinde kalıyor",
        "başlık_en": "The transparent rule stays a few points behind the model",
        "alt_tr": f"Sınıf içi ilk %{rate}. " + " ".join(chunks["tr"]),
        "alt_en": f"Within-class top {rate}%. " + " ".join(chunks["en"]),
    }


def _draw_rule2(report: dict, lang: str):
    fig, ax = _new_figure()
    periods = report["periods"]
    n3 = len(report["signals"]["rule"])
    n2 = len(report["signals"]["rule2"])
    if lang == "tr":
        series = (
            ("rule", NAVY, f"{n3} sinyal"),
            ("rule2", AMBER, f"{n2} sinyal"),
            ("general_hgb", GREEN, "Model"),
        )
        ylabel = "Kesinlik"
    else:
        series = (
            ("rule", NAVY, f"{n3} signals"),
            ("rule2", AMBER, f"{n2} signals"),
            ("general_hgb", GREEN, "Model"),
        )
        ylabel = "Precision"
    labels = [
        f"{period['presentation']}\n{_ROLE_TEXT[lang][period['role']]}" for period in periods
    ]
    x = np.arange(len(periods), dtype=float)
    width = 0.24
    peak = 0.0
    for index, (method, color, label) in enumerate(series):
        values = []
        texts = []
        for period in periods:
            raw = _method_row(period, method)["precision"]
            values.append(_number(raw))
            texts.append(_percent_text(raw, lang))
        peak = max(peak, max(values))
        offset = (index - (len(series) - 1) / 2.0) * width
        bars = ax.bar(x + offset, values, width=width * 0.92, color=color, label=label, zorder=3)
        for bar, text in zip(bars, texts):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                text,
                ha="center",
                va="bottom",
                fontsize=7,
                color=color,
                clip_on=False,
                zorder=4,
            )
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0.0, max(peak + 0.16, 1.0))
    _localize_axis(ax.yaxis, lang, percent=True)
    rate = _flag_percent(report)
    if lang == "tr":
        subtitle = f"Sınıf içi ilk %{rate} bayrakta kesinlik; {n3} sinyal, {n2} sinyal ve model"
    else:
        subtitle = f"Precision at the within-class top {rate}%; {n3} signals, {n2} signals and the model"
    ax.set_title(subtitle, loc="left", fontsize=10, color=GREY, pad=8)
    ax.legend(
        frameon=False,
        fontsize=8,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        borderaxespad=0.0,
    )
    return fig


RULE2_MAX_MODEL_GAP = 0.10


def _check_rule2_title_holds(report: dict) -> None:
    """Başlık iddiası: model iki kuraldan yüksek ve model - 2 sinyal farkı 0,10'dan küçük (iki dönem)."""
    for period in report["periods"]:
        values = {name: _number(_method_row(period, name)["precision"]) for name in ("rule", "rule2", "general_hgb")}
        where = f"{period['presentation']} {period['role']}"
        if any(np.isnan(value) for value in values.values()):
            raise ValueError(f"fig01 basligi: kesinlik yok ({where})")
        if not (values["general_hgb"] > values["rule"] and values["general_hgb"] > values["rule2"]):
            raise ValueError(f"fig01 basligi gecersiz: model iki kuraldan yuksek degil ({where})")
        gap = values["general_hgb"] - values["rule2"]
        if not gap < RULE2_MAX_MODEL_GAP:
            raise ValueError(
                f"fig01 basligi gecersiz: model - 2 sinyal farki {gap:.4f} >= {RULE2_MAX_MODEL_GAP} ({where})"
            )


def write_rule2_figures(report_path: Path | None = None, dest: Path | None = None) -> list[dict]:
    from data_science.oulad.rule import RULE2_PATH

    report_path = RULE2_PATH if report_path is None else Path(report_path)
    dest = WEEK11_DIR if dest is None else Path(dest)
    report = _read_json(report_path)
    _check_rule2_title_holds(report)
    dest.mkdir(parents=True, exist_ok=True)
    _configure_font()
    spec = _rule2_spec(report)
    for lang in ("tr", "en"):
        fig = _draw_rule2(report, lang)
        _title(fig, spec[f"başlık_{lang}"])
        fig.set_size_inches(10, 5.6)
        path = dest / f"{spec['dosya']}_{lang}.png"
        try:
            fig.savefig(path, dpi=200)
        finally:
            plt.close(fig)
    catalog = [_catalog_entry(spec)]
    _merge_catalog(dest / "figures.json", catalog)
    return catalog


# --- Ek analiz grafikleri (E1, E2, E3, beklentiler) -------------------------
# Veri yalnızca ek_metrics.json içinden okunur. Hepsi hgb.
EK_PATH = METRICS_PATH.parent / "ek_metrics.json"
_EK_VIEW = "b_sabit_kohort"
_EK_PERIODS = ("validation", "test")
_EK_PERIOD_KEYS = {"validation": "validation_2014B", "test": "test_2014J"}
_E1_ORDER = ("NOT", "TESLİM", "ETKİNLİK", "NOT_TESLİM", "GENERAL")
_E2_ORDER = ("GENERAL", "NOT", "TESLİM", "ETKİNLİK")
_E2_TARGETS = ("referans", "KALDI", "BIRAKTI")
_RESULT_COLORS = {"tuttu": GREEN, "tutmadı": RED, "belirsiz": AMBER}
EK_FIGURE_FILES = (
    "fig02_sinyal_gruplari",
    "fig03_hedef_ayristirma",
    "fig04_kural_yakalama",
    "fig05_erkenlik",
    "fig06_erkenlik_hedef",
    "fig07_beklentiler",
    "fig07a_beklentiler_once",
)
PENDING_GREY = "#C7CAD1"

_EK_LABELS = {
    "tr": {
        "sets": {
            "NOT": "NOT",
            "TESLİM": "TESLİM",
            "ETKİNLİK": "ETKİNLİK",
            "NOT_TESLİM": "NOT + TESLİM",
            "GENERAL": "GENERAL",
        },
        "targets": {
            "referans": "Referans (başarısız + bırakan)",
            "KALDI": "KALDI (Fail)",
            "BIRAKTI": "BIRAKTI (Withdrawn)",
        },
        "test_interval": "Test 2014J, %95 aralık",
        "validation": "Doğrulama 2014B",
        "fail": "Başarısız olacaklar (Fail)",
        "withdrawn": "Bırakacaklar (Withdrawn)",
        "subtitle_signals": "Not ve teslim birlikte tam modele yaklaşıyor",
        "caught_rate": "Kuralın yakaladığı oran",
        "cutoff": "Kesim günü",
        "selected_cutoff": "seçilen kesim",
        "contribution": "not ve teslim katkısı",
        "late_note": "BIRAKTI: 120. günden sonra bırakanlar",
        "results": {"tuttu": "Tuttu", "tutmadı": "Tutmadı", "belirsiz": "Belirsiz"},
        "general": "GENERAL",
        "activity": "ETKİNLİK",
    },
    "en": {
        "sets": {
            "NOT": "GRADES",
            "TESLİM": "SUBMISSION",
            "ETKİNLİK": "ACTIVITY",
            "NOT_TESLİM": "GRADES + SUBMISSION",
            "GENERAL": "GENERAL",
        },
        "targets": {
            "referans": "Reference (fail + withdrawn)",
            "KALDI": "KALDI (Fail)",
            "BIRAKTI": "BIRAKTI (Withdrawn)",
        },
        "test_interval": "Test 2014J, 95% interval",
        "validation": "Validation 2014B",
        "fail": "Will fail (Fail)",
        "withdrawn": "Will withdraw (Withdrawn)",
        "subtitle_signals": "Grades and submissions together come close to the full model",
        "caught_rate": "Share caught by the rule",
        "cutoff": "Cutoff day",
        "selected_cutoff": "selected cutoff",
        "contribution": "grades and submission contribution",
        "late_note": "BIRAKTI: students who withdrew after day 120",
        "results": {"tuttu": "Held", "tutmadı": "Did not hold", "belirsiz": "Inconclusive"},
        "general": "GENERAL",
        "activity": "ACTIVITY",
    },
}

EK_EXPECTATION_NAMES = {
    "B1": {"tr": "Tek grup GENERAL'e ulaşmaz", "en": "No single group reaches GENERAL"},
    "B2": {"tr": "NOT en zayıf tek grup", "en": "GRADES is the weakest single group"},
    "B3": {"tr": "Etkinliksiz model yakın kalır", "en": "Model without activity stays close"},
    "B4": {"tr": "BIRAKTI, KALDI'dan kolay", "en": "BIRAKTI is easier than KALDI"},
    "B5": {"tr": "BIRAKTI'da ETKİNLİK güçlü", "en": "ACTIVITY is strong for BIRAKTI"},
    "B6": {"tr": "KALDI'da NOT'un payı artar", "en": "GRADES share grows for KALDI"},
    "B7": {"tr": "Kural isabetleri çoğunlukla bırakan", "en": "Rule hits are mostly withdrawals"},
    "B8": {"tr": "Başarı kesim günüyle artar", "en": "Performance rises with cutoff day"},
    "B9": {"tr": "Kazancın çoğu erken gelir", "en": "Most of the gain comes early"},
    "B10": {"tr": "14. günde ETKİNLİK taşır", "en": "ACTIVITY carries day 14"},
}

_EK_TITLES = {
    "fig02_sinyal_gruplari": (
        "Tek bir sinyal grubu yetmiyor",
        "A single signal group is not enough",
    ),
    "fig03_hedef_ayristirma": (
        "Başarısız olacak öğrenciyi bulmak, bırakacak öğrenciyi bulmaktan kolay",
        "Finding students who will fail is easier than finding students who will withdraw",
    ),
    "fig04_kural_yakalama": (
        "Kural, başarısız olacakları bırakacaklardan biraz daha yüksek oranda yakalıyor",
        "The rule catches students who will fail at a somewhat higher rate than those who will withdraw",
    ),
    "fig05_erkenlik": (
        "Erken uyarının bedeli: beklemek isabeti artırır, müdahale süresini kısaltır",
        "Cost of early warning: waiting raises hit accuracy and shortens the time to intervene",
    ),
    "fig06_erkenlik_hedef": (
        "Geç bırakanları erken görmek daha zor",
        "Late withdrawals are harder to see early",
    ),
}


def _roc_cell(cell: dict, where: str) -> tuple[float, float, float]:
    if "undefined" in cell:
        raise ValueError(f"tanimsiz hucre: {where}")
    roc = cell["roc_auc"]
    values = (_number(roc["estimate"]), _number(roc["low"]), _number(roc["high"]))
    if any(np.isnan(value) for value in values):
        raise ValueError(f"ROC AUC yok: {where}")
    return values


def _e1_cells(report: dict) -> dict:
    results = report["e1"]["results"]
    return {
        (set_name, period): _roc_cell(results[set_name]["hgb"][period], f"e1 {set_name} {period}")
        for set_name in _E1_ORDER
        for period in _EK_PERIODS
    }


def _e2_cells(report: dict) -> dict:
    targets = report["e2"]["targets"]
    return {
        (target, set_name, period): _roc_cell(
            targets[target]["results"][set_name]["hgb"][period], f"e2 {target} {set_name} {period}"
        )
        for target in _E2_TARGETS
        for set_name in _E2_ORDER
        for period in _EK_PERIODS
    }


def _e3_cutoffs(report: dict) -> list[int]:
    cutoffs = [int(value) for value in report["e3"]["cutoffs"]]
    if 60 not in cutoffs:
        raise ValueError("E3 kesim gunleri arasinda 60 yok")
    return cutoffs


def _e3_series(report: dict, target: str, set_name: str, period: str) -> list[float]:
    block = report["e3"]["cutoff_results"]
    return [
        _roc_cell(
            block[str(cutoff)]["targets"][target]["results"][set_name]["hgb"][_EK_VIEW][period],
            f"e3 {cutoff} {target} {set_name} {period}",
        )[0]
        for cutoff in _e3_cutoffs(report)
    ]


def _ek_rule_data(report: dict) -> list[dict]:
    """Kuralın yakaladığı Fail ve Withdrawn oranları. Pozitif sayıları e2 counts'tan."""
    counts = report["e2"]["counts"]
    rows = []
    for period in _EK_PERIODS:
        hits = report["b7_rule2_hits"][period]
        positives_fail = int(counts["KALDI"][_EK_PERIOD_KEYS[period]]["n_positive"])
        positives_withdrawn = int(counts["BIRAKTI"][_EK_PERIOD_KEYS[period]]["n_positive"])
        if positives_fail < 1 or positives_withdrawn < 1:
            raise ValueError(f"pozitif sayisi yok: {period}")
        if int(hits["n_fail"]) + int(hits["n_withdrawn"]) != int(hits["n_hit"]):
            raise ValueError(f"isabet kirilimi tutarsiz: {period}")
        rows.append(
            {
                "period": period,
                "presentation": str(report["protocol"][f"{period}_presentation"]),
                "n_fail": int(hits["n_fail"]),
                "n_withdrawn": int(hits["n_withdrawn"]),
                "positives_fail": positives_fail,
                "positives_withdrawn": positives_withdrawn,
                "fail_rate": int(hits["n_fail"]) / positives_fail,
                "withdrawn_rate": int(hits["n_withdrawn"]) / positives_withdrawn,
            }
        )
    return rows


def _ek_expectations(report: dict) -> list[tuple[str, str]]:
    merged = dict(report["expectations"])
    for key, block in report["e3"]["expectations"].items():
        if key in merged:
            raise ValueError(f"beklenti iki kez var: {key}")
        merged[key] = block
    if len(merged) != 10:
        raise ValueError(f"10 beklenti bekleniyordu: {len(merged)}")
    items = []
    for key in sorted(merged, key=lambda name: int(name[1:])):
        result = merged[key]["result"]
        if result not in _RESULT_COLORS:
            raise ValueError(f"bilinmeyen sonuc: {key} {result}")
        if key not in EK_EXPECTATION_NAMES:
            raise ValueError(f"beklenti adi yok: {key}")
        items.append((key, result))
    return items


def _check_titles_hold(report: dict) -> None:
    """Başlıklardaki iddia veriyle çelişiyorsa durur (başlık sabit metindir)."""
    e1 = _e1_cells(report)
    for period in _EK_PERIODS:
        for set_name in ("NOT", "TESLİM", "ETKİNLİK"):
            if not e1[(set_name, period)][0] < e1[("GENERAL", period)][0]:
                raise ValueError(f"fig02 basligi gecersiz: {set_name} GENERAL'e ulasti ({period})")
    from data_science.oulad.ek import B3_MAX_GAP

    for period in _EK_PERIODS:
        gap = e1[("GENERAL", period)][0] - e1[("NOT_TESLİM", period)][0]
        if not gap < B3_MAX_GAP:
            raise ValueError(
                f"fig02 alt basligi gecersiz: NOT_TESLİM ile GENERAL farki {gap:.4f} >= {B3_MAX_GAP} ({period})"
            )
    e2 = _e2_cells(report)
    for period in _EK_PERIODS:
        if not e2[("KALDI", "GENERAL", period)][0] > e2[("BIRAKTI", "GENERAL", period)][0]:
            raise ValueError(f"fig03 basligi gecersiz: KALDI BIRAKTI'dan kolay degil ({period})")
    for row in _ek_rule_data(report):
        if not row["fail_rate"] > row["withdrawn_rate"]:
            raise ValueError(f"fig04 basligi gecersiz: Fail orani Withdrawn oranindan buyuk degil ({row['period']})")
    for period in _EK_PERIODS:
        failed = _e3_series(report, "KALDI", "GENERAL", period)
        left = _e3_series(report, "BIRAKTI", "GENERAL", period)
        if not all(a > b for a, b in zip(failed, left)):
            raise ValueError(f"fig06 basligi gecersiz: KALDI her kesimde BIRAKTI'dan kolay degil ({period})")


def _plot_pair(ax, y: float, validation, test, color: str, size: float = 7.0) -> None:
    ax.plot([validation[0], test[0]], [y, y], color=color, linewidth=1.0, linestyle=":", zorder=2)
    ax.errorbar(
        [test[0]],
        [y],
        xerr=[[max(0.0, test[0] - test[1])], [max(0.0, test[2] - test[0])]],
        fmt="o",
        color=color,
        markersize=size,
        markeredgecolor="white",
        markeredgewidth=0.6,
        elinewidth=1.4,
        capsize=3.5,
        zorder=4,
    )
    ax.plot(
        [validation[0]],
        [y],
        marker="o",
        markersize=size,
        markerfacecolor="white",
        markeredgecolor=color,
        markeredgewidth=1.6,
        linestyle="none",
        zorder=3,
    )


def _pair_handles(lang: str) -> list:
    labels = _EK_LABELS[lang]
    return [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=GREY, markeredgecolor="white", markersize=7,
               label=labels["test_interval"]),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor=GREY,
               markeredgewidth=1.6, markersize=7, label=labels["validation"]),
    ]


def _draw_ek_signals(report: dict, lang: str):
    fig, ax = _new_figure()
    cells = _e1_cells(report)
    names = _EK_LABELS[lang]["sets"]
    for position, set_name in enumerate(_E1_ORDER):
        highlight = set_name == "GENERAL"
        if highlight:
            ax.axhspan(position - 0.45, position + 0.45, color=ICE, zorder=0)
        _plot_pair(
            ax,
            position,
            cells[(set_name, "validation")],
            cells[(set_name, "test")],
            NAVY if highlight else GREY,
            size=8.0 if highlight else 7.0,
        )
    ax.set_yticks(range(len(_E1_ORDER)))
    ax.set_yticklabels([names[name] for name in _E1_ORDER])
    for tick, set_name in zip(ax.get_yticklabels(), _E1_ORDER):
        tick.set_color(NAVY if set_name == "GENERAL" else GREY)
        tick.set_fontweight("bold" if set_name == "GENERAL" else "normal")
    low = min(min(cell[0], cell[1]) for cell in cells.values())
    high = max(max(cell[0], cell[2]) for cell in cells.values())
    ax.set_xlim(low - 0.02, high + 0.02)
    # Üstte boş bir şerit bırakılır; lejant orada, vurgulu bandın dışında durur.
    ax.set_ylim(len(_E1_ORDER) - 0.5, -1.15)
    ax.set_xlabel(_LABELS[lang]["roc"])
    _localize_axis(ax.xaxis, lang)
    ax.set_title(_EK_LABELS[lang]["subtitle_signals"], loc="left", fontsize=10, color=GREY, pad=8)
    ax.legend(handles=_pair_handles(lang), frameon=False, fontsize=8, loc="upper right")
    return fig


def _draw_ek_targets(report: dict, lang: str):
    fig, axes = _new_figure(3)
    cells = _e2_cells(report)
    names = _EK_LABELS[lang]["sets"]
    low = min(min(cell[0], cell[1]) for cell in cells.values())
    high = max(max(cell[0], cell[2]) for cell in cells.values())
    for panel, (ax, target) in enumerate(zip(axes, _E2_TARGETS)):
        for position, set_name in enumerate(_E2_ORDER):
            highlight = set_name == "GENERAL"
            if highlight:
                ax.axhspan(position - 0.45, position + 0.45, color=ICE, zorder=0)
            _plot_pair(
                ax,
                position,
                cells[(target, set_name, "validation")],
                cells[(target, set_name, "test")],
                NAVY if highlight else GREY,
                size=7.0,
            )
        ax.set_yticks(range(len(_E2_ORDER)))
        ax.set_xlim(low - 0.02, high + 0.02)
        ax.set_ylim(len(_E2_ORDER) - 0.5, -0.5)
        ax.set_xlabel(_LABELS[lang]["roc"])
        _localize_axis(ax.xaxis, lang)
        ax.set_title(_EK_LABELS[lang]["targets"][target], color=GREY, fontsize=9)
        if panel == 0:
            ax.set_yticklabels([names[name] for name in _E2_ORDER])
            for tick, set_name in zip(ax.get_yticklabels(), _E2_ORDER):
                tick.set_color(NAVY if set_name == "GENERAL" else GREY)
                tick.set_fontweight("bold" if set_name == "GENERAL" else "normal")
        else:
            ax.tick_params(labelleft=False)
    axes[-1].legend(handles=_pair_handles(lang), frameon=False, fontsize=7, loc="lower right")
    return fig


def _draw_ek_rule(report: dict, lang: str):
    fig, ax = _new_figure()
    labels = _EK_LABELS[lang]
    rows = _ek_rule_data(report)
    x = np.arange(len(rows), dtype=float)
    width = 0.34
    peak = 0.0
    for offset, key, color, label in (
        (-width / 2, "fail", NAVY, labels["fail"]),
        (width / 2, "withdrawn", AMBER, labels["withdrawn"]),
    ):
        values = [row[f"{key}_rate"] for row in rows]
        peak = max(peak, max(values))
        bars = ax.bar(x + offset, values, width=width * 0.94, color=color, label=label, zorder=3)
        for bar, row in zip(bars, rows):
            hits = row[f"n_{key}"]
            positives = row[f"positives_{key}"]
            text = (
                f"{_format_number(row[f'{key}_rate'], lang, digits=1, percent=True)} · "
                f"{_format_number(hits, lang)} / {_format_number(positives, lang)}"
            )
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                text,
                ha="center",
                va="bottom",
                fontsize=8.5,
                color=color,
                clip_on=False,
                zorder=4,
            )
    ax.set_xticks(list(x))
    ax.set_xticklabels(
        [f"{row['presentation']}\n{_ROLE_TEXT[lang][row['period']]}" for row in rows]
    )
    ax.set_ylabel(labels["caught_rate"])
    ax.set_ylim(0.0, peak + 0.1)
    _localize_axis(ax.yaxis, lang, percent=True)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    return fig


_TEST_LINE = {
    "linestyle": "-",
    "linewidth": 2.4,
    "marker": "o",
    "markersize": 6,
    "markeredgewidth": 0.6,
}
_VALIDATION_LINE = {
    "linestyle": (0, (4, 2)),
    "linewidth": 1.6,
    "marker": "o",
    "markersize": 5,
    "markerfacecolor": "white",
    "markeredgewidth": 1.3,
}


def _plot_early_lines(ax, x, series) -> list:
    """Çizgileri çizer ve çizimle aynı stilde lejant elemanları döndürür.

    series: (değerler, renk, etiket, test_mi). Test düz, doğrulama kesiklidir.
    """
    handles = []
    for values, color, label, is_test in series:
        if is_test:
            style = {**_TEST_LINE, "markerfacecolor": color, "markeredgecolor": "white"}
            zorder = 3
        else:
            style = {**_VALIDATION_LINE, "markeredgecolor": color}
            zorder = 2
        ax.plot(x, values, color=color, zorder=zorder, **style)
        handles.append(Line2D([0], [0], color=color, label=label, **style))
    return handles


def _band_label_position(fig, ax, text, x, upper, lower, others, avoid, vertical, preferred_x) -> tuple[float, float]:
    """Etiketi iki test çizgisi arasındaki alanda, hiçbir çizgiyle çakışmayan noktaya yerleştirir.

    Bulunamazsa durur (sessizce yanlış yere koymaz).
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inverse = ax.transData.inverted()

    def data_box(artist):
        box = artist.get_window_extent(renderer)
        (left, bottom), (right, top) = inverse.transform([(box.x0, box.y0), (box.x1, box.y1)])
        return left, min(bottom, top), right, max(bottom, top)

    left, bottom, right, top = data_box(text)
    half_w = (right - left) / 2 * 1.15
    low_y, high_y = ax.get_ylim()
    axes_height_pt = ax.get_window_extent(renderer).height * 72.0 / fig.dpi
    per_pt = abs(high_y - low_y) / axes_height_pt
    # Başlık eklenince eksen biraz küçülür; yükseklik payı ve çizgi/işaret kalınlığı payı eklenir.
    half_h = (top - bottom) / 2 * 1.5 + 4.0 * per_pt
    blocked = [data_box(artist) for artist in avoid]
    upper = np.asarray(upper, dtype=float)
    lower = np.asarray(lower, dtype=float)
    x = np.asarray(x, dtype=float)
    span = float(x[-1] - x[0])
    y_range = abs(high_y - low_y)
    best = None
    for cx in np.arange(x[0] + half_w, x[-1] - half_w + 1e-9, 0.5):
        if cx - half_w <= vertical <= cx + half_w:
            continue
        sample = np.linspace(cx - half_w, cx + half_w, 25)
        band_low = np.interp(sample, x, lower).max()
        band_high = np.interp(sample, x, upper).min()
        if band_high - band_low <= 2 * half_h:
            continue
        for cy in np.linspace(band_low + half_h, band_high - half_h, 41):
            if any(not (cx + half_w < bl or cx - half_w > br or cy + half_h < bb or cy - half_h > bt)
                   for bl, bb, br, bt in blocked):
                continue
            margin = min(cy - half_h - band_low, band_high - cy - half_h)
            clash = False
            for values in others:
                curve = np.interp(sample, x, np.asarray(values, dtype=float))
                if np.any((curve > cy - half_h) & (curve < cy + half_h)):
                    clash = True
                    break
                margin = min(margin, float(np.min(np.abs(curve - cy))) - half_h)
            if clash:
                continue
            score = margin / y_range - 0.25 * abs(cx - preferred_x) / span
            if best is None or score > best[0]:
                best = (score, float(cx), float(cy))
    if best is None:
        raise ValueError("fig05: etiket taralı alanda çizgilerle çakışmadan yerleştirilemedi")
    return best[1], best[2]


def _draw_ek_early(report: dict, lang: str):
    fig, ax = _new_figure()
    labels = _EK_LABELS[lang]
    cutoffs = _e3_cutoffs(report)
    x = np.array(cutoffs, dtype=float)
    general_test = np.array(_e3_series(report, "referans", "GENERAL", "test"))
    activity_test = np.array(_e3_series(report, "referans", "ETKİNLİK", "test"))
    general_validation = np.array(_e3_series(report, "referans", "GENERAL", "validation"))
    activity_validation = np.array(_e3_series(report, "referans", "ETKİNLİK", "validation"))
    ax.fill_between(x, activity_test, general_test, color=ICE, alpha=0.7, linewidth=0, zorder=1)
    ax.axvline(60, color=GREY, linewidth=0.8, alpha=0.7, zorder=1)
    handles = _plot_early_lines(
        ax,
        x,
        (
            (general_test, NAVY, f"{labels['general']}, {_LABELS[lang]['test']}", True),
            (activity_test, AMBER, f"{labels['activity']}, {_LABELS[lang]['test']}", True),
            (general_validation, NAVY, f"{labels['general']}, {_LABELS[lang]['validation']}", False),
            (activity_validation, AMBER, f"{labels['activity']}, {_LABELS[lang]['validation']}", False),
        ),
    )
    ax.set_xticks(cutoffs)
    ax.set_xlabel(labels["cutoff"])
    ax.set_ylabel(_LABELS[lang]["roc"])
    low, high = ax.get_ylim()
    pad = (high - low) * 0.06
    ax.set_ylim(low - pad, high + pad)
    _localize_axis(ax.yaxis, lang)
    selected = ax.text(60.0 + (x[-1] - x[0]) * 0.008, high + pad * 0.6, labels["selected_cutoff"], color=GREY,
                       fontsize=8, ha="left", va="top", zorder=5)
    legend = ax.legend(handles=handles, frameon=False, fontsize=8, loc="lower right", handlelength=3.6)
    middle = len(x) // 2
    label = ax.text(float(x[middle]), float((general_test[middle] + activity_test[middle]) / 2),
                    labels["contribution"], color=GREY, fontsize=8, ha="center", va="center", zorder=5)
    px, py = _band_label_position(
        fig,
        ax,
        label,
        x,
        upper=np.maximum(general_test, activity_test),
        lower=np.minimum(general_test, activity_test),
        others=(general_validation, activity_validation),
        avoid=(legend, selected),
        vertical=60.0,
        preferred_x=90.0,
    )
    label.set_position((px, py))
    return fig


def _draw_ek_early_targets(report: dict, lang: str):
    fig, ax = _new_figure()
    labels = _EK_LABELS[lang]
    cutoffs = _e3_cutoffs(report)
    x = np.array(cutoffs, dtype=float)
    series = []
    for target, color in (("KALDI", NAVY), ("BIRAKTI", AMBER)):
        name = labels["targets"][target]
        series.append((_e3_series(report, target, "GENERAL", "test"), color,
                       f"{name}, {_LABELS[lang]['test']}", True))
    for target, color in (("KALDI", NAVY), ("BIRAKTI", AMBER)):
        name = labels["targets"][target]
        series.append((_e3_series(report, target, "GENERAL", "validation"), color,
                       f"{name}, {_LABELS[lang]['validation']}", False))
    handles = _plot_early_lines(ax, x, series)
    ax.set_xticks(cutoffs)
    ax.set_xlabel(f"{labels['cutoff']}\n{labels['late_note']}")
    ax.set_ylabel(_LABELS[lang]["roc"])
    _localize_axis(ax.yaxis, lang)
    ax.legend(handles=handles, frameon=False, fontsize=8, loc="lower right", handlelength=3.6)
    return fig


# Kart ızgarası (inç, 10 x 5,6 şekil): satırlar arası boşluk = kartlar arası yatay boşluk.
_CARD_COLUMNS = 5
_CARD_SIDE = 0.35
_CARD_GAP = 0.18
_CARD_WIDTH = (10.0 - 2 * _CARD_SIDE - (_CARD_COLUMNS - 1) * _CARD_GAP) / _CARD_COLUMNS
_CARD_HEIGHT = 0.95 * _CARD_WIDTH
_CARD_EDGE = 0.15  # üst ve alt kenar boşluğu (aynı)
_CARD_TITLE_HEIGHT = 0.25
_CARD_TITLE_GAP = 0.2
# Şekil yüksekliği içerikten: kenar + başlık + aralık + 2 kart sırası + satır arası + kenar
_CARD_FIG_HEIGHT = (
    _CARD_EDGE + _CARD_TITLE_HEIGHT + _CARD_TITLE_GAP + 2 * _CARD_HEIGHT + _CARD_GAP + _CARD_EDGE
)
_CARD_FIGURES = ("fig07_beklentiler", "fig07a_beklentiler_once")


def _draw_ek_expectations(report: dict, lang: str, pending: bool = False):
    """B1-B10 kartları. pending=True: sonuç yerine '?' ve gri şerit (sonuç okunmaz)."""
    items = _ek_expectations(report)
    height = _CARD_FIG_HEIGHT
    fig = plt.figure(figsize=(10, height), dpi=200)
    # Başlık üst kenardan _CARD_EDGE kadar aşağıda başlar (writer bu değeri kullanır).
    fig.title_y = 1.0 - _CARD_EDGE / height
    axes = []
    for index in range(len(items)):
        row, column = divmod(index, _CARD_COLUMNS)
        left = _CARD_SIDE + column * (_CARD_WIDTH + _CARD_GAP)
        bottom = _CARD_EDGE + (1 - row) * (_CARD_HEIGHT + _CARD_GAP)
        axes.append(fig.add_axes([left / 10.0, bottom / height, _CARD_WIDTH / 10.0, _CARD_HEIGHT / height]))
    for ax, (key, result) in zip(axes, items):
        color = PENDING_GREY if pending else _RESULT_COLORS[result]
        ax.set_box_aspect(0.95)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_facecolor("white")
        for spine in ax.spines.values():
            spine.set_color(LIGHT_GREY)
            spine.set_linewidth(1.2)
        ax.add_patch(Rectangle((0, 0), 1, 0.07, color=color, zorder=2))
        ax.text(0.5, 0.85, key, color=NAVY, fontsize=18, fontweight="bold", ha="center", va="center")
        ax.text(0.5, 0.50, textwrap.fill(EK_EXPECTATION_NAMES[key][lang], 17), color=GREY, fontsize=12,
                ha="center", va="center")
        if pending:
            ax.text(0.5, 0.17, "?", color=GREY, fontsize=20, fontweight="bold", ha="center", va="center")
        else:
            ax.text(0.5, 0.17, _EK_LABELS[lang]["results"][result], color=color, fontsize=12,
                    fontweight="bold", ha="center", va="center")
    return fig


def _draw_ek_expectations_pending(report: dict, lang: str):
    return _draw_ek_expectations(report, lang, pending=True)


def _ek_titles(report: dict) -> dict[str, tuple[str, str]]:
    counts = {name: 0 for name in _RESULT_COLORS}
    for _key, result in _ek_expectations(report):
        counts[result] += 1
    total = sum(counts.values())
    titles = dict(_EK_TITLES)
    titles["fig07_beklentiler"] = (
        f"Önceden yazılan {total} beklenti: {counts['tuttu']} tuttu, "
        f"{counts['tutmadı']} tutmadı, {counts['belirsiz']} belirsiz",
        f"{total} pre-registered expectations: {counts['tuttu']} held, "
        f"{counts['tutmadı']} did not hold, {counts['belirsiz']} inconclusive",
    )
    titles["fig07a_beklentiler_once"] = (
        f"Koşmadan önce yazılan {total} beklenti",
        f"{total} expectations written before the run",
    )
    return titles


def _sealed_records(md5_path: Path | None) -> list[tuple[str, str]]:
    """Ön kayıt dosyalarının on_kayit_md5.txt'deki geçerli (son) md5 kayıtları."""
    from data_science.oulad import ek

    source = ek.PRE_REGISTRATION_MD5_PATH if md5_path is None else Path(md5_path)
    text = source.read_text(encoding="utf-8")
    return [
        (path.name, ek.registration_history(text, path.name)[-1]["md5"])
        for path in ek.PRE_REGISTRATION_PATHS
    ]


def _ek_alts(report: dict, sealed: list[tuple[str, str]]) -> dict[str, tuple[str, str]]:
    e1 = _e1_cells(report)
    e2 = _e2_cells(report)
    cutoffs = _e3_cutoffs(report)
    cohort = report["e3"]["cohort"]
    rule = _ek_rule_data(report)
    items = _ek_expectations(report)

    def auc(value, lang):
        return _format_number(value, lang, digits=3)

    def count(value, lang):
        return _format_number(value, lang)

    def share(rate, lang):
        return _format_number(rate, lang, digits=1, percent=True)

    def e1_text(lang):
        sets = _EK_LABELS[lang]["sets"]
        return ", ".join(f"{sets[name]} {auc(e1[(name, 'test')][0], lang)}" for name in _E1_ORDER)

    def e2_text(lang):
        sets = _EK_LABELS[lang]["sets"]
        return "; ".join(
            f"{target}: " + ", ".join(f"{sets[name]} {auc(e2[(target, name, 'test')][0], lang)}" for name in _E2_ORDER)
            for target in _E2_TARGETS
        )

    def rule_text(lang):
        return " ".join(
            f"{row['presentation']} {_ROLE_TEXT[lang][row['period']]}: "
            f"Fail {count(row['n_fail'], lang)} / {count(row['positives_fail'], lang)} "
            f"({share(row['fail_rate'], lang)}), "
            f"Withdrawn {count(row['n_withdrawn'], lang)} / {count(row['positives_withdrawn'], lang)} "
            f"({share(row['withdrawn_rate'], lang)})."
            for row in rule
        )

    e1_tr, e1_en = e1_text("tr"), e1_text("en")
    e2_tr, e2_en = e2_text("tr"), e2_text("en")
    rule_tr, rule_en = rule_text("tr"), rule_text("en")
    flag = int(round(float(report["protocol"]["flag_fraction"]) * 100))

    def curve(target, name, lang):
        values = _e3_series(report, target, name, "test")
        return ", ".join(
            f"{day}. gün {auc(v, lang)}" if lang == "tr" else f"day {day} {auc(v, lang)}"
            for day, v in zip(cutoffs, values)
        )

    seal_text = "; ".join(f"{name} {digest}" for name, digest in sealed)

    groups = {"tuttu": [], "tutmadı": [], "belirsiz": []}
    for key, result in items:
        groups[result].append(key)

    def listed(lang):
        names = _EK_LABELS[lang]["results"]
        return " ".join(f"{names[result]}: {', '.join(keys) if keys else '-'}." for result, keys in groups.items())

    cohort_tr = (
        f"Sabit kohort: {cohort['cutoff']}. günde hâlâ kayıtlı {count(cohort['n_students'], 'tr')} öğrenci "
        f"(doğrulama {count(cohort['n_by_period']['validation'], 'tr')}, test "
        f"{count(cohort['n_by_period']['test'], 'tr')}); modeller her kesimde kendi eğitim örneklemiyle eğitildi."
    )
    cohort_en = (
        f"Fixed cohort: {count(cohort['n_students'], 'en')} students still registered on day "
        f"{cohort['cutoff']} (validation {count(cohort['n_by_period']['validation'], 'en')}, test "
        f"{count(cohort['n_by_period']['test'], 'en')}); models are trained at each cutoff on that "
        "cutoff's own training sample."
    )
    return {
        "fig02_sinyal_gruplari": (
            "ek analiz (keşifsel). Her satır bir özellik setidir (hgb, referans hedef). Dolu nokta test 2014J "
            "ROC AUC değerini ve yüzde doksan beş aralığını, içi boş nokta doğrulama 2014B değerini gösterir; "
            f"GENERAL vurgulanmıştır. Test: {e1_tr}.",
            "Additional analysis (exploratory). Each row is a feature set (hgb, reference target). The filled dot "
            "shows test 2014J ROC AUC with its ninety-five percent interval and the hollow dot shows the validation "
            f"2014B value; GENERAL is highlighted. Test: {e1_en}.",
        ),
        "fig03_hedef_ayristirma": (
            "ek analiz (keşifsel). Üç pano üç hedefi gösterir: referans (Fail veya Withdrawn), KALDI (Fail; "
            "Withdrawn dışarıda) ve BIRAKTI (Withdrawn; Fail dışarıda). Dolu nokta test, içi boş nokta doğrulama "
            f"ROC AUC değeridir (hgb). Test: {e2_tr}.",
            "Additional analysis (exploratory). Three panels show three targets: reference (Fail or Withdrawn), "
            "KALDI (Fail; Withdrawn excluded) and BIRAKTI (Withdrawn; Fail excluded). The filled dot is test and "
            f"the hollow dot is validation ROC AUC (hgb). Test: {e2_en}.",
        ),
        "fig04_kural_yakalama": (
            f"ek analiz (keşifsel). İki sinyalli kuralın sınıf içi ilk %{flag} bayraklarındaki isabetler "
            "final_result'a göre ayrılır; her çubuk, o gruptaki pozitiflerin kuralca yakalanan oranıdır "
            f"(isabet / pozitif). {rule_tr}",
            f"Additional analysis (exploratory). Hits among the within-class top {flag}% flags of the two-signal "
            "rule are split by final_result; each bar is the share of positives in that group caught by the rule "
            f"(hits / positives). {rule_en}",
        ),
        "fig05_erkenlik": (
            "ek analiz (keşifsel). Sabit kohortta kesim gününe göre ROC AUC (hgb, referans hedef): düz çizgi test, "
            "kesikli çizgi doğrulama. İki çizgi arası açık renkle doldurulmuştur. "
            f"{cohort_tr} Test GENERAL: {curve('referans', 'GENERAL', 'tr')}. "
            f"Test ETKİNLİK: {curve('referans', 'ETKİNLİK', 'tr')}.",
            "Additional analysis (exploratory). ROC AUC by cutoff day in the fixed cohort (hgb, reference target): "
            "solid line is test, dashed line is validation. The area between the two lines is shaded. "
            f"{cohort_en} Test GENERAL: {curve('referans', 'GENERAL', 'en')}. "
            f"Test ACTIVITY: {curve('referans', 'ETKİNLİK', 'en')}.",
        ),
        "fig06_erkenlik_hedef": (
            "ek analiz (keşifsel). Sabit kohortta KALDI ve BIRAKTI için GENERAL ROC AUC (hgb): düz çizgi test, "
            "kesikli çizgi doğrulama. BIRAKTI: 120. günden sonra bırakanlar; erken bırakanlar bu grafikte yoktur. "
            f"{cohort_tr} Test KALDI: {curve('KALDI', 'GENERAL', 'tr')}. "
            f"Test BIRAKTI: {curve('BIRAKTI', 'GENERAL', 'tr')}.",
            "Additional analysis (exploratory). GENERAL ROC AUC for KALDI and BIRAKTI in the fixed cohort (hgb): "
            "solid line is test, dashed line is validation. BIRAKTI: students who withdrew after day 120; early "
            f"withdrawals are not in this chart. {cohort_en} Test KALDI: {curve('KALDI', 'GENERAL', 'en')}. "
            f"Test BIRAKTI: {curve('BIRAKTI', 'GENERAL', 'en')}.",
        ),
        "fig07_beklentiler": (
            "ek analiz (keşifsel). B1–B10 beklentilerinin sonuçları, ön kayıttaki karar kuralıyla: doğrulama ve "
            "testte ikisinde de sağlanırsa Tuttu, ikisinde de sağlanmazsa Tutmadı, dönemler ayrışırsa Belirsiz. "
            f"Her kartta sonuç hem renkle hem metinle yazılıdır. {listed('tr')}",
            "Additional analysis (exploratory). Results of expectations B1–B10 under the pre-registered decision "
            "rule: Held if the criterion holds in both validation and test, Did not hold if it holds in neither, "
            "Inconclusive if the periods disagree. Each card gives the result as both color and text. "
            f"{listed('en')}",
        ),
        "fig07a_beklentiler_once": (
            "ek analiz (keşifsel). B1–B10 beklentileri koşudan önce yazıldı; ön kayıt md5 ile mühürlendi "
            f"({seal_text}). Bu grafikte sonuçlar gösterilmez: her kartta '?' ve gri şerit vardır.",
            "Additional analysis (exploratory). Expectations B1–B10 were written before the run and sealed with "
            f"the pre-registration md5 ({seal_text}). Results are not shown in this chart: each card has a '?' "
            "and a gray strip.",
        ),
    }


def _merge_catalog(path: Path, entries: list[dict]) -> list[dict]:
    """Mevcut kayıtlara dokunmadan yeni kayıtları ekler; aynı dosya adı varsa onu değiştirir."""
    path = Path(path)
    existing = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    by_name = {entry["dosya"]: entry for entry in entries}
    merged = [by_name.pop(item["dosya"], item) for item in existing]
    merged.extend(by_name.values())
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return merged


def write_ek_figures(
    report_path: Path | None = None,
    dest: Path | None = None,
    md5_path: Path | None = None,
) -> list[dict]:
    """E1-E3 ve beklenti grafikleri. Veri yalnız ek_metrics.json'dan; figures.json'a eklenir.

    md5_path: fig07a alt metnindeki ön kayıt md5 değerlerinin okunduğu dosya (varsayılan docs/on_kayit_md5.txt).
    """
    report_path = EK_PATH if report_path is None else Path(report_path)
    dest = WEEK11_DIR if dest is None else Path(dest)
    report = _read_json(report_path)
    _check_titles_hold(report)
    titles = _ek_titles(report)
    alts = _ek_alts(report, _sealed_records(md5_path))
    dest.mkdir(parents=True, exist_ok=True)
    _configure_font()
    drawers = {
        "fig02_sinyal_gruplari": _draw_ek_signals,
        "fig03_hedef_ayristirma": _draw_ek_targets,
        "fig04_kural_yakalama": _draw_ek_rule,
        "fig05_erkenlik": _draw_ek_early,
        "fig06_erkenlik_hedef": _draw_ek_early_targets,
        "fig07_beklentiler": _draw_ek_expectations,
        "fig07a_beklentiler_once": _draw_ek_expectations_pending,
    }
    entries = []
    for name in EK_FIGURE_FILES:
        for index, lang in enumerate(("tr", "en")):
            fig = drawers[name](report, lang)
            if name in _CARD_FIGURES:
                _title(fig, titles[name][index], fig.title_y)  # yükseklik içerikten; boyut sabitlenmez
            else:
                _title(fig, titles[name][index])
                fig.set_size_inches(10, 5.6)
            try:
                fig.savefig(dest / f"{name}_{lang}.png", dpi=200)
            finally:
                plt.close(fig)
        entries.append(
            {
                "dosya": name,
                "başlık_tr": titles[name][0],
                "başlık_en": titles[name][1],
                "alt_tr": alts[name][0],
                "alt_en": alts[name][1],
            }
        )
    _merge_catalog(dest / "figures.json", entries)
    return entries


def print_catalog(catalog: list[dict]) -> None:
    print("figures")
    print("dosya\tbaşlık_tr\tbaşlık_en")
    for item in catalog:
        print(f"{item['dosya']}\t{item['başlık_tr']}\t{item['başlık_en']}")


def main() -> None:
    catalog = write_figures(METRICS_PATH, EXPLAIN_PATH, FIGURES_DIR)
    print_catalog(catalog)
    print(f"figures_path={FIGURES_DIR / 'figures.json'}")


def main_rule2() -> None:
    catalog = write_rule2_figures()
    print_catalog(catalog)
    print(f"figures_path={WEEK11_DIR / 'figures.json'}")


def main_ek() -> None:
    catalog = write_ek_figures()
    print_catalog(catalog)
    print(f"figures_path={WEEK11_DIR / 'figures.json'}")


def cli(argv: list[str] | None = None) -> None:
    """Bayraksız: Hafta 10. --rule2: fig01. --ek: fig02-fig07a. İkisi birlikte verilebilir."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--rule2", action="store_true", help="Hafta 11 fig01 (rule2_metrics.json)")
    parser.add_argument("--ek", action="store_true", help="Hafta 11 ek analiz grafikleri (ek_metrics.json)")
    arguments = parser.parse_args(argv)
    if not (arguments.rule2 or arguments.ek):
        main()
        return
    if arguments.rule2:
        main_rule2()
    if arguments.ek:
        main_ek()


if __name__ == "__main__":
    cli()
