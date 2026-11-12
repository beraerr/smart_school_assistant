"""Hafta 10 grafikleri. Sayılar model_metrics.json ve explain.json içinden okunur."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, NullLocator

from data_science.oulad.model import REPORT_PATH as METRICS_PATH
from data_science.oulad.model import SET_NAMES

EXPLAIN_PATH = METRICS_PATH.parent / "explain.json"
FIGURES_DIR = METRICS_PATH.parent / "figures" / "week10"

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


def _title(fig, text: str) -> None:
    fig.suptitle(text, color=NAVY, fontsize=13, x=0.02, ha="left")


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


def print_catalog(catalog: list[dict]) -> None:
    print("figures")
    print("dosya\tbaşlık_tr\tbaşlık_en")
    for item in catalog:
        print(f"{item['dosya']}\t{item['başlık_tr']}\t{item['başlık_en']}")


def main() -> None:
    catalog = write_figures(METRICS_PATH, EXPLAIN_PATH, FIGURES_DIR)
    print_catalog(catalog)
    print(f"figures_path={FIGURES_DIR / 'figures.json'}")


if __name__ == "__main__":
    main()
